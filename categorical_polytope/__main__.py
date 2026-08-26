#!/usr/bin/env python3
"""Run the categorical polytope lecture demo (standalone)."""

from __future__ import annotations

import sys

from .adversarial_probe import adversarial_theorem_summary, demonstrate_adversarial
from .bridge_fisher_adversarial import factorization_from_hypersurface
from .decomposition_stability import demonstrate_robustness, stability_framework_summary
from .nonlinear_objective import demonstrate_nonlinear
from .extremal_substitute import demonstrate_substitute, substitute_summary
from .firsts import deliverables_manifest
from .fisher_factorization import demonstrate_fisher_factorization, factorization_summary
from .hypersurface_box import box_theorem_summary, demonstrate_box
from .neighboring_vertices import (
    NEIGHBOR_GUIDES,
    demonstrate_neighbors,
    duality_strategy_note,
    walk_from_empty_coexponential,
)
from .set_category import cardinality_obstruction, demonstrate_growth_contradiction
from .cartesian_closed import hom_product_exp_cardinality, verify_curry_adjunction
from .conceptual_polytope import (
    ConceptualPolytope,
    CoproductBlock,
    DiagramPoint,
    Vertex,
    lecture_summary,
    maximize_under_coproduct_blocks,
)
from .vertex_probe import demonstrate_vertex_algorithm, vertex_reduction_argument
from .fisher_pruned_search import FisherPrunedVertexSearch


def _section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "firsts":
        print(deliverables_manifest())
        return
    if len(sys.argv) > 1 and sys.argv[1] == "discover":
        from .discoveries import print_discovery_summary, write_discovery_artifacts

        jp, md, formal = write_discovery_artifacts()
        print(f"Wrote {jp}")
        print(f"Wrote {md}")
        print(f"Wrote {formal}")
        print()
        print_discovery_summary()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "research":
        from .discoveries_research import run_research_discoveries

        for d in run_research_discoveries():
            print(f"  [{d.category}] {d.id}: {d.summary}")
        print("\nRun: python experiments/run_research_probes.py for JSON/Markdown artifacts.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "friday":
        from .discoveries_friday import run_friday_discoveries

        for d in run_friday_discoveries():
            print(f"  [{d.category}] {d.id}: {d.summary}")
        print("\nRun: python experiments/run_friday_probes.py for JSON/Markdown artifacts.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "tutor":
        from .category_tutor import run_default_tutor_session

        s = run_default_tutor_session()
        print(f"Turns: {s['n_turns']}, first interior turn: {s['first_interior_turn']}")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        from .loop_closure import run_loop_closure

        s = run_loop_closure(use_api="--api" in sys.argv)
        print(s["narrative"])
        print(f"Closure turn {s['closure_turn']}: {s.get('closure_quote')}")
        return

    _section("0. Deliverables (firsts)")
    print(deliverables_manifest())

    _section("1. Cartesian closed corner (Set)")
    a = frozenset({"a1", "a2"})
    x = frozenset({"x1"})
    y = frozenset({"y1", "y2"})

    def f(pair: tuple[str, str]) -> str:
        a0, x0 = pair
        return "y1" if a0 == "a1" else "y2"

    ok = verify_curry_adjunction(a, x, y, f)
    left, right = hom_product_exp_cardinality(2, 1, 2)
    print(f"  Curry round-trip OK: {ok}")
    print(f"  |Hom(A x X,Y)| = {left}, |Hom(X,Y^A)| = {right}  (equal: {left == right})")

    _section("2. Vanishing corner: coexponential left adjoint to coproduct in Set")
    report = cardinality_obstruction(y=2, a=2, z_probe=range(6))
    print(demonstrate_growth_contradiction(2, 2))
    print(f"  Verdict: {report.reason}")

    _section("3. Conceptual polytope - extremal maximizer")
    poly = ConceptualPolytope()
    p_max, u_max, v_max = poly.global_maximizer()
    print(f"  Global max understanding ~ {u_max:.3f}")
    print(f"  At vertex: {v_max.name}")
    print(f"  Coordinates: product_exp={p_max.product_exp}, coproduct_coexp={p_max.coproduct_coexp}")

    if v_max is Vertex.PRODUCT_EXPONENTIAL:
        print("  -> Inhabited corner: exponential right adjoint to product (CCC).")
    else:
        print("  (unexpected vertex; tune coexp_shadow_penalty for Set lecture)")

    _section("4. Coproduct decomposition (bounded cross-naturality)")
    block_a = CoproductBlock(
        "logic",
        (
            DiagramPoint(1, 0, 0.9, 0.95, 0.05),
            DiagramPoint(0.5, 0.2, 0.7, 0.8, 0.15),
        ),
        cross_bound=0.1,
    )
    block_b = CoproductBlock(
        "type",
        (
            DiagramPoint(1, 0, 0.85, 0.9, 0.08),
            DiagramPoint(0, 1, 0.75, 0.7, 0.25),
        ),
        cross_bound=0.1,
    )
    for name, p, u, v in maximize_under_coproduct_blocks(poly, [block_a, block_b]):
        print(f"  Block {name!r}: u={u:.3f}, vertex={v.name}, cross={p.cross_naturality}")

    _section("5. Where to walk next (neighboring vertices)")
    print("  From empty coexponential corner in Set:")
    for step in walk_from_empty_coexponential():
        print(f"    -> {step.to_vertex.name}: {step.lesson}")
    print()
    for guide in NEIGHBOR_GUIDES:
        print(f"  [{guide.vertex.name}]")
        print(f"    shape: {guide.adjunction_shape}")
        print(f"    instead: {guide.instead_of_coexponential}")
        print(f"    inhabited in Set: {guide.inhabited_in_set}")
    print()
    for line in demonstrate_neighbors(2, 1, 2):
        print(f"  {line}")

    _section("6. Hypersurface box H - theta_max in ext(H)")
    for line in demonstrate_box():
        print(f"  {line}")
    print()
    print(box_theorem_summary())

    _section("7. Adversarial probe (bounded cross-information)")
    for line in demonstrate_adversarial(cross_info_bound=0.25):
        print(f"  {line}")
    print()
    print(adversarial_theorem_summary())

    _section("8. Fisher off-diagonals and factorization")
    for line in demonstrate_fisher_factorization():
        print(f"  {line}")
    print()
    _, analysis = factorization_from_hypersurface(cross_info_bound=0.25)
    print(f"  Hypersurface bridge: leakage={analysis.leakage.epsilon:.4f}  gap={analysis.gap:.6f}")
    print(f"  nearly optimal: {analysis.separable_nearly_optimal}")
    print()
    print(factorization_summary())

    _section("9. Coexponential substitute (extremal selection + limits)")
    for line in demonstrate_substitute():
        print(f"  {line}")
    print()
    print(substitute_summary())

    _section("10. Constructive vertex probe algorithm")
    for line in demonstrate_vertex_algorithm():
        print(f"  {line}")
    print(vertex_reduction_argument())

    pruned = FisherPrunedVertexSearch(fisher_epsilon=0.25, top_k=4).run()
    print(f"  Fisher-pruned: theta={pruned.theta.as_corner_tuple()}  val={pruned.objective_value:.3f}")
    print(
        f"  factorization gap={pruned.gap:.4f}  Phi={pruned.phi_bound:.4f}  "
        f"certified={pruned.certified} ({pruned.certify_reason})  pairs={pruned.pairs_checked}"
    )

    _section("11. Coproduct robustness (Fisher stability bounds)")
    for line in demonstrate_robustness():
        print(f"  {line}")
    print(stability_framework_summary())

    _section("12. Non-quadratic objectives (empirical Fisher)")
    for line in demonstrate_nonlinear():
        print(f"  {line}")

    _section("13. Summary")
    print(lecture_summary())
    print(duality_strategy_note())
    print("Keep traversing the polytope.")


if __name__ == "__main__":
    main()
