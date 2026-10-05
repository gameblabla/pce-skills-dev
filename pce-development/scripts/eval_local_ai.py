#!/usr/bin/env python3
"""Paired baseline/skill-assisted evaluation for the local OpenAI-compatible API."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
CASES_PATH = HERE / "eval_cases.json"
SYSTEM_PROMPT = (
    "You are answering a PC Engine CD engineering question. LLVM-MOS is the "
    "only supported compiler/assembler toolchain; HuC6280 refers to the target "
    "CPU hardware and instruction set. Use the supplied "
    "project evidence. Distinguish facts from inference, give a concrete "
    "answer, and do not claim tests or hardware checks that were not performed. "
    "Do not do arithmetic mentally, including approximate comparisons/ranges: "
    "rely on supplied Python calculator output, or state that the Python tool "
    "must be run before giving any computed number. Do not invent numeric values "
    "or example measurements, limits, burst sizes, pixel offsets, or sample values "
    "when source/Python output is absent. For a vague visual position request without calculation output, "
    "state only the qualitative direction; do not give a pixel count, range, "
    "example value, or new numeric coordinates. This evaluation endpoint has no "
    "shell/Python tool: give a symbolic helper expression, never a numeric example. "
    "When a Python result is supplied, report it without repeating or re-evaluating its input expression. "
    "Keep the answer under 220 words."
)


def http_json(url: str, *, body: dict | None = None, timeout: int = 300) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail[:1200]}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach {url}: {error.reason}") from error


def discover_model(base_url: str, timeout: int) -> str:
    data = http_json(f"{base_url}/v1/models", timeout=timeout)
    rows = data.get("data") or data.get("models") or []
    if not rows:
        raise RuntimeError("/v1/models returned no models; pass --model explicitly")
    row = rows[0]
    model = row.get("id") or row.get("model") or row.get("name")
    if not model:
        raise RuntimeError("Could not find a model id in /v1/models response")
    return model


def load_cases(path: Path) -> list[dict]:
    path = path.resolve()
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise RuntimeError(f"No evaluation cases in {path}")
    for case in cases:
        for field in ("id", "question", "context", "references", "checks"):
            if field not in case:
                raise RuntimeError(f"Case missing {field}: {case!r}")
        for check in case["checks"]:
            if not any(key in check for key in ("regex", "forbidden", "not_regex", "all_terms", "any_groups")):
                raise RuntimeError(f"Check needs a regex or forbidden terms: {check!r}")
        if "image" in case:
            image_path = (path.parent / case["image"]).resolve()
            if not image_path.is_file():
                raise RuntimeError(f"Missing eval image for {case['id']}: {image_path}")
            case["_image_path"] = str(image_path)
        if "calculation" in case:
            case["_calculation_output"] = run_python_calculation(case["calculation"])
        if "bank_report" in case:
            report = (path.parent / case["bank_report"]).resolve()
            if not report.is_relative_to(path.parent.resolve()):
                raise RuntimeError(f"Bank report escapes the eval directory: {case['bank_report']}")
            if not report.is_file():
                raise RuntimeError(f"Missing bank-report fixture for {case['id']}: {report}")
            case["_bank_output"] = run_python_bank_report(
                report, int(case.get("bank_needed", 0))
            )
    return cases


def run_python_calculation(expression: str) -> str:
    result = subprocess.run(
        [sys.executable, str(HERE / "calc.py"), expression],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Python calculation failed for {expression!r}: {result.stderr.strip()}")
    return result.stdout.strip()


def run_python_bank_report(report: Path, needed: int) -> str:
    result = subprocess.run(
        [sys.executable, str(HERE / "bank_space.py"), str(report), "--needed", str(needed), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Python bank report failed for {report}: {result.stderr.strip()}")
    return result.stdout.strip()


def load_skill_context(skill_dir: Path, case: dict) -> str:
    parts = [
        "Apply the following OpenCode skill and the relevant supporting guide(s).",
        (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
    ]
    for relative in case["references"]:
        path = (skill_dir / relative).resolve()
        if not path.is_relative_to(skill_dir.resolve()):
            raise RuntimeError(f"Reference escapes the skill directory: {relative}")
        if not path.is_file():
            raise RuntimeError(f"Missing skill reference: {relative}")
        parts.append(f"\n--- Supporting guide: {relative} ---\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def score_answer(text: str, checks: list[dict]) -> dict:
    results = []
    folded_text = text.casefold()
    for check in checks:
        if "all_terms" in check or "any_groups" in check:
            matched = all(term.casefold() in folded_text for term in check.get("all_terms", []))
            matched = matched and all(
                any(term.casefold() in folded_text for term in group)
                for group in check.get("any_groups", [])
            )
        elif "regex" in check:
            matched = re.search(check["regex"], text, flags=re.IGNORECASE | re.DOTALL) is not None
        elif "not_regex" in check:
            matched = re.search(check["not_regex"], text, flags=re.IGNORECASE | re.DOTALL) is None
        else:
            matched = all(
                re.search(re.escape(term), text, flags=re.IGNORECASE) is None
                for term in check.get("forbidden", [])
            )
        results.append({"id": check["id"], "matched": matched})
    passed = sum(row["matched"] for row in results)
    return {
        "heuristic_score": round(100 * passed / max(1, len(results))),
        "checks_passed": passed,
        "checks_total": len(results),
        "checks": results,
        "score_note": "Lexical coverage is only a triage signal; review the raw answer for meaning and correctness.",
    }


def ask_model(
    base_url: str,
    model: str,
    skill_dir: Path,
    case: dict,
    mode: str,
    *,
    timeout: int,
    max_tokens: int,
    thinking: str,
) -> dict:
    context = case["context"]
    if "_calculation_output" in case:
        context += (
            "\n\nPython calculation output from scripts/calc.py:\n"
            + case["_calculation_output"]
        )
    if "_bank_output" in case:
        context += (
            "\n\nPython bank_space.py capacity-only output:\n"
            + case["_bank_output"]
        )
    question = (
        f"Project evidence:\n{context}\n\n"
        f"Task:\n{case['question']}"
    )
    if mode == "skill":
        question = f"{load_skill_context(skill_dir, case)}\n\n--- Evaluation task ---\n{question}"
    user_content: str | list[dict] = question
    image_path = case.get("_image_path")
    if image_path:
        path = Path(image_path)
        mime_type = mimetypes.guess_type(path.name)[0]
        if not mime_type or not mime_type.startswith("image/"):
            raise RuntimeError(f"Unsupported eval image type: {path}")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        user_content = [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
        ]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if thinking == "off":
        # llama.cpp passes this through to Qwen-style chat templates. Without
        # it, some reasoning models spend the whole output budget on hidden
        # reasoning and return no user-visible answer.
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    response = http_json(f"{base_url}/v1/chat/completions", body=payload, timeout=timeout)
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError(f"No completion returned for {case['id']} ({mode})")
    message = choices[0].get("message") or {}
    text = message.get("content") or ""
    if isinstance(text, list):
        text = "\n".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in text
        )
    if not text.strip():
        raise RuntimeError(
            f"Empty user-visible answer for {case['id']} ({mode}); "
            f"finish_reason={choices[0].get('finish_reason')!r}. "
            "Try --thinking off (the default) and a larger --max-tokens value."
        )
    if choices[0].get("finish_reason") == "length":
        raise RuntimeError(
            f"Truncated answer for {case['id']} ({mode}); increase --max-tokens."
        )
    return {
        "mode": mode,
        "answer": text,
        "finish_reason": choices[0].get("finish_reason"),
        **score_answer(text, case["checks"]),
    }


def parse_args() -> argparse.Namespace:
    default_output = Path(tempfile.gettempdir()) / (
        "pce-ai-eval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LOCAL_AI_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        help="OpenAI-compatible local server (default: %(default)s; use loopback for a 0.0.0.0 bind)",
    )
    parser.add_argument("--model", default=os.environ.get("LOCAL_AI_MODEL"), help="Model id; defaults to first /v1/models entry")
    parser.add_argument("--cases", type=Path, default=CASES_PATH, help="Evaluation case JSON")
    parser.add_argument("--skill-dir", type=Path, default=SKILL_DIR, help="OpenCode skill directory to test")
    parser.add_argument("--mode", choices=("both", "baseline", "skill"), default="both")
    parser.add_argument("--case", action="append", dest="case_ids", help="Run only this case id; can be repeated")
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases")
    parser.add_argument("--repeats", type=int, default=1, help="Repeat each selected case pair to reduce sampling noise (default: %(default)s)")
    parser.add_argument("--workers", type=int, default=1, help="Parallel case pairs (default: %(default)s)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-request timeout in seconds")
    parser.add_argument("--max-tokens", type=int, default=700, help="Maximum generated tokens per answer")
    parser.add_argument(
        "--thinking", choices=("off", "on"), default="off",
        help="Disable Qwen-style hidden reasoning so the output budget measures the visible answer (default: %(default)s)",
    )
    parser.add_argument("--output", type=Path, default=default_output, help="JSON report path (default is under /tmp)")
    return parser.parse_args()


def run_case_pair(args: argparse.Namespace, base_url: str, model: str, case: dict, repeat: int) -> dict:
    modes = ("baseline", "skill") if args.mode == "both" else (args.mode,)
    result = {
        "id": case["id"],
        "repeat": repeat,
        "question": case["question"],
        "has_image": "_image_path" in case,
        "has_bank_report": "_bank_output" in case,
        "runs": {},
    }
    for mode in modes:
        print(f"[{case['id']} #{repeat}] {mode}", flush=True)
        result["runs"][mode] = ask_model(
            base_url, model, args.skill_dir, case, mode, timeout=args.timeout,
            max_tokens=args.max_tokens, thinking=args.thinking
        )
    baseline = result["runs"].get("baseline", {}).get("heuristic_score")
    skilled = result["runs"].get("skill", {}).get("heuristic_score")
    if baseline is not None and skilled is not None:
        result["delta_points"] = skilled - baseline
    return result


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1")
    cases = load_cases(args.cases)
    if args.case_ids:
        cases = [case for case in cases if case["id"] in args.case_ids]
        missing = sorted(set(args.case_ids) - {case["id"] for case in cases})
        if missing:
            raise SystemExit("Unknown case id(s): " + ", ".join(missing))
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]
    if not cases:
        raise SystemExit("No cases selected")

    args.skill_dir = args.skill_dir.resolve()
    if args.mode in ("both", "skill"):
        for case in cases:
            load_skill_context(args.skill_dir, case)
    base_url = args.base_url.rstrip("/")
    model = args.model or discover_model(base_url, args.timeout)
    print(f"Endpoint: {base_url}\nModel: {model}\nCases: {len(cases)}\nMode: {args.mode}", flush=True)

    scheduled = [(case, repeat) for repeat in range(1, args.repeats + 1) for case in cases]
    results = []
    if args.workers == 1:
        for case, repeat in scheduled:
            results.append(run_case_pair(args, base_url, model, case, repeat))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(run_case_pair, args, base_url, model, case, repeat): (case, repeat)
                for case, repeat in scheduled
            }
            for future in as_completed(futures):
                results.append(future.result())
        order = {case["id"]: index for index, case in enumerate(cases)}
        results.sort(key=lambda row: (row["repeat"], order[row["id"]]))

    summary = {}
    for mode in (("baseline", "skill") if args.mode == "both" else (args.mode,)):
        scores = [row["runs"][mode]["heuristic_score"] for row in results if mode in row["runs"]]
        if scores:
            summary[mode] = {"mean_heuristic_score": round(sum(scores) / len(scores), 1), "cases": len(scores)}
    if args.mode == "both":
        deltas = [row["delta_points"] for row in results if "delta_points" in row]
        summary["mean_skill_delta_points"] = round(sum(deltas) / max(1, len(deltas)), 1)

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": base_url,
        "model": model,
        "skill_dir": str(args.skill_dir),
        "mode": args.mode,
        "repeats": args.repeats,
        "thinking": args.thinking,
        "summary": summary,
        "results": results,
        "limitations": [
            "The benchmark evaluates written answers from fixed evidence snippets; it does not edit files or operate an emulator.",
            "Image cases send the fixture image to the endpoint but do not verify the model's visual understanding by themselves.",
            "Regex concept checks are triage signals, not semantic proof; inspect each raw answer.",
            "Baseline and skill-assisted outputs are stochastic and this small suite is not a general capability score.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nHeuristic coverage (review raw answers before drawing conclusions):")
    for row in results:
        if args.mode == "both":
            before = row["runs"]["baseline"]["heuristic_score"]
            after = row["runs"]["skill"]["heuristic_score"]
            print(f"  {row['id']} #{row['repeat']}: {before}% -> {after}% ({row['delta_points']:+d})")
        else:
            score = row["runs"][args.mode]["heuristic_score"]
            print(f"  {row['id']} #{row['repeat']}: {score}%")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
