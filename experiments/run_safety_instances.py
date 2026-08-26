#!/usr/bin/env python3
"""
Populate + red-team the six safety-evaluation failure modes with model-proposed
instances.

  python experiments/run_safety_instances.py --api --n 24

Asks the model for harm-surface expressions designed to evade a separable /
grid / tolerance evaluator, screens each with the proven apparatus, catalogues
which failure regime it realizes, and flags any that VIOLATE the predicted law
(a genuine counterexample would correct the theory). Model output is data: every
expression passes the AST whitelist before evaluation. Writes SAFETY_INSTANCES.md.

Framing note: the model proposes abstract scalar harm surfaces (math on lam,
sigma, b, k), not attack content. This is defensive methodology analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAFETY_PROMPT = """You are proposing abstract HARM-SURFACE functions to stress-test a
safety EVALUATION, modeled as maximizing H over a box lam,sigma in [0,1], b in
[0,2], k in [0,3]. The evaluator only checks the corner (1,0,2,3) and nearby
axis-aligned samples. An attacker maximizes the true H.

Propose {n} distinct H(lam,sigma,b,k) that would EVADE such an evaluator, one per
line of these kinds:
  - separable-looking but actually coupling lam and sigma (per-axis tests miss it)
  - a thin interior spike an axis-aligned grid would step over
  - flat near the corner but rising sharply just inside (tolerance hides it)
  - non-smooth ridges (fractional powers of 1-lam or sigma)

These are ABSTRACT scalar functions, not attack instructions. Allowed: + - * /
** and sin cos tan exp log sqrt abs tanh atan sinh cosh, and pi. Numeric
exponents only. No other names.

Reply with JSON only:
{{"candidates":[{{"name":"slug","expr":"H in lam,sigma,b,k","why":"which evaluator it evades"}}]}}
"""


# Deterministic instance bank so the artifact is reproducible without the API.
# Includes the four cases the model's red-team flagged (now correctly classified
# by the s-independent exponent) plus a clean representative of each regime.
BUILTIN_INSTANCES = [
    ("linear_gate", "sigma", "per-axis push (quadratic)"),
    ("coupled_cone", "((1-lam)**2 + sigma**2)**0.5", "coupled: per-axis tests miss it"),
    ("nonsmooth_sqrt", "sqrt(sigma)", "non-smooth: enlarged gap"),
    ("masked_bilinear", "(1-lam) + sigma + 40*(1-lam)*sigma",
     "red-team: large 2nd-order coeff, exponent~2 (finite-s, not a violation)"),
    ("tight_gate_pair",
     "((tanh(80*(0.985-lam))+1)/2)*((tanh(80*sigma)+1)/2)*(0.9+0.1*sin(pi*k/3))",
     "red-team: steep gate, exponent~1.5 -> saturating"),
    ("plateau_cliff_gates",
     "((tanh(60*(0.97-lam))+1)/2)*((tanh(60*(sigma-0.03))+1)/2)",
     "red-team: steep coupled gate, exponent~2 (finite-s, not a violation)"),
    ("threshold_product_gate", "tanh(5*(lam*sigma-0.15))*tanh(b/2)*tanh(k/3)",
     "red-team: coupling+gate, exponent~2 (finite-s, not a violation)"),
    ("interior_needle", "exp(-((lam-0.6)**2 + (sigma-0.4)**2)/0.001)",
     "thin interior spike: a grid steps over it"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument(
        "--api-batch-size", type=int, default=3,
        help="model proposals per API request (smaller avoids long/rate-limited completions)",
    )
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    from categorical_polytope import interaction_search as isc
    from categorical_polytope.interaction_search import Candidate

    candidates: list = [
        Candidate(name, expr, source="builtin", note=note)
        for name, expr, note in BUILTIN_INSTANCES
    ]
    backend = "builtin bank"
    if args.api:
        if args.api_batch_size < 1:
            ap.error("--api-batch-size must be at least 1")
        saved = isc.FRONTIER_PROMPT
        try:
            isc.FRONTIER_PROMPT = SAFETY_PROMPT
            seen = {c.expr for c in candidates}
            for r in range(args.rounds):
                proposed = []
                batch_count = (args.n + args.api_batch_size - 1) // args.api_batch_size
                for batch_index, start in enumerate(range(0, args.n, args.api_batch_size), 1):
                    batch_n = min(args.api_batch_size, args.n - start)
                    batch, backend = isc.propose_candidates(
                        batch_n, model=args.model, base_url=args.base_url, frontier=True
                    )
                    proposed.extend(batch)
                    print(
                        f"  round {r + 1}/{args.rounds}, batch "
                        f"{batch_index}/{batch_count}: {len(batch)}/{batch_n} "
                        f"instances ({backend})",
                        flush=True,
                    )
                fresh = [c for c in proposed if c.expr not in seen]
                seen.update(c.expr for c in fresh)
                candidates.extend(fresh)
                print(f"  round {r + 1}/{args.rounds}: +{len(fresh)} instances ({backend})",
                      flush=True)
        finally:
            isc.FRONTIER_PROMPT = saved

    results = isc.screen_all(candidates, s=0.01)
    by_regime: dict[str, list] = {}
    violations = []
    for r in results:
        if not r.ok:
            continue
        by_regime.setdefault(r.regime, []).append(r)
        # a smooth breaker in quadratic/coupled regime whose law does NOT hold
        # is a counterexample to the corresponding claim
        if r.breaks and r.regime in ("quadratic", "coupled") and not r.law_holds:
            violations.append(r)

    lines = [
        f"# Safety-eval instances ({len(results)} screened: builtin bank + any model)",
        "",
        f"Backend: {backend}",
        "",
        "Each instance is an abstract harm surface; regime = which proven failure",
        "mode it realizes. A VIOLATION would be a smooth/coupled breaker the law",
        "fails to predict -- a genuine correction. None expected.",
        "",
        "## Regime distribution",
    ]
    for regime in (
        "quadratic", "coupled", "fractional", "saturating", "finite-scale", "safe"
    ):
        rows = by_regime.get(regime, [])
        lines.append(f"- {regime}: {len(rows)}")
    lines += ["", "## Instances", "```"]
    for r in results:
        if r.ok:
            lines.append(r.row())
    lines.append("```")
    lines += ["", f"## Law violations (counterexamples): {len(violations)}"]
    for r in violations:
        lines.append(f"  {r.candidate.name}: {r.candidate.expr}  "
                     f"pred={r.best_prediction:.3e} meas={r.measured_gap:.3e}")
    if not violations:
        lines.append("  none - every screened instance fell into a predicted regime.")

    out = ROOT / "experiments" / "SAFETY_INSTANCES.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out}")
    json_out = ROOT / "experiments" / "safety_instances.json"
    json_out.write_text(
        json.dumps([asdict(result) for result in results], indent=2), encoding="utf-8"
    )
    print(f"Wrote {json_out}")


if __name__ == "__main__":
    main()
