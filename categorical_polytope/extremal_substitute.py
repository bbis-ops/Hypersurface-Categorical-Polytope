"""
Operational substitute when formal coexponential (left adjoint to coproduct) is absent.

The extremal-selection mechanism: maximize on ext(H), build componentwise probes on
coproduct blocks, penalize the empty coexponential corner. Reproduces factorization
behavior under low leakage; documented limits when constraints bite.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from .adversarial_probe import ComponentwiseProbe, CoupledProblem, default_hypersurface_problem
from .conceptual_polytope import ConceptualPolytope, DiagramPoint, Vertex
from .hypersurface_box import BoxBounds, HypersurfaceBox
from .set_category import cardinality_obstruction, left_adjoint_to_coproduct_exists
from .neighboring_vertices import NeighborVertex, walk_from_empty_coexponential


class SubstituteMode(Enum):
    """Operational substitutes for absent coexponential."""

    EXTREMAL_SELECTION = auto()  # search ext(H), vertex localization
    COMPONENTWISE_PROBE = auto()  # per-block max on coproduct factors, assemble
    NEIGHBOR_VERTEX = auto()  # walk Chu / monoidal / continuation / coalgebra corners
    FORMAL_COEXPONENTIAL = auto()  # not available in Set (reference only)


@dataclass(frozen=True)
class FormalCoexponentialSpec:
    """
    What a coexponential would provide if inhabited:

        Hom(coexp(A,Y), Z) ~= Hom(Y, A sqcup Z)   natural in Z
    """

    description: str = "left adjoint to coproduct (co-curry)"
    natural_in: str = "Z"

    def representable_in_set(self, y: int, a: int) -> bool:
        return left_adjoint_to_coproduct_exists(y, a)


@dataclass(frozen=True)
class SubstituteLimits:
    """Where extremal selection stops matching formal factorization."""

    items: tuple[str, ...]

    @staticmethod
    def catalog() -> SubstituteLimits:
        return SubstituteLimits(
            items=(
                "Set: cardinality obstruction - no single coexp(A,Y) represents "
                "Z |-> Hom(Y, A+Z) for all Z.",
                "Universal property not preserved under projecting exp adjunction to coproduct.",
                "Coexponential corner is a shadow only (penalized/uninhabited in scoring).",
                "Cross-leakage / Fisher off-diagonals: componentwise probe loses optimality "
                "when epsilon is large.",
                "Extremal selection is discrete (vertices); no internal co-curry morphism.",
                "Neighbor vertices (Chu, continuation, coalgebra) are different duals, "
                "not replacements in Set.",
            )
        )


@dataclass(frozen=True)
class ExtremalSelectionResult:
    """Outcome of the extremal-selection substitute on a diagram polytope."""

    maximizer: DiagramPoint
    value: float
    vertex: Vertex
    avoided_shadow_corner: bool
    coexp_corner_penalized: bool


@dataclass(frozen=True)
class FactorizationBehavior:
    """Does the substitute reproduce coexp-style factorization on this instance?"""

    componentwise_matches_joint: bool
    fisher_leakage: float
    fisher_gap: float
    separable_nearly_optimal: bool
    cross_satisfies_bound: bool


@dataclass(frozen=True)
class SubstituteReport:
    formal_available: bool
    obstruction_reason: str
    extremal: ExtremalSelectionResult
    probe: ComponentwiseProbe | None
    factorization: FactorizationBehavior | None
    substitute_modes_used: tuple[SubstituteMode, ...]
    limits: SubstituteLimits
    recommendation: str


def extremal_selection_on_polytope(
    polytope: ConceptualPolytope | None = None,
) -> ExtremalSelectionResult:
    """
    Operational substitute (i): push optimization to ext(P) vertices.

    Replaces coexponential-mediated factorization by corner search; in Set the
    global max typically lands on PRODUCT_EXPONENTIAL, not COPRODUCT_COEXPONENTIAL.
    """
    poly = polytope or ConceptualPolytope()
    p_max, u_max, v_max = poly.global_maximizer()
    return ExtremalSelectionResult(
        maximizer=p_max,
        value=u_max,
        vertex=v_max,
        avoided_shadow_corner=v_max is not Vertex.COPRODUCT_COEXPONENTIAL,
        coexp_corner_penalized=poly.coexp_shadow_penalty > 0,
    )


def componentwise_factorization_probe(
    problem: CoupledProblem | None = None,
    *,
    cross_info_bound: float = 0.25,
) -> ComponentwiseProbe:
    """
    Operational substitute (ii): coproduct factorization via per-block vertex probe.

    Mimics 'coexp on each summand' without a representing object — assemble from ext(block).
    """
    prob = problem or default_hypersurface_problem(cross_info_bound=cross_info_bound)
    return prob.build_componentwise_probe()


def evaluate_factorization_behavior(
    *,
    cross_info_bound: float = 0.25,
    fisher_coupling: float | None = None,
) -> FactorizationBehavior:
    """Check whether substitute factorization is (nearly) optimal under constraints."""
    from .bridge_fisher_adversarial import factorization_from_hypersurface

    problem, analysis = factorization_from_hypersurface(cross_info_bound=cross_info_bound)
    probe = problem.build_componentwise_probe()
    worst = problem.localize_worst_case()
    matches = abs(probe.objective_value - worst.objective_value) < 1e-6

    if fisher_coupling is not None:
        from .fisher_factorization import BlockLayout, QuadraticJointObjective, build_block_fisher

        layout = BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
        fisher = build_block_fisher(layout, off_diag_coupling=fisher_coupling)
        analysis = QuadraticJointObjective(
            fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0)
        ).factorization_analysis()

    return FactorizationBehavior(
        componentwise_matches_joint=matches,
        fisher_leakage=analysis.leakage.epsilon,
        fisher_gap=analysis.gap,
        separable_nearly_optimal=analysis.separable_nearly_optimal,
        cross_satisfies_bound=probe.satisfies_cross_bound,
    )


def evaluate_substitute(
    *,
    y: int = 2,
    a: int = 2,
    cross_info_bound: float = 0.25,
) -> SubstituteReport:
    """
    Full pipeline: formal obstruction + extremal selection + componentwise probe + limits.
    """
    obs = cardinality_obstruction(y, a)
    formal = FormalCoexponentialSpec()
    extremal = extremal_selection_on_polytope()
    problem = default_hypersurface_problem(cross_info_bound=cross_info_bound)
    probe = componentwise_factorization_probe(problem)
    fact = evaluate_factorization_behavior(cross_info_bound=cross_info_bound)

    if fact.separable_nearly_optimal and fact.componentwise_matches_joint:
        rec = (
            "Use extremal selection + componentwise probe; factorization is nearly optimal "
            "under current cross/Fisher leakage."
        )
    elif fact.componentwise_matches_joint:
        rec = "Componentwise probe matches joint vertex; prefer probe for construction."
    else:
        rec = (
            "Leakage too high for naive factorization; use joint vertex search on ext(H) "
            "or reduce cross-information."
        )

    modes = (
        SubstituteMode.EXTREMAL_SELECTION,
        SubstituteMode.COMPONENTWISE_PROBE,
    )
    if not formal.representable_in_set(y, a):
        modes = modes + (SubstituteMode.NEIGHBOR_VERTEX,)

    return SubstituteReport(
        formal_available=formal.representable_in_set(y, a),
        obstruction_reason=obs.reason,
        extremal=extremal,
        probe=probe,
        factorization=fact,
        substitute_modes_used=modes,
        limits=SubstituteLimits.catalog(),
        recommendation=rec,
    )


def neighbor_fallbacks() -> list[tuple[NeighborVertex, str]]:
    """When coexp is absent, these corners carry dual-flavored structure (not co-curry)."""
    return [(step.to_vertex, step.lesson) for step in walk_from_empty_coexponential()]


def substitute_summary() -> str:
    return (
        "Coexponential substitute (operational):\n"
        "  1. Extremal selection on ext(H) — Weierstrass + vertex localization.\n"
        "  2. Componentwise probe on coproduct blocks — factorization without coexp object.\n"
        "  3. Shadow penalty on COPRODUCT_COEXPONENTIAL corner — marks formal absence.\n"
        "Limits: no natural coexp in Set; projections break UP; large Fisher off-diagonals.\n"
    )


def demonstrate_substitute() -> list[str]:
    report = evaluate_substitute()
    hs = HypersurfaceBox(
        BoxBounds(lam=(0.0, 1.0), sigma=(0.0, 1.0), b=(0.0, 2.0), k=(0.0, 3.0))
    )
    box_max = hs.maximize_on_ext_H()

    lines = [
        "Formal coexponential in Set:",
        f"  available: {report.formal_available}",
        f"  obstruction: {report.obstruction_reason}",
        "",
        "Extremal-selection substitute:",
        f"  diagram vertex: {report.extremal.vertex.name}",
        f"  avoided shadow coexp corner: {report.extremal.avoided_shadow_corner}",
        f"  value: {report.extremal.value:.3f}",
        "",
        "Componentwise probe (factorization behavior):",
    ]
    if report.probe:
        lines.append(f"  assembled: {report.probe.to_theta().as_corner_tuple()}")
        lines.append(f"  objective: {report.probe.objective_value:.3f}")
        lines.append(f"  cross bound ok: {report.probe.satisfies_cross_bound}")
    if report.factorization:
        f = report.factorization
        lines.extend(
            [
                f"  probe matches joint: {f.componentwise_matches_joint}",
                f"  fisher leakage eps: {f.fisher_leakage:.4f}",
                f"  fisher gap: {f.fisher_gap:.6f}",
                f"  nearly optimal: {f.separable_nearly_optimal}",
            ]
        )
    lines.append(f"  box H corner (CCC): {box_max.theta_max.as_corner_tuple()}")
    lines.append("")
    lines.append(f"Recommendation: {report.recommendation}")
    lines.append("")
    lines.append("Limits:")
    for item in report.limits.items:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("Neighbor fallbacks (not coexponential):")
    for vtx, lesson in neighbor_fallbacks():
        lines.append(f"  - {vtx.name}: {lesson}")
    return lines
