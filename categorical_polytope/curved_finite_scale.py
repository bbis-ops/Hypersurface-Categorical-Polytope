"""Rational finite-scale bounds for an exactly transported quadratic channel.

The full reduced polynomial gives a one-variable upper envelope. Bernstein
coefficients bound it on a partition of the retained-coordinate projection;
verified feasible points give lower bounds for the full objective. Neither
floating point optimization nor a fitted exponent enters the certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import heapq
from math import comb, isfinite
import re
from typing import Any, Mapping, Sequence

from .curved_reduction import QuadraticReduction


MAX_DEGREE = 32
MAX_SUBDIVISIONS = 1024
MAX_WORKING_BITS = 4096
POWER_PRECISION_BITS = 96


class _ResourceLimit(Exception):
    pass


def _rational(value: Any, name: str) -> Q:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Q)):
        raise ValueError(f"finite_scale.{name} must be a rational number")
    if isinstance(value, int) and value.bit_length() > 1024:
        raise ValueError(f"finite_scale.{name} is too large")
    if isinstance(value, Q):
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > 1024:
            raise ValueError(f"finite_scale.{name} is too large")
    literal = str(value).strip()
    if len(literal) > 256:
        raise ValueError(f"finite_scale.{name} exceeds 256 characters")
    decimal = re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?", literal)
    rational = re.fullmatch(r"[+-]?[0-9]+/[0-9]+", literal)
    if not (decimal or rational):
        raise ValueError(f"finite_scale.{name} must be a finite rational number")
    if decimal and decimal[1] and abs(int(decimal[1])) > 1000:
        raise ValueError(f"finite_scale.{name} decimal exponent exceeds 1000")
    try:
        return Q(literal)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"finite_scale.{name} must be a finite rational number") from exc


@dataclass(frozen=True)
class FiniteScaleRequest:
    s: Q
    relative_tolerance: Q = Q(1, 10)
    max_subdivisions: int = 512

    def __post_init__(self) -> None:
        for name in ("s", "relative_tolerance"):
            object.__setattr__(self, name, _rational(getattr(self, name), name))
        if self.s <= 0:
            raise ValueError("finite_scale.s must be positive")
        if not 0 <= self.relative_tolerance < 1:
            raise ValueError("finite_scale.relative_tolerance must lie in [0, 1)")
        if (isinstance(self.max_subdivisions, bool)
                or not isinstance(self.max_subdivisions, int)
                or not 0 <= self.max_subdivisions <= MAX_SUBDIVISIONS):
            raise ValueError(f"finite_scale.max_subdivisions must be an integer in [0, {MAX_SUBDIVISIONS}]")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> FiniteScaleRequest:
        if not isinstance(payload, Mapping):
            raise ValueError("finite_scale must be an object")
        unknown = set(payload) - {"s", "relative_tolerance", "max_subdivisions"}
        if unknown:
            raise ValueError("unknown finite_scale field: " + ", ".join(sorted(map(str, unknown))))
        if "s" not in payload:
            raise ValueError("finite_scale.s is required")
        return cls(**payload)


def _check_size(values: Sequence[Q]) -> None:
    if any(max(v.numerator.bit_length(), v.denominator.bit_length()) > MAX_WORKING_BITS
           for v in values):
        raise _ResourceLimit("rational_size_limit")


def _number(value: Q) -> dict[str, Any]:
    try:
        approximate = float(value)
        if not isfinite(approximate) or (value and approximate == 0):
            approximate = None
    except OverflowError:
        approximate = None
    return {"exact": str(value), "value": approximate}


def _interval(lower: Q, upper: Q) -> dict[str, Any]:
    return {"lower": _number(lower), "upper": _number(upper)}


def _evaluate(terms: Mapping[int, Q], y: Q) -> Q:
    return sum((c * y**k for k, c in terms.items()), Q(0))


def _power_interval(base: Q, power: Q) -> tuple[Q, Q]:
    """Enclose a positive rational power using rational bisection only."""
    target = base**power.numerator
    _check_size([target])
    n = power.denominator
    if n == 1:
        return target, target
    # A power-of-two bracket avoids an absolute precision floor near zero.
    k = target.numerator.bit_length() - target.denominator.bit_length()
    if Q(2)**k > target:
        k -= 1
    lower, upper = Q(2)**(k // n), Q(2)**(k // n + 1)
    if lower**n == target:
        return lower, lower
    for _ in range(POWER_PRECISION_BITS):
        middle = (lower + upper) / 2
        powered = middle**n
        if powered == target:
            return middle, middle
        if powered < target:
            lower = middle
        else:
            upper = middle
    return lower, upper


def _bernstein(terms: Mapping[int, Q], extent: Q) -> tuple[Q, ...]:
    """Power coefficients on [0, extent] -> Bernstein coefficients on [0, 1]."""
    degree = max(terms, default=0)
    scaled = {k: c * extent**k for k, c in terms.items()}
    result = tuple(sum((c * Q(comb(i, k), comb(degree, k))
                        for k, c in scaled.items() if k <= i), Q(0))
                   for i in range(degree + 1))
    _check_size(result)
    return result


def _subdivide(coefficients: tuple[Q, ...]) -> tuple[tuple[Q, ...], tuple[Q, ...]]:
    """Exact de Casteljau subdivision at the interval midpoint."""
    row = coefficients
    left, right = [row[0]], [row[-1]]
    while len(row) > 1:
        row = tuple((a + b) / 2 for a, b in zip(row, row[1:]))
        left.append(row[0])
        right.append(row[-1])
    result = tuple(left), tuple(reversed(right))
    _check_size(result[0] + result[1])
    return result


def _projection_bound(rows: Sequence[tuple[Q, Q, Q]]) -> Q:
    """Eliminate x from ax+by<=c, including x,y>=0, by exact inequalities."""
    upper_x = [(a, b, c) for a, b, c in rows if a > 0]
    lower_x = [(a, b, c) for a, b, c in rows if a < 0]
    projected = [(b, c) for a, b, c in rows if a == 0]
    for a, b, c in upper_x:
        for d, e, f in lower_x:
            projected.append((b / a - e / d, c / a - f / d))
    bounds = [c / b for b, c in projected if b > 0]
    if not bounds or min(bounds) <= 0:
        raise ValueError("finite-scale assessment requires a bounded positive retained projection")
    return min(bounds)


def _assessment(lower: Q, upper: Q, prediction: tuple[Q, Q], tolerance: Q
                ) -> tuple[str, Q, Q, Q]:
    ratio_lower, ratio_upper = lower / prediction[1], upper / prediction[0]
    error = max(abs(ratio_lower - 1), abs(ratio_upper - 1))
    if error <= tolerance:
        status = "within_tolerance"
    elif ratio_lower > 1 + tolerance or ratio_upper < 1 - tolerance:
        status = "outside_tolerance"
    else:
        status = "not_resolved"
    return status, ratio_lower, ratio_upper, error


def certify_finite_scale(
    reduction: QuadraticReduction, request: FiniteScaleRequest, *,
    chart_rows: Sequence[Sequence[Q]], chart_rhs: Sequence[Q], axes: tuple[str, str],
) -> dict[str, Any]:
    """Bound the gap on a bounded full-dimensional nonnegative edge chart.

    The caller supplies the exact full-polynomial reduction and transported
    constraints, with the origin feasible. The polyhedral backend proves these
    prerequisites. Coordinate nonnegativity is part of this domain contract.
    """
    result: dict[str, Any] = {
        "status": "not_resolved", "bounds_certified": False,
        "s": _number(request.s), "relative_tolerance": _number(request.relative_tolerance),
        "gap_interval": None, "prediction_interval": None, "gap_to_prediction_ratio": None,
        "relative_error_bound": None, "witness": None,
        "method": "rational_bernstein_envelope_and_feasible_witness",
        "limits": {"max_degree": MAX_DEGREE, "max_subdivisions": request.max_subdivisions,
                   "max_working_bits": MAX_WORKING_BITS, "power_precision_bits": POWER_PRECISION_BITS},
    }
    degree = max(reduction.retained_base_order, reduction.eliminated_base_order,
                 max(reduction.reduced), max(reduction.driver))
    if degree > MAX_DEGREE:
        return {**result, "reason": "degree_limit"}
    if (set(axes) != {reduction.eliminated_axis, reduction.retained_axis}
            or len(axes) != 2 or len(chart_rows) != len(chart_rhs)
            or any(len(row) != 2 for row in chart_rows) or any(b < 0 for b in chart_rhs)):
        raise ValueError("finite-scale constraints must describe the feasible origin in the stated chart")
    xi, yi = axes.index(reduction.eliminated_axis), axes.index(reduction.retained_axis)
    rows = [(Q(row[xi]), Q(row[yi]), Q(b)) for row, b in zip(chart_rows, chart_rhs)]
    # Explicit nonnegative coordinates also handle callers omitting redundant rows.
    rows.extend([(Q(-1), Q(0), Q(0)), (Q(0), Q(-1), Q(0))])
    s, alpha, q = request.s, reduction.reduced_order, reduction.retained_base_order
    terms = {k: s * c for k, c in reduction.reduced.items()}
    terms[q] = terms.get(q, Q(0)) - reduction.retained_base_coefficient
    terms = {k: c for k, c in terms.items() if c}
    try:
        _check_size([v for row in rows for v in row] + list(terms.values())
                    + list(reduction.driver.values()) + [reduction.eliminated_base_coefficient,
                       reduction.penalty_coefficient, reduction.scale_base])
        extent = _projection_bound(rows)
        _check_size([extent])
        coefficients = _bernstein(terms, extent)
        power = _power_interval(reduction.scale_base * s, Q(alpha, q - alpha))
        prefactor = reduction.reduced[alpha] * Q(q - alpha, q) * s
        prediction = tuple(prefactor * v for v in power)
        _check_size(prediction)
    except _ResourceLimit as exc:
        return {**result, "reason": str(exc)}

    best_value, envelope_lower = Q(0), Q(0)
    witness: dict[str, Any] = {}

    def sample(y: Q) -> None:
        nonlocal best_value, envelope_lower, witness
        center = _evaluate(reduction.driver, y) / (2 * reduction.penalty_coefficient)
        lower_x, upper_x = Q(0), None
        for a, b, c in rows:
            rhs = c - b * y
            if a > 0:
                upper_x = rhs / a if upper_x is None else min(upper_x, rhs / a)
            elif a < 0:
                lower_x = max(lower_x, rhs / a)
            elif rhs < 0:
                return
        if upper_x is not None and lower_x > upper_x:
            return
        x = max(lower_x, center if upper_x is None else min(center, upper_x))
        envelope = _evaluate(terms, y)
        base_cost = reduction.eliminated_base_coefficient * x**reduction.eliminated_base_order
        square_cost = s * reduction.penalty_coefficient * (x - center)**2
        value = envelope - base_cost - square_cost
        slacks = [c - a*x - b*y for a, b, c in rows]
        _check_size([x, y, envelope, value, base_cost, square_cost] + slacks)
        envelope_lower = max(envelope_lower, envelope)
        if value > best_value or not witness:
            best_value = value
            witness = {
                "kind": "square_center" if x == center else "clipped_square_center",
                "coordinates_exact": {reduction.eliminated_axis: str(x), reduction.retained_axis: str(y)},
                "feasible": True, "constraint_slacks_exact": [str(v) for v in slacks[:-2]],
                "nonnegative_coordinates": True, "objective_gain": _number(value),
                "omitted_base_cost": _number(base_cost), "square_penalty_cost": _number(square_cost),
            }

    # Every unpruned leaf remains in the heap until its children are certified.
    heap = [(-max(coefficients), 0, Q(0), extent, coefficients)]
    count, serial, reason = 0, 0, "subdivision_limit"
    try:
        sample(Q(0))
        sample(extent)
        sample(extent / 2)
        while heap:
            upper = max(best_value, -heap[0][0])
            if _assessment(best_value, upper, prediction, request.relative_tolerance)[0] != "not_resolved":
                reason = "tolerance_decided"
                break
            if upper - envelope_lower <= prediction[0] / 2**40:
                reason = "envelope_relaxation_gap"
                break
            if count >= request.max_subdivisions:
                break
            _, _, left, right, coeffs = heap[0]
            midpoint = (left + right) / 2
            children = _subdivide(coeffs)
            sample((left + midpoint) / 2)
            sample((midpoint + right) / 2)
            heapq.heappop(heap)
            count += 1
            for lo, hi, child in ((left, midpoint, children[0]), (midpoint, right, children[1])):
                upper_child = max(child)
                if upper_child > best_value:
                    serial += 1
                    heapq.heappush(heap, (-upper_child, serial, lo, hi, child))
    except _ResourceLimit as exc:
        reason = str(exc)
    upper = max(best_value, -heap[0][0]) if heap else best_value
    status, ratio_lower, ratio_upper, error = _assessment(
        best_value, upper, prediction, request.relative_tolerance)
    if status != "not_resolved":
        reason = "tolerance_decided"
    return {
        **result, "status": status, "reason": reason, "bounds_certified": True,
        "gap_interval": _interval(best_value, upper), "prediction_interval": _interval(*prediction),
        "gap_to_prediction_ratio": _interval(ratio_lower, ratio_upper),
        "relative_error_bound": _number(error), "witness": witness,
        "envelope": {"polynomial_exact": {str(k): str(c) for k, c in sorted(terms.items())},
                     "retained_axis": reduction.retained_axis,
                     "retained_projection": _interval(Q(0), extent),
                     "maximum_interval": _interval(envelope_lower, upper),
                     "subdivisions": count},
        "proof": {"upper": "full reduced envelope bounded by rational Bernstein coefficients",
                  "lower": "full objective evaluated at an exactly feasible rational witness",
                  "comparison": "rational enclosure of L*s**gamma with coefficients fixed",
                  "transport": "exact inward chart preserves feasible points and objective values"},
    }
