"""
Local adjudicators for an adversarial V.7--V.14 verification corpus.

Adjudication runs in two stages that may not see each other:

  scope   Does this candidate satisfy the theorem's hypotheses? Decided from
          the candidate alone, before any attempt to check whether the law
          holds. May answer `rejected`, `outside_scope`, or `inconclusive`.

  verdict Given an admitted candidate, does the law hold? May answer
          `verified`, `counterexample`, or `inconclusive` -- never
          `outside_scope`.

The separation is the point. A verifier that can retire a candidate as
"outside scope" *after* seeing that the law failed on it can shrink its own
denominator at will, and its pass rate stops meaning anything. Keeping the
stages apart means a case the verifier cannot resolve is recorded as
`inconclusive` -- an admission -- rather than as a hypothesis it never covered.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import cos, isfinite, log, pi, sin
from typing import Any

from .base_search import Candidate, combined_screen, screen_base
from .interaction_search import _local_max, compile_expression, screen_candidate
from .nonlinear_objective import default_nonlinear_bounds, vertex_maximize
from .base_search import CustomBase
from .hypersurface_box import Theta

#: Statuses a scope decision may assign.
SCOPE_STATUSES = frozenset({"rejected", "outside_scope", "inconclusive"})

#: Statuses a verdict may assign. `outside_scope` is deliberately absent: once a
#: candidate is admitted, the only honest outcomes are held, failed, or unknown.
VERDICT_STATUSES = frozenset({"verified", "counterexample", "inconclusive"})


@dataclass(frozen=True)
class VerificationRecord:
    law: str
    name: str
    expr: str
    base_expr: str = ""
    status: str = "inconclusive"
    reason: str = ""
    metrics: dict[str, Any] | None = None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScopeDecision:
    """Whether a candidate satisfies a theorem's hypotheses, and the evidence."""

    admitted: bool
    status: str = ""
    reason: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    #: The screen shared with the verdict stage, so it is measured only once.
    screen: Any = None

    def __post_init__(self) -> None:
        if not self.admitted and self.status not in SCOPE_STATUSES:
            raise ValueError(f"scope may not assign status {self.status!r}")


def _record(law: str, cand: Candidate, status: str, reason: str, metrics: dict[str, Any]) -> VerificationRecord:
    return VerificationRecord(law, cand.name, cand.expr, status=status, reason=reason,
                              metrics=metrics, note=cand.note)


def _verdict_record(
    law: str, cand: Candidate, outcome: tuple[str, str, dict[str, Any]]
) -> VerificationRecord:
    """Build a record from a verdict, enforcing that it stayed in its lane."""
    status, reason, metrics = outcome
    if status not in VERDICT_STATUSES:
        raise ValueError(f"verdict may not assign status {status!r}")
    return _record(law, cand, status, reason, metrics)


def _remeasure_exponent(cand: Candidate, s_hi: float, s_lo: float) -> float:
    """Use resolvable strengths for high exponents that underflow at s/4."""
    bounds = default_nonlinear_bounds()
    from .nonlinear_objective import HypersurfacePlusInteraction
    from .vertex_threshold import vertex_margin
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    corner = vertex_margin(base, bounds).theta
    perturbation = compile_expression(cand.expr)
    gaps = []
    for strength in (s_hi, s_lo):
        objective = lambda theta, q=strength: base(theta) + q * perturbation(theta)
        gaps.append(_local_max(objective, bounds, corner) - objective(corner))
    return log(gaps[0] / gaps[1]) / log(s_hi / s_lo) if min(gaps) > 1e-14 else 0.0


def _measure_gap(cand: Candidate, strength: float) -> float:
    bounds = default_nonlinear_bounds()
    from .nonlinear_objective import HypersurfacePlusInteraction
    from .vertex_threshold import vertex_margin
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    corner = vertex_margin(base, bounds).theta
    perturbation = compile_expression(cand.expr)
    objective = lambda theta: base(theta) + strength * perturbation(theta)
    return _local_max(objective, bounds, corner, passes=10, samples=800) - objective(corner)


def _measure_degree_one_polar_gap(
    cand: Candidate, strength: float, *, directions: int = 1441, radial_steps: int = 42
) -> float:
    """Independent global slack-plane search for V.9 creases and cones.

    Coordinate ascent can be trapped on one branch of ``abs(a*x-b*y)``.  This
    scans the full inward quadrant and maximizes the actual objective on every
    ray by ternary refinement.  It does not use the directional derivative
    coefficient being tested.
    """
    bounds = default_nonlinear_bounds()
    from .nonlinear_objective import HypersurfacePlusInteraction
    from .vertex_threshold import vertex_margin
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    corner = vertex_margin(base, bounds).theta
    perturbation = compile_expression(cand.expr)

    def value(radius: float, dx: float, dy: float) -> float:
        theta = Theta(corner.lam - radius * dx, corner.sigma + radius * dy,
                      corner.b, corner.k)
        return base(theta) + strength * perturbation(theta)

    corner_value = base(corner) + strength * perturbation(corner)
    best = corner_value
    for index in range(directions):
        angle = (pi / 2.0) * index / (directions - 1)
        dx, dy = cos(angle), sin(angle)
        radius_max = min(
            (bounds.lam[1] - bounds.lam[0]) / dx if dx > 1e-15 else float("inf"),
            (bounds.sigma[1] - bounds.sigma[0]) / dy if dy > 1e-15 else float("inf"),
        )
        left, right = 0.0, radius_max
        for _ in range(radial_steps):
            r1, r2 = (2.0 * left + right) / 3.0, (left + 2.0 * right) / 3.0
            v1, v2 = value(r1, dx, dy), value(r2, dx, dy)
            best = max(best, v1, v2)
            if v1 < v2:
                left = r1
            else:
                right = r2
    return best - corner_value


def _axis_homogeneities(cand: Candidate) -> dict[str, float]:
    """Leading degrees on each flat axis that the perturbation actually changes."""
    from .nonlinear_objective import HypersurfacePlusInteraction
    from .vertex_threshold import estimate_homogeneity, vertex_margin
    bounds = default_nonlinear_bounds()
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    corner = vertex_margin(base, bounds).theta
    perturbation = compile_expression(cand.expr)
    out = {}
    for axis in ("lam", "sigma"):
        moved = Theta(corner.lam - (1e-3 if axis == "lam" else 0.0),
                      corner.sigma + (1e-3 if axis == "sigma" else 0.0),
                      corner.b, corner.k)
        if abs(perturbation(moved) - perturbation(corner)) > 1e-10:
            # V.10 candidates deliberately include degree-two distractions.
            # At the generic h=1e-3 probe those terms can still bias a degree
            # near 1.65 by several tenths.  h=1e-6 remains numerically resolved
            # for the admitted expressions while exposing the leading degree.
            out[axis] = estimate_homogeneity(
                perturbation, corner, bounds, axis, h=1e-6
            )
    return out


def _adaptive_single_axis_exponent(cand: Candidate, axis: str) -> tuple[float, tuple[float, float]]:
    """Independent resolved 1-D measurement for tiny fractional gaps."""
    from .base_search import CustomBase, adaptive_axis_gap_exponent

    bounds = default_nonlinear_bounds()
    base = CustomBase(lambda theta: -(1.0 - theta.lam) ** 2 - theta.sigma**2)
    corner = Theta(bounds.lam[1], bounds.sigma[0], bounds.b[1], bounds.k[1])
    exponent, _, _, scales = adaptive_axis_gap_exponent(
        base, compile_expression(cand.expr), corner, bounds, axis
    )
    return exponent, scales


def _adaptive_separable_exponent(
    cand: Candidate, axes: tuple[str, ...]
) -> tuple[float, dict[str, list[float]]]:
    """Measure each active separable axis; equal homogeneity gives equal exponents."""
    readings: list[float] = []
    scales: dict[str, list[float]] = {}
    for axis in axes:
        exponent, pair = _adaptive_single_axis_exponent(cand, axis)
        if exponent <= 0.0:
            return 0.0, scales
        readings.append(exponent)
        scales[axis] = list(pair)
    if max(readings) - min(readings) > 0.15:
        return 0.0, scales
    return sum(readings) / len(readings), scales


def scope_interaction(law: str, cand: Candidate) -> ScopeDecision:
    """
    Decide whether `cand` satisfies the hypotheses of V.7--V.11.

    Every condition here is a property of the candidate and the fixed base. None
    of them consults whether the law subsequently holds, so admission cannot be
    withdrawn once the verdict is unwelcome.
    """
    result = screen_candidate(cand, s=0.01)
    metrics = {
        "regime": result.regime if result.ok else "rejected",
        "alpha": result.alpha,
        "predicted_exponent": result.predicted_exponent,
        "measured_exponent": result.gap_exponent,
        "predicted_gap": result.best_prediction,
        "measured_gap": result.measured_gap,
        "sampled_amplitude_bound": result.amp_bound,
        "coupled": result.coupled,
        "saturating": result.saturating,
    }
    if not result.ok:
        return ScopeDecision(False, "rejected", result.reason, metrics, result)
    if not all(isfinite(float(x)) for x in (result.alpha, result.measured_gap, result.amp_bound)):
        return ScopeDecision(False, "inconclusive", "non-finite local measurement", metrics, result)

    if law == "V.7":
        if not result.breaks or result.regime != "quadratic":
            return ScopeDecision(False, "outside_scope", "not a finite-slope separable breaker", metrics, result)
        return ScopeDecision(True, metrics=metrics, screen=result)

    if law in ("V.8", "V.10"):
        axis_alphas = _axis_homogeneities(cand)
        metrics["axis_alphas"] = axis_alphas
        theorem_alpha = (
            sum(axis_alphas.values()) / len(axis_alphas) if axis_alphas else result.alpha
        )
        metrics["theorem_alpha"] = theorem_alpha
        in_alpha = (
            (0.05 < theorem_alpha <= 1.05)
            if law == "V.8" else (1.05 < theorem_alpha < 1.95)
        )
        homogeneous_axes = bool(axis_alphas) and max(axis_alphas.values()) - min(axis_alphas.values()) <= 0.10
        local_controls_global = result.measured_gap <= result.amp_bound * 1.10 + 1e-10
        resolved_scope = result.breaks and result.regime == "fractional"
        # High V.10 exponents can put the initial s=.01 gap below the generic
        # optimizer's resolution. Axis homogeneity still identifies the formal
        # slice; whether a gap resolves is a verdict question, not a scope one.
        if law == "V.10" and in_alpha and homogeneous_axes:
            resolved_scope = True
        if not resolved_scope or not in_alpha or not homogeneous_axes or not local_controls_global:
            return ScopeDecision(False, "outside_scope", "measured homogeneity is outside this theorem slice", metrics, result)
        if law == "V.10":
            # The generic screen routes anything heuristically marked coupled
            # through the degree-one V.9 branch and can therefore leave a stale
            # exponent of 2.  V.10's own hypothesis supplies its prediction
            # directly from the locally measured homogeneous degree.
            metrics["screen_predicted_exponent"] = result.predicted_exponent
            metrics["predicted_exponent"] = 2.0 / (2.0 - theorem_alpha)
        return ScopeDecision(True, metrics=metrics, screen=result)

    if law == "V.9":
        if not result.breaks or result.regime != "coupled":
            return ScopeDecision(False, "outside_scope", "not a degree-one coupled breaker", metrics, result)
        return ScopeDecision(True, metrics=metrics, screen=result)

    if law == "V.11":
        if not result.breaks:
            return ScopeDecision(False, "outside_scope", "candidate did not dislodge the corner", metrics, result)
        return ScopeDecision(True, metrics=metrics, screen=result)

    raise ValueError(f"unsupported interaction law: {law}")


def _verdict_interaction(
    law: str, cand: Candidate, scope: ScopeDecision
) -> tuple[str, str, dict[str, Any]]:
    """Decide whether an admitted candidate satisfies V.7--V.11."""
    result = scope.screen
    metrics = dict(scope.metrics)

    if law == "V.7":
        # Accept a well-resolved initial estimate. Only shrink s when that
        # estimate disagrees; blindly shrinking tiny-slope cases pushes their
        # O(s^2) gaps below optimizer resolution and creates false survivors.
        holds = result.gap_exponent > 0 and abs(result.gap_exponent - 2.0) < 0.15
        if not holds:
            asymptotic = _remeasure_exponent(cand, 0.00125, 0.000625)
            metrics["measured_exponent_asymptotic"] = asymptotic
            holds = asymptotic > 0 and abs(asymptotic - 2.0) < 0.15
        return ("verified" if holds else "counterexample",
                "quadratic exponent matched" if holds else "in-scope exponent mismatch", metrics)

    if law in ("V.8", "V.10"):
        axis_alphas = metrics["axis_alphas"]
        # Prefer the already-resolved local estimate. Enlarging V.10 strengths
        # to 0.08/0.04 lets nominally higher-order distractions alter curvature
        # and creates a finite-scale exponent that the asymptotic theorem never
        # claims. Only fall back when the initial gap is below resolution.
        predicted_exponent = float(metrics["predicted_exponent"])
        tol = max(0.15, 0.10 * predicted_exponent)
        if law == "V.8":
            measured = _remeasure_exponent(cand, 0.000625, 0.0003125)
        elif result.gap_exponent > 0:
            measured = result.gap_exponent
            if abs(measured - predicted_exponent) > tol:
                measured, scales = _adaptive_separable_exponent(
                    cand, tuple(axis_alphas)
                )
                metrics["adaptive_measurement_scales"] = scales
        else:
            measured, scales = _adaptive_separable_exponent(cand, tuple(axis_alphas))
            metrics["adaptive_measurement_scales"] = scales
        if measured <= 0.0:
            # The candidate is inside the theorem slice -- scope already said so
            # on evidence that did not include this measurement. Failing to
            # resolve a gap here is the verifier's limit, not the theorem's
            # boundary, so it is recorded as an admission rather than banked as
            # a hypothesis this campaign never covered.
            return ("inconclusive", "no resolved inward fractional gap", metrics)
        metrics["measured_exponent_campaign"] = measured
        holds = measured > 0 and abs(measured - predicted_exponent) <= tol
        return ("verified" if holds else "counterexample",
                "fractional exponent matched" if holds else "in-scope exponent mismatch", metrics)

    if law == "V.9":
        small_s = 0.00125
        small_gap = _measure_degree_one_polar_gap(cand, small_s)
        high_gap = _measure_degree_one_polar_gap(cand, 0.0025)
        scaled_prediction = result.best_prediction * (small_s / 0.01) ** 2
        metrics["polar_measured_gap"] = small_gap
        # Both readings underflow together on a genuinely flat ray. Calling that
        # a directional-law mismatch would report the optimizer's floor as a
        # counterexample, so it is an admission instead.
        if min(high_gap, small_gap) <= 1e-14 or scaled_prediction <= 0:
            return ("inconclusive", "polar gap below resolution", metrics)
        ratio = small_gap / scaled_prediction
        asymptotic = log(high_gap / small_gap) / log(2.0)
        metrics["measured_to_directional_ratio"] = ratio
        metrics["measured_exponent_asymptotic"] = asymptotic
        holds = abs(asymptotic - 2.0) < 0.15 and 0.70 <= ratio <= 1.30
        return ("verified" if holds else "counterexample",
                "directional exponent and coefficient matched" if holds else "directional law mismatch", metrics)

    if law == "V.11":
        from .vertex_threshold import amplitude_bound
        perturbation = compile_expression(cand.expr)
        dense_bound = amplitude_bound(perturbation, default_nonlinear_bounds(), 0.01, steps=21)
        metrics["dense_amplitude_bound"] = dense_bound
        # A failure remains a numerical lead requiring an analytic supremum
        # check; the 21-grid is independent and denser, but still not interval arithmetic.
        holds = result.measured_gap <= dense_bound * 1.02 + 1e-10
        return ("verified" if holds else "counterexample",
                "measured gap stayed below dense amplitude ceiling" if holds else "dense sampled amplitude ceiling exceeded", metrics)

    raise ValueError(f"unsupported interaction law: {law}")


def verify_interaction(law: str, cand: Candidate) -> VerificationRecord:
    """Adjudicate V.7--V.11 against the fixed quadratic base."""
    scope = scope_interaction(law, cand)
    if not scope.admitted:
        return _record(law, cand, scope.status, scope.reason, scope.metrics)
    return _verdict_record(law, cand, _verdict_interaction(law, cand, scope))


def _dense_base_gap(cand: Candidate, *, steps: int = 101) -> tuple[bool, float]:
    """Independent 2-D grid witness for an off-corner base maximum."""
    r = compile_expression(cand.expr)
    base = CustomBase(r)
    bounds = default_nonlinear_bounds()
    _, vertex_value = vertex_maximize(base, bounds)
    best = float("-inf")
    for i in range(steps):
        lam = bounds.lam[0] + (bounds.lam[1] - bounds.lam[0]) * i / (steps - 1)
        for j in range(steps):
            sigma = bounds.sigma[0] + (bounds.sigma[1] - bounds.sigma[0]) * j / (steps - 1)
            best = max(best, base(Theta(lam, sigma, bounds.b[1], bounds.k[1])))
    return best > vertex_value + 1e-8, best - vertex_value


def scope_base(law: str, cand: Candidate) -> ScopeDecision:
    """
    Decide whether a base objective satisfies V.12's or V.13's hypotheses.

    For V.13 the hypothesis *is* the existence of an off-corner maximum, so the
    independent dense witness is a scope question, decided before the finite
    guard's performance is looked at.
    """
    result = screen_base(cand)
    metrics = {
        "flatness_order": result.flatness_order,
        "predicted_exponent": result.predicted_exponent,
        "measured_exponent": result.measured_exponent,
        "base_self_fails": result.base_self_fails,
        "search_method": result.search_method,
        "legacy_grid_missed": result.legacy_grid_missed,
    }
    if not result.ok:
        return ScopeDecision(False, "rejected", result.reason, metrics, result)
    if law == "V.12":
        if result.base_self_fails or not result.breaks or result.predicted_exponent <= 0:
            return ScopeDecision(False, "outside_scope", "base is not an in-scope flat corner", metrics, result)
        return ScopeDecision(True, metrics=metrics, screen=result)
    if law == "V.13":
        try:
            dense_fails, dense_gap = _dense_base_gap(cand)
        except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
            return ScopeDecision(False, "rejected", f"dense check failed: {exc}", metrics, result)
        metrics["dense_grid_self_failure"] = dense_fails
        metrics["dense_grid_vertex_gap"] = dense_gap
        if not dense_fails:
            return ScopeDecision(False, "outside_scope", "independent dense grid found no off-vertex maximum", metrics, result)
        return ScopeDecision(True, metrics=metrics, screen=result)
    raise ValueError(f"unsupported base law: {law}")


def _verdict_base(
    law: str, cand: Candidate, scope: ScopeDecision
) -> tuple[str, str, dict[str, Any]]:
    """Decide whether an admitted base objective satisfies V.12 or V.13."""
    result = scope.screen
    metrics = dict(scope.metrics)
    if law == "V.12":
        return ("verified" if result.law_holds else "counterexample",
                "master exponent matched" if result.law_holds else "in-scope exponent mismatch", metrics)
    if law == "V.13":
        caught = result.base_self_fails
        metrics["adversarial_guard_missed"] = not caught
        # The independent witness confirms V.13 either way. A miss refutes the
        # finite guard, not the theorem that off-corner base maxima exist.
        return ("verified",
                "adversarial guard caught independent off-vertex witness" if caught
                else "V.13 witness confirmed; finite adversarial guard missed it",
                metrics)
    raise ValueError(f"unsupported base law: {law}")


def verify_base(law: str, cand: Candidate) -> VerificationRecord:
    scope = scope_base(law, cand)
    if not scope.admitted:
        return _record(law, cand, scope.status, scope.reason, scope.metrics)
    return _verdict_record(law, cand, _verdict_base(law, cand, scope))


def scope_combined(base: Candidate, pert: Candidate) -> ScopeDecision:
    """Decide whether a (base, perturbation) pair satisfies V.14's hypotheses."""
    result = combined_screen(base, pert)
    metrics = {
        "beta": result.beta,
        "alpha": result.alpha,
        "axis": result.axis,
        "predicted_exponent": result.predicted_exponent,
        "measured_exponent": result.measured_exponent,
        "weighted_degree": result.weighted_degree,
        "active_axes": list(result.active_axes),
        "base_orders": dict(result.base_orders),
        "base_self_fails": result.base_self_fails,
        "measurement_scales": list(result.measurement_scales),
    }
    if not result.ok:
        return ScopeDecision(False, "rejected", result.reason, metrics, result)
    if result.base_self_fails or not result.breaks or result.predicted_exponent <= 0:
        return ScopeDecision(False, "outside_scope",
                             result.reason or "pair does not satisfy weighted coercive-corner hypotheses",
                             metrics, result)
    return ScopeDecision(True, metrics=metrics, screen=result)


def verify_combined(base: Candidate, pert: Candidate) -> VerificationRecord:
    scope = scope_combined(base, pert)
    name = base.name.removesuffix("_b")
    record = VerificationRecord("V.14", name, pert.expr, base_expr=base.expr,
                                metrics=scope.metrics, note=base.note or pert.note)
    if not scope.admitted:
        return VerificationRecord(**{**record.as_dict(), "status": scope.status,
                                     "reason": scope.reason})
    result = scope.screen
    if result.measured_exponent <= 0.0:
        # Admitted, but no gap resolved at any strength the screen tried. That
        # is the verifier's limit, not a failure of the law - the same call
        # V.8/V.10 make. Banking it as a counterexample would inflate the
        # finding count with measurement noise.
        return VerificationRecord(**{**record.as_dict(), "status": "inconclusive",
                                     "reason": "no resolved weighted gap"})
    status = "verified" if result.law_holds else "counterexample"
    if status not in VERDICT_STATUSES:  # pragma: no cover - guarded by construction
        raise ValueError(f"verdict may not assign status {status!r}")
    reason = ("weighted unified exponent matched" if result.law_holds
              else f"in-scope weighted exponent mismatch "
                   f"(|{result.measured_exponent:.3f} - {result.predicted_exponent:.3f}| "
                   f">= {result.tolerance:.3f})")
    return VerificationRecord(**{**record.as_dict(), "status": status, "reason": reason})
