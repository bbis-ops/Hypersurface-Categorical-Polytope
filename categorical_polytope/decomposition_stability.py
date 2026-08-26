"""
Robustness of coproduct-like decompositions to small independence violations.

In statistical models, approximate factorization p(theta) ~ p1(theta1) p2(theta2)
corresponds to small Fisher off-diagonals between blocks. This module gives
explicit stability bounds and design rules for when separable optimization is safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import sqrt
from typing import Sequence

from .fisher_factorization import (
    BlockFisher,
    BlockLayout,
    FactorizationAnalysis,
    LeakageReport,
    QuadraticJointObjective,
    build_block_fisher,
    leakage_gap_bound,
)


class DecompositionStrategy(Enum):
    """Design rule output: which optimization path to use."""

    SEPARABLE_PROBE = auto()  # coproduct split + componentwise (epsilon small)
    VERTEX_SEARCH = auto()  # ext(H) exhaustive when box + compact
    JOINT_SOLVE = auto()  # coupled F theta = c (epsilon large)
    BLOCK_COORDINATE_ASCENT = auto()  # middle leakage: multiple passes


@dataclass(frozen=True)
class StabilityBounds:
    """
    Explicit bounds under Fisher leakage epsilon = ||F_off||_F / ||F_diag||_F.

    Local quadratic / Gaussian approximation around the MLE.
    """

    epsilon: float
    objective_gap_bound: float
    objective_gap_observed: float
    relative_gap: float
    theta_displacement_bound: float
    theta_displacement_observed: float
    independence_valid: bool  # epsilon below safe threshold

    def within_bounds(self, *, tol: float = 1e-6) -> bool:
        return (
            self.objective_gap_observed <= self.objective_gap_bound + tol
            and self.theta_displacement_observed <= self.theta_displacement_bound + tol
        )


@dataclass(frozen=True)
class DesignRule:
    id: str
    condition: str
    action: str


@dataclass(frozen=True)
class DesignRulebook:
    """Operational rules for coproduct-like splits under approximate independence."""

    rules: tuple[DesignRule, ...]
    epsilon_safe: float = 0.10
    epsilon_moderate: float = 0.25
    epsilon_unsafe: float = 0.35

    @staticmethod
    def default() -> DesignRulebook:
        return DesignRulebook(
            rules=(
                DesignRule(
                    "R1",
                    "normalized leakage epsilon <= epsilon_safe",
                    "Use separable coproduct probe; decomposition stable.",
                ),
                DesignRule(
                    "R2",
                    "epsilon_safe < epsilon <= epsilon_moderate",
                    "Run block coordinate ascent (2+ passes); verify gap <= bound.",
                ),
                DesignRule(
                    "R3",
                    "epsilon > epsilon_moderate OR gap_observed > gap_bound",
                    "Escalate to joint solve or full vertex search on ext(H).",
                ),
                DesignRule(
                    "R4",
                    "per_pair leakage ||F_ij||_F dominates",
                    "Refine block partition: merge or re-index coupled coordinates.",
                ),
                DesignRule(
                    "R5",
                    "objective relative_gap <= 1e-3 and within_bounds",
                    "Certify near-optimal; categorical coproduct split is robust.",
                ),
            ),
        )

    def recommend(self, epsilon: float, *, gap_ratio: float, within_bound: bool) -> DecompositionStrategy:
        if epsilon <= self.epsilon_safe and (within_bound or gap_ratio <= 1e-3):
            return DecompositionStrategy.SEPARABLE_PROBE
        if epsilon <= self.epsilon_moderate:
            return DecompositionStrategy.BLOCK_COORDINATE_ASCENT
        if epsilon <= self.epsilon_unsafe:
            return DecompositionStrategy.VERTEX_SEARCH
        return DecompositionStrategy.JOINT_SOLVE


@dataclass(frozen=True)
class DecompositionStabilityReport:
    """Full robustness assessment for a coproduct-like split."""

    layout: BlockLayout
    leakage: LeakageReport
    bounds: StabilityBounds
    analysis: FactorizationAnalysis
    strategy: DecompositionStrategy
    rulebook: DesignRulebook
    coproduct_robust: bool
    summary: str


def _theta_displacement(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def theta_displacement_bound(
    leak: LeakageReport,
    fisher: list[list[float]],
    theta_joint: Sequence[float],
) -> float:
    """
    Parameter stability: ||theta_joint - theta_sep|| <= (epsilon / lambda_min) ||theta_joint||.

    Perturbation bound when F = D + E with ||E||_F ~ epsilon * ||D||_F.
    """
    diag_min = min(fisher[i][i] for i in range(len(fisher)))
    if diag_min <= 1e-12:
        diag_min = 1.0
    norm = sqrt(sum(t * t for t in theta_joint))
    return (leak.normalized_leakage / diag_min) * norm


def assess_decomposition(
    fisher: BlockFisher,
    linear: tuple[float, ...],
    *,
    rulebook: DesignRulebook | None = None,
    separable_passes: int = 1,
) -> DecompositionStabilityReport:
    """
    Quantify robustness of a coproduct split to small independence violations.

    Maps statistical dependence -> Fisher off-diagonals -> gap + displacement bounds.
    """
    rb = rulebook or DesignRulebook.default()
    obj = QuadraticJointObjective(fisher=fisher, linear=linear)
    analysis = obj.factorization_analysis(separable_passes=separable_passes)
    leak = analysis.leakage
    f = fisher.as_lists()
    disp_obs = _theta_displacement(analysis.theta_joint, analysis.theta_separable)
    disp_bnd = theta_displacement_bound(leak, f, analysis.theta_joint)
    obj_bnd = leakage_gap_bound(leak, f, analysis.theta_joint)

    bounds = StabilityBounds(
        epsilon=leak.epsilon,
        objective_gap_bound=obj_bnd,
        objective_gap_observed=analysis.gap,
        relative_gap=analysis.relative_gap,
        theta_displacement_bound=disp_bnd,
        theta_displacement_observed=disp_obs,
        independence_valid=leak.epsilon <= rb.epsilon_safe,
    )

    strategy = rb.recommend(
        leak.epsilon,
        gap_ratio=abs(analysis.relative_gap),
        within_bound=bounds.within_bounds(),
    )
    robust = (
        bounds.independence_valid
        and analysis.separable_nearly_optimal
        and bounds.within_bounds()
    )

    if robust:
        summary = (
            f"Coproduct decomposition stable (eps={leak.epsilon:.4f}): "
            "separable probe certified near-optimal."
        )
    elif strategy is DecompositionStrategy.BLOCK_COORDINATE_ASCENT:
        summary = (
            f"Moderate dependence (eps={leak.epsilon:.4f}): "
            "use extra block passes or monitor per-pair F_ij."
        )
    else:
        summary = (
            f"Decomposition stressed (eps={leak.epsilon:.4f}, gap={analysis.gap:.4f}): "
            "do not rely on independence; joint optimization required."
        )

    return DecompositionStabilityReport(
        layout=fisher.layout,
        leakage=leak,
        bounds=bounds,
        analysis=analysis,
        strategy=strategy,
        rulebook=rb,
        coproduct_robust=robust,
        summary=summary,
    )


def independence_violation_from_coupling(
    off_diag_coupling: float,
    diag_value: float = 1.0,
) -> float:
    """
    Scalar coupling in Fisher ~ statistical dependence strength.

    For 2 scalar blocks, off_diag / diag approximates correlation scale.
    """
    if diag_value <= 0:
        return 0.0
    return abs(off_diag_coupling) / diag_value


def robustness_sweep(
    layout: BlockLayout | None = None,
    linear: tuple[float, ...] = (1.0, 0.5, 2.0, 3.0),
    couplings: Sequence[float] = (0.0, 0.05, 0.10, 0.15, 0.25, 0.35),
) -> list[DecompositionStabilityReport]:
    """Stability curve: coproduct robustness vs independence violation."""
    layout = layout or BlockLayout(names=("block_A", "block_B"), sizes=(2, 2))
    reports: list[DecompositionStabilityReport] = []
    for c in couplings:
        fisher = build_block_fisher(layout, off_diag_coupling=c)
        try:
            reports.append(assess_decomposition(fisher, linear))
        except ValueError:
            # Strong coupling: Fisher nearly singular — joint solve ill-conditioned
            reports.append(_stressed_report(layout, fisher, linear, coupling=c))
    return reports


def _stressed_report(
    layout: BlockLayout,
    fisher: BlockFisher,
    linear: tuple[float, ...],
    *,
    coupling: float,
) -> DecompositionStabilityReport:
    """Fallback when joint maximizer is ill-posed (large dependence)."""
    rb = DesignRulebook.default()
    leak = fisher.leakage()
    obj = QuadraticJointObjective(fisher=fisher, linear=linear)
    theta_s = obj.separable_block_optimization(passes=3)
    ls = obj.value(theta_s)
    bounds = StabilityBounds(
        epsilon=leak.epsilon,
        objective_gap_bound=float("inf"),
        objective_gap_observed=float("inf"),
        relative_gap=1.0,
        theta_displacement_bound=float("inf"),
        theta_displacement_observed=0.0,
        independence_valid=False,
    )
    analysis = FactorizationAnalysis(
        leakage=leak,
        theta_joint=theta_s,
        theta_separable=theta_s,
        objective_joint=ls,
        objective_separable=ls,
        gap=0.0,
        relative_gap=0.0,
        theoretical_bound=float("inf"),
        separable_nearly_optimal=False,
        separable_passes=3,
    )
    return DecompositionStabilityReport(
        layout=layout,
        leakage=leak,
        bounds=bounds,
        analysis=analysis,
        strategy=DecompositionStrategy.JOINT_SOLVE,
        rulebook=rb,
        coproduct_robust=False,
        summary=(
            f"Strong dependence (coupling={coupling:.2f}, eps={leak.epsilon:.3f}): "
            "Fisher ill-conditioned; coproduct split not robust — use joint model."
        ),
    )


def stability_framework_summary() -> str:
    return (
        "Coproduct decomposition robustness (statistical view):\n"
        "  - Exact independence <=> F_off = 0 <=> coproduct factorization exact.\n"
        "  - Small violation <=> small epsilon = ||F_off||_F / ||F_diag||_F.\n"
        "  - Objective gap <= 0.5 * (eps^2 / lambda_min) * ||theta*||^2 * ||F_diag||_F.\n"
        "  - Parameter drift <= (eps / lambda_min) * ||theta*||.\n"
        "  - Design: separable if eps<=0.1; coordinate ascent if moderate; else joint.\n"
    )


def design_rules_text(rulebook: DesignRulebook | None = None) -> list[str]:
    rb = rulebook or DesignRulebook.default()
    lines = [
        f"Thresholds: safe<={rb.epsilon_safe}, moderate<={rb.epsilon_moderate}, "
        f"unsafe>{rb.epsilon_unsafe}",
        "",
    ]
    for rule in rb.rules:
        lines.append(f"  {rule.id}: IF {rule.condition} THEN {rule.action}")
    return lines


def demonstrate_robustness() -> list[str]:
    reports = robustness_sweep()
    lines = [
        "Robustness sweep (independence violation -> Fisher coupling):",
        "",
    ]
    for r in reports:
        b = r.bounds
        lines.append(
            f"  coupling~eps={r.leakage.epsilon:.3f}  "
            f"gap={b.objective_gap_observed:.4f} (bound {b.objective_gap_bound:.4f})  "
            f"disp={b.theta_displacement_observed:.4f} (bound {b.theta_displacement_bound:.4f})"
        )
        lines.append(
            f"    strategy={r.strategy.name}  robust={r.coproduct_robust}  {r.summary}"
        )
    lines.append("")
    lines.extend(design_rules_text())
    lines.append("")
    lines.append(stability_framework_summary())
    return lines
