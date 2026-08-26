#!/usr/bin/env python3
"""
Screen candidate interaction terms for vertex-localization failure.

  python experiments/run_interaction_search.py                 # builtin bank
  python experiments/run_interaction_search.py --api           # + model proposals
  python experiments/run_interaction_search.py --api --n 30 --rounds 3

Model output is treated as data: every proposed expression is validated by an
AST whitelist before it is evaluated, and rejected proposals are reported rather
than run. Writes interaction_search.json and INTERACTION_SEARCH.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true", help="also ask a model for candidates")
    ap.add_argument("--n", type=int, default=12, help="proposals per round")
    ap.add_argument("--rounds", type=int, default=1, help="proposal rounds")
    ap.add_argument("--s", type=float, default=0.01, help="interaction strength")
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--preset", default=None, help="named endpoint preset (openai, openrouter, ox-alpha); --model/--base-url override it")
    args = ap.parse_args()

    from categorical_polytope.interaction_search import (
        BUILTIN_CANDIDATES,
        propose_candidates,
        screen_all,
        search_report,
    )

    candidates = list(BUILTIN_CANDIDATES)
    backend = "builtin only"
    if args.api:
        seen = {c.expr for c in candidates}
        kept = 0
        for r in range(args.rounds):
            proposed, backend = propose_candidates(
                args.n, model=args.model, base_url=args.base_url, preset=args.preset
            )
            fresh = [c for c in proposed if c.expr not in seen]
            seen.update(c.expr for c in fresh)
            candidates.extend(fresh)
            kept += len(fresh)
            print(f"  round {r + 1}: {len(fresh)} new valid candidates from {backend}")
        if kept == 0:
            print(f"  no usable proposals ({backend}); continuing with the builtin bank")

    results = screen_all(candidates, s=args.s)
    print()
    print("\n".join(search_report(results, s=args.s)))

    out = ROOT / "experiments"
    payload = {
        "strength": args.s,
        "backend": backend,
        "n_candidates": len(results),
        "results": [
            {**asdict(r.candidate), **{
                "ok": r.ok, "reason": r.reason, "axis": r.axis, "gamma": r.gamma,
                "s_star": (None if r.s_star == float("inf") else r.s_star),
                "predicted_gap": r.predicted_gap, "measured_gap": r.measured_gap,
                "smooth": r.smooth, "breaks": r.breaks, "law_holds": r.law_holds,
            }}
            for r in results
        ],
    }
    (out / "interaction_search.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (out / "INTERACTION_SEARCH.md").write_text(
        "# Interaction search\n\n```\n"
        + "\n".join(search_report(results, s=args.s))
        + "\n```\n",
        encoding="utf-8",
    )
    print(f"\nWrote {out / 'interaction_search.json'}")


if __name__ == "__main__":
    main()
