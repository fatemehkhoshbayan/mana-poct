#!/usr/bin/env python3
"""
MANA POCT QC Assistant — Scenario Eval Runner
==============================================

Runs all five QC scenarios against a live backend and reports pass/fail
for each expected decision.  Writes a timestamped JSON result to evals/results/.

Usage
-----
  # Against local docker-compose stack (default):
  python evals/run_eval.py

  # Against a different host:
  python evals/run_eval.py --base-url http://localhost:8000

  # Save results to a custom path:
  python evals/run_eval.py --out evals/results/my_run.json

  # Only run specific scenarios:
  python evals/run_eval.py --scenarios A C E

Requirements
------------
  Python 3.10+, no extra packages (uses stdlib only).
  The backend must be running and accessible.

Exit codes
----------
  0  All scenarios passed
  1  One or more scenarios failed or produced wrong decisions
  2  Backend unreachable
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCENARIOS_FILE = Path(__file__).parent / "scenarios.json"
RESULTS_DIR = Path(__file__).parent / "results"


def post_json(base: str, path: str, data: dict | None = None) -> dict:
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=body,
        headers={"Content-Type": "application/json", "X-Tenant-ID": "demo"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get_json(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=30) as r:
        return json.loads(r.read())


def send_turn(base: str, sid: str, msg: str) -> tuple[dict | None, list[str]]:
    """POST a message turn and parse SSE stream for decision/error events."""
    body = json.dumps({"message": msg}).encode()
    conn = http.client.HTTPConnection(
        base.replace("http://", "").split(":")[0],
        int(base.split(":")[-1]) if ":" in base.split("//")[-1] else 8000,
        timeout=180,
    )
    conn.request(
        "POST",
        f"/api/sessions/{sid}/messages",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-Tenant-ID": "demo",
        },
    )
    raw = conn.getresponse().read().decode("utf-8", errors="replace").replace("\r", "")
    conn.close()

    errors: list[str] = []
    decision: dict | None = None
    for block in raw.split("\n\n"):
        ev = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if ev == "error" and data:
            try:
                errors.append(json.loads(data).get("message", data)[:200])
            except Exception:
                errors.append(data[:200])
        if ev == "decision" and data:
            try:
                decision = json.loads(data)
            except Exception:
                pass
    return decision, errors


def run_scenario(base: str, scenario: dict) -> dict:
    sid = post_json(base, "/api/sessions")["session_id"]
    resolved = False
    actual_scenario = None
    actual_variables: dict = {}
    errors: list[str] = []
    turns = 0
    t0 = time.time()

    for msg in scenario["messages"]:
        turns += 1
        dec, errs = send_turn(base, sid, msg)
        errors.extend(errs)
        if dec:
            resolved = True
            actual_scenario = dec["scenario"]
            actual_variables = dec.get("variables", {})
            break
        # Fall back to GET in case SSE parsing missed the event
        detail = get_json(base, f"/api/sessions/{sid}")
        if detail.get("status") == "resolved" and detail.get("decision"):
            d = detail["decision"]
            resolved = True
            actual_scenario = d["scenario"]
            actual_variables = d.get("variables", {})
            break

    elapsed = round(time.time() - t0, 2)

    extraction = {}
    if not resolved:
        try:
            ext = get_json(base, f"/api/sessions/{sid}").get("extraction") or {}
            extraction = {
                "consumable_known": ext.get("consumable_known"),
                "storage_known": ext.get("storage_known"),
                "historical_known": ext.get("historical_known"),
                "eqa_known": ext.get("eqa_known"),
                "storage": ext.get("storage"),
            }
        except Exception:
            pass

    scenario_match = resolved and actual_scenario == scenario["expected_scenario"]
    variables_match = actual_variables == scenario["expected_variables"] if resolved else False

    return {
        "scenario_id": scenario["id"],
        "label": scenario["label"],
        "session_id": sid,
        "turns_used": turns,
        "max_turns": len(scenario["messages"]),
        "elapsed_s": elapsed,
        "error_count": len(errors),
        "errors": errors,
        "resolved": resolved,
        "expected_scenario": scenario["expected_scenario"],
        "actual_scenario": actual_scenario,
        "expected_variables": scenario["expected_variables"],
        "actual_variables": actual_variables,
        "scenario_match": scenario_match,
        "variables_match": variables_match,
        "passed": scenario_match and variables_match,
        "extraction_at_failure": extraction if not resolved else None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="MANA POCT QC eval runner")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--out", default=None, help="Output JSON path (auto-named if omitted)")
    parser.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help="Scenario IDs to run, e.g. A C E (runs all if omitted)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    # Verify backend reachable
    try:
        health = get_json(base, "/api/health")
        assert health.get("status") == "ok"
    except Exception as e:
        print(f"ERROR: Backend not reachable at {base}: {e}", file=sys.stderr)
        return 2

    # Load scenario definitions
    all_scenarios: list[dict] = json.loads(SCENARIOS_FILE.read_text())
    if args.scenarios:
        all_scenarios = [s for s in all_scenarios if s["id"] in args.scenarios]

    # Detect active model
    model = "unknown"
    try:
        import subprocess  # noqa: PLC0415
        model = subprocess.check_output(
            ["grep", "LLM_MODEL", str(Path(__file__).parent.parent / "back-end" / "app" / "config.py")],
            text=True,
        ).strip().split('"')[1]
    except Exception:
        pass

    run_ts = datetime.now(tz=timezone.utc).isoformat()
    print(f"\nMANA POCT QC Eval — {run_ts}")
    print(f"Model   : {model}")
    print(f"Backend : {base}")
    print(f"Running : {len(all_scenarios)} scenario(s)\n")

    results = []
    for scenario in all_scenarios:
        print(f"  [{scenario['id']}] {scenario['label']}...", end=" ", flush=True)
        result = run_scenario(base, scenario)
        results.append(result)
        icon = "PASS" if result["passed"] else ("WRONG" if result["resolved"] else "STUCK")
        print(f"{icon}  ({result['turns_used']}/{result['max_turns']} turns, {result['elapsed_s']}s)")
        if result["errors"]:
            print(f"       errors: {result['errors'][0]}")
        if not result["passed"]:
            print(f"       expected={result['expected_scenario']} got={result['actual_scenario']}")
            print(f"       expected_vars={result['expected_variables']}")
            print(f"       actual_vars  ={result['actual_variables']}")
            if result["extraction_at_failure"]:
                print(f"       known_flags={result['extraction_at_failure']}")

    passed = sum(1 for r in results if r["passed"])
    resolved = sum(1 for r in results if r["resolved"])
    total = len(results)

    print(f"\nSUMMARY: {passed}/{total} passed  |  {resolved}/{total} resolved")
    print(f"Model: {model}\n")

    # Write results file
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = model.replace("/", "-").replace(":", "-")
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"{ts_slug}_{model_slug}.json"

    payload = {
        "run_at": run_ts,
        "model": model,
        "base_url": base,
        "passed": passed,
        "resolved": resolved,
        "total": total,
        "scenarios": results,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Results written to: {out_path}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
