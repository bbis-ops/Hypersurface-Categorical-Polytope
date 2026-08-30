#!/usr/bin/env python3
"""Keep high-quality adversarial verification batches running for a fixed event window."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "experiments" / "run_verification_campaign.py"
CORPUS = ROOT / "experiments" / "verification_campaign.json"
EVENT = ROOT / "experiments" / "verification_72h_state.json"
HEARTBEAT = ROOT / "experiments" / "verification_72h_heartbeat.json"
RATE_STATE = ROOT / "experiments" / "verification_api_rate_state.json"
LAWS = [f"V.{i}" for i in range(7, 15)]


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, data: Any) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


# --dry-run swaps this in for _write: a rehearsal must never touch campaign state.
def _noop_write(path: Path, data: Any) -> None:
    return None


def _counts() -> tuple[dict[str, Counter], list[dict[str, Any]]]:
    records = _read(CORPUS, {}).get("records", [])
    out = {law: Counter() for law in LAWS}
    for row in records:
        if row.get("rule_id") in out:
            out[row["rule_id"]][row.get("status", "unknown")] += 1
            out[row["rule_id"]]["corpus"] += 1
    return out, records


def _choose_law(cycle: int, counts: dict[str, Counter], records: list[dict[str, Any]]) -> tuple[str, bool]:
    survivor_laws = sorted({r["rule_id"] for r in records if r.get("status") == "counterexample"})
    if survivor_laws and cycle % 4 == 0:
        return survivor_laws[(cycle // 4) % len(survivor_laws)], True
    if cycle % 4 == 3:
        return LAWS[(cycle // 4) % len(LAWS)], False
    return min(LAWS, key=lambda law: (counts[law]["verified"] + counts[law]["counterexample"],
                                      counts[law]["corpus"], law)), False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=72.0)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-tokens", type=int, default=15000)
    ap.add_argument("--cycle-timeout", type=float, default=900.0,
                    help="kill and recover a child that makes no cycle progress within this many seconds")
    ap.add_argument("--base-interval", type=float, default=120.0,
                    help="minimum seconds between provider requests across child processes")
    ap.add_argument("--min-batch-size", type=int, default=4)
    ap.add_argument("--api-retries", type=int, default=4)
    ap.add_argument("--model", default=None,
                    help="any OpenAI-compatible model id; default resolves from preset/env")
    ap.add_argument("--preset", default=None, help="named endpoint preset (openai, openrouter, nemotron); --model/--base-url override it")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if (args.hours <= 0 or args.batch_size < 1 or args.max_tokens < 1 or args.cycle_timeout < 60
            or args.base_interval < 1 or args.min_batch_size < 1 or args.api_retries < 1):
        ap.error("sizes/intervals must be positive and cycle-timeout >= 60")
    if args.min_batch_size > args.batch_size:
        ap.error("min-batch-size cannot exceed batch-size")
    keys = ("LOOP_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")
    if not any(os.environ.get(k, "").strip() for k in keys):
        raise SystemExit("no API key in this process; set one of " + ", ".join(keys))

    write = _noop_write if args.dry_run else _write

    now = datetime.now(timezone.utc)
    prior = _read(EVENT, {})
    if prior.get("status") == "running" and prior.get("deadline_utc"):
        deadline = datetime.fromisoformat(prior["deadline_utc"])
        if deadline <= now:
            deadline = now + timedelta(hours=args.hours)
            prior = {}
    else:
        deadline = now + timedelta(hours=args.hours)
        prior = {}
    state = {
        "status": "running", "started_utc": prior.get("started_utc", now.isoformat()),
        "deadline_utc": deadline.isoformat(), "cycle": int(prior.get("cycle", 0)),
        "pid": os.getpid(),
        "model": args.model, "batch_size": args.batch_size, "max_tokens": args.max_tokens,
        "base_interval": args.base_interval, "min_batch_size": args.min_batch_size,
        "attempts_by_law": prior.get("attempts_by_law", {law: 0 for law in LAWS}),
        "last_exit_code": prior.get("last_exit_code"),
    }
    write(EVENT, state)

    env = os.environ.copy()
    env.update({
        "POLYTOPE_API_MAX_TOKENS": str(args.max_tokens),
        "POLYTOPE_API_REASONING_EFFORT": "high",
        "POLYTOPE_API_TIMEOUT": "300",
        "POLYTOPE_API_MIN_INTERVAL": str(args.base_interval),
        "POLYTOPE_API_CONFIGURED_BATCH_SIZE": str(args.batch_size),
        "POLYTOPE_API_RATE_STATE": str(RATE_STATE),
        "POLYTOPE_API_RAW_LOG": str(ROOT / "experiments" / "verification_api_raw.jsonl"),
    })
    while datetime.now(timezone.utc) < deadline:
        rate_state = _read(RATE_STATE, {})
        cooldown = max(0.0, float(rate_state.get("next_allowed_epoch", 0.0)) - time.time())
        while cooldown > 0 and not args.dry_run and datetime.now(timezone.utc) < deadline:
            write(HEARTBEAT, {
                "utc": datetime.now(timezone.utc).isoformat(), "cycle": state["cycle"],
                "phase": "shared_rate_cooldown", "cooldown_seconds": round(cooldown, 1),
                "rate_state": rate_state, "deadline_utc": deadline.isoformat(),
            })
            time.sleep(min(30.0, cooldown))
            rate_state = _read(RATE_STATE, {})
            cooldown = max(0.0, float(rate_state.get("next_allowed_epoch", 0.0)) - time.time())
        if datetime.now(timezone.utc) >= deadline:
            break
        counts, records = _counts()
        law, focus = _choose_law(state["cycle"], counts, records)
        in_scope = counts[law]["verified"] + counts[law]["counterexample"]
        corpus = counts[law]["corpus"]
        recommended = int(rate_state.get("recommended_batch_size", args.batch_size))
        active_batch = max(args.min_batch_size, min(args.batch_size, recommended))
        state["active_batch_size"] = active_batch
        state["rate_state"] = rate_state
        write(EVENT, state)
        command = [
            sys.executable, str(CAMPAIGN), "--api",
            "--laws", law, "--batch-size", str(active_batch),
            "--per-law", str(max(1, corpus)), "--in-scope-per-law", str(in_scope + 1),
            "--max-attempts-per-law", "1", "--retries", str(args.api_retries),
        ]
        # Both are optional: with neither, the child resolves model and endpoint
        # from LOOP_API_* / LOOP_API_PRESET the same way a direct run would.
        if args.model:
            command += ["--model", args.model]
        if args.preset:
            command += ["--preset", args.preset]
        if focus:
            command.append("--focus-counterexamples")
        heartbeat = {
            "utc": datetime.now(timezone.utc).isoformat(), "cycle": state["cycle"],
            "law": law, "focus_counterexample": focus, "in_scope_before": in_scope,
            "corpus_before": corpus, "active_batch_size": active_batch,
            "rate_state": rate_state, "deadline_utc": deadline.isoformat(), "phase": "api_batch",
        }
        write(HEARTBEAT, heartbeat)
        print(f"72h cycle {state['cycle']}: {law}, in-scope={in_scope}, corpus={corpus}, focus={focus}, batch={active_batch}", flush=True)
        if args.dry_run:
            if cooldown > 0:
                print(f"would wait {cooldown:.1f}s for the shared rate cooldown first")
            print(" ".join(command))
            return
        child = subprocess.Popen(command, cwd=str(ROOT), env=env)
        cycle_started = time.monotonic()
        timed_out = False
        while child.poll() is None:
            elapsed = time.monotonic() - cycle_started
            write(HEARTBEAT, {
                **heartbeat, "utc": datetime.now(timezone.utc).isoformat(),
                "phase": "api_or_local_work", "child_pid": child.pid,
                "elapsed_seconds": round(elapsed, 1),
            })
            if elapsed >= args.cycle_timeout:
                child.kill()
                child.wait()
                timed_out = True
                print(f"72h cycle {state['cycle']}: watchdog killed child {child.pid} after {elapsed:.1f}s", flush=True)
                break
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
        returncode = 124 if timed_out else int(child.returncode or 0)
        state["last_exit_code"] = returncode
        state["cycle"] += 1
        state["attempts_by_law"][law] = int(state["attempts_by_law"].get(law, 0)) + 1
        write(EVENT, state)
        if returncode != 0:
            write(HEARTBEAT, {**heartbeat, "utc": datetime.now(timezone.utc).isoformat(),
                              "phase": "backoff", "exit_code": returncode})
            time.sleep(30)

    subprocess.run([sys.executable, str(CAMPAIGN)], cwd=str(ROOT), env=env, check=False)
    state["status"] = "complete"
    state["completed_utc"] = datetime.now(timezone.utc).isoformat()
    write(EVENT, state)
    write(HEARTBEAT, {"utc": state["completed_utc"], "phase": "complete", "deadline_utc": deadline.isoformat()})


if __name__ == "__main__":
    main()
