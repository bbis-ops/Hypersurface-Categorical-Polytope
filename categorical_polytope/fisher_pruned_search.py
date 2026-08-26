"""
Theorem 3 algorithm: Fisher-pruned vertex search with Phi(epsilon) certificate.

Pseudocode:
  V_A, V_B = vertices of block projections
  top-k by marginal score
  evaluate feasible pairs; return best + certificate
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adversarial_probe import CoupledProblem, default_hypersurface_problem
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .fisher_factorization import BlockLayout, QuadraticJointObjective, build_block_fisher
from .fisher_factorization import build_block_fisher, coupling_from_cross_proxy
from .hypersurface_box import BoxBounds, HypersurfaceBox, Theta
from .vertex_probe import VertexProbeAlgorithm


def _default_bounds() -> BoxBounds:
    return BoxBounds(lam=(0.0, 1.0), sigma=(0.0, 1.0), b=(0.0, 2.0), k=(0.0, 3.0))


@dataclass
class FisherPrunedVertexSearch:
    """
    Constructive near-optimal probe with top-k pruning per block.

    Complexity: O(k^2 * #blocks) evaluations vs O(4^n) full vertex product.
    """

    bounds: BoxBounds = field(default_factory=_default_bounds)
    fisher_epsilon: float = 0.25
    top_k: int = 4
    cross_info_bound: float | None = None

    def __post_init__(self) -> None:
        if self.cross_info_bound is None:
            self.cross_info_bound = self.fisher_epsilon

    def _vertices_r_block(self) -> list[tuple[float, float]]:
        return [
            (lam, sigma)
            for lam in self.bounds.lam
            for sigma in self.bounds.sigma
        ]

    def _vertices_c_block(self) -> list[tuple[float, float]]:
        return [(b, k) for b in self.bounds.b for k in self.bounds.k]

    def marginal_score_r(self, lam: float, sigma: float) -> float:
        hs = HypersurfaceBox(self.bounds)
        return hs.objective.r(Theta(lam, sigma, 0, 0), self.bounds)

    def marginal_score_c(self, b: float, k: float) -> float:
        hs = HypersurfaceBox(self.bounds)
        return hs.objective.C(Theta(0, 0, b, k))

    def full_score(self, theta: Theta) -> float:
        return HypersurfaceBox(self.bounds).objective.composite(theta, self.bounds)

    def run(self) -> NearOptimalProbeResult:
        problem = default_hypersurface_problem(
            cross_info_bound=self.cross_info_bound or 0.25,
            bounds=self.bounds,
        )

        r_verts = self._vertices_r_block()
        c_verts = self._vertices_c_block()
        r_ranked = sorted(r_verts, key=lambda t: self.marginal_score_r(*t), reverse=True)
        c_ranked = sorted(c_verts, key=lambda t: self.marginal_score_c(*t), reverse=True)
        k = min(self.top_k, len(r_ranked), len(c_ranked))
        r_top = r_ranked[:k]
        c_top = c_ranked[:k]

        best_theta = Theta(*r_top[0], *c_top[0])
        best_val = float("-inf")
        pairs_checked = 0
        for lam, sigma in r_top:
            for b, kc in c_top:
                pairs_checked += 1
                theta = Theta(lam, sigma, b, kc)
                from .adversarial_probe import BlockAssignment

                if self.cross_info_bound is not None and not problem.feasible(
                    [
                        BlockAssignment("r_block", {"lam": lam, "sigma": sigma}),
                        BlockAssignment("C_block", {"b": b, "k": kc}),
                    ]
                ):
                    continue
                val = self.full_score(theta)
                if val > best_val:
                    best_val, best_theta = val, theta

        # Full ext(H) reference for gap certificate
        full = VertexProbeAlgorithm(
            bounds=self.bounds,
            cross_info_bound=self.cross_info_bound,
        ).find_near_optimal_probe()

        if best_val == float("-inf"):
            best_theta = full.theta
            best_val = full.objective_value

        probe_gap = full.objective_value - best_val
        layout = problem.blocks
        fisher = build_block_fisher(
            BlockLayout(
                tuple(b.name for b in layout),
                tuple(len(b.variables) for b in layout),
            ),
            off_diag_coupling=coupling_from_cross_proxy(self.fisher_epsilon),
        )
        linear = (1.0, 0.5, 2.0, 3.0)
        factor = QuadraticJointObjective(fisher=fisher, linear=linear).factorization_analysis()
        leak = factor.leakage
        constants = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(fisher.layout.n)],
            full.theta.as_corner_tuple(),
        )
        certified, phi, reason = certify_suboptimality(
            leak.epsilon,
            factor.gap,
            constants,
        )

        return NearOptimalProbeResult(
            theta=best_theta,
            objective_value=best_val,
            full_vertex_value=full.objective_value,
            gap=factor.gap,
            probe_gap=probe_gap,
            phi_bound=phi,
            certified=certified,
            certify_reason=reason,
            factorization_gap=factor.gap,
            pairs_checked=pairs_checked,
            top_k=k,
            epsilon=self.fisher_epsilon,
            epsilon_0=constants.epsilon_0,
        )


@dataclass(frozen=True)
class NearOptimalProbeResult:
    theta: Theta
    objective_value: float
    full_vertex_value: float
    gap: float  # joint - separable (Theorem 2)
    probe_gap: float  # full vertex search - pruned value
    phi_bound: float
    certified: bool
    certify_reason: str
    factorization_gap: float
    pairs_checked: int
    top_k: int
    epsilon: float
    epsilon_0: float

