#!/usr/bin/env python3
"""Minimal MCP stdio server for mednafen-pce-headless.

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


class Native:
    def __init__(self, binary, rom, base_dir, bios=None, initial_frames=1):
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
    if name == "disassemble":
        d = native.call("disasm", as_native_int(args["address"]), int(args.get("count", 16)))
        return [_text("\n".join(d["lines"]))]
    if name == "read_memory":
        d = native.call("memread", as_native_int(args["address"]), int(args["length"]), 1 if args.get("logical", True) else 0)
        return [_text(d["hex"])]
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
    binary_candidates = [script_path.with_name("mednafen-pce-headless"), script_path.parent.parent / "mednafen-pce-headless"]
    auto_binary = next((str(x) for x in binary_candidates if x.exists()), "mednafen-pce-headless")
    ap.add_argument("--binary", default=os.environ.get("MEDNAFEN_PCE_HEADLESS", auto_binary))
    ap.add_argument("--base-dir", default=os.environ.get("MEDNAFEN_HEADLESS_BASE", ".mednafen-headless"))
    ap.add_argument("--bios")
    ap.add_argument("--output-dir", default=os.environ.get("MEDNAFEN_HEADLESS_OUTPUT", "."))
    ap.add_argument("--initial-frames", type=int, default=1)
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
                        "serverInfo": {"name": "mednafen-pce-headless", "version": "1.0"},
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
