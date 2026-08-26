#!/usr/bin/env python3
"""
Numerical firsts: toy models, vertex localization, gap vs epsilon.

Run from package root:
  python experiments/run_experiments.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.decomposition_stability import robustness_sweep
from categorical_polytope.fisher_factorization import (
    BlockLayout,
    QuadraticJointObjective,
    build_block_fisher,
)
from categorical_polytope.fisher_pruned_search import FisherPrunedVertexSearch
from categorical_polytope.formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from categorical_polytope.hypersurface_box import BoxBounds, HypersurfaceBox
from categorical_polytope.vertex_probe import VertexProbeAlgorithm


OUT = ROOT / "experiments" / "results.json"


def experiment_1_two_blocks() -> list[dict]:
    """Toy 1: two blocks, vary Fisher coupling f in {0, 0.01, 0.05, 0.1, 0.25, 0.35}."""
    layout = BlockLayout(names=("A", "B"), sizes=(2, 2))
    linear = (1.0, 0.5, 2.0, 3.0)
    rows: list[dict] = []
    for f in (0.0, 0.01, 0.05, 0.1, 0.25, 0.35):
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        obj = QuadraticJointObjective(fisher=fisher, linear=linear)
        try:
            analysis = obj.factorization_analysis()
            leak = analysis.leakage
            theta_j = analysis.theta_joint
            theta_s = analysis.theta_separable
            gap = analysis.gap
            joint_val = analysis.objective_joint
            sep_val = analysis.objective_separable
            vertex_localized = True
        except ValueError:
            gap = float("nan")
            joint_val = sep_val = float("nan")
            vertex_localized = False
            leak = fisher.leakage()
            theta_j = theta_s = []

        hs = HypersurfaceBox(
            BoxBounds(lam=(0.0, 1.0), sigma=(0.0, 1.0), b=(0.0, 2.0), k=(0.0, 3.0))
        )
        probe = VertexProbeAlgorithm(cross_info_bound=max(0.25, f)).find_near_optimal_probe()
        pruned = FisherPrunedVertexSearch(
            fisher_epsilon=f if f > 0 else 0.01,
            top_k=4,
            cross_info_bound=max(0.25, f),
        ).run()

        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(fisher.layout.n)],
            theta_joint=theta_j if theta_j else (1.0, 0.5, 2.0, 3.0),
        )
        import math

        gap_finite = gap if (isinstance(gap, float) and math.isfinite(gap)) else float("inf")
        strict_cert, phi_thm, cert_reason = certify_suboptimality(
            leak.epsilon, gap_finite, const
        )

        rows.append(
            {
                "experiment": "toy_2block",
                "fisher_coupling": f,
                "epsilon": leak.epsilon,
                "gap_joint_sep": gap,
                "objective_joint": joint_val,
                "objective_separable": sep_val,
                "vertex_theta": probe.theta.as_corner_tuple(),
                "vertex_value": probe.objective_value,
                "pruned_value": pruned.objective_value,
                "pruned_gap_vs_full": pruned.gap,
                "phi_bound": pruned.phi_bound,
                "phi_theorem": phi_thm,
                "certified_pruned": pruned.certified,
                "certified_strict": strict_cert,
                "certify_reason": cert_reason or pruned.certify_reason,
                "pairs_checked": pruned.pairs_checked,
                "global_is_vertex": vertex_localized,
            }
        )
    return rows


def experiment_2_three_blocks() -> list[dict]:
    """Toy 2: three scalar blocks — asymmetric layout."""
    layout = BlockLayout(names=("X", "Y", "Z"), sizes=(1, 1, 1))
    linear = (1.0, 2.0, 3.0)
    rows: list[dict] = []
    for f in (0.0, 0.1, 0.4):
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        obj = QuadraticJointObjective(fisher=fisher, linear=linear)
        try:
            a = obj.factorization_analysis(separable_passes=3)
            robust = a.gap <= a.theoretical_bound + 1e-6
        except ValueError:
            a = None
            robust = False
        rows.append(
            {
                "experiment": "toy_3block",
                "fisher_coupling": f,
                "epsilon": a.leakage.epsilon if a else None,
                "gap": a.gap if a else None,
                "robust": robust,
                "failure_mode": f > 0.25,
            }
        )
    return rows


def main() -> None:
    results = {
        "toy_2block": experiment_1_two_blocks(),
        "toy_3block": experiment_2_three_blocks(),
        "robustness_sweep": [
            {
                "epsilon": r.leakage.epsilon,
                "gap": r.bounds.objective_gap_observed,
                "bound": r.bounds.objective_gap_bound,
                "robust": r.coproduct_robust,
                "strategy": r.strategy.name,
            }
            for r in robustness_sweep()
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print("\nToy 2-block (gap vs coupling):")
    for row in results["toy_2block"]:
        print(
            f"  f={row['fisher_coupling']:.2f}  eps={row['epsilon']:.4f}  "
            f"gap={row['gap_joint_sep']:.4f}  vertex_val={row['vertex_value']:.3f}  "
            f"strict_cert={row['certified_strict']}"
        )


if __name__ == "__main__":
    main()
