#!/usr/bin/env python3
"""
Search over BASE objectives for the master exponent law V.12.

  python experiments/run_base_search.py                 # builtin bases
  python experiments/run_base_search.py --api --n 16    # + model-proposed bases

Model-proposed r(lam,sigma) go through the same AST whitelist as interaction
terms. Writes experiments/base_search.json.
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
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    from categorical_polytope.base_search import (
        BUILTIN_BASES,
        base_report,
        propose_bases,
        screen_bases,
    )

    bases = list(BUILTIN_BASES)
    backend = "builtin only"
    if args.api:
        seen = {c.expr for c in bases}
        for r in range(args.rounds):
            proposed, backend = propose_bases(args.n, model=args.model, base_url=args.base_url)
            fresh = [c for c in proposed if c.expr not in seen]
            seen.update(c.expr for c in fresh)
            bases.extend(fresh)
            print(f"  round {r + 1}/{args.rounds}: +{len(fresh)} new bases ({backend})",
                  flush=True)

    results = screen_bases(bases)
    print()
    print("\n".join(base_report(results)))

    out = ROOT / "experiments" / "base_search.json"
    out.write_text(json.dumps({
        "backend": backend, "n": len(results),
        "results": [{**asdict(r.candidate), **{
            "ok": r.ok, "reason": r.reason, "corner": list(r.corner),
            "flat_axis": r.flat_axis, "flatness_order": r.flatness_order,
            "predicted_exponent": r.predicted_exponent,
            "measured_exponent": r.measured_exponent,
            "base_self_fails": r.base_self_fails, "breaks": r.breaks,
            "law_holds": r.law_holds,
        }} for r in results],
    }, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
