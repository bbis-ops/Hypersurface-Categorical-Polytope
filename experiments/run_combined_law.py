#!/usr/bin/env python3
"""
Capstone: does the unified law p = beta/(beta-alpha) hold when the base flatness
AND the perturbation degree AND coupling all vary at once?

  python experiments/run_combined_law.py --api --n 16

Asks the model for (base r, perturbation P) pairs, screens each with
combined_screen, and flags any where the measured gap exponent departs from the
prediction. A survivor would be a genuine counterexample. Writes COMBINED_LAW.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Deterministic pairs so the artifact reproduces without the API.
BUILTIN_PAIRS = [
    ("quad_linear", "-(1-lam)**2 - sigma**2", "sigma"),
    ("quad_sqrt", "-(1-lam)**2 - sigma**2", "sqrt(sigma)"),
    ("quartic_linear", "-(1-lam)**4 - sigma**4", "sigma"),
    ("quartic_sqrt", "-(1-lam)**4 - sigma**4", "sqrt(sigma)"),
    ("quartic_cone", "-(1-lam)**4 - sigma**4", "((1-lam)**2+sigma**2)**0.5"),
    ("sextic_cbrt", "-(1-lam)**6 - sigma**6", "sigma**0.3333333333333333"),
    ("aniso_sqrt", "-(1-lam)**2 - sigma**6", "sqrt(sigma)"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument(
        "--api-batch-size", type=int, default=3,
        help="model proposals per API request (smaller avoids long/rate-limited completions)",
    )
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    from categorical_polytope.base_search import Candidate, combined_screen, propose_pairs

    pairs = [
        (Candidate(f"{n}_b", b, "builtin"), Candidate(f"{n}_p", p, "builtin"))
        for n, b, p in BUILTIN_PAIRS
    ]
    backend = "builtin pairs"
    if args.api:
        if args.api_batch_size < 1:
            ap.error("--api-batch-size must be at least 1")
        seen = {(b.expr, p.expr) for b, p in pairs}
        for r in range(args.rounds):
            proposed = []
            batch_count = (args.n + args.api_batch_size - 1) // args.api_batch_size
            for batch_index, start in enumerate(range(0, args.n, args.api_batch_size), 1):
                batch_n = min(args.api_batch_size, args.n - start)
                batch, backend = propose_pairs(
                    batch_n, model=args.model, base_url=args.base_url
                )
                proposed.extend(batch)
                print(
                    f"  round {r + 1}/{args.rounds}, batch {batch_index}/{batch_count}: "
                    f"{len(batch)}/{batch_n} pairs ({backend})",
                    flush=True,
                )
            fresh = [(b, p) for b, p in proposed if (b.expr, p.expr) not in seen]
            seen.update((b.expr, p.expr) for b, p in fresh)
            pairs.extend(fresh)
            print(f"  round {r + 1}/{args.rounds}: +{len(fresh)} pairs ({backend})", flush=True)

    results = [combined_screen(b, p) for b, p in pairs]
    breaks = [r for r in results if r.ok and r.breaks and not r.base_self_fails]
    self_fail = [r for r in results if r.ok and r.base_self_fails]
    violations = [r for r in breaks if not r.law_holds]

    lines = [
        f"# Unified law V.14: p = beta/(beta-alpha)  ({backend})",
        "",
        f"{len(breaks)} breaking pairs screened, {len(self_fail)} base-self-fail, "
        f"{len(violations)} law violations.",
        "",
        "base x perturbation -> measured vs predicted gap exponent:",
        "```",
    ]
    lines += [r.row() for r in sorted(breaks, key=lambda r: r.predicted_exponent)]
    if self_fail:
        lines += ["", "base self-fails (max off-corner even at s=0):"]
        lines += [r.row() for r in self_fail]
    lines += ["", f"## Counterexamples: {len(violations)}"]
    lines += ([f"  {r.row()}" for r in violations]
              if violations else ["  none - the unified law held across every combination."])
    lines.append("```")

    out = ROOT / "experiments" / "COMBINED_LAW.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    (ROOT / "experiments" / "combined_law.json").write_text(
        json.dumps(
            [
                {
                    **asdict(result),
                    "base_expr": base.expr,
                    "pert_expr": pert.expr,
                    "base_source": base.source,
                    "pert_source": pert.source,
                    "note": base.note or pert.note,
                }
                for (base, pert), result in zip(pairs, results)
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
