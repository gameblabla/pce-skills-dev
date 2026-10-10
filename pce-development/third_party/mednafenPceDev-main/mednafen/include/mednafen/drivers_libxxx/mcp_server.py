#!/usr/bin/env python3
"""Minimal MCP stdio server for the PCE headless frontend.

Starts one native emulator process and exposes frame execution, disassembly,
coverage, screenshots, memory reads, reset, and Y4M recording as MCP tools.
Only Python's standard library is required.
"""
import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse


def _write(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _text(s):
    return {"type": "text", "text": str(s)}


_trace_lib = pathlib.Path(__file__).resolve().parents[5] / "tools" / "pce"
sys.path.insert(0, str(_trace_lib))
from platformer_trace import BUTTON_BITS, TRACE_WINDOW_BYTES, analyze_platform_trace


_PALETTE_SNAPSHOTS = {}


def _palette_bytes(native, start_palette, palette_count):
    if not isinstance(start_palette, int) or isinstance(start_palette, bool) or not 0 <= start_palette <= 31:
        raise ValueError("start_palette must be an integer from 0 to 31")
    if not isinstance(palette_count, int) or isinstance(palette_count, bool) or not 1 <= palette_count <= 32:
        raise ValueError("palette_count must be an integer from 1 to 32")
    if start_palette + palette_count > 32:
        raise ValueError("the requested palette range must end at palette 31 or earlier")
    address = start_palette * 32
    length = palette_count * 32
    raw = bytes.fromhex(native.call("asread", "pram", address, length)["hex"])
    if len(raw) != length:
        raise RuntimeError(f"VCE PRAM returned {len(raw)} bytes; expected {length}")
    return raw


def _palette_colors(raw, start_palette):
    palettes = []
    for p in range(len(raw) // 32):
        palette_index = start_palette + p
        colors = []
        for entry in range(16):
            offset = p * 32 + entry * 2
            word = raw[offset] | (raw[offset + 1] << 8)
            colors.append({
                "entry": entry,
                "word": f"0x{word & 0x1FF:03X}",
                "channels_3bit": {
                    "red": (word >> 3) & 7,
                    "green": (word >> 6) & 7,
                    "blue": word & 7,
                },
            })
        palettes.append({
            "index": palette_index,
            "type": "background" if palette_index < 16 else "sprite",
            "colors": colors,
        })
    return palettes


class Native:
    def __init__(self, binary, rom, base_dir, bios=None, initial_frames=2):
        cmd = [binary, "--rom", rom, "--base-dir", base_dir, "--frames", str(initial_frames), "--rpc"]
        if bios:
            cmd += ["--bios", bios]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1,
        )

    def call(self, op, *args):
        if self.proc.poll() is not None:
            raise RuntimeError(f"native emulator exited with code {self.proc.returncode}")
        fields = [op] + [str(x) for x in args]
        self.proc.stdin.write("\t".join(fields) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("native emulator closed its control channel")
        data = json.loads(line)
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "native command failed"))
        return data

    def close(self):
        if self.proc.poll() is None:
            try:
                self.call("quit")
            except Exception:
                pass
            try:
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.terminate()


def tool_defs():
    return [
        {
            "name": "run_frames",
            "description": "Run the loaded PC Engine title for a number of video frames.",
            "inputSchema": {
                "type": "object",
                "properties": {"frames": {"type": "integer", "minimum": 1, "maximum": 100000}},
                "required": ["frames"],
                "additionalProperties": False,
            },
        },
        {
            "name": "run_platformer_scenario",
            "description": "Apply a deterministic PCE button script and sample a P2TR v1 platformer trace from the game's logical RAM every frame. Returns frame-addressed movement, gravity, landing, collision-geometry, sprite-offset, and camera diagnostics as text; it does not interpret pixels.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "trace_address": {"description": "Logical CPU RAM address of the first of two consecutive P2TR v1 records, obtained from the current link map/symbol table."},
                    "steps": {
                        "type": "array", "minItems": 1, "maxItems": 32,
                        "items": {
                            "type": "object",
                            "properties": {
                                "frames": {"type": "integer", "minimum": 1, "maximum": 3600},
                                "buttons": {"type": "array", "items": {"type": "string", "enum": list(BUTTON_BITS)}},
                            },
                            "required": ["frames", "buttons"], "additionalProperties": False,
                        },
                    },
                },
                "required": ["trace_address", "steps"], "additionalProperties": False,
            },
        },
        {
            "name": "disassemble",
            "description": "Disassemble HuC6280 instructions from a logical 16-bit address using the current MPR mapping.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "address": {"description": "Integer or string such as 0xE000"},
                    "count": {"type": "integer", "minimum": 1, "maximum": 512, "default": 16},
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_memory",
            "description": "Read logical or physical PCE memory without side effects.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "address": {"description": "Integer or string such as 0x2000"},
                    "length": {"type": "integer", "minimum": 1, "maximum": 65536},
                    "logical": {"type": "boolean", "default": True},
                },
                "required": ["address", "length"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_palette",
            "description": "Read PCE VCE palette RAM as 9-bit color words. Palettes 0-15 are background palettes and 16-31 are sprite palettes. Optionally save a named snapshot for a later comparison.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_palette": {"type": "integer", "minimum": 0, "maximum": 31, "default": 0},
                    "palette_count": {"type": "integer", "minimum": 1, "maximum": 32, "default": 32},
                    "snapshot": {"type": "string", "minLength": 1, "maxLength": 80},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "compare_palette",
            "description": "Compare current VCE palette RAM with a named snapshot saved by read_palette. Reports changed color words grouped by background and sprite palette.",
            "inputSchema": {
                "type": "object",
                "properties": {"snapshot": {"type": "string", "minLength": 1, "maxLength": 80}},
                "required": ["snapshot"],
                "additionalProperties": False,
            },
        },
        {
            "name": "take_screenshot",
            "description": "Capture the most recently rendered frame as PNG and return it as MCP image content.",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Optional output PNG path."}},
                "additionalProperties": False,
            },
        },
        {
            "name": "coverage_clear",
            "description": "Clear HuC6280 logical-PC execution counters.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "coverage_dump",
            "description": "Write logical-PC execution coverage as JSON.",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Optional JSON output path."}},
                "additionalProperties": False,
            },
        },
        {
            "name": "start_y4m_recording",
            "description": "Start YUV4MPEG2 C444 recording. Subsequent run_frames calls append video frames.",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "name": "stop_y4m_recording",
            "description": "Stop and flush the active Y4M recording.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "reset",
            "description": "Reset the emulated PC Engine.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "status",
            "description": "Return frame count, coverage counters, recording state, and current display rectangle.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def as_native_int(v):
    if isinstance(v, int):
        return hex(v)
    return str(v)


def handle_tool(native, name, args, output_dir):
    args = args or {}
    if name == "run_frames":
        d = native.call("run", int(args["frames"]))
        return [_text(f"frame={d['frame']}")]
    if name == "run_platformer_scenario":
        try:
            address = int(str(args["trace_address"]), 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("trace_address must be an integer or 0x-prefixed address") from exc
        if address > 0xFFFF and address >> 16 == 0xF8:
            address &= 0xFFFF
        if address < 0x2000 or address + TRACE_WINDOW_BYTES > 0x4000:
            raise ValueError(f"two P2TR v1 records must fit completely in PCE main RAM ($2000-$3FFF); got 0x{address:04X}")
        steps = args["steps"]
        if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
            raise ValueError("steps must contain 1-32 input segments")
        if sum(int(step.get("frames", 0)) for step in steps) > 3600:
            raise ValueError("a platformer scenario is limited to 3600 frames")
        samples = []
        held = []
        for step in steps:
            frames = int(step.get("frames", 0))
            buttons = [str(button).lower() for button in step.get("buttons", [])]
            if not 1 <= frames <= 3600:
                raise ValueError("each step must run 1-3600 frames")
            if any(button not in BUTTON_BITS for button in buttons):
                raise ValueError("buttons must be PCE names: i, ii, select, run, up, right, down, left, iii, iv, v, vi")
            if len(set(buttons)) != len(buttons):
                raise ValueError("button names must be unique within a step")
            mask = sum(1 << BUTTON_BITS[button] for button in buttons)
            start = len(samples)
            native.call("input", mask)
            batch = native.call("trace_frames", hex(address), TRACE_WINDOW_BYTES, frames)["samples"]
            held.append((start, start + len(batch) - 1, buttons))
            samples.extend(batch)
        report = analyze_platform_trace(samples, held)
        report["input_script"] = [{"frames": int(step["frames"]), "buttons": [str(b).lower() for b in step.get("buttons", [])]} for step in steps]
        report["trace_address"] = f"0x{address:04X}"
        return [_text(json.dumps(report, separators=(",", ":")))]
    if name == "disassemble":
        d = native.call("disasm", as_native_int(args["address"]), int(args.get("count", 16)))
        return [_text("\n".join(d["lines"]))]
    if name == "read_memory":
        d = native.call("memread", as_native_int(args["address"]), int(args["length"]), 1 if args.get("logical", True) else 0)
        return [_text(d["hex"])]
    if name == "read_palette":
        start = args.get("start_palette", 0)
        count = args.get("palette_count", 32)
        raw = _palette_bytes(native, start, count)
        label = args.get("snapshot")
        if label is not None:
            if not isinstance(label, str) or not label.strip() or len(label) > 80:
                raise ValueError("snapshot must be a non-empty label of at most 80 characters")
            _PALETTE_SNAPSHOTS[label] = (start, count, raw)
        report = {
            "source": "VCE PRAM",
            "encoding": "little-endian 9-bit PCE color word; bits 0-2 blue, 3-5 red, 6-8 green",
            "start_palette": start,
            "palette_count": count,
            "snapshot": label,
            "palettes": _palette_colors(raw, start),
        }
        return [_text(json.dumps(report, separators=(",", ":")))]
    if name == "compare_palette":
        label = args.get("snapshot")
        if label not in _PALETTE_SNAPSHOTS:
            raise ValueError(f"unknown palette snapshot: {label!r}")
        start, count, before = _PALETTE_SNAPSHOTS[label]
        after = _palette_bytes(native, start, count)
        changes = []
        by_type = {"background": 0, "sprite": 0}
        for palette_offset in range(count):
            palette_index = start + palette_offset
            palette_type = "background" if palette_index < 16 else "sprite"
            for entry in range(16):
                offset = palette_offset * 32 + entry * 2
                old = (before[offset] | (before[offset + 1] << 8)) & 0x1FF
                new = (after[offset] | (after[offset + 1] << 8)) & 0x1FF
                if old != new:
                    by_type[palette_type] += 1
                    changes.append({
                        "palette": palette_index,
                        "type": palette_type,
                        "entry": entry,
                        "before": f"0x{old:03X}",
                        "after": f"0x{new:03X}",
                    })
        report = {
            "source": "VCE PRAM",
            "snapshot": label,
            "start_palette": start,
            "palette_count": count,
            "changed_colors": len(changes),
            "changed_background_colors": by_type["background"],
            "changed_sprite_colors": by_type["sprite"],
            "changes": changes,
        }
        return [_text(json.dumps(report, separators=(",", ":")))]
    if name == "take_screenshot":
        path = args.get("path") or str(pathlib.Path(output_dir) / "mcp-screenshot.png")
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        d = native.call("screenshot", urllib.parse.quote(path, safe="/._-"))
        raw = pathlib.Path(d["path"]).read_bytes()
        return [_text(d["path"]), {"type": "image", "data": base64.b64encode(raw).decode("ascii"), "mimeType": "image/png"}]
    if name == "coverage_clear":
        native.call("cov_clear")
        return [_text("coverage cleared")]
    if name == "coverage_dump":
        path = args.get("path") or str(pathlib.Path(output_dir) / "coverage.json")
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        d = native.call("cov_dump", urllib.parse.quote(path, safe="/._-"))
        return [_text(json.dumps({"path": d["path"], "unique_pcs": d["unique_pcs"], "instructions": d["instructions"]}))]
    if name == "start_y4m_recording":
        path = args["path"]
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        d = native.call("record_start", urllib.parse.quote(path, safe="/._-"))
        return [_text(f"recording {d['path']}")]
    if name == "stop_y4m_recording":
        native.call("record_stop")
        return [_text("recording stopped")]
    if name == "reset":
        native.call("reset")
        return [_text("reset")]
    if name == "status":
        return [_text(json.dumps(native.call("status"), separators=(",", ":")))]
    raise ValueError(f"unknown tool: {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    script_path = pathlib.Path(__file__).resolve()
    binary_candidates = [script_path.parents[3] / "pce-headless", script_path.parent / "pce-headless"]
    auto_binary = next((str(x) for x in binary_candidates if x.exists()), "pce-headless")
    ap.add_argument("--binary", default=os.environ.get("PCE_HEADLESS", auto_binary))
    ap.add_argument("--base-dir", default=os.environ.get("PCE_HEADLESS_BASE_DIR", ".pce-headless"))
    ap.add_argument("--bios")
    ap.add_argument("--output-dir", default=os.environ.get("PCE_HEADLESS_OUTPUT_DIR", "."))
    ap.add_argument("--initial-frames", type=int, default=2)
    ns = ap.parse_args()

    pathlib.Path(ns.base_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(ns.output_dir).mkdir(parents=True, exist_ok=True)
    native = Native(ns.binary, ns.rom, ns.base_dir, ns.bios, ns.initial_frames)
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            req = None
            try:
                req = json.loads(line)
                method = req.get("method")
                rid = req.get("id")
                if method == "initialize":
                    requested = (req.get("params") or {}).get("protocolVersion", "2025-03-26")
                    result = {
                        "protocolVersion": requested,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "pce-headless", "version": "1.0"},
                    }
                    _write({"jsonrpc": "2.0", "id": rid, "result": result})
                elif method == "notifications/initialized":
                    continue
                elif method == "ping":
                    _write({"jsonrpc": "2.0", "id": rid, "result": {}})
                elif method == "tools/list":
                    _write({"jsonrpc": "2.0", "id": rid, "result": {"tools": tool_defs()}})
                elif method == "tools/call":
                    p = req.get("params") or {}
                    content = handle_tool(native, p.get("name"), p.get("arguments") or {}, ns.output_dir)
                    _write({"jsonrpc": "2.0", "id": rid, "result": {"content": content, "isError": False}})
                elif rid is not None:
                    _write({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found"}})
            except Exception as e:
                rid = req.get("id") if isinstance(req, dict) else None
                if rid is not None:
                    _write({"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)}})
    finally:
        native.close()


if __name__ == "__main__":
    main()
