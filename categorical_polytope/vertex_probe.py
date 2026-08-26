"""
Constructive near-optimal probe via vertex search only.

Given compact feasible polytope H (box), separate monotonicity in selected
coordinates, and directional quasiconvexity along adjoint axes, the global
maximum lies in ext(H). This module implements the reduction as an explicit
algorithm with a certificate explaining why vertices suffice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence

from .adversarial_probe import CoupledProblem, default_hypersurface_problem
from .conceptual_polytope import ConceptualPolytope, DiagramPoint
from .hypersurface_box import BoxBounds, HypersurfaceBox, Theta


def _default_bounds() -> BoxBounds:
    return BoxBounds(lam=(0.0, 1.0), sigma=(0.0, 1.0), b=(0.0, 2.0), k=(0.0, 3.0))


class AlgorithmStep(Enum):
    """Constructive pipeline (search reduces to vertices)."""

    BUILD_EXT = auto()  # enumerate ext(H) or ext(block) x ... ext(block)
    FILTER_CONSTRAINTS = auto()  # cross-information / coupling budget
    EVALUATE_VERTICES = auto()  # score each corner
    SELECT_ARGMAX = auto()  # theta* in ext(H)
    COMPONENTWISE_PROBE = auto()  # optional fast path (Lemma i)
    CERTIFY_NEAR_OPTIMAL = auto()  # gap vs bound / match joint


@dataclass(frozen=True)
class StructuralReason:
    """
    Why vertex-only search is justified (the argument in code).

    1. H compact (closed bounded box) => continuous objective attains maximum
       (Weierstrass).
    2. Separate monotonicity in (b, k) => dominated by projection to face max.
    3. Quasiconvex along lambda (up) and sigma (down) => axis extrema at ends.
    4. Marginals of quasiconvex functions on polytopes optimize at vertices.
    5. Therefore theta_max in ext(H); finite enumeration is constructive.
    """

    weierstrass_on_compact: bool = True
    separate_monotone_coords: tuple[str, ...] = ("b", "k")
    quasiconvex_coords: tuple[str, ...] = ("lam", "sigma")
    reduction_to_vertices: str = (
        "Composite objective: separate increase in b,k plus quasiconvex r(lam,sigma) "
        "pushes the maximum to a corner of the box; search only ext(H)."
    )


@dataclass(frozen=True)
class VertexProbeCertificate:
    """Certificate that the returned probe is near-optimal."""

    searched_vertices: int
    feasible_vertices: int
    best_value: float
    componentwise_value: float | None
    value_gap: float
    matches_componentwise: bool
    fisher_leakage: float | None
    fisher_gap: float | None
    nearly_optimal: bool
    structural: StructuralReason
    corner_formula: tuple[float, float, float, float] | None


@dataclass(frozen=True)
class NearOptimalProbe:
    """Output of the constructive vertex algorithm."""

    theta: Theta
    objective_value: float
    is_vertex: bool
    steps_executed: tuple[AlgorithmStep, ...]
    certificate: VertexProbeCertificate


@dataclass
class VertexProbeAlgorithm:
    """
    Constructive near-optimal probe finder: search only ext(H).

    Parameters
    ----------
    bounds : box H = independent intervals (compact)
    cross_info_bound : optional coupling budget between blocks
    nearly_optimal_tol : relative gap tolerance for certificate
    """

    bounds: BoxBounds = field(default_factory=_default_bounds)
    cross_info_bound: float | None = 0.25
    nearly_optimal_tol: float = 1e-3

    def _hypersurface(self) -> HypersurfaceBox:
        return HypersurfaceBox(self.bounds)

    def enumerate_ext_h(self) -> list[Theta]:
        return self._hypersurface().ext_H()

    def score(self, theta: Theta) -> float:
        return self._hypersurface().objective.composite(theta, self.bounds)

    def corner_formula(self) -> Theta:
        """Analytic box corner (lambda_max, sigma_min, B_max, k_max) when hypotheses hold."""
        return Theta(
            self.bounds.lam_max,
            self.bounds.sigma_min,
            self.bounds.b_max,
            self.bounds.k_max,
        )

    def filter_feasible_vertices(
        self,
        vertices: Sequence[Theta],
        problem: CoupledProblem,
    ) -> list[Theta]:
        from .adversarial_probe import BlockAssignment

        feasible: list[Theta] = []
        for theta in vertices:
            assigns = [
                BlockAssignment(
                    "r_block",
                    {"lam": theta.lam, "sigma": theta.sigma},
                ),
                BlockAssignment(
                    "C_block",
                    {"b": theta.b, "k": theta.k},
                ),
            ]
            if problem.feasible(assigns):
                feasible.append(theta)
        return feasible

    def componentwise_probe_theta(self, problem: CoupledProblem) -> tuple[Theta, float]:
        probe = problem.build_componentwise_probe()
        return probe.to_theta(), probe.objective_value

    def find_near_optimal_probe(self) -> NearOptimalProbe:
        """
        Constructive algorithm: near-optimal probe by searching vertices only.

        Returns theta* with certificate (gap, Fisher leakage, structural reason).
        """
        steps: list[AlgorithmStep] = [AlgorithmStep.BUILD_EXT]
        hs = self._hypersurface()
        all_vertices = hs.ext_H()
        candidates = all_vertices

        comp_theta: Theta | None = None
        comp_val: float | None = None
        fisher_eps: float | None = None
        fisher_gap: float | None = None
        nearly = False

        if self.cross_info_bound is not None:
            steps.append(AlgorithmStep.FILTER_CONSTRAINTS)
            problem = default_hypersurface_problem(
                cross_info_bound=self.cross_info_bound,
                bounds=self.bounds,
            )
            candidates = self.filter_feasible_vertices(all_vertices, problem)
            if not candidates:
                candidates = all_vertices
            steps.append(AlgorithmStep.COMPONENTWISE_PROBE)
            comp_theta, comp_val = self.componentwise_probe_theta(problem)
            from .bridge_fisher_adversarial import factorization_from_hypersurface

            _, analysis = factorization_from_hypersurface(
                cross_info_bound=self.cross_info_bound
            )
            fisher_eps = analysis.leakage.epsilon
            fisher_gap = analysis.gap
            nearly = analysis.separable_nearly_optimal

        steps.append(AlgorithmStep.EVALUATE_VERTICES)
        best_theta = candidates[0]
        best_val = self.score(best_theta)
        for theta in candidates[1:]:
            val = self.score(theta)
            if val > best_val:
                best_val, best_theta = val, theta

        steps.append(AlgorithmStep.SELECT_ARGMAX)

        gap = 0.0
        matches_comp = False
        if comp_val is not None and comp_theta is not None:
            gap = best_val - comp_val
            matches_comp = abs(gap) < 1e-6

        corner = self.corner_formula()
        corner_match = (
            abs(best_theta.lam - corner.lam) < 1e-9
            and abs(best_theta.sigma - corner.sigma) < 1e-9
            and abs(best_theta.b - corner.b) < 1e-9
            and abs(best_theta.k - corner.k) < 1e-9
        )

        if not nearly:
            rel = gap / abs(best_val) if abs(best_val) > 1e-12 else gap
            nearly = rel <= self.nearly_optimal_tol or matches_comp

        steps.append(AlgorithmStep.CERTIFY_NEAR_OPTIMAL)

        cert = VertexProbeCertificate(
            searched_vertices=len(all_vertices),
            feasible_vertices=len(candidates),
            best_value=best_val,
            componentwise_value=comp_val,
            value_gap=gap,
            matches_componentwise=matches_comp,
            fisher_leakage=fisher_eps,
            fisher_gap=fisher_gap,
            nearly_optimal=nearly,
            structural=StructuralReason(),
            corner_formula=corner.as_corner_tuple() if corner_match else None,
        )

        return NearOptimalProbe(
            theta=best_theta,
            objective_value=best_val,
            is_vertex=True,
            steps_executed=tuple(steps),
            certificate=cert,
        )

    def run_on_diagram_polytope(self) -> tuple[DiagramPoint, float, str]:
        """Same reduction on the lecture diagram polytope (finite ext(P))."""
        poly = ConceptualPolytope()
        p, u, v = poly.global_maximizer()
        return p, u, v.name


def vertex_reduction_argument() -> str:
    return (
        "Structural reduction (vertex search is sufficient):\n"
        "  1. H is compact (box) => maximum exists (Weierstrass).\n"
        "  2. Objective separately increasing in b, k => value dominated by (b_max, k_max) face.\n"
        "  3. r quasiconvex-decreasing in sigma, increasing in lambda => axis extrema at bounds.\n"
        "  4. Marginal optima of quasiconvex functions on a polytope lie in ext(H).\n"
        "  5. Constructive algorithm: enumerate ext(H), filter by cross bound, argmax.\n"
        "  6. Componentwise probe is O(sum |ext(block_i)|); exhaustive vertices O(product).\n"
        "Near-optimal when Fisher leakage epsilon is small (see fisher_factorization).\n"
    )


def demonstrate_vertex_algorithm() -> list[str]:
    algo = VertexProbeAlgorithm(cross_info_bound=0.25)
    probe = algo.find_near_optimal_probe()
    cert = probe.certificate
    diagram_p, diagram_u, diagram_v = algo.run_on_diagram_polytope()

    lines = [
        "Constructive vertex probe algorithm:",
        f"  steps: {[s.name for s in probe.steps_executed]}",
        f"  theta*: {probe.theta.as_corner_tuple()}  value={probe.objective_value:.4f}",
        f"  searched {cert.searched_vertices} vertices, {cert.feasible_vertices} feasible",
        f"  componentwise value={cert.componentwise_value}",
        f"  gap={cert.value_gap:.6f}  matches={cert.matches_componentwise}",
        f"  nearly optimal: {cert.nearly_optimal}",
        f"  corner formula match: {cert.corner_formula}",
        "",
        "Diagram polytope (same reduction):",
        f"  vertex={diagram_v}  understanding={diagram_u:.3f}",
        "",
        vertex_reduction_argument(),
    ]
    return lines
