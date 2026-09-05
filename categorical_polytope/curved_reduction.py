"""Certified quadratic elimination of a curved asymptotic channel.

For exact localized data D=A*x**p+B*y**q and
R=-a*x**2+x*H(y)+K(y), complete the square before reading a degree.
The reduced polynomial is S=H**2/(4*a)+K. If H has positive leading
coefficient and order r, S has positive leading coefficient C and order
0<alpha<q, and p*r>q, then the local gap is asymptotic to L*s**gamma,
gamma=q/(q-alpha). See docs/FORMAL_CURVED_REDUCTION.md for the proof.

This is a sufficient certificate for an exact two-variable model, not a
general solver for signed polynomials or arbitrary principal remainders.
All structural calculations are rational; floats are display values only.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


Signature = tuple[int, int]
MAX_DRIVER_TERMS = 128


class ReductionNotApplicable(ValueError):
    """The supplied data do not satisfy this sufficient reduction theorem."""


def _number(value: Fraction) -> dict[str, Any]:
    try:
        approximate = float(value)
    except OverflowError:
        approximate = None
    return {"exact": str(value), "value": approximate}


def _univariate(terms: Mapping[int, Fraction]) -> list[dict[str, Any]]:
    return [{"power": power, "coefficient": _number(coefficient)}
            for power, coefficient in sorted(terms.items())]


@dataclass(frozen=True)
class QuadraticReduction:
    """An exact square identity and the checks licensing its local asymptotic."""

    eliminated_axis: str
    retained_axis: str
    eliminated_base_coefficient: Fraction
    retained_base_coefficient: Fraction
    eliminated_base_order: int
    retained_base_order: int
    penalty_coefficient: Fraction
    driver: Mapping[int, Fraction]
    remainder: Mapping[int, Fraction]
    reduced: Mapping[int, Fraction]

    @property
    def driver_order(self) -> int:
        return min(self.driver)

    @property
    def reduced_order(self) -> int:
        return min(self.reduced)

    @property
    def effective_weight(self) -> Fraction:
        return Fraction(self.reduced_order, self.retained_base_order)

    @property
    def exponent(self) -> Fraction:
        return 1 / (1 - self.effective_weight)

    @property
    def omitted_base_exponent(self) -> Fraction:
        return Fraction(self.eliminated_base_order * self.driver_order,
                        self.retained_base_order - self.reduced_order)

    @property
    def scale_base(self) -> Fraction:
        return (self.reduced_order * self.reduced[self.reduced_order]
                / (self.retained_base_order * self.retained_base_coefficient))

    def leading_coefficient(self) -> dict[str, Any]:
        alpha, q = self.reduced_order, self.retained_base_order
        prefactor = self.reduced[alpha] * Fraction(q - alpha, q)
        power = Fraction(alpha, q - alpha)
        exact = (str(prefactor * self.scale_base ** power.numerator)
                 if power.denominator == 1
                 else f"({prefactor}) * ({self.scale_base})**({power})")
        try:
            value = float(prefactor) * float(self.scale_base) ** float(power)
            if not isfinite(value) or value <= 0:
                value = None
        except (OverflowError, ZeroDivisionError):
            value = None
        return {"exact": exact, "value": value, "prefactor": _number(prefactor),
                "power_base": _number(self.scale_base), "power": _number(power)}

    def witness(self, s: float) -> dict[str, float]:
        """Evaluate the asymptotically sharp feasible curve for small s.

        Membership in a particular bounded polyhedron must still be checked
        at a finite s. The theorem only guarantees membership eventually.
        """
        if not isfinite(s) or s <= 0:
            raise ValueError("s must be finite and positive")
        y = (float(self.scale_base) * s) ** (
            1 / (self.retained_base_order - self.reduced_order)
        )
        x = sum(float(c) * y**k for k, c in self.driver.items()) / (
            2 * float(self.penalty_coefficient)
        )
        return {self.eliminated_axis: x, self.retained_axis: y}

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": "quadratic_square_completion",
            "eliminated_axis": self.eliminated_axis,
            "retained_axis": self.retained_axis,
            "base": {
                self.eliminated_axis: {"order": self.eliminated_base_order,
                                      "coefficient": _number(self.eliminated_base_coefficient)},
                self.retained_axis: {"order": self.retained_base_order,
                                    "coefficient": _number(self.retained_base_coefficient)},
            },
            "penalty_coefficient": _number(self.penalty_coefficient),
            "driver_polynomial": _univariate(self.driver),
            "remainder_polynomial": _univariate(self.remainder),
            "reduced_polynomial": _univariate(self.reduced),
            "identity": "R = S(y) - a*(x - H(y)/(2*a))**2",
            "identity_variables": {"x": self.eliminated_axis, "y": self.retained_axis},
            "checks": {
                "exact_diagonal_base": True,
                "driver_positive_near_origin": True,
                "reduced_positive_near_origin": True,
                "reduced_order_below_base": True,
                "omitted_base_is_subleading": True,
                "order_margin": self.eliminated_base_order * self.driver_order
                                - self.retained_base_order,
            },
            "effective_weight": _number(self.effective_weight),
            "response_exponent": _number(self.exponent),
            "leading_coefficient": self.leading_coefficient(),
            "witness": {
                "retained_coordinate": "y_s = (scale_base*s)**(1/(q-alpha))",
                "eliminated_coordinate": "x_s = H(y_s)/(2*a)",
                "scale_base": _number(self.scale_base),
                "coordinate_exponents": {
                    self.eliminated_axis: _number(Fraction(
                        self.driver_order, self.retained_base_order - self.reduced_order)),
                    self.retained_axis: _number(Fraction(
                        1, self.retained_base_order - self.reduced_order)),
                },
                "omitted_base_exponent": _number(self.omitted_base_exponent),
                "interpretation": "asymptotically sharp witness, not an exact optimizer formula",
            },
        }


def _polynomial(terms: Mapping[Signature, Fraction]) -> dict[Signature, Fraction]:
    result = {}
    for signature, coefficient in terms.items():
        if (len(signature) != 2 or any(isinstance(k, bool) or not isinstance(k, int)
                                      or k < 0 for k in signature)):
            raise ValueError("signatures must have two nonnegative integer powers")
        if isinstance(coefficient, bool):
            raise ValueError("coefficients must be numeric, not boolean")
        value = Fraction(str(coefficient))
        if value:
            result[signature] = value
    if (0, 0) in result:
        raise ReductionNotApplicable("localized loss and perturbation must vanish at the origin")
    return result


def reduce_quadratic_channel(
    base_loss: Mapping[Signature, Fraction],
    perturbation: Mapping[Signature, Fraction],
    *, axes: tuple[str, str] = ("x", "y"),
) -> QuadraticReduction:
    """Find either eligible elimination orientation, or explain the refusal.

    Input maps are already combined polynomial signatures in the stated
    axes. The full base loss is required: passing just a principal part
    does not certify an objective with additional terms.
    """
    if len(axes) != 2 or len(set(axes)) != 2 or any(not axis for axis in axes):
        raise ValueError("two distinct nonempty axis names are required")
    base, pert = _polynomial(base_loss), _polynomial(perturbation)
    if len(base) != 2 or any(sum(k > 0 for k in sig) != 1 for sig in base):
        raise ReductionNotApplicable("the full base loss must be exactly two pure powers")
    base_terms = {}
    for signature, coefficient in base.items():
        index = next(i for i, power in enumerate(signature) if power)
        if index in base_terms or signature[index] <= 1 or coefficient <= 0:
            raise ReductionNotApplicable("each base axis needs one positive power of order > 1")
        base_terms[index] = (signature[index], coefficient)

    reasons = []
    for x_index in (0, 1):
        y_index = 1 - x_index
        p, A = base_terms[x_index]
        q, B = base_terms[y_index]
        driver, remainder = {}, {}
        a = Fraction(0)
        invalid_shape = False
        for signature, coefficient in pert.items():
            i, j = signature[x_index], signature[y_index]
            if i == 2 and j == 0:
                a = -coefficient
            elif i == 1 and j > 0:
                driver[j] = coefficient
            elif i == 0:
                remainder[j] = coefficient
            else:
                invalid_shape = True
        if invalid_shape or a <= 0 or not driver:
            reasons.append(f"{axes[x_index]}: requires -a*x**2+x*H(y)+K(y), a>0, H(0)=0")
            continue
        r = min(driver)
        if driver[r] <= 0:
            reasons.append(f"{axes[x_index]}: square-center curve is not positive near the origin")
            continue
        if len(driver) > MAX_DRIVER_TERMS:
            reasons.append(f"{axes[x_index]}: driver exceeds {MAX_DRIVER_TERMS} terms")
            continue
        reduced = dict(remainder)
        for i, ci in driver.items():
            for j, cj in driver.items():
                reduced[i + j] = reduced.get(i + j, Fraction(0)) + ci * cj / (4 * a)
        reduced = {k: c for k, c in reduced.items() if c}
        if not reduced or reduced[min(reduced)] <= 0:
            reasons.append(f"{axes[x_index]}: reduced gain has no positive initial layer")
            continue
        if not 0 < min(reduced) < q:
            reasons.append(f"{axes[x_index]}: reduced order must lie strictly between 0 and {q}")
            continue
        if p * r <= q:
            reasons.append(f"{axes[x_index]}: omitted base cost is not subleading (p*r={p*r} <= q={q})")
            continue
        return QuadraticReduction(
            axes[x_index], axes[y_index], A, B, p, q, a,
            MappingProxyType(driver), MappingProxyType(remainder), MappingProxyType(reduced),
        )
    raise ReductionNotApplicable("; ".join(reasons))
