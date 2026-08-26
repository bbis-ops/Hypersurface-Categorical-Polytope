"""
Fisher off-diagonal leakage and factorization of joint optimization.

Controlled dependence between parameter blocks appears as Fisher off-diagonals.
Small leakage implies the joint maximizer is close to separable (per-block)
optimization; quantify the gap and when separable is nearly optimal.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence


# --- Small dense linear algebra (stdlib only) ---


def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    return [sum(m[i][j] * v[j] for j in range(len(v))) for i in range(len(m))]


def _frobenius(m: list[list[float]]) -> float:
    return sqrt(sum(x * x for row in m for x in row))


def _solve_linear(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve A x = b by Gaussian elimination (n small)."""
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular Fisher matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [x / div for x in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [
                aug[row][c] - factor * aug[col][c] for c in range(n + 1)
            ]
    return [aug[i][n] for i in range(n)]


# --- Block-structured Fisher ---


@dataclass(frozen=True)
class BlockLayout:
    """Partition of coordinates into named blocks (sizes sum to n)."""

    names: tuple[str, ...]
    sizes: tuple[int, ...]

    @property
    def n(self) -> int:
        return sum(self.sizes)

    def slices(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        start = 0
        for s in self.sizes:
            out.append((start, start + s))
            start += s
        return out


@dataclass(frozen=True)
class LeakageReport:
    """Fisher off-diagonal leakage between blocks."""

    frobenius_off: float
    frobenius_diag: float
    normalized_leakage: float  # ||F_off||_F / ||F_diag||_F
    max_abs_off: float
    per_pair: dict[tuple[str, str], float]

    @property
    def epsilon(self) -> float:
        """Scalar leakage budget (normalized)."""
        return self.normalized_leakage


@dataclass(frozen=True)
class BlockFisher:
    """
    Fisher information matrix F (symmetric, typically PSD) with block layout.

    Off-diagonal blocks F_ij quantify dependence / information leakage between
    components. Small leakage => joint objective nearly factorizes.
    """

    layout: BlockLayout
    matrix: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        n = self.layout.n
        if len(self.matrix) != n or any(len(row) != n for row in self.matrix):
            raise ValueError("matrix size must match layout.n")
        for i in range(n):
            for j in range(i + 1, n):
                if abs(self.matrix[i][j] - self.matrix[j][i]) > 1e-9:
                    raise ValueError("Fisher matrix must be symmetric")

    def as_lists(self) -> list[list[float]]:
        return [list(row) for row in self.matrix]

    def leakage(self) -> LeakageReport:
        n = self.layout.n
        slices = self.layout.slices()
        full = self.as_lists()
        diag_blocks: list[list[float]] = [[0.0] * n for _ in range(n)]
        off_blocks: list[list[float]] = [[0.0] * n for _ in range(n)]
        for bi, (i0, i1) in enumerate(slices):
            for bj, (j0, j1) in enumerate(slices):
                for i in range(i0, i1):
                    for j in range(j0, j1):
                        if bi == bj:
                            diag_blocks[i][j] = full[i][j]
                        else:
                            off_blocks[i][j] = full[i][j]

        per_pair: dict[tuple[str, str], float] = {}
        names = self.layout.names
        for bi, (i0, i1) in enumerate(slices):
            for bj, (j0, j1) in enumerate(slices):
                if bi >= bj:
                    continue
                block = [
                    [off_blocks[i][j] for j in range(j0, j1)]
                    for i in range(i0, i1)
                ]
                per_pair[(names[bi], names[bj])] = _frobenius(block)

        fro_off = _frobenius(off_blocks)
        fro_diag = _frobenius(diag_blocks)
        norm = fro_off / fro_diag if fro_diag > 1e-12 else 0.0
        max_off = max(
            (abs(full[i][j]) for i in range(n) for j in range(n) if _block_index(i, slices) != _block_index(j, slices)),
            default=0.0,
        )
        return LeakageReport(
            frobenius_off=fro_off,
            frobenius_diag=fro_diag,
            normalized_leakage=norm,
            max_abs_off=max_off,
            per_pair=per_pair,
        )


def _block_index(i: int, slices: list[tuple[int, int]]) -> int:
    for bi, (lo, hi) in enumerate(slices):
        if lo <= i < hi:
            return bi
    return -1


def build_block_fisher(
    layout: BlockLayout,
    *,
    diag_value: float = 1.0,
    off_diag_coupling: float = 0.0,
    off_diag_per_pair: dict[tuple[str, str], float] | None = None,
) -> BlockFisher:
    """
    Construct PSD-ish Fisher with uniform or per-pair off-diagonal coupling.

    F_ii = diag_value * I, F_ij = coupling * 1 for i != j blocks (scalar blocks).
    """
    n = layout.n
    names = layout.names
    pair_map = off_diag_per_pair or {}
    mat = [[0.0] * n for _ in range(n)]
    slices = layout.slices()
    for bi, (i0, i1) in enumerate(slices):
        for i in range(i0, i1):
            mat[i][i] = diag_value
    for bi, (i0, i1) in enumerate(slices):
        for bj, (j0, j1) in enumerate(slices):
            if bi >= bj:
                continue
            c = pair_map.get((names[bi], names[bj]), off_diag_coupling)
            for i in range(i0, i1):
                for j in range(j0, j1):
                    mat[i][j] = c
                    mat[j][i] = c
    return BlockFisher(layout, tuple(tuple(row) for row in mat))


# --- Quadratic joint objective (local Fisher approximation) ---


@dataclass
class QuadraticJointObjective:
    """
    L(theta) = linear^T theta - 0.5 theta^T F theta  (joint log-likelihood proxy).

    Unconstrained maximizer solves F theta = linear (when F is positive definite).
    """

    fisher: BlockFisher
    linear: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.linear) != self.fisher.layout.n:
            raise ValueError("linear term dimension must match Fisher size")

    def value(self, theta: Sequence[float]) -> float:
        f = self.fisher.as_lists()
        n = len(theta)
        quad = 0.0
        for i in range(n):
            for j in range(n):
                quad += theta[i] * f[i][j] * theta[j]
        lin = sum(self.linear[i] * theta[i] for i in range(n))
        return lin - 0.5 * quad

    def joint_maximizer(self) -> list[float]:
        """Full coupled optimum (F theta = linear)."""
        return _solve_linear(self.fisher.as_lists(), list(self.linear))

    def separable_block_optimization(
        self,
        *,
        passes: int = 1,
        initial: Sequence[float] | None = None,
    ) -> list[float]:
        """
        Per-component optimization: optimize each block holding others fixed.

        One pass = Lemma (i) componentwise probe in the quadratic regime;
        multiple passes = block coordinate ascent.
        """
        n = self.fisher.layout.n
        theta = list(initial if initial is not None else [0.0] * n)
        f = self.fisher.as_lists()
        slices = self.fisher.layout.slices()

        for _ in range(passes):
            for (i0, i1) in slices:
                for i in range(i0, i1):
                    cross = self.linear[i]
                    for j in range(n):
                        if j == i:
                            continue
                        cross -= f[i][j] * theta[j]
                    theta[i] = cross / f[i][i]
        return theta

    def factorization_analysis(
        self,
        *,
        separable_passes: int = 1,
        nearly_optimal_tol: float = 1e-3,
    ) -> FactorizationAnalysis:
        """
        Compare joint vs separable optimizers; bound gap from Fisher leakage.
        """
        leak = self.fisher.leakage()
        theta_j = self.joint_maximizer()
        theta_s = self.separable_block_optimization(passes=separable_passes)
        lj = self.value(theta_j)
        ls = self.value(theta_s)
        gap = lj - ls
        bound = leakage_gap_bound(leak, self.fisher.as_lists(), theta_j)
        rel = gap / abs(lj) if abs(lj) > 1e-12 else gap
        nearly = (gap <= bound + 1e-9) or (
            rel <= nearly_optimal_tol and leak.normalized_leakage <= 0.15
        )
        return FactorizationAnalysis(
            leakage=leak,
            theta_joint=theta_j,
            theta_separable=theta_s,
            objective_joint=lj,
            objective_separable=ls,
            gap=gap,
            relative_gap=rel,
            theoretical_bound=bound,
            separable_nearly_optimal=nearly,
            separable_passes=separable_passes,
        )


@dataclass(frozen=True)
class FactorizationAnalysis:
    leakage: LeakageReport
    theta_joint: list[float]
    theta_separable: list[float]
    objective_joint: float
    objective_separable: float
    gap: float
    relative_gap: float
    theoretical_bound: float
    separable_nearly_optimal: bool
    separable_passes: int


def leakage_gap_bound(
    leak: LeakageReport,
    fisher: list[list[float]],
    theta_joint: Sequence[float] | None = None,
) -> float:
    """
    Upper bound on objective gap from separable vs joint (quadratic proxy).

    gap <= 0.5 * (epsilon^2 / lambda_min_diag) * ||theta_joint||^2
    with epsilon = normalized off-diagonal Frobenius leakage.
    """
    n = len(fisher)
    diag_min = min(fisher[i][i] for i in range(n))
    if diag_min <= 1e-12:
        diag_min = 1.0
    if theta_joint is not None:
        theta_norm_sq = sum(t * t for t in theta_joint)
    else:
        theta_norm_sq = 1.0
    eps = leak.normalized_leakage
    return 0.5 * (eps * eps / diag_min) * theta_norm_sq * leak.frobenius_diag


def coupling_from_cross_proxy(cross_information: float, *, diag: float = 1.0) -> float:
    """Map cross-information proxy (adversarial_probe) to Fisher off-diagonal."""
    return cross_information * diag


def nearly_optimal_when(
    leak: LeakageReport,
    *,
    epsilon_threshold: float = 0.1,
    gap_tol: float = 1e-2,
    analysis: FactorizationAnalysis | None = None,
) -> bool:
    """
    Separable optimization is (nearly) optimal when leakage and gap are small.
    """
    if leak.epsilon > epsilon_threshold:
        return False
    if analysis is None:
        return True
    return analysis.gap <= gap_tol or analysis.gap <= analysis.theoretical_bound + 1e-9


def factorization_summary() -> str:
    return (
        "Fisher factorization:\n"
        "  - Off-diagonal blocks F_ij = leakage between components.\n"
        "  - Joint L(theta): maximize with F theta = linear.\n"
        "  - Separable: per-block coordinate solve (one or more passes).\n"
        "  - Small normalized leakage => gap <= theoretical_bound; nearly optimal.\n"
    )


def demonstrate_fisher_factorization() -> list[str]:
    layout = BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
    lines: list[str] = []

    for eps in (0.0, 0.05, 0.15, 0.35):
        fisher = build_block_fisher(layout, off_diag_coupling=eps)
        obj = QuadraticJointObjective(
            fisher=fisher,
            linear=(1.0, 0.5, 2.0, 3.0),
        )
        analysis = obj.factorization_analysis(separable_passes=1)
        leak = analysis.leakage
        nearly = nearly_optimal_when(leak, analysis=analysis)
        lines.append(f"epsilon_coupling={eps:.2f}  normalized_leakage={leak.epsilon:.4f}")
        lines.append(
            f"  joint={analysis.objective_joint:.4f}  separable={analysis.objective_separable:.4f}  "
            f"gap={analysis.gap:.6f}  bound={analysis.theoretical_bound:.6f}"
        )
        lines.append(f"  nearly_optimal={nearly}  separable~=joint: {analysis.separable_nearly_optimal}")

    lines.append("")
    lines.append("Interpretation: eps->0 => factorization exact; large eps => per-block misses coupling.")
    return lines
