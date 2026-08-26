"""
V-category enrichment: weighted Fisher as enrichment matrix.

Dual limits/colimits in a weighted lattice: colimit = max-plus with weights,
limit = min-plus. Fisher leakage becomes enrichment-weighted off-diagonal mass.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from .fisher_factorization import (
    BlockFisher,
    BlockLayout,
    QuadraticJointObjective,
    build_block_fisher,
)
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher


@dataclass(frozen=True)
class EnrichmentWeights:
    """
    Weights w_ij in V = (R_{>0}, x) acting on Fisher entries.

    W_ij scales sensitivity of block i to block j in the enriched sense.
    """

    block_weights: tuple[float, float] = (1.0, 1.0)
    cross_weight: float = 1.0

    def _block_index(self, layout: BlockLayout, coord: int) -> int:
        acc = 0
        for bi, size in enumerate(layout.sizes):
            if coord < acc + size:
                return bi
            acc += size
        return len(layout.sizes) - 1

    def scale_off_diag(self, fisher: BlockFisher) -> float:
        """Weighted Frobenius norm of off-diagonal blocks."""
        layout = fisher.layout
        n = layout.n
        slices = layout.slices()
        total = 0.0
        for bi, (i0, i1) in enumerate(slices):
            for bj, (j0, j1) in enumerate(slices):
                if bi == bj:
                    continue
                w = self.cross_weight * sqrt(
                    self.block_weights[bi] * self.block_weights[bj]
                )
                for i in range(i0, i1):
                    for j in range(j0, j1):
                        total += (w * fisher.matrix[i][j]) ** 2
        return sqrt(total)

    def scale_diag_norm(self, fisher: BlockFisher) -> float:
        total = 0.0
        for i in range(fisher.layout.n):
            bi = self._block_index(fisher.layout, i)
            w = self.block_weights[bi]
            total += (w * fisher.matrix[i][i]) ** 2
        return sqrt(total)

    def epsilon_weighted(self, fisher: BlockFisher) -> float:
        d = self.scale_diag_norm(fisher)
        if d <= 1e-12:
            return 0.0
        return self.scale_off_diag(fisher) / d


@dataclass(frozen=True)
class EnrichedColimitLimit:
    """
    Toy dual: colimit (coproduct side) = weighted max; limit = weighted min.

    On a 2-element diagram with weights w_0, w_1, colimit value is
    max(w_0 * x_0, w_1 * x_1); limit is min(w_0 * x_0, w_1 * x_1).
    """

    weights: tuple[float, float]

    def colimit(self, x0: float, x1: float) -> float:
        w0, w1 = self.weights
        return max(w0 * x0, w1 * x1)

    def limit(self, x0: float, x1: float) -> float:
        w0, w1 = self.weights
        return min(w0 * x0, w1 * x1)

    def gap_colimit_limit(self, x0: float, x1: float) -> float:
        return self.colimit(x0, x1) - self.limit(x0, x1)


def compare_epsilon_unweighted_vs_enriched(
    couplings: Sequence[float] = (0.0, 0.05, 0.1, 0.15, 0.2, 0.35),
    enrichments: Sequence[EnrichmentWeights] | None = None,
) -> list[dict[str, float]]:
    layout = BlockLayout(names=("A", "B"), sizes=(2, 2))
    enrichments = enrichments or (
        EnrichmentWeights(block_weights=(1.0, 1.0), cross_weight=1.0),
        EnrichmentWeights(block_weights=(1.0, 1.0), cross_weight=12.0),
        EnrichmentWeights(block_weights=(0.15, 0.15), cross_weight=1.0),
    )
    rows: list[dict[str, float]] = []
    for f in couplings:
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        eps_u = fisher.leakage().epsilon
        for ew in enrichments:
            eps_w = ew.epsilon_weighted(fisher)
            obj = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0))
            try:
                a = obj.factorization_analysis()
                gap = a.gap
            except ValueError:
                gap = float("nan")
            const = theorem_constants_from_fisher(
                fisher.leakage(),
                [fisher.matrix[i][i] for i in range(4)],
                theta_joint=(1.0, 0.5, 2.0, 3.0),
            )
            cert_u, _, _ = certify_suboptimality(eps_u, gap if gap == gap else 1e9, const)
            cert_w, _, _ = certify_suboptimality(eps_w, gap if gap == gap else 1e9, const)
            rows.append(
                {
                    "coupling": f,
                    "epsilon_unweighted": eps_u,
                    "epsilon_enriched": eps_w,
                    "block_w0": ew.block_weights[0],
                    "block_w1": ew.block_weights[1],
                    "cross_w": ew.cross_weight,
                    "cert_unweighted": float(cert_u),
                    "cert_enriched": float(cert_w),
                    "cert_flip": float(cert_u) != float(cert_w),
                }
            )
    return rows


def colimit_limit_sweep(
    x0: float = 1.0,
    x1: float = 2.0,
) -> list[dict[str, float]]:
    """How enrichment asymmetry widens colimit-limit gap."""
    out: list[dict[str, float]] = []
    for w0 in (0.5, 1.0, 2.0):
        for w1 in (0.5, 1.0, 2.0):
            el = EnrichedColimitLimit((w0, w1))
            out.append(
                {
                    "w0": w0,
                    "w1": w1,
                    "colimit": el.colimit(x0, x1),
                    "limit": el.limit(x0, x1),
                    "gap": el.gap_colimit_limit(x0, x1),
                }
            )
    return out
