"""Scope-aware codification of the polyhedral face-selection law.

The module implements the finite algebraic part of the law from
``docs/face_selection_noteBrisen15.pdf``:

    edge chart -> weighted principal part -> face restrictions -> initial forms
    -> admissibility -> q_star -> gamma = 1 / (1 - q_star).

It intentionally separates three kinds of information that are easy to blur:

* structural facts checked exactly here (a simple edge chart, positive base
  coefficients and orders, polynomial monomial exponents);
* facewise algebra (survival, cancellation, relevance and positivity),
  including a constructive certificate for mixed-sign binomials;
* analytic hypotheses supplied by the caller (local maximality, a uniform
  weighted remainder and global isolation).

A selection can therefore be computed without being advertised as a theorem-
licensed conclusion. General mixed-sign initial forms require an explicit
positive relative-interior witness, but a binomial with distinct signatures is
resolved constructively by monomial-ratio separation. Absence of either
certificate is ``UNRESOLVED``, not evidence of inactivity. The implementation
is stdlib-only and uses
``fractions.Fraction`` for all weights and response exponents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from itertools import combinations
from math import isfinite
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence


Axis = str
Face = frozenset[Axis]


def _fraction(value: int | float | str | Fraction) -> Fraction:
    """Convert user-facing numeric input without importing float artefacts."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("numeric values must be finite")
        return Fraction(str(value))
    return Fraction(value)


def _frozen_mapping(values: Mapping[Axis, float]) -> Mapping[Axis, float]:
    return MappingProxyType(dict(values))


def _face_key(face: Iterable[Axis]) -> tuple[Axis, ...]:
    return tuple(sorted(face))


class HypothesisStatus(Enum):
    """Evidence level for an analytic hypothesis outside the finite model."""

    VERIFIED = "verified"
    ASSUMED = "assumed"
    UNVERIFIED = "unverified"
    VIOLATED = "violated"

    @property
    def licenses_conditional_use(self) -> bool:
        return self in {HypothesisStatus.VERIFIED, HypothesisStatus.ASSUMED}


@dataclass(frozen=True)
class LawHypotheses:
    """The analytic hypotheses that cannot be inferred from monomial data.

    ``ASSUMED`` is a valid license for a conditional symbolic calculation;
    ``VERIFIED`` records independent evidence.  The distinction is retained in
    every :class:`SelectionResult`.
    """

    local_base_maximality: HypothesisStatus = HypothesisStatus.UNVERIFIED
    uniform_principal_remainder: HypothesisStatus = HypothesisStatus.UNVERIFIED
    global_isolation: HypothesisStatus = HypothesisStatus.UNVERIFIED

    def items(self) -> tuple[tuple[str, HypothesisStatus], ...]:
        return (
            ("local_base_maximality", self.local_base_maximality),
            ("uniform_principal_remainder", self.uniform_principal_remainder),
            ("global_isolation", self.global_isolation),
        )

    @property
    def theorem_licensed(self) -> bool:
        return all(status.licenses_conditional_use for _, status in self.items())

    @property
    def blockers(self) -> tuple[str, ...]:
        return tuple(
            f"{name} is {status.value}"
            for name, status in self.items()
            if not status.licenses_conditional_use
        )


@dataclass(frozen=True)
class EdgeCoordinateChart:
    """Linear edge coordinates at a full-dimensional simple vertex.

    ``generators[axis]`` is the inward edge generator ``u_i`` and
    ``point(c) = vertex + sum_i c_i u_i``.  Construction verifies that there
    are exactly ``n`` generators in ambient dimension ``n`` and that their
    matrix has full rank.  Feasibility of the rays is geometric input and is
    deliberately not guessed from the coordinates alone.
    """

    vertex: tuple[float, ...]
    generators: Mapping[Axis, tuple[float, ...]]
    rank_tolerance: float = field(default=1e-12, repr=False, compare=False)

    def __post_init__(self) -> None:
        vertex = tuple(float(x) for x in self.vertex)
        generators = {
            str(axis): tuple(float(x) for x in vector)
            for axis, vector in self.generators.items()
        }
        if not vertex:
            raise ValueError("vertex must have positive ambient dimension")
        if len(generators) != len(vertex):
            raise ValueError(
                "a simple full-dimensional vertex needs exactly one independent "
                "edge generator per ambient dimension"
            )
        if any(len(vector) != len(vertex) for vector in generators.values()):
            raise ValueError("every edge generator must have the ambient dimension")
        if any(not axis for axis in generators):
            raise ValueError("edge-coordinate axis names must be non-empty")
        if _matrix_rank(tuple(generators.values()), self.rank_tolerance) != len(vertex):
            raise ValueError("edge generators are linearly dependent; vertex is not simple")
        object.__setattr__(self, "vertex", vertex)
        object.__setattr__(self, "generators", MappingProxyType(generators))

    @property
    def axes(self) -> tuple[Axis, ...]:
        return tuple(self.generators)

    def point(self, coordinates: Mapping[Axis, float]) -> tuple[float, ...]:
        self._validate_coordinate_names(coordinates)
        return tuple(
            self.vertex[j]
            + sum(float(coordinates.get(axis, 0.0)) * vector[j]
                  for axis, vector in self.generators.items())
            for j in range(len(self.vertex))
        )

    def _validate_coordinate_names(self, coordinates: Mapping[Axis, float]) -> None:
        unknown = set(coordinates) - set(self.axes)
        if unknown:
            raise ValueError(f"unknown edge-coordinate axes: {sorted(unknown)}")
        if any(value < 0.0 or not isfinite(value) for value in coordinates.values()):
            raise ValueError("edge coordinates must be finite and nonnegative")


def _matrix_rank(rows: Sequence[Sequence[float]], tolerance: float) -> int:
    matrix = [list(row) for row in rows]
    if not matrix:
        return 0
    row_count, column_count = len(matrix), len(matrix[0])
    rank = 0
    for column in range(column_count):
        pivot = max(range(rank, row_count), key=lambda row: abs(matrix[row][column]))
        if abs(matrix[pivot][column]) <= tolerance:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        pivot_value = matrix[rank][column]
        matrix[rank] = [value / pivot_value for value in matrix[rank]]
        for row in range(row_count):
            if row == rank:
                continue
            factor = matrix[row][column]
            if abs(factor) > tolerance:
                matrix[row] = [
                    value - factor * pivot_entry
                    for value, pivot_entry in zip(matrix[row], matrix[rank])
                ]
        rank += 1
        if rank == row_count:
            break
    return rank


@dataclass(frozen=True)
class BasePower:
    """One term ``A_i c_i**beta_i`` of the weighted principal part."""

    coefficient: float
    order: Fraction | int | float | str

    def __post_init__(self) -> None:
        coefficient = float(self.coefficient)
        order = _fraction(self.order)
        if coefficient <= 0.0 or not isfinite(coefficient):
            raise ValueError("base coefficients A_i must be finite and positive")
        if order <= 1:
            raise ValueError("base orders beta_i must be greater than one")
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "order", order)

    @property
    def weight(self) -> Fraction:
        return 1 / self.order


@dataclass(frozen=True)
class WeightedPrincipalPart:
    """Diagonal weighted-homogeneous principal part ``D_0``."""

    powers: Mapping[Axis, BasePower]

    def __post_init__(self) -> None:
        powers = {str(axis): power for axis, power in self.powers.items()}
        if not powers:
            raise ValueError("weighted principal part needs at least one axis")
        if any(not isinstance(power, BasePower) for power in powers.values()):
            raise TypeError("every principal-part entry must be a BasePower")
        object.__setattr__(self, "powers", MappingProxyType(powers))

    @property
    def axes(self) -> tuple[Axis, ...]:
        return tuple(self.powers)

    def evaluate(self, coordinates: Mapping[Axis, float]) -> float:
        unknown = set(coordinates) - set(self.axes)
        if unknown:
            raise ValueError(f"unknown principal-part axes: {sorted(unknown)}")
        if any(value < 0.0 or not isfinite(value) for value in coordinates.values()):
            raise ValueError("principal-part coordinates must be finite and nonnegative")
        return sum(
            power.coefficient
            * float(coordinates.get(axis, 0.0)) ** float(power.order)
            for axis, power in self.powers.items()
        )

    def dilate(self, tau: float, coordinates: Mapping[Axis, float]) -> dict[Axis, float]:
        if tau < 0.0 or not isfinite(tau):
            raise ValueError("tau must be finite and nonnegative")
        unknown = set(coordinates) - set(self.axes)
        if unknown:
            raise ValueError(f"unknown principal-part axes: {sorted(unknown)}")
        return {
            axis: tau ** float(power.weight) * float(coordinates.get(axis, 0.0))
            for axis, power in self.powers.items()
        }


@dataclass(frozen=True)
class PerturbationMonomial:
    """Polynomial term ``coefficient * product(c_i**alpha_i)``.

    Zero exponents are removed.  The remaining powers must be nonnegative
    integers, matching the polynomial hypothesis of the note.
    """

    coefficient: float | Fraction
    powers: Mapping[Axis, int]

    def __post_init__(self) -> None:
        raw_coefficient = self.coefficient
        if isinstance(raw_coefficient, bool):
            raise ValueError("monomial coefficient must be numeric")
        # Fractions produced by the ambient compiler must stay exact through
        # cancellation and sign classification.  Coercing them to float here
        # reintroduced precisely the underflow/epsilon loss that symbolic
        # transport is intended to prevent.
        if isinstance(raw_coefficient, Fraction):
            coefficient: float | Fraction = raw_coefficient
        else:
            coefficient = float(raw_coefficient)
            if not isfinite(coefficient):
                raise ValueError("monomial coefficient must be finite")
        powers: dict[Axis, int] = {}
        for raw_axis, raw_power in self.powers.items():
            axis = str(raw_axis)
            if not axis:
                raise ValueError("monomial axis names must be non-empty")
            if isinstance(raw_power, bool) or int(raw_power) != raw_power or raw_power < 0:
                raise ValueError("polynomial powers alpha_ij must be nonnegative integers")
            power = int(raw_power)
            if power:
                powers[axis] = power
        object.__setattr__(self, "coefficient", coefficient)
        object.__setattr__(self, "powers", MappingProxyType(powers))

    @property
    def signature(self) -> tuple[tuple[Axis, int], ...]:
        return tuple(sorted(self.powers.items()))

    @property
    def support(self) -> Face:
        return frozenset(self.powers)

    def weighted_degree(self, principal: WeightedPrincipalPart) -> Fraction:
        unknown = self.support - set(principal.axes)
        if unknown:
            raise ValueError(f"monomial uses axes absent from D_0: {sorted(unknown)}")
        return sum(
            (Fraction(power) * principal.powers[axis].weight
             for axis, power in self.powers.items()),
            start=Fraction(0),
        )

    def evaluate(self, coordinates: Mapping[Axis, float]) -> float:
        value = float(self.coefficient)
        for axis, power in self.powers.items():
            value *= float(coordinates.get(axis, 0.0)) ** power
        return value


@dataclass(frozen=True)
class PolynomialPerturbation:
    """Finite polynomial in edge coordinates, retaining raw cancellation data."""

    terms: tuple[PerturbationMonomial, ...]
    cancellation_tolerance: float = field(default=1e-12, repr=False, compare=False)

    def __post_init__(self) -> None:
        terms = tuple(self.terms)
        if not terms:
            raise ValueError("polynomial perturbation needs at least one term")
        if any(not isinstance(term, PerturbationMonomial) for term in terms):
            raise TypeError("perturbation terms must be PerturbationMonomial objects")
        if self.cancellation_tolerance < 0.0:
            raise ValueError("cancellation tolerance must be nonnegative")
        object.__setattr__(self, "terms", terms)

    @property
    def axes(self) -> Face:
        return frozenset(axis for term in self.terms for axis in term.support)


@dataclass(frozen=True)
class InitialForm:
    """The first non-cancelling weighted-homogeneous layer on one face."""

    degree: Fraction
    terms: tuple[PerturbationMonomial, ...]

    def evaluate(self, coordinates: Mapping[Axis, float]) -> float:
        return sum(term.evaluate(coordinates) for term in self.terms)

    @property
    def support(self) -> Face:
        return frozenset(axis for term in self.terms for axis in term.support)

    @property
    def has_mixed_signs(self) -> bool:
        signs = {term.coefficient > 0.0 for term in self.terms}
        return len(signs) > 1


@dataclass(frozen=True)
class PositivityWitness:
    """A point in ``relint(C_S)`` at which ``D_0`` and ``W_S`` are positive."""

    coordinates: Mapping[Axis, float]
    provenance: str = "caller"

    def __post_init__(self) -> None:
        coordinates = {str(axis): float(value) for axis, value in self.coordinates.items()}
        if any(value < 0.0 or not isfinite(value) for value in coordinates.values()):
            raise ValueError("witness coordinates must be finite and nonnegative")
        object.__setattr__(self, "coordinates", _frozen_mapping(coordinates))


class FaceStatus(Enum):
    """Complete classification of a tangent-cone face for this mechanism."""

    ADMISSIBLE = "admissible"
    NO_SURVIVING_MONOMIAL = "no_surviving_monomial"
    CANCELLED_INITIAL_FORM = "cancelled_initial_form"
    ZERO_WEIGHT = "zero_weight"
    NON_POSITIVE = "non_positive"
    POSITIVITY_UNRESOLVED = "positivity_unresolved"
    CRITICAL = "critical"
    SUBLEADING = "subleading"


@dataclass(frozen=True)
class FaceAnalysis:
    """Restriction, initial form and admissibility decision for one face."""

    face: Face
    status: FaceStatus
    initial_form: InitialForm | None
    cancelled_degrees: tuple[Fraction, ...] = ()
    witness: PositivityWitness | None = None
    reason: str = ""

    @property
    def degree(self) -> Fraction | None:
        return None if self.initial_form is None else self.initial_form.degree

    @property
    def response_exponent(self) -> Fraction | None:
        if self.status is not FaceStatus.ADMISSIBLE or self.degree is None:
            return None
        return 1 / (1 - self.degree)


@dataclass(frozen=True)
class StationaryProfile:
    """One witnessed channel of the facewise balance.

    The coefficient is the value along the supplied projective direction.  It
    is a certified positive channel, not automatically the facewise optimum.
    """

    face: Face
    degree: Fraction
    exponent: Fraction
    tau: float
    leading_value: float
    coefficient: float
    direction: Mapping[Axis, float]


@dataclass(frozen=True)
class SelectionResult:
    """Finite face-selection output plus its analytic scope status."""

    analyses: tuple[FaceAnalysis, ...]
    hypotheses: LawHypotheses
    q_star: Fraction | None
    response_exponent: Fraction | None
    winning_faces: tuple[Face, ...]

    @property
    def theorem_licensed(self) -> bool:
        return (
            self.q_star is not None
            and self.hypotheses.theorem_licensed
            and not self.unresolved_faces
        )

    @property
    def scope_blockers(self) -> tuple[str, ...]:
        face_blockers = tuple(
            f"positivity is unresolved on face {_face_key(analysis.face)}"
            for analysis in self.unresolved_faces
        )
        return self.hypotheses.blockers + face_blockers

    @property
    def admissible_faces(self) -> tuple[FaceAnalysis, ...]:
        return tuple(a for a in self.analyses if a.status is FaceStatus.ADMISSIBLE)

    @property
    def unresolved_faces(self) -> tuple[FaceAnalysis, ...]:
        return tuple(
            a for a in self.analyses if a.status is FaceStatus.POSITIVITY_UNRESOLVED
        )

    @property
    def minimal_winning_faces(self) -> tuple[Face, ...]:
        """Winning channels with redundant containing faces removed."""
        return tuple(
            face for face in self.winning_faces
            if not any(other < face for other in self.winning_faces)
        )

    def analysis_for(self, face: Iterable[Axis]) -> FaceAnalysis:
        wanted = frozenset(face)
        for analysis in self.analyses:
            if analysis.face == wanted:
                return analysis
        raise KeyError(f"face {_face_key(wanted)} was not analysed")

    def conclusion(self) -> str:
        if self.q_star is None:
            return "no admissible fractional-power face was selected"
        qualifier = "theorem-licensed" if self.theorem_licensed else "conditional/unlicensed"
        return (
            f"{qualifier}: q*={self.q_star}, gamma={self.response_exponent}; "
            "gap order Theta(s**gamma)"
        )


@dataclass(frozen=True)
class FaceSelectionProblem:
    """All finite and analytic data for the face-selection procedure."""

    chart: EdgeCoordinateChart
    principal: WeightedPrincipalPart
    perturbation: PolynomialPerturbation
    hypotheses: LawHypotheses = field(default_factory=LawHypotheses)

    def __post_init__(self) -> None:
        chart_axes = set(self.chart.axes)
        principal_axes = set(self.principal.axes)
        if chart_axes != principal_axes:
            raise ValueError(
                "edge chart and weighted principal part must use exactly the same axes"
            )
        unknown = self.perturbation.axes - chart_axes
        if unknown:
            raise ValueError(f"perturbation uses unknown edge axes: {sorted(unknown)}")

    def faces(self) -> tuple[Face, ...]:
        """All nonempty orthant faces, including the full cone."""
        axes = self.chart.axes
        return tuple(
            frozenset(face)
            for size in range(1, len(axes) + 1)
            for face in combinations(axes, size)
        )

    def select(
        self,
        *,
        positivity_witnesses: Mapping[Face, PositivityWitness | Mapping[Axis, float]] | None = None,
    ) -> SelectionResult:
        witnesses = positivity_witnesses or {}
        analyses = tuple(
            self._analyse_face(face, witnesses.get(face)) for face in self.faces()
        )
        admissible = tuple(a for a in analyses if a.status is FaceStatus.ADMISSIBLE)
        if not admissible:
            return SelectionResult(analyses, self.hypotheses, None, None, ())
        q_star = min(a.degree for a in admissible if a.degree is not None)
        winners = tuple(a.face for a in admissible if a.degree == q_star)
        return SelectionResult(
            analyses=analyses,
            hypotheses=self.hypotheses,
            q_star=q_star,
            response_exponent=1 / (1 - q_star),
            winning_faces=winners,
        )

    def stationary_profile(
        self,
        analysis: FaceAnalysis,
        s: float,
        *,
        witness: PositivityWitness | None = None,
    ) -> StationaryProfile:
        """Evaluate the note's one-parameter balance on a witnessed face."""
        if analysis.status is not FaceStatus.ADMISSIBLE or analysis.initial_form is None:
            raise ValueError("stationary profile requires an admissible face")
        if s <= 0.0 or not isfinite(s):
            raise ValueError("s must be finite and positive")
        selected_witness = witness or analysis.witness
        if selected_witness is None:
            raise ValueError("stationary profile requires a positivity witness")
        self._validate_witness(analysis.face, analysis.initial_form, selected_witness)
        coordinates = selected_witness.coordinates
        A = self.principal.evaluate(coordinates)
        B = analysis.initial_form.evaluate(coordinates)
        k = float(analysis.initial_form.degree)
        exponent = analysis.response_exponent
        assert exponent is not None
        tau = (s * k * B / A) ** float(exponent)
        coefficient = (1.0 - k) / k * A * (k * B / A) ** float(exponent)
        return StationaryProfile(
            face=analysis.face,
            degree=analysis.initial_form.degree,
            exponent=exponent,
            tau=tau,
            leading_value=coefficient * s ** float(exponent),
            coefficient=coefficient,
            direction=_frozen_mapping(coordinates),
        )

    def _analyse_face(
        self,
        face: Face,
        supplied_witness: PositivityWitness | Mapping[Axis, float] | None,
    ) -> FaceAnalysis:
        surviving = tuple(term for term in self.perturbation.terms if term.support <= face)
        if not surviving:
            return FaceAnalysis(
                face, FaceStatus.NO_SURVIVING_MONOMIAL, None,
                reason="the perturbation restricts identically to zero on this face",
            )

        layers: dict[Fraction, list[PerturbationMonomial]] = {}
        for term in surviving:
            degree = term.weighted_degree(self.principal)
            layers.setdefault(degree, []).append(term)

        cancelled: list[Fraction] = []
        initial: InitialForm | None = None
        for degree in sorted(layers):
            combined = self._combine_like_terms(layers[degree])
            if combined:
                initial = InitialForm(degree, combined)
                break
            cancelled.append(degree)
        if initial is None:
            return FaceAnalysis(
                face, FaceStatus.CANCELLED_INITIAL_FORM, None, tuple(cancelled),
                reason="all weighted layers cancel identically on this face",
            )

        degree = initial.degree
        if degree <= 0:
            return FaceAnalysis(
                face, FaceStatus.ZERO_WEIGHT, initial, tuple(cancelled),
                reason="q_S must lie strictly between zero and one",
            )
        if degree == 1:
            return FaceAnalysis(
                face, FaceStatus.CRITICAL, initial, tuple(cancelled),
                reason="q_S = 1 requires a different balance",
            )
        if degree > 1:
            return FaceAnalysis(
                face, FaceStatus.SUBLEADING, initial, tuple(cancelled),
                reason="q_S > 1 is subleading for the fractional-power mechanism",
            )

        witness = self._resolve_witness(face, initial, supplied_witness)
        if witness is not None:
            return FaceAnalysis(
                face, FaceStatus.ADMISSIBLE, initial, tuple(cancelled), witness,
                reason="0 < q_S < 1 and a positive relative-interior witness exists",
            )
        if all(term.coefficient <= 0.0 for term in initial.terms):
            return FaceAnalysis(
                face, FaceStatus.NON_POSITIVE, initial, tuple(cancelled),
                reason="the initial form is non-positive throughout the positive orthant",
            )
        return FaceAnalysis(
            face, FaceStatus.POSITIVITY_UNRESOLVED, initial, tuple(cancelled),
            reason="mixed-sign initial form needs an explicit positive interior witness",
        )

    def _combine_like_terms(
        self, terms: Sequence[PerturbationMonomial]
    ) -> tuple[PerturbationMonomial, ...]:
        coefficients: dict[
            tuple[tuple[Axis, int], ...], float | Fraction
        ] = {}
        for term in terms:
            coefficients[term.signature] = coefficients.get(term.signature, 0) + term.coefficient
        combined = [
            PerturbationMonomial(coefficient, dict(signature))
            for signature, coefficient in sorted(coefficients.items())
            if abs(coefficient) > self.perturbation.cancellation_tolerance
        ]
        return tuple(combined)

    def _resolve_witness(
        self,
        face: Face,
        initial: InitialForm,
        supplied: PositivityWitness | Mapping[Axis, float] | None,
    ) -> PositivityWitness | None:
        if supplied is not None:
            witness = supplied if isinstance(supplied, PositivityWitness) else PositivityWitness(supplied)
            self._validate_witness(face, initial, witness)
            return witness
        if all(term.coefficient >= 0.0 for term in initial.terms) and any(
            term.coefficient > 0.0 for term in initial.terms
        ):
            witness = PositivityWitness(
                {axis: (1.0 if axis in face else 0.0) for axis in self.chart.axes},
                provenance="positive-coefficient certificate",
            )
            self._validate_witness(face, initial, witness)
            return witness
        binomial = self._binomial_positivity_witness(face, initial)
        if binomial is not None:
            self._validate_witness(face, initial, binomial)
            return binomial
        return None

    def _binomial_positivity_witness(
        self, face: Face, initial: InitialForm
    ) -> PositivityWitness | None:
        """Construct a positive witness for a distinct mixed-sign binomial.

        If ``a*x**alpha - b*x**beta`` has distinct exponent signatures, some
        face coordinate has ``alpha_i != beta_i``. Varying that coordinate
        makes the monomial ratio range from zero to infinity. We choose it so
        the positive term is at least four times the negative term, leaving a
        generous floating-point validation margin.
        """
        if len(initial.terms) != 2 or not initial.has_mixed_signs:
            return None
        positive = next(term for term in initial.terms if term.coefficient > 0.0)
        negative = next(term for term in initial.terms if term.coefficient < 0.0)
        if positive.signature == negative.signature:
            return None
        axis = next(
            (
                candidate for candidate in sorted(face)
                if positive.powers.get(candidate, 0)
                != negative.powers.get(candidate, 0)
            ),
            None,
        )
        if axis is None:
            return None
        delta = positive.powers.get(axis, 0) - negative.powers.get(axis, 0)
        dominance = max(
            4.0,
            4.0 * abs(negative.coefficient) / positive.coefficient,
        )
        try:
            coordinate = (
                dominance ** (1.0 / delta)
                if delta > 0
                else dominance ** (-1.0 / abs(delta))
            )
        except (OverflowError, ZeroDivisionError):
            return None
        if not isfinite(coordinate) or coordinate <= 0.0:
            return None
        coordinates = {
            candidate: (
                coordinate if candidate == axis
                else 1.0 if candidate in face
                else 0.0
            )
            for candidate in self.chart.axes
        }
        return PositivityWitness(
            coordinates,
            provenance="mixed-sign binomial ratio certificate",
        )

    def _validate_witness(
        self, face: Face, initial: InitialForm, witness: PositivityWitness
    ) -> None:
        coordinates = witness.coordinates
        unknown = set(coordinates) - set(self.chart.axes)
        if unknown:
            raise ValueError(f"witness uses unknown edge axes: {sorted(unknown)}")
        missing_positive = [axis for axis in face if coordinates.get(axis, 0.0) <= 0.0]
        nonzero_outside = [
            axis for axis in self.chart.axes
            if axis not in face and coordinates.get(axis, 0.0) != 0.0
        ]
        if missing_positive or nonzero_outside:
            raise ValueError(
                "witness must lie in the relative interior of its face: "
                f"nonpositive inside={sorted(missing_positive)}, "
                f"nonzero outside={sorted(nonzero_outside)}"
            )
        if self.principal.evaluate(coordinates) <= 0.0:
            raise ValueError("witness does not make D_0 positive")
        # A nonnegative polynomial with a positive coefficient is strictly
        # positive on the relative interior of a face containing its support.
        # Use that exact certificate before floating evaluation so a rational
        # coefficient smaller than the float range cannot become a false zero.
        exact_positive = (
            all(term.coefficient >= 0 for term in initial.terms)
            and any(
                term.coefficient > 0
                and all(coordinates.get(axis, 0.0) > 0.0 for axis in term.support)
                for term in initial.terms
            )
        )
        if not exact_positive and initial.evaluate(coordinates) <= 0.0:
            raise ValueError("witness does not make the initial form positive")


def infer_weight_from_exponent(exponent: int | float | str | Fraction) -> Fraction:
    """Invert ``gamma = 1/(1-q)`` to ``q = 1 - 1/gamma``."""
    gamma = _fraction(exponent)
    if gamma <= 1:
        raise ValueError("a fractional-response exponent must be greater than one")
    return 1 - 1 / gamma


def tilted_simplex_problem(
    *, hypotheses: LawHypotheses | None = None
) -> FaceSelectionProblem:
    """The complete worked example from the note."""
    return FaceSelectionProblem(
        chart=EdgeCoordinateChart(
            vertex=(0.0, 1.0),
            generators={"c1": (1.0, -1.0), "c2": (0.0, -1.0)},
        ),
        principal=WeightedPrincipalPart(
            {"c1": BasePower(1.0, 4), "c2": BasePower(1.0, 2)}
        ),
        perturbation=PolynomialPerturbation(
            (PerturbationMonomial(1.0, {"c1": 1}),)
        ),
        hypotheses=hypotheses or LawHypotheses(),
    )


__all__ = [
    "Axis",
    "BasePower",
    "EdgeCoordinateChart",
    "Face",
    "FaceAnalysis",
    "FaceSelectionProblem",
    "FaceStatus",
    "HypothesisStatus",
    "InitialForm",
    "LawHypotheses",
    "PerturbationMonomial",
    "PolynomialPerturbation",
    "PositivityWitness",
    "SelectionResult",
    "StationaryProfile",
    "WeightedPrincipalPart",
    "infer_weight_from_exponent",
    "tilted_simplex_problem",
]
