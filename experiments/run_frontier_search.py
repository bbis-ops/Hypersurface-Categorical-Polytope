#!/usr/bin/env python3
"""
Frontier hunt: ask the model for interaction terms that ESCAPE the current
theory (V.7 additive, V.8 fractional, V.9 directional), screen them, and surface
anything the laws fail to predict.

  python experiments/run_frontier_search.py --rounds 6 --n 20

Needs OPENROUTER_API_KEY (see scripts/set_api_key.ps1). Writes
experiments/frontier_search.json and prints the anomalies.
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
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--s", type=float, default=0.01)
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    from categorical_polytope.interaction_search import (
        BUILTIN_CANDIDATES,
        propose_candidates,
        screen_all,
    )

    known = {c.expr for c in BUILTIN_CANDIDATES}
    # also treat anything already saved as known, so we only chase novelty
    prev = ROOT / "experiments" / "interaction_search.json"
    if prev.exists():
        for r in json.loads(prev.read_text()).get("results", []):
            known.add(r["expr"])

    fresh: list = []
    backend = "no run"
    for r in range(args.rounds):
        proposed, backend = propose_candidates(
            args.n, model=args.model, base_url=args.base_url, frontier=True
        )
        new = [c for c in proposed if c.expr not in known]
        known.update(c.expr for c in new)
        fresh.extend(new)
        print(f"  round {r + 1}/{args.rounds}: +{len(new)} new (backend: {backend})",
              flush=True)

    if not fresh:
        print(f"\nNo new candidates ({backend}).")
        return

    print(f"\nScreening {len(fresh)} new candidates at s={args.s} ...", flush=True)
    results = screen_all(fresh, s=args.s)

    # Anomalies: smooth breakers the applicable law fails to predict, plus any
    # candidate that produced a negative-curvature / non-finite situation.
    anomalies = [
        r for r in results
        if r.ok and r.breaks and r.smooth and not r.law_holds
    ]
    coupled_nonsmooth = [
        r for r in results if r.ok and r.breaks and r.coupled and not r.smooth
    ]

    print(f"\n{len(results)} screened: "
          f"{sum(r.breaks for r in results)} break, "
          f"{sum(1 for r in results if r.ok and r.breaks and r.coupled)} coupled, "
          f"{sum(1 for r in results if r.ok and r.breaks and not r.smooth)} non-smooth")

    print("\n=== ANOMALIES (smooth breakers no current law predicts) ===")
    if anomalies:
        for r in sorted(anomalies, key=lambda x: -x.measured_gap):
            print(f"  {r.candidate.name:<18} {r.candidate.expr}")
            print(f"      meas={r.measured_gap:.3e} add={r.predicted_gap:.3e} "
                  f"dir={r.directional_gap:.3e} coupled={r.coupled}")
            if r.candidate.note:
                print(f"      model: {r.candidate.note}")
    else:
        print("  none - every smooth breaker fit an existing law (confirmation).")

    print("\n=== COUPLED + NON-SMOOTH (V.8 x V.9 frontier) ===")
    for r in sorted(coupled_nonsmooth, key=lambda x: -x.measured_gap):
        print(f"  {r.candidate.name:<18} {r.candidate.expr}  meas={r.measured_gap:.3e}")
    if not coupled_nonsmooth:
        print("  none this batch.")

    out = ROOT / "experiments" / "frontier_search.json"
    out.write_text(json.dumps({
        "strength": args.s, "backend": backend, "n_new": len(fresh),
        "results": [{**asdict(r.candidate), **{
            "ok": r.ok, "reason": r.reason, "breaks": r.breaks, "smooth": r.smooth,
            "coupled": r.coupled, "law_holds": r.law_holds, "axis": r.axis,
            "gamma": r.gamma, "predicted_gap": r.predicted_gap,
            "directional_gap": r.directional_gap, "measured_gap": r.measured_gap,
        }} for r in results],
    }, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
