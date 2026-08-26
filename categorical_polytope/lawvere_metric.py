"""
Lawvere metric enrichment: distance-weighted Fisher and homs.

In a metric-enriched category, hom-objects carry a cost d(x,y).
Fisher leakage is weighted by exp(-d(block_i, block_j)) so distant
blocks leak less in the enriched norm.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from typing import Sequence

from .fisher_factorization import BlockFisher, BlockLayout, build_block_fisher
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .fisher_factorization import QuadraticJointObjective


@dataclass(frozen=True)
class LawvereMetric:
    """
    Block metric d(i,j) >= 0; enrichment weight w_ij = exp(-d_ij).

    Small distance => strong cross-block sensitivity in enriched Fisher.
    """

    distances: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        n = len(self.distances)
        if n == 0 or any(len(row) != n for row in self.distances):
            raise ValueError("distances must be a square matrix")
        for row in self.distances:
            for d in row:
                if d < 0:
                    raise ValueError("Lawvere distances must be non-negative")

    @classmethod
    def two_blocks(cls, d_01: float = 0.5) -> LawvereMetric:
        return cls(((0.0, d_01), (d_01, 0.0)))

    def weight(self, i: int, j: int) -> float:
        return exp(-self.distances[i][j])

    def epsilon_metric(self, fisher: BlockFisher) -> float:
        layout = fisher.layout
        slices = layout.slices()
        off = 0.0
        diag = 0.0
        for bi, (i0, i1) in enumerate(slices):
            for bj, (j0, j1) in enumerate(slices):
                w = self.weight(bi, bj)
                for i in range(i0, i1):
                    for j in range(j0, j1):
                        val = fisher.matrix[i][j]
                        if bi == bj:
                            diag += (w * val) ** 2
                        else:
                            off += (w * val) ** 2
        if diag <= 1e-12:
            return 0.0
        return sqrt(off) / sqrt(diag)


@dataclass(frozen=True)
class MetricColimitLimit:
    """
    Metric colimit: min over paths of (cost + value).
    Metric limit: max of (value - cost) on dual picture (toy max-min).
    """

    metric: LawvereMetric
    values: tuple[float, float]

    def colimit_cost(self) -> float:
        """Weighted min: pick branch with lower metric-adjusted cost."""
        v0, v1 = self.values
        d01 = self.metric.distances[0][1]
        via_0 = v0
        via_1 = v1 - d01
        return max(via_0, via_1)

    def limit_cost(self) -> float:
        v0, v1 = self.values
        d01 = self.metric.distances[0][1]
        return min(v0 + d01, v1)

    def gap(self) -> float:
        return self.colimit_cost() - self.limit_cost()


def compare_lawvere_vs_plain(
    couplings: Sequence[float] = (0.0, 0.1, 0.15, 0.2),
    distances: Sequence[float] = (0.0, 0.3, 1.0, 2.0),
) -> list[dict[str, float]]:
    layout = BlockLayout(names=("A", "B"), sizes=(2, 2))
    rows: list[dict[str, float]] = []
    for f in couplings:
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        eps_plain = fisher.leakage().epsilon
        for d in distances:
            met = LawvereMetric.two_blocks(d)
            eps_m = met.epsilon_metric(fisher)
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
            cu, _, _ = certify_suboptimality(eps_plain, gap if gap == gap else 1e9, const)
            cm, _, _ = certify_suboptimality(eps_m, gap if gap == gap else 1e9, const)
            rows.append(
                {
                    "coupling": f,
                    "block_distance": d,
                    "epsilon_plain": eps_plain,
                    "epsilon_lawvere": eps_m,
                    "weight_cross": exp(-d),
                    "cert_plain": float(cu),
                    "cert_lawvere": float(cm),
                }
            )
    return rows


def metric_colimit_limit_sweep() -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    for d in (0.0, 0.5, 1.0, 2.0):
        m = LawvereMetric.two_blocks(d)
        ml = MetricColimitLimit(m, (1.0, 2.0))
        out.append(
            {
                "distance": d,
                "colimit": ml.colimit_cost(),
                "limit": ml.limit_cost(),
                "gap": ml.gap(),
            }
        )
    return out
