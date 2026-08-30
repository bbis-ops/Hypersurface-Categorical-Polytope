"""Exact parametric phase diagrams for the face-selection law.

The ordinary face-selection law answers one asymptotic problem.  This module
answers a family of them at once.  Suppose a finite collection of already
admissible face mechanisms has affine weighted degree

    q_j(t) = a_j + b_j t

on a closed control-parameter interval.  The selected degree is the lower
envelope of the relevant mechanisms, ``q_star(t) = min_j q_j(t)`` with
``0 < q_j(t) < 1``.  Consequently the winner can change only where two affine
degrees agree or where one degree crosses the relevance walls zero and one.

All arithmetic is exact ``Fraction`` arithmetic.  The implementation computes
the complete one-parameter phase diagram: open chambers, wall values, tied
winners, activation/deactivation events, and the response law
``gamma(t) = 1 / (1 - q_star(t))`` in every chamber.

This is the executable one-dimensional section of the face-selection phase-fan
law.  For several parameters, the same equations are affine hyperplanes.
Admissibility is deliberately supplied rather than guessed: if positivity,
cancellation, or geometry changes with the parameter, those changes must first
be included as additional walls.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence


def _fraction(value: int | float | str | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError("boolean values are not rational numbers")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("numeric values must be finite")
        return Fraction(str(value))
    return Fraction(value)


def _label(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _number(value: Fraction) -> dict[str, str | float]:
    return {"exact": _label(value), "value": float(value)}


@dataclass(frozen=True)
class AffineWeightedDegree:
    """An exact affine weighted-degree law ``q(t) = intercept + slope*t``."""

    intercept: Fraction | int | float | str
    slope: Fraction | int | float | str = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "intercept", _fraction(self.intercept))
        object.__setattr__(self, "slope", _fraction(self.slope))

    def evaluate(self, parameter: Fraction | int | float | str) -> Fraction:
        return self.intercept + self.slope * _fraction(parameter)

    def crossing(self, other: "AffineWeightedDegree") -> Fraction | None:
        slope_difference = self.slope - other.slope
        if slope_difference == 0:
            return None
        return (other.intercept - self.intercept) / slope_difference

    def level_crossing(self, level: Fraction | int | float | str) -> Fraction | None:
        if self.slope == 0:
            return None
        return (_fraction(level) - self.intercept) / self.slope

    @property
    def exact_expression(self) -> str:
        if self.slope == 0:
            return _label(self.intercept)
        sign = "+" if self.slope > 0 else "-"
        magnitude = abs(self.slope)
        return f"{_label(self.intercept)} {sign} {_label(magnitude)}*t"

    def to_dict(self, *, parameter_name: str = "t") -> dict[str, Any]:
        expression = self.exact_expression.replace("t", parameter_name)
        return {
            "intercept": _number(self.intercept),
            "slope": _number(self.slope),
            "expression": expression,
        }


def weighted_degree_from_exponents(
    exponents: Mapping[str, AffineWeightedDegree],
    base_orders: Mapping[str, Fraction | int | float | str],
) -> AffineWeightedDegree:
    """Derive ``q(t)=sum_i alpha_i(t)/beta_i`` exactly.

    This is the parametric Newton-weight compiler used by the backend.  It
    converts monomial exponent laws and fixed base orders into the affine face
    degree consumed by the phase selector.
    """
    if not exponents:
        raise ValueError("a parametric monomial needs at least one exponent law")
    orders = {str(axis): _fraction(order) for axis, order in base_orders.items()}
    if not orders:
        raise ValueError("base_orders must be supplied for exponent-derived degrees")
    invalid = sorted(axis for axis, order in orders.items() if order <= 1)
    if invalid:
        raise ValueError(f"base orders must exceed one on axes {invalid}")
    unknown = sorted(set(exponents) - set(orders))
    if unknown:
        raise ValueError(f"exponent laws use axes absent from base_orders: {unknown}")
    intercept = sum(
        (law.intercept / orders[axis] for axis, law in exponents.items()),
        start=Fraction(0),
    )
    slope = sum(
        (law.slope / orders[axis] for axis, law in exponents.items()),
        start=Fraction(0),
    )
    return AffineWeightedDegree(intercept, slope)


@dataclass(frozen=True)
class ParametricFaceMechanism:
    """One face/universality mechanism competing in the parametric selection."""

    identifier: str
    degree: AffineWeightedDegree
    face: tuple[str, ...] = ()
    admitted: bool = True
    reason: str = ""
    coefficient: AffineWeightedDegree | None = None

    def __post_init__(self) -> None:
        if self.identifier is None:
            raise ValueError("mechanism identifiers must be non-empty")
        identifier = str(self.identifier).strip()
        if not identifier:
            raise ValueError("mechanism identifiers must be non-empty")
        if not isinstance(self.degree, AffineWeightedDegree):
            raise TypeError("mechanism degree must be an AffineWeightedDegree")
        if self.coefficient is not None and not isinstance(
            self.coefficient, AffineWeightedDegree
        ):
            raise TypeError("mechanism coefficient must be an affine law")
        face = tuple(sorted({str(axis).strip() for axis in self.face if str(axis).strip()}))
        object.__setattr__(self, "identifier", identifier)
        object.__setattr__(self, "face", face)
        object.__setattr__(self, "reason", str(self.reason))

    def to_dict(self, *, parameter_name: str = "t") -> dict[str, Any]:
        return {
            "id": self.identifier,
            "face": list(self.face),
            "admitted": self.admitted,
            "reason": self.reason or None,
            "degree": self.degree.to_dict(parameter_name=parameter_name),
            "coefficient_law": (
                None if self.coefficient is None
                else self.coefficient.to_dict(parameter_name=parameter_name)
            ),
            "qualification": (
                "fixed" if self.coefficient is None
                else "positive exactly where coefficient(parameter) > 0"
            ),
        }


@dataclass(frozen=True)
class PhaseChamber:
    """An open interval on which the winning affine mechanism is constant."""

    lower: Fraction
    upper: Fraction
    winners: tuple[str, ...]
    degree: AffineWeightedDegree | None

    @property
    def answered(self) -> bool:
        return bool(self.winners)

    def to_dict(self, *, parameter_name: str = "t") -> dict[str, Any]:
        response = None
        if self.degree is not None:
            response = {
                "expression": f"1 / (1 - ({self.degree.exact_expression.replace('t', parameter_name)}))",
                "law": "gamma(parameter) = 1 / (1 - q_star(parameter))",
            }
        return {
            "kind": "open_chamber",
            "domain": {
                "lower": _number(self.lower),
                "upper": _number(self.upper),
                "lower_closed": False,
                "upper_closed": False,
            },
            "answered": self.answered,
            "winning_mechanisms": list(self.winners),
            "weighted_degree_law": (
                None if self.degree is None
                else self.degree.to_dict(parameter_name=parameter_name)
            ),
            "response_exponent_law": response,
            "universality_class": (
                None if self.degree is None
                else "parametric-face-weight:"
                + self.degree.exact_expression.replace("t", parameter_name)
            ),
        }


@dataclass(frozen=True)
class PhaseWall:
    """An exact parameter value at which ordering or relevance can change."""

    parameter: Fraction
    winners: tuple[str, ...]
    degree: Fraction | None

    def to_dict(self) -> dict[str, Any]:
        gamma = None if self.degree is None else 1 / (1 - self.degree)
        return {
            "kind": "wall",
            "parameter": _number(self.parameter),
            "answered": bool(self.winners),
            "winning_mechanisms": list(self.winners),
            "weighted_degree": None if self.degree is None else _number(self.degree),
            "response_exponent": None if gamma is None else _number(gamma),
        }


@dataclass(frozen=True)
class PhaseTransition:
    """A change in the selected mechanism across one interior wall."""

    parameter: Fraction
    before: tuple[str, ...]
    at: tuple[str, ...]
    after: tuple[str, ...]
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": _number(self.parameter),
            "kind": self.kind,
            "before": list(self.before),
            "at_wall": list(self.at),
            "after": list(self.after),
        }


@dataclass(frozen=True)
class MechanismQualification:
    """Why one mechanism is or is not eligible at a parameter value."""

    identifier: str
    status: str
    qualified: bool
    degree: Fraction
    coefficient: Fraction | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier,
            "status": self.status,
            "qualified": self.qualified,
            "weighted_degree": _number(self.degree),
            "coefficient": (
                None if self.coefficient is None else _number(self.coefficient)
            ),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PhaseEvaluation:
    """Exact selection and robustness information at one parameter value."""

    parameter: Fraction
    location: str
    winners: tuple[str, ...]
    degree: Fraction | None
    nearest_transition: Fraction | None
    transition_distance: Fraction | None
    transition_on_left: Fraction | None
    transition_on_right: Fraction | None
    qualifications: tuple[MechanismQualification, ...]

    def to_dict(self) -> dict[str, Any]:
        gamma = None if self.degree is None else 1 / (1 - self.degree)
        return {
            "parameter": _number(self.parameter),
            "location": self.location,
            "answered": bool(self.winners),
            "winning_mechanisms": list(self.winners),
            "qualified_selection": {
                "rule": "minimum weighted degree among qualified mechanisms",
                "mechanisms": [item.to_dict() for item in self.qualifications],
            },
            "weighted_degree": None if self.degree is None else _number(self.degree),
            "response_exponent": None if gamma is None else _number(gamma),
            "robustness": {
                "on_transition": self.transition_distance == 0,
                "nearest_transition": (
                    None if self.nearest_transition is None
                    else _number(self.nearest_transition)
                ),
                "parameter_distance": (
                    None if self.transition_distance is None
                    else _number(self.transition_distance)
                ),
                "transition_on_left": (
                    None if self.transition_on_left is None
                    else _number(self.transition_on_left)
                ),
                "transition_on_right": (
                    None if self.transition_on_right is None
                    else _number(self.transition_on_right)
                ),
                "interpretation": (
                    "exact distance to a change in the selected universality mechanism"
                ),
            },
        }


@dataclass(frozen=True)
class FaceSelectionPhaseDiagram:
    """The exact lower-envelope decomposition of a parameter interval."""

    parameter_name: str
    lower: Fraction
    upper: Fraction
    mechanisms: tuple[ParametricFaceMechanism, ...]
    breakpoints: tuple[Fraction, ...]
    chambers: tuple[PhaseChamber, ...]
    walls: tuple[PhaseWall, ...]
    transitions: tuple[PhaseTransition, ...]

    def evaluate(
        self, parameter: Fraction | int | float | str
    ) -> PhaseEvaluation:
        """Evaluate the selected class and its exact transition margin."""
        value = _fraction(parameter)
        if not self.lower <= value <= self.upper:
            raise ValueError(
                f"parameter must lie in [{_label(self.lower)}, {_label(self.upper)}]"
            )
        winners, degree, qualifications = _qualified_selection(self.mechanisms, value)

        transition_values = tuple(transition.parameter for transition in self.transitions)
        left_values = tuple(point for point in transition_values if point < value)
        right_values = tuple(point for point in transition_values if point > value)
        left = max(left_values) if left_values else None
        right = min(right_values) if right_values else None
        if value in transition_values:
            nearest, distance = value, Fraction(0)
            location = "transition_wall"
        else:
            distances = [
                (abs(value - point), point) for point in transition_values
            ]
            if distances:
                distance, nearest = min(distances, key=lambda item: (item[0], item[1]))
            else:
                nearest, distance = None, None
            location = "candidate_wall" if value in self.breakpoints else "open_chamber"
        return PhaseEvaluation(
            parameter=value,
            location=location,
            winners=winners,
            degree=degree,
            nearest_transition=nearest,
            transition_distance=distance,
            transition_on_left=left,
            transition_on_right=right,
            qualifications=qualifications,
        )

    def to_dict(self) -> dict[str, Any]:
        resolved = sum(chamber.answered for chamber in self.chambers)
        return {
            "parameter": self.parameter_name,
            "domain": {
                "lower": _number(self.lower),
                "upper": _number(self.upper),
                "closed": True,
            },
            "mechanisms": [
                mechanism.to_dict(parameter_name=self.parameter_name)
                for mechanism in self.mechanisms
            ],
            "breakpoints": [_number(value) for value in self.breakpoints],
            "chambers": [
                chamber.to_dict(parameter_name=self.parameter_name)
                for chamber in self.chambers
            ],
            "walls": [wall.to_dict() for wall in self.walls],
            "transitions": [transition.to_dict() for transition in self.transitions],
            "summary": {
                "mechanism_count": len(self.mechanisms),
                "admitted_mechanism_count": sum(m.admitted for m in self.mechanisms),
                "dynamic_qualification_count": sum(
                    m.coefficient is not None for m in self.mechanisms
                ),
                "chamber_count": len(self.chambers),
                "resolved_chamber_count": resolved,
                "transition_count": len(self.transitions),
            },
        }


@dataclass(frozen=True)
class ParametricFaceSelectionProblem:
    """Finite exact input for a one-parameter face-selection phase diagram."""

    mechanisms: tuple[ParametricFaceMechanism, ...]
    lower: Fraction | int | float | str
    upper: Fraction | int | float | str
    parameter_name: str = "t"

    def __post_init__(self) -> None:
        mechanisms = tuple(self.mechanisms)
        if not mechanisms:
            raise ValueError("a phase diagram needs at least one mechanism")
        if any(not isinstance(item, ParametricFaceMechanism) for item in mechanisms):
            raise TypeError("phase mechanisms must be ParametricFaceMechanism objects")
        identifiers = [item.identifier for item in mechanisms]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("phase mechanism identifiers must be unique")
        lower, upper = _fraction(self.lower), _fraction(self.upper)
        if lower >= upper:
            raise ValueError("phase domain must satisfy lower < upper")
        parameter_name = str(self.parameter_name).strip()
        if not parameter_name:
            raise ValueError("parameter_name must be non-empty")
        object.__setattr__(self, "mechanisms", mechanisms)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "parameter_name", parameter_name)

    def solve(self) -> FaceSelectionPhaseDiagram:
        breakpoints = {self.lower, self.upper}
        admitted = tuple(mechanism for mechanism in self.mechanisms if mechanism.admitted)

        for mechanism in admitted:
            for level in (Fraction(0), Fraction(1)):
                crossing = mechanism.degree.level_crossing(level)
                if crossing is not None and self.lower < crossing < self.upper:
                    breakpoints.add(crossing)
            if mechanism.coefficient is not None:
                crossing = mechanism.coefficient.level_crossing(0)
                if crossing is not None and self.lower < crossing < self.upper:
                    breakpoints.add(crossing)
        for left, right in combinations(admitted, 2):
            crossing = left.degree.crossing(right.degree)
            if crossing is not None and self.lower < crossing < self.upper:
                breakpoints.add(crossing)

        ordered = tuple(sorted(breakpoints))
        chambers: list[PhaseChamber] = []
        for lower, upper in zip(ordered, ordered[1:]):
            midpoint = (lower + upper) / 2
            winners, _ = self._select(midpoint)
            degree = None
            if winners:
                degree = self._mechanism(winners[0]).degree
            chambers.append(PhaseChamber(lower, upper, winners, degree))

        walls = tuple(
            PhaseWall(parameter, *self._select(parameter))
            for parameter in ordered
        )
        transitions: list[PhaseTransition] = []
        for index, wall in enumerate(walls[1:-1], start=1):
            before = chambers[index - 1].winners
            after = chambers[index].winners
            at = wall.winners
            if before == after and at == before:
                continue
            if not before and after:
                kind = "mechanism_activation"
            elif before and not after:
                kind = "mechanism_deactivation"
            elif before != after:
                kind = "universality_class_transition"
            else:
                kind = "wall_only_event"
            transitions.append(PhaseTransition(wall.parameter, before, at, after, kind))

        return FaceSelectionPhaseDiagram(
            parameter_name=self.parameter_name,
            lower=self.lower,
            upper=self.upper,
            mechanisms=self.mechanisms,
            breakpoints=ordered,
            chambers=tuple(chambers),
            walls=walls,
            transitions=tuple(transitions),
        )

    def _mechanism(self, identifier: str) -> ParametricFaceMechanism:
        return next(item for item in self.mechanisms if item.identifier == identifier)

    def _select(self, parameter: Fraction) -> tuple[tuple[str, ...], Fraction | None]:
        winners, degree, _ = _qualified_selection(self.mechanisms, parameter)
        return winners, degree


def _qualified_selection(
    mechanisms: Sequence[ParametricFaceMechanism], parameter: Fraction
) -> tuple[
    tuple[str, ...], Fraction | None, tuple[MechanismQualification, ...]
]:
    eligible: list[tuple[str, Fraction]] = []
    qualifications: list[MechanismQualification] = []
    for mechanism in mechanisms:
        degree = mechanism.degree.evaluate(parameter)
        coefficient = (
            None if mechanism.coefficient is None
            else mechanism.coefficient.evaluate(parameter)
        )
        if not mechanism.admitted:
            status = "geometry_filtered"
            reason = mechanism.reason or "mechanism was not admitted by face geometry"
        elif coefficient is not None and coefficient < 0:
            status = "non_positive"
            reason = "affine coefficient is negative, so this monomial channel is non-positive"
        elif coefficient == 0:
            status = "cancelled"
            reason = "affine coefficient vanishes exactly at this qualification wall"
        elif degree <= 0:
            status = "zero_weight"
            reason = "weighted degree must be strictly positive"
        elif degree == 1:
            status = "critical"
            reason = "weighted degree one requires a different balance"
        elif degree > 1:
            status = "subleading"
            reason = "weighted degree above one is outside the fractional-power mechanism"
        else:
            status = "qualified"
            reason = "positive channel with weighted degree strictly between zero and one"
            eligible.append((mechanism.identifier, degree))
        qualifications.append(MechanismQualification(
            identifier=mechanism.identifier,
            status=status,
            qualified=status == "qualified",
            degree=degree,
            coefficient=coefficient,
            reason=reason,
        ))
    if not eligible:
        return (), None, tuple(qualifications)
    minimum = min(degree for _, degree in eligible)
    winners = tuple(identifier for identifier, degree in eligible if degree == minimum)
    return winners, minimum, tuple(qualifications)


def problem_from_mapping(payload: Mapping[str, Any]) -> ParametricFaceSelectionProblem:
    """Build an exact phase problem from the backend's JSON-safe mapping."""
    if not isinstance(payload, Mapping):
        raise ValueError("phase-diagram request must be a JSON object")
    domain = payload.get("domain")
    if not isinstance(domain, Sequence) or isinstance(domain, (str, bytes)) or len(domain) != 2:
        raise ValueError("phase domain must be a two-item array [lower, upper]")
    lower, upper = _fraction(domain[0]), _fraction(domain[1])
    raw_base_orders = payload.get("base_orders", {})
    if not isinstance(raw_base_orders, Mapping):
        raise ValueError("base_orders must be a JSON object")
    base_orders = {str(axis): value for axis, value in raw_base_orders.items()}
    raw_mechanisms = payload.get("mechanisms", payload.get("candidates"))
    if not isinstance(raw_mechanisms, Sequence) or isinstance(raw_mechanisms, (str, bytes)):
        raise ValueError("phase mechanisms must be a non-empty JSON array")
    mechanisms: list[ParametricFaceMechanism] = []
    for index, raw in enumerate(raw_mechanisms):
        if not isinstance(raw, Mapping):
            raise ValueError(f"phase mechanism {index} must be a JSON object")
        degree = raw.get("degree")
        raw_exponents = raw.get("exponents")
        if degree is not None and raw_exponents is not None:
            raise ValueError(
                f"phase mechanism {index} must use degree or exponents, not both"
            )
        if degree is None and raw_exponents is None:
            raise ValueError(
                f"phase mechanism {index} needs a degree or exponents object"
            )
        if degree is not None:
            if not isinstance(degree, Mapping):
                raise ValueError(f"phase mechanism {index} degree must be an object")
            affine_degree = AffineWeightedDegree(
                degree.get("intercept"), degree.get("slope", 0)
            )
        else:
            if not isinstance(raw_exponents, Mapping) or not raw_exponents:
                raise ValueError(
                    f"phase mechanism {index} exponents must be a non-empty object"
                )
            exponent_laws: dict[str, AffineWeightedDegree] = {}
            for raw_axis, raw_law in raw_exponents.items():
                axis = str(raw_axis)
                if not isinstance(raw_law, Mapping):
                    raise ValueError(
                        f"phase mechanism {index} exponent for {axis} must be an object"
                    )
                law = AffineWeightedDegree(
                    raw_law.get("intercept"), raw_law.get("slope", 0)
                )
                if law.evaluate(lower) < 0 or law.evaluate(upper) < 0:
                    raise ValueError(
                        f"phase mechanism {index} exponent for {axis} becomes negative"
                    )
                exponent_laws[axis] = law
            affine_degree = weighted_degree_from_exponents(exponent_laws, base_orders)
        face = raw.get("face", tuple(raw_exponents or ()))
        if not isinstance(face, Sequence) or isinstance(face, (str, bytes)):
            raise ValueError(f"phase mechanism {index} face must be an array")
        raw_coefficient = raw.get("coefficient", raw.get("amplitude"))
        coefficient = None
        if raw_coefficient is not None:
            if not isinstance(raw_coefficient, Mapping):
                raise ValueError(
                    f"phase mechanism {index} coefficient must be an affine-law object"
                )
            coefficient = AffineWeightedDegree(
                raw_coefficient.get("intercept"), raw_coefficient.get("slope", 0)
            )
        mechanisms.append(ParametricFaceMechanism(
            identifier=raw.get("id", raw.get("identifier", f"mechanism-{index}")),
            degree=affine_degree,
            face=tuple(str(axis) for axis in face),
            admitted=raw.get("admitted", True) is True,
            reason=raw.get("reason", ""),
            coefficient=coefficient,
        ))
    return ParametricFaceSelectionProblem(
        mechanisms=tuple(mechanisms),
        lower=lower,
        upper=upper,
        parameter_name=payload.get("parameter", "t"),
    )


__all__ = [
    "AffineWeightedDegree",
    "FaceSelectionPhaseDiagram",
    "MechanismQualification",
    "ParametricFaceMechanism",
    "ParametricFaceSelectionProblem",
    "PhaseChamber",
    "PhaseEvaluation",
    "PhaseTransition",
    "PhaseWall",
    "problem_from_mapping",
    "weighted_degree_from_exponents",
]
