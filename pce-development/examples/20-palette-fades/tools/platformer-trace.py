#!/usr/bin/env python3
"""P2TR v1 trace decoding, diagnostics, and deterministic PCE input runner."""
import argparse
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse

BUTTON_BITS = {
    "i": 0, "ii": 1, "select": 2, "run": 3,
    "up": 4, "right": 5, "down": 6, "left": 7,
    "iii": 8, "iv": 9, "v": 10, "vi": 11,
}
EVENT_BITS = {
    "landed": 0, "jumped": 1, "stomped": 2,
    "died": 3, "respawned": 4, "goal": 5,
}
TRACE_HEADER = struct.Struct("<4s8BI2H13i")
TRACE_SURFACE = struct.Struct("<HBB8i")
TRACE_BYTES = TRACE_HEADER.size + 4 * TRACE_SURFACE.size
TRACE_WINDOW_BYTES = 2 * TRACE_BYTES


def _q8(raw):
    return round(raw / 256.0, 3)


def decode_platform_trace(raw):
    """Decode the stable little-endian P2TR v1 record from target RAM."""
    if len(raw) != TRACE_BYTES:
        raise ValueError(f"P2TR v1 record must be {TRACE_BYTES} bytes, got {len(raw)}")
    h = TRACE_HEADER.unpack_from(raw)
    if h[0] != b"P2TR" or h[1] != 1:
        raise ValueError(f"invalid P2TR record signature/version: {h[0]!r}/{h[1]}")
    if h[11] & 1:
        raise ValueError("P2TR publication sequence is odd; the RAM record is incomplete")
    vals = h[12:]
    result = {
        "frame": h[9], "scene": h[2], "player_flags": h[3], "event_flags": h[4],
        "surface_count": min(h[5], 4), "sat_first": h[6], "sat_piece_count": h[7],
        "palette": h[8], "buttons": h[10], "camera_x": _q8(vals[0]),
        "player_x": _q8(vals[1]), "player_y": _q8(vals[2]),
        "vx": _q8(vals[3]), "vy": _q8(vals[4]),
        "player_w": _q8(vals[5]), "player_h": _q8(vals[6]),
        "sprite_dx": _q8(vals[7]), "sprite_dy": _q8(vals[8]),
        "sprite_w": _q8(vals[9]), "sprite_h": _q8(vals[10]),
        "draw_x": _q8(vals[11]), "draw_y": _q8(vals[12]), "surfaces": [],
    }
    base = TRACE_HEADER.size
    for i in range(result["surface_count"]):
        surf = TRACE_SURFACE.unpack_from(raw, base + i * TRACE_SURFACE.size)
        values = [_q8(v) for v in surf[3:]]
        result["surfaces"].append({
            "id": surf[0], "flags": surf[1],
            "collision": values[:4], "visual": values[4:],
        })
    return result


def analyze_platform_trace(samples, held_buttons):
    """Return short, frame-addressed evidence rather than a wall of RAM bytes."""
    issues = []

    def issue(frame, kind, detail):
        for item in issues:
            if item["kind"] == kind and item["detail"] == detail:
                item["last_frame"] = frame
                item["samples"] += 1
                return
        issues.append({"frame": frame, "last_frame": frame, "samples": 1,
                       "kind": kind, "detail": detail})

    decoded = [decode_platform_trace(bytes.fromhex(sample["hex"])) for sample in samples]
    for sample, state in zip(samples, decoded):
        state["emulator_frame"] = sample.get("frame")
    play = [s for s in decoded if s["scene"] == 1 and not (s["player_flags"] & 0x02)]
    active_scene = [s for s in decoded if s["scene"] == 1]
    for current in play:
        if current["surface_count"] == 0:
            issue(current["frame"], "surface_geometry_unavailable",
                  "active gameplay sample publishes no collidable surfaces; landing and support geometry cannot be verified from this trace")
    for previous, current in zip(play, play[1:]):
        if current["frame"] != previous["frame"] + 1:
            delta = current["frame"] - previous["frame"]
            sample_pair = (f" between emulator samples {previous['emulator_frame']} and "
                           f"{current['emulator_frame']}" if previous["emulator_frame"] is not None
                           and current["emulator_frame"] is not None else " between trace samples")
            issue(current["frame"], "game_frame_cadence",
                  f"P2TR game_frame changed by {delta}{sample_pair}; check VBlank sampling and the game's frame publisher before attributing this to physics")
        bottom0 = previous["player_y"] + previous["player_h"]
        bottom1 = current["player_y"] + current["player_h"]
        for surface in current["surfaces"]:
            if (surface["flags"] & 0x03) != 0x03:
                continue
            left, top, width, height = surface["collision"]
            overlaps = current["player_x"] + current["player_w"] > left and current["player_x"] < left + width
            crossed_down = previous["vy"] >= 0 and bottom0 <= top and bottom1 >= top
            if overlaps and crossed_down and not (current["event_flags"] & 0x01) and not (current["player_flags"] & 0x01):
                issue(current["frame"], "missed_landing", f"feet crossed platform {surface['id']} top at y={top} while descending; no landed event or grounded flag")
            visual_top = surface["visual"][1]
            if abs(visual_top - top) > 1.0:
                issue(current["frame"], "platform_art_collision_mismatch", f"platform {surface['id']} art top differs from collision top by {round(visual_top - top, 2)} px")
        if current["player_flags"] & 0x01:
            supported = any(
                (surface["flags"] & 0x03) == 0x03
                and current["player_x"] + current["player_w"] > surface["collision"][0]
                and current["player_x"] < surface["collision"][0] + surface["collision"][2]
                and abs((current["player_y"] + current["player_h"]) - surface["collision"][1]) <= 1.0
                for surface in current["surfaces"]
            )
            if current["surface_count"] and not supported:
                issue(current["frame"], "unsupported_grounded", "grounded flag is set but no traced collidable surface supports the feet")
        expected_draw_x = current["player_x"] + current["sprite_dx"] - current["camera_x"]
        if abs(current["draw_x"] - expected_draw_x) > 1.0:
            issue(current["frame"], "camera_or_sprite_x_mismatch", f"submitted player screen x differs from world x minus camera and sprite offset by {round(current['draw_x'] - expected_draw_x, 2)} px")
        expected_draw_y = current["player_y"] + current["sprite_dy"]
        if abs(current["draw_y"] - expected_draw_y) > 1.0:
            issue(current["frame"], "sprite_y_mismatch", f"submitted player screen y differs from collision position plus sprite offset by {round(current['draw_y'] - expected_draw_y, 2)} px")
    stuck_y = 0
    for previous, current in zip(play, play[1:]):
        airborne = not (previous["player_flags"] & 0x01) and not (current["player_flags"] & 0x01)
        if airborne and abs(current["vy"]) >= 0.25 and abs(current["player_y"] - previous["player_y"]) < 1 / 256:
            stuck_y += 1
            if stuck_y == 3:
                issue(current["frame"], "vertical_position_stalled", "airborne vertical velocity is nonzero but y did not advance for three frames")
        else:
            stuck_y = 0
        if current["sat_piece_count"] > 1 and current["sat_first"] + current["sat_piece_count"] > 64:
            issue(current["frame"], "sat_range_invalid", "player metasprite SAT range exceeds 64 entries")

    for current in active_scene:
        if current["event_flags"] & (1 << EVENT_BITS["landed"]):
            if not (current["player_flags"] & 0x01):
                issue(current["frame"], "landing_state_mismatch", "landed event is set but grounded is clear")
            if current["vy"] > 1 / 256:
                issue(current["frame"], "landing_velocity_not_reset", "landed event is set but downward velocity is still positive")
            if current["surface_count"] == 0:
                issue(current["frame"], "landing_support_unverified",
                      "landed event is set but no collidable surface is published to verify the support")
    for previous, current in zip(active_scene, active_scene[1:]):
        if current["frame"] != previous["frame"] + 1:
            continue
        repeated = current["event_flags"] & previous["event_flags"]
        for name, bit in EVENT_BITS.items():
            if repeated & (1 << bit):
                issue(current["frame"], "repeated_event_flag",
                      f"{name} event flag is set on consecutive game frames; publish transition events as one-frame pulses")

    if len(play) >= 30:
        still = play[-30:]
        if all(not (s["player_flags"] & 0x01) for s in still):
            if all(abs(s["player_y"] - still[0]["player_y"]) < 1 / 256 for s in still) and all(abs(s["vy"]) < 1 / 256 for s in still):
                issue(still[-1]["frame"], "gravity_stalled", "airborne player y and vertical velocity stayed unchanged at zero for 30 consecutive frames")
    for start, end, buttons in held_buttons:
        if "right" in buttons or "left" in buttons:
            segment = [s for s in play[start:end + 1]]
            if len(segment) >= 2 and segment[0]["player_x"] == segment[-1]["player_x"] and not any(s["player_flags"] & 0x08 for s in segment):
                direction = "right" if "right" in buttons else "left"
                issue(segment[-1]["frame"], "movement_stalled", f"{direction} held for {len(segment)} traced frames but world x did not change and no horizontal collision was reported")

    if not decoded:
        return {"samples": 0, "issues": [], "note": "No frames were captured."}
    selected = sorted(set([0, len(decoded) - 1] + [round(i * (len(decoded) - 1) / 7) for i in range(1, 7)]))
    points = []
    for i in selected:
        s = decoded[i]
        points.append({k: s[k] for k in ("frame", "emulator_frame", "scene", "player_x", "player_y", "vx", "vy", "camera_x", "draw_x", "draw_y", "player_flags", "event_flags", "buttons")})
    vertical = [s for s in play if not (s["player_flags"] & 0x01)]
    accelerations = [round(b["vy"] - a["vy"], 3) for a, b in zip(vertical, vertical[1:])
                     if b["frame"] == a["frame"] + 1]
    segment_summaries = []
    for start, end, buttons in held_buttons:
        segment = decoded[start:end + 1]
        if segment:
            expected_mask = sum(1 << BUTTON_BITS[name] for name in buttons)
            first_match = next((i for i, s in enumerate(segment)
                                if s["buttons"] == expected_mask), None)
            segment_summaries.append({
                "frames": [segment[0]["frame"], segment[-1]["frame"]],
                "buttons": buttons,
                "observed_buttons_start_end": [segment[0]["buttons"], segment[-1]["buttons"]],
                "input_latch_delay_samples": first_match if first_match is not None else len(segment),
                "world_x": [segment[0]["player_x"], segment[-1]["player_x"]],
                "dx": round(segment[-1]["player_x"] - segment[0]["player_x"], 3),
                "vx_start_end": [segment[0]["vx"], segment[-1]["vx"]],
                "grounded_start_end": [bool(segment[0]["player_flags"] & 1), bool(segment[-1]["player_flags"] & 1)],
            })
    event_samples = []
    for s in decoded:
        names = [name for name, bit in EVENT_BITS.items() if s["event_flags"] & (1 << bit)]
        if names:
            feet = s["player_y"] + s["player_h"]
            supports = [surface["id"] for surface in s["surfaces"]
                        if (surface["flags"] & 0x03) == 0x03
                        and s["player_x"] + s["player_w"] > surface["collision"][0]
                        and s["player_x"] < surface["collision"][0] + surface["collision"][2]
                        and abs(feet - surface["collision"][1]) <= 1.0]
            event_samples.append({
                "frame": s["frame"], "events": names,
                "player_x": s["player_x"], "player_y": s["player_y"],
                "feet_y": round(feet, 3), "vy": s["vy"],
                "grounded": bool(s["player_flags"] & 1),
                "support_surface_ids": supports,
            })
    return {
        "trace_format": "P2TR v1", "samples": len(decoded),
        "frame_range": [decoded[0]["frame"], decoded[-1]["frame"]],
        "emulator_frame_range": ([decoded[0]["emulator_frame"], decoded[-1]["emulator_frame"]]
                                  if decoded[0]["emulator_frame"] is not None
                                  and decoded[-1]["emulator_frame"] is not None else None),
        "issues": issues, "trajectory_samples": points,
        "held_input_segments": segment_summaries, "event_samples": event_samples,
        "airborne_velocity": ({
            "frames": [vertical[0]["frame"], vertical[-1]["frame"]],
            "vy_start_min_max_end": [vertical[0]["vy"], min(s["vy"] for s in vertical),
                                      max(s["vy"] for s in vertical), vertical[-1]["vy"]],
            "observed_dvy_min_max": [min(accelerations), max(accelerations)] if accelerations else None,
        } if vertical else None),
        "evidence_limit": "Trace values are authored by the game. Compare them with source and collision/map data; they do not independently prove pixel output or physical hardware behavior.",
    }


class NativeControl:
    def __init__(self, binary, rom, base_dir, bios=None, initial_frames=2):
        command = [binary, "--rom", str(rom), "--base-dir", str(base_dir),
                   "--frames", str(initial_frames), "--rpc"]
        if bios:
            command.extend(["--bios", str(bios)])
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=sys.stderr,
                                        text=True, bufsize=1)

    def call(self, op, *args):
        if self.process.poll() is not None:
            raise RuntimeError(f"headless process exited with code {self.process.returncode}")
        self.process.stdin.write("\t".join([op] + [str(a) for a in args]) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("headless control channel closed")
        result = json.loads(line)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "headless command failed"))
        return result

    def close(self):
        if self.process.poll() is None:
            try:
                self.call("quit")
            except Exception:
                self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()


def _find_binary(rom):
    configured = os.environ.get("PCE_HEADLESS")
    if configured:
        return pathlib.Path(configured).expanduser().resolve()
    roots = [pathlib.Path.cwd(), pathlib.Path(rom).expanduser().resolve().parent,
             pathlib.Path(__file__).resolve().parent]
    directories = []
    for root in roots:
        directories.extend(directory for directory in (root, *root.parents)
                           if directory not in directories)
    # Prefer the bundled RPC build because it exposes the scripted input and
    # trace commands this tool needs. Only then fall back to a workspace build.
    for directory in directories:
        third_party_roots = (
            directory / "third_party",
            directory / "pce-development" / "third_party",
            directory / ".opencode" / "skills" / "pce-development" / "third_party",
        )
        for third_party in third_party_roots:
            for candidate in third_party.glob("*/pce-headless") if third_party.is_dir() else ():
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate
    for directory in directories:
        candidates = (directory / "PCE" / "pce-headless",)
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
        for candidate in (directory / "PCE").glob("*headless*") if (directory / "PCE").is_dir() else ():
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
    raise RuntimeError("No configured PCE headless executable found; set PCE_HEADLESS or use the project's make run/debug setup.")


def resolve_trace_address(elf, symbol="pce_platformer_trace", nm=None):
    candidates = []
    if nm:
        candidates.append(nm)
    if os.environ.get("PCE_TRACE_NM"):
        candidates.append(os.environ["PCE_TRACE_NM"])
    if os.environ.get("LLVM_MOS_BIN_DIR"):
        candidates.extend([str(pathlib.Path(os.environ["LLVM_MOS_BIN_DIR"]) / name)
                           for name in ("mos-pce-nm", "llvm-nm")])
    candidates.extend([shutil.which("mos-pce-nm"), shutil.which("llvm-nm")])
    tool = next((candidate for candidate in candidates if candidate and
                 (pathlib.Path(candidate).is_file() or shutil.which(candidate))), None)
    if not tool:
        raise RuntimeError("No LLVM-MOS symbol reader found; pass PCE_PLATFORM_TRACE_ADDRESS from the current map.")
    result = subprocess.run([tool, "--defined-only", str(elf)], check=True,
                            capture_output=True, text=True)
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*(?:0x)?([0-9a-fA-F]+)\s+\S\s+(.+?)\s*$", line)
        if match and match.group(2).split()[-1] == symbol:
            address = int(match.group(1), 16)
            # LLVM-MOS represents main RAM as bank F8 plus its PCE CPU address.
            if address > 0xFFFF and address >> 16 == 0xF8:
                address &= 0xFFFF
            return address
    raise RuntimeError(f"symbol {symbol!r} not found in {elf}; build the current debug image and inspect its map")


def run_scenario(rom, address, steps, bios=None, base_dir=None, initial_frames=2):
    if address < 0x2000 or address + TRACE_WINDOW_BYTES > 0x4000:
        raise ValueError(f"two P2TR v1 records must fit completely in PCE main RAM ($2000-$3FFF); got 0x{address:04X}")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise ValueError("scenario must contain 1-32 input segments")
    if sum(int(step.get("frames", 0)) for step in steps) > 3600:
        raise ValueError("scenario is limited to 3600 total frames")
    binary = _find_binary(rom)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError("configured PCE_HEADLESS is not an executable file")
    base_dir = pathlib.Path(base_dir or pathlib.Path("build") / "platformer-trace-base").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    native = NativeControl(str(binary), rom, base_dir, bios, initial_frames)
    samples, held = [], []
    try:
        for step in steps:
            frames = int(step.get("frames", 0))
            buttons = [str(button).lower() for button in step.get("buttons", [])]
            if not 1 <= frames <= 3600:
                raise ValueError("each step must run 1-3600 frames")
            if any(button not in BUTTON_BITS for button in buttons):
                raise ValueError("unknown PCE button name")
            if len(set(buttons)) != len(buttons):
                raise ValueError("button names must be unique within a step")
            mask = sum(1 << BUTTON_BITS[button] for button in buttons)
            start = len(samples)
            native.call("input", mask)
            batch = native.call("trace_frames", hex(address), TRACE_WINDOW_BYTES, frames)["samples"]
            held.append((start, start + len(batch) - 1, buttons))
            samples.extend(batch)
    finally:
        native.close()
    report = analyze_platform_trace(samples, held)
    report["input_script"] = [{"frames": int(s["frames"]), "buttons": [str(b).lower() for b in s.get("buttons", [])]} for s in steps]
    report["trace_address"] = f"0x{address:04X}"
    report["binary_selected"] = "configured PCE_HEADLESS"
    return report


def main():
    parser = argparse.ArgumentParser(description="Run scripted PCE inputs and summarize a P2TR v1 platformer trace.")
    parser.add_argument("--rom", required=True, help="current built ROM or packaged disc image")
    parser.add_argument("--address", help="optional P2TR main-RAM address from the current link map")
    parser.add_argument("--elf", help="symbol-bearing ELF output; defaults to ROM path plus .elf")
    parser.add_argument("--symbol", default="pce_platformer_trace")
    parser.add_argument("--nm", help="optional LLVM-MOS nm tool path")
    parser.add_argument("--scenario", default="tools/platformer-scenario.example.json", help="JSON list of {frames, buttons} segments")
    parser.add_argument("--bios", default=os.environ.get("PCE_SYSTEM_CARD_BIOS"))
    parser.add_argument("--base-dir", default="build/platformer-trace-base")
    parser.add_argument("--output", help="optional path to save the JSON report")
    parser.add_argument("--initial-frames", type=int, default=2)
    args = parser.parse_args()
    try:
        elf = args.elf or (args.rom + ".elf")
        address = int(args.address, 0) if args.address else resolve_trace_address(elf, args.symbol, args.nm)
        if address > 0xFFFF and address >> 16 == 0xF8:
            address &= 0xFFFF
        steps = json.loads(pathlib.Path(args.scenario).read_text())
        report = run_scenario(args.rom, address, steps, args.bios, args.base_dir, args.initial_frames)
        rendered = json.dumps(report, indent=2)
        if args.output:
            pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(args.output).write_text(rendered + "\n")
        print(rendered)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
