#!/usr/bin/env python3
"""
Close the loop: live probe while learner internalizes coexp failure.

  python experiments/run_loop_closure.py                 # scripted (default)
  python experiments/run_loop_closure.py --api           # any OpenAI-compatible key
  python experiments/run_loop_closure.py --api       --model MODEL_ID --base-url https://your-openai-compatible-endpoint/v1
  python experiments/run_loop_closure.py --check     --model MODEL_ID   # validate a key, write nothing
  python experiments/plot_loop_closure.py

Keys checked in order: LOOP_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY.
A key alone picks that provider's endpoint with a generic default model;
use --model, or --preset / LOOP_API_PRESET, to choose another.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--api",
        action="store_true",
        help="Use a real model if an API key is set (else scripted)",
    )
    ap.add_argument("--model", default=None, help="any OpenAI-compatible model id")
    ap.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible base, e.g. https://openrouter.ai/api/v1",
    )
    ap.add_argument(
        "--preset",
        default=None,
        help="named endpoint preset (openai, openrouter, nemotron); "
        "--model/--base-url override it",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="One round-trip to validate the key/endpoint, then exit",
    )
    args = ap.parse_args()

    if args.check:
        from categorical_polytope.loop_closure import check_backend

        r = check_backend(args.model, args.base_url, args.preset)
        print(f"  backend: {r['backend'] or '(none)'}")
        print(f"  {'OK' if r['ok'] else 'FAILED'}: {r['detail']}")
        raise SystemExit(0 if r["ok"] else 1)

    from categorical_polytope.loop_closure import run_loop_closure

    s = run_loop_closure(
        ROOT / "experiments",
        use_api=args.api,
        model=args.model,
        base_url=args.base_url,
        preset=args.preset,
    )
    print("Loop closure session")
    print(f"  backend: {s['backend']}")
    if args.api and s["backend"] == "scripted":
        print("  (no API key found -> scripted; set LOOP_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY)")
    for fb in s.get("api_fallbacks", []):
        print(f"  ! turn {fb['turn']} fell back to scripted: {fb['error']}")
    print(f"  closure_turn: {s['closure_turn']}")
    print(f"  modes: {' -> '.join(s['modes'])}")
    if s.get("closure_quote"):
        print(f"  quote: {s['closure_quote']}")

    plot = ROOT / "experiments" / "plot_loop_closure.py"
    if plot.exists():
        import subprocess

        subprocess.run([sys.executable, str(plot)], cwd=str(ROOT))


if __name__ == "__main__":
    main()
