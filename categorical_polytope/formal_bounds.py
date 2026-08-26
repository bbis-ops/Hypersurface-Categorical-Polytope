"""
Explicit theorem constants: epsilon_0 and Phi(epsilon).

Matches docs/FORMAL_THEOREMS.md — stability modulus for separable near-optimality.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from .fisher_factorization import LeakageReport, leakage_gap_bound


@dataclass(frozen=True)
class TheoremConstants:
    """
    Threshold epsilon_0 and gap modulus Phi(epsilon).

    epsilon_0: below this normalized leakage, separable decomposition is certified
               (design rule default 0.10; theory uses diag curvature).
    Phi:       upper bound on C(theta*) - C(theta_sep).
    """

    epsilon_0: float
    lambda_min_diag: float
    theta_norm: float
    frobenius_diag: float

    def Phi(self, epsilon: float) -> float:
        """Phi(epsilon) -> 0 as epsilon -> 0. Lipschitz-style modulus."""
        if epsilon <= 0:
            return 0.0
        return 0.5 * (epsilon * epsilon / self.lambda_min_diag) * (
            self.theta_norm**2
        ) * self.frobenius_diag

    def delta(self, epsilon: float) -> float:
        """Probe construction error delta(epsilon) <= Phi(epsilon)."""
        return self.Phi(epsilon)

    def separable_certified(self, epsilon: float) -> bool:
        return epsilon <= self.epsilon_0


def epsilon_0_explicit(
    *,
    lambda_min_diag: float,
    slope_sum: float = 2.0,
    quasiconvex_curvature: float = 1.0,
) -> float:
    """
    Explicit epsilon_0 (Theorem 2 / design rule).

    epsilon_0 = lambda_min(F_diag) / (slope_sum + quasiconvex_curvature)

    slope_sum: combined Lipschitz constants for monotone blocks g, h.
    quasiconvex_curvature: maximal curvature of r along lambda, sigma axes.
    """
    denom = slope_sum + quasiconvex_curvature
    if denom <= 0:
        return 0.1
    return min(0.25, lambda_min_diag / denom)


def theorem_constants_from_fisher(
    leak: LeakageReport,
    fisher_diag: list[float],
    theta_joint: Sequence[float],
    *,
    slope_sum: float = 2.0,
    quasiconvex_curvature: float = 1.0,
) -> TheoremConstants:
    diag_min = min(fisher_diag)
    if diag_min <= 1e-12:
        diag_min = 1.0
    norm = sqrt(sum(t * t for t in theta_joint))
    eps0 = epsilon_0_explicit(
        lambda_min_diag=diag_min,
        slope_sum=slope_sum,
        quasiconvex_curvature=quasiconvex_curvature,
    )
    return TheoremConstants(
        epsilon_0=eps0,
        lambda_min_diag=diag_min,
        theta_norm=norm,
        frobenius_diag=leak.frobenius_diag,
    )


def certify_suboptimality(
    epsilon: float,
    gap_observed: float,
    constants: TheoremConstants,
    *,
    require_epsilon_threshold: bool = True,
    relative_gap_tol: float | None = None,
) -> tuple[bool, float, str]:
    """
    Certificate (Theorem 2): gap_observed <= Phi(epsilon) and epsilon <= epsilon_0.

    Returns (certified, Phi(epsilon), reason).
    """
    phi = constants.Phi(epsilon)
    gap_ok = gap_observed <= phi + 1e-9
    eps_ok = epsilon <= constants.epsilon_0
    rel_ok = True
    if relative_gap_tol is not None and phi > 1e-12:
        rel_ok = (gap_observed / phi) <= (1.0 + relative_gap_tol)

    if require_epsilon_threshold and not eps_ok:
        return False, phi, f"epsilon={epsilon:.4f} > epsilon_0={constants.epsilon_0:.4f}"
    if not gap_ok:
        return False, phi, f"gap={gap_observed:.4f} > Phi(epsilon)={phi:.4f}"
    if not rel_ok:
        return False, phi, "relative gap exceeds tolerance vs Phi(epsilon)"
    return True, phi, "gap <= Phi(epsilon) and epsilon <= epsilon_0"


def certify_from_analysis(
    analysis: object,
    constants: TheoremConstants | None = None,
) -> tuple[bool, float, str]:
    """Certify separable factorization from FactorizationAnalysis."""
    from .fisher_factorization import FactorizationAnalysis

    if not isinstance(analysis, FactorizationAnalysis):
        raise TypeError("expected FactorizationAnalysis")
    leak = analysis.leakage
    const = constants or theorem_constants_from_fisher(
        leak,
        [analysis.theta_joint[i] if i < len(analysis.theta_joint) else 1.0 for i in range(4)],
        theta_joint=analysis.theta_joint,
    )
    return certify_suboptimality(
        leak.epsilon,
        analysis.gap,
        const,
        require_epsilon_threshold=True,
    )
