"""Exact ambient-to-face compiler for the face-selection hierarchy.

This module promotes polynomial transport from a private backend helper into a
first-class mathematical asset.  It compiles

    ambient expression -> edge polynomial -> face restrictions
    -> weighted initial forms -> qualified selection -> response exponent

while retaining the provenance of every top-level ambient perturbation term.
All polynomial coefficients and chart entries use exact ``Fraction``
arithmetic.  Floating chart values are interpreted through their decimal
spelling, so the compiler is exact relative to the supplied chart.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .face_selection import (
    EdgeCoordinateChart,
    FaceSelectionProblem,
    LawHypotheses,
    PerturbationMonomial,
    PolynomialPerturbation,
    SelectionResult,
    WeightedPrincipalPart,
)


Signature = tuple[int, ...]
ExactPolynomial = dict[Signature, Fraction]
MAX_TRANSPORTED_MONOMIALS = 4096


def _fraction(value: int | float | str | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError("boolean values are not polynomial coefficients")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("polynomial and chart values must be finite")
        return Fraction(str(value))
    return Fraction(value)


def _label(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _number(value: Fraction) -> dict[str, str | float]:
    return {"exact": _label(value), "value": float(value)}


def _powers(signature: Signature, axes: Sequence[str]) -> dict[str, int]:
    return {axis: power for axis, power in zip(axes, signature) if power}


def _support(signature: Signature, axes: Sequence[str]) -> frozenset[str]:
    return frozenset(axis for axis, power in zip(axes, signature) if power)


def _solve_exact_square(
    matrix: Sequence[Sequence[int | float | str | Fraction]],
    right_hand_side: Sequence[int | float | str | Fraction],
) -> tuple[Fraction, ...]:
    size = len(matrix)
    if size == 0 or len(right_hand_side) != size or any(len(row) != size for row in matrix):
        raise ValueError("exact chart reconstruction needs a square active system")
    augmented = [
        [_fraction(value) for value in row] + [_fraction(rhs)]
        for row, rhs in zip(matrix, right_hand_side)
    ]
    for column in range(size):
        pivot = next(
            (row for row in range(column, size) if augmented[row][column] != 0),
            None,
        )
        if pivot is None:
            raise ValueError("active constraints are singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(augmented[row], augmented[column])
                ]
    return tuple(row[-1] for row in augmented)


def exact_chart_from_active_constraints(
    rows: Sequence[Sequence[int | float | str | Fraction]],
    rhs: Sequence[int | float | str | Fraction],
    active_constraints: Sequence[int],
    *,
    axes: Sequence[str] | None = None,
) -> tuple[tuple[Fraction, ...], Mapping[str, tuple[Fraction, ...]]]:
    """Reconstruct a simple vertex and inward edge basis exactly.

    For the active matrix ``A_S``, the vertex solves ``A_S v = b_S`` and edge
    ``i`` solves ``A_S u_i = -e_i``.  No normalization is applied: positive
    rescaling changes coefficients but never Newton support or weighted order.
    """
    dimension = len(rows[0]) if rows else 0
    active = tuple(int(index) for index in active_constraints)
    if dimension == 0 or len(active) != dimension:
        raise ValueError("a simple vertex needs exactly ambient-dimension active constraints")
    if len(rhs) != len(rows) or any(len(row) != dimension for row in rows):
        raise ValueError("constraint matrix and right-hand side disagree")
    if any(index < 0 or index >= len(rows) for index in active):
        raise ValueError("active constraint index is outside the system")
    names = tuple(axes) if axes is not None else tuple(f"c{i}" for i in range(dimension))
    if len(names) != dimension or len(set(names)) != dimension:
        raise ValueError("edge-axis names must be distinct and match ambient dimension")
    active_matrix = [rows[index] for index in active]
    vertex = _solve_exact_square(active_matrix, [rhs[index] for index in active])
    generators = {
        axis: _solve_exact_square(
            active_matrix,
            [Fraction(-1 if row == column else 0) for row in range(dimension)],
        )
        for column, axis in enumerate(names)
    }
    return vertex, MappingProxyType(generators)


def _poly_add(left: Mapping[Signature, Fraction], right: Mapping[Signature, Fraction]) -> ExactPolynomial:
    result = dict(left)
    for signature, coefficient in right.items():
        result[signature] = result.get(signature, Fraction(0)) + coefficient
        if result[signature] == 0:
            del result[signature]
    return result


def _poly_multiply(
    left: Mapping[Signature, Fraction], right: Mapping[Signature, Fraction]
) -> ExactPolynomial:
    if not left or not right:
        return {}
    result: ExactPolynomial = {}
    for left_signature, left_coefficient in left.items():
        for right_signature, right_coefficient in right.items():
            signature = tuple(a + b for a, b in zip(left_signature, right_signature))
            result[signature] = result.get(signature, Fraction(0)) + (
                left_coefficient * right_coefficient
            )
            if result[signature] == 0:
                del result[signature]
            if len(result) > MAX_TRANSPORTED_MONOMIALS:
                raise ValueError(
                    f"transported polynomial exceeds {MAX_TRANSPORTED_MONOMIALS} monomials"
                )
    return result


def _poly_power(polynomial: Mapping[Signature, Fraction], exponent: int, zero: Signature) -> ExactPolynomial:
    result: ExactPolynomial = {zero: Fraction(1)}
    factor = dict(polynomial)
    power = exponent
    while power:
        if power & 1:
            result = _poly_multiply(result, factor)
        power //= 2
        if power:
            factor = _poly_multiply(factor, factor)
    return result


def _additive_nodes(node: ast.AST, sign: int = 1) -> tuple[ast.AST, ...]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _additive_nodes(node.left, sign) + _additive_nodes(node.right, sign)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
        return _additive_nodes(node.left, sign) + _additive_nodes(node.right, -sign)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _additive_nodes(node.operand, sign)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _additive_nodes(node.operand, -sign)
    return (node if sign > 0 else ast.UnaryOp(op=ast.USub(), operand=node),)


@dataclass(frozen=True)
class AmbientTermTransport:
    """Exact edge expansion of one top-level ambient additive term."""

    index: int
    expression: str
    constant_at_vertex: Fraction
    polynomial: Mapping[Signature, Fraction]

    def __post_init__(self) -> None:
        object.__setattr__(self, "polynomial", MappingProxyType(dict(self.polynomial)))

    @property
    def status(self) -> str:
        return "transported" if self.polynomial else "geometrically_suppressed"

    def to_dict(self, axes: Sequence[str], weights: Mapping[str, Fraction] | None = None) -> dict[str, Any]:
        monomials = []
        for signature, coefficient in sorted(self.polynomial.items()):
            degree = None
            if weights is not None:
                degree = sum(
                    (Fraction(power) * weights[axis] for axis, power in zip(axes, signature)),
                    start=Fraction(0),
                )
            monomials.append({
                "signature": list(signature),
                "powers": _powers(signature, axes),
                "coefficient": _number(coefficient),
                "weighted_degree": None if degree is None else _number(degree),
            })
        return {
            "index": self.index,
            "expression": self.expression,
            "status": self.status,
            "constant_at_vertex": _number(self.constant_at_vertex),
            "edge_monomials": monomials,
        }


@dataclass(frozen=True)
class EdgeMonomialLineage:
    """Combined edge monomial and all ambient-term contributions to it."""

    signature: Signature
    coefficient: Fraction
    contributions: tuple[tuple[int, Fraction], ...]

    @property
    def cancelled(self) -> bool:
        return self.coefficient == 0

    def to_dict(self, axes: Sequence[str], weights: Mapping[str, Fraction] | None = None) -> dict[str, Any]:
        degree = None
        if weights is not None:
            degree = sum(
                (Fraction(power) * weights[axis] for axis, power in zip(axes, self.signature)),
                start=Fraction(0),
            )
        return {
            "signature": list(self.signature),
            "powers": _powers(self.signature, axes),
            "coefficient": _number(self.coefficient),
            "cancelled": self.cancelled,
            "weighted_degree": None if degree is None else _number(degree),
            "ambient_contributions": [
                {"term_index": index, "coefficient": _number(coefficient)}
                for index, coefficient in self.contributions
            ],
        }


@dataclass(frozen=True)
class AmbientTransport:
    """Complete exact transport, cancellations, and face restrictions."""

    expression: str
    axes: tuple[str, ...]
    vertex: tuple[Fraction, ...]
    generators: Mapping[str, tuple[Fraction, ...]]
    terms: tuple[AmbientTermTransport, ...]
    lineage: tuple[EdgeMonomialLineage, ...]

    @property
    def polynomial(self) -> Mapping[Signature, Fraction]:
        return MappingProxyType({
            item.signature: item.coefficient for item in self.lineage
            if not item.cancelled
        })

    @property
    def cancellations(self) -> tuple[EdgeMonomialLineage, ...]:
        return tuple(item for item in self.lineage if item.cancelled)

    @property
    def axial_orders(self) -> Mapping[str, int | None]:
        """Lowest nonconstant order surviving on each one-edge face.

        These are the coordinate orders of the *pulled-back* polynomial, not
        orders measured on ambient coordinate axes.  That distinction is the
        obstruction exposed by the two ambient counterexamples.
        """
        active = tuple(item for item in self.lineage if not item.cancelled)
        return MappingProxyType({
            axis: min(
                (
                    item.signature[index]
                    for item in active
                    if item.signature[index] > 0
                    and all(
                        power == 0
                        for other, power in enumerate(item.signature)
                        if other != index
                    )
                ),
                default=None,
            )
            for index, axis in enumerate(self.axes)
        })

    def to_dict(self, principal: WeightedPrincipalPart | None = None) -> dict[str, Any]:
        weights = None if principal is None else {
            axis: principal.powers[axis].weight for axis in self.axes
        }
        active = tuple(item for item in self.lineage if not item.cancelled)
        signature_id = ";".join(
            f"{','.join(map(str, item.signature))}:{_label(item.coefficient)}"
            for item in active
        )
        faces = self._face_restrictions(weights)
        return {
            "status": "compiled",
            "arithmetic": "exact rational",
            "expression": self.expression,
            "chart": {
                "vertex": [_number(value) for value in self.vertex],
                "edge_axes": list(self.axes),
                "generators": {
                    axis: [_number(value) for value in self.generators[axis]]
                    for axis in self.axes
                },
            },
            "ambient_terms": [term.to_dict(self.axes, weights) for term in self.terms],
            "edge_monomials": [item.to_dict(self.axes, weights) for item in active],
            "cancellations": [item.to_dict(self.axes, weights) for item in self.cancellations],
            "face_restrictions": faces,
            "summary": {
                "ambient_term_count": len(self.terms),
                "transported_term_count": sum(bool(term.polynomial) for term in self.terms),
                "geometrically_suppressed_term_indices": [
                    term.index for term in self.terms if not term.polynomial
                ],
                "edge_monomial_count": len(active),
                "cancelled_edge_monomial_count": len(self.cancellations),
                "transport_signature": signature_id,
                "axial_orders": dict(self.axial_orders),
            },
        }

    def _face_restrictions(self, weights: Mapping[str, Fraction] | None) -> list[dict[str, Any]]:
        restrictions = []
        active = tuple(item for item in self.lineage if not item.cancelled)
        for size in range(1, len(self.axes) + 1):
            for raw_face in combinations(self.axes, size):
                face = frozenset(raw_face)
                surviving = tuple(
                    item for item in active if _support(item.signature, self.axes) <= face
                )
                term_states = []
                for term in self.terms:
                    term_survives = any(
                        _support(signature, self.axes) <= face
                        for signature in term.polynomial
                    )
                    term_states.append({
                        "term_index": term.index,
                        "status": "survives" if term_survives else "geometrically_suppressed",
                    })
                degree = None
                initial = ()
                if surviving and weights is not None:
                    degrees = {
                        item.signature: sum(
                            (
                                Fraction(power) * weights[axis]
                                for axis, power in zip(self.axes, item.signature)
                            ),
                            start=Fraction(0),
                        )
                        for item in surviving
                    }
                    degree = min(degrees.values())
                    initial = tuple(
                        item for item in surviving if degrees[item.signature] == degree
                    )
                ambient_initial = sorted({
                    index for item in initial for index, _ in item.contributions
                })
                restrictions.append({
                    "face": list(raw_face),
                    "status": "nonzero" if surviving else "zero_restriction",
                    "surviving_signatures": [list(item.signature) for item in surviving],
                    "initial_weighted_degree": None if degree is None else _number(degree),
                    "initial_ambient_term_indices": ambient_initial,
                    "ambient_terms": term_states,
                })
        return restrictions


@dataclass(frozen=True)
class AmbientFaceCompilation:
    """Exact ambient transport composed with the face-selection core."""

    transport: AmbientTransport
    selection: SelectionResult | None

    def to_dict(self, principal: WeightedPrincipalPart) -> dict[str, Any]:
        payload = self.transport.to_dict(principal)
        if self.selection is None:
            payload["selection"] = {
                "status": "no_nonconstant_perturbation",
                "q_star": None,
                "response_exponent": None,
                "winning_faces": [],
            }
            return payload
        winning = set(self.selection.winning_faces)
        faces = []
        for analysis in self.selection.analyses:
            signatures = (
                () if analysis.initial_form is None
                else tuple(
                    tuple(term.powers.get(axis, 0) for axis in self.transport.axes)
                    for term in analysis.initial_form.terms
                )
            )
            lineages = [
                item for item in self.transport.lineage
                if item.signature in signatures and not item.cancelled
            ]
            ambient_indices = sorted({
                index for item in lineages for index, _ in item.contributions
            })
            faces.append({
                "face": sorted(analysis.face),
                "status": analysis.status.value,
                "weighted_degree": (
                    None if analysis.degree is None else _number(analysis.degree)
                ),
                "winning": analysis.face in winning,
                "initial_signatures": [list(signature) for signature in signatures],
                "initial_ambient_term_indices": ambient_indices,
                "positivity_certificate": (
                    None if analysis.witness is None else {
                        "provenance": analysis.witness.provenance,
                        "coordinates": dict(analysis.witness.coordinates),
                    }
                ),
            })
        payload["selection"] = {
            "status": "selected" if self.selection.q_star is not None else "not_selected",
            "theorem_licensed": self.selection.theorem_licensed,
            "q_star": None if self.selection.q_star is None else _number(self.selection.q_star),
            "response_exponent": (
                None if self.selection.response_exponent is None
                else _number(self.selection.response_exponent)
            ),
            "winning_faces": [sorted(face) for face in self.selection.winning_faces],
            "faces": faces,
            "scope_blockers": list(self.selection.scope_blockers),
        }
        return payload


def transport_ambient_polynomial(
    expression: str,
    vertex: Sequence[int | float | str | Fraction],
    generators: Mapping[str, Sequence[int | float | str | Fraction]],
) -> AmbientTransport:
    """Transport a polynomial exactly and retain top-level term provenance."""
    axes = tuple(str(axis) for axis in generators)
    if not axes:
        raise ValueError("ambient transport needs at least one edge generator")
    exact_vertex = tuple(_fraction(value) for value in vertex)
    exact_generators = {
        str(axis): tuple(_fraction(value) for value in vector)
        for axis, vector in generators.items()
    }
    if any(len(vector) != len(exact_vertex) for vector in exact_generators.values()):
        raise ValueError("every edge generator must have the ambient dimension")
    zero = (0,) * len(axes)

    ambient_coordinates: list[ExactPolynomial] = []
    for coordinate, origin in enumerate(exact_vertex):
        polynomial: ExactPolynomial = {} if origin == 0 else {zero: origin}
        for edge_index, axis in enumerate(axes):
            coefficient = exact_generators[axis][coordinate]
            if coefficient == 0:
                continue
            signature = tuple(1 if i == edge_index else 0 for i in range(len(axes)))
            polynomial[signature] = coefficient
        ambient_coordinates.append(polynomial)

    def walk(node: ast.AST) -> ExactPolynomial:
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            # AST float constants have already passed through binary floating
            # point (and 1e-400 has already become 0.0).  Recover the original
            # token so decimal/scientific literals enter Fraction exactly.
            source = ast.get_source_segment(expression, node)
            literal = (
                source.replace("_", "")
                if isinstance(node.value, float) and source
                else node.value
            )
            value = _fraction(literal)
            return {} if value == 0 else {zero: value}
        if isinstance(node, ast.Name) and node.id.startswith("x") and node.id[1:].isdigit():
            index = int(node.id[1:])
            if index >= len(ambient_coordinates):
                raise ValueError("ambient variable index outside the chart dimension")
            return dict(ambient_coordinates[index])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return walk(node.operand)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return {signature: -coefficient for signature, coefficient in walk(node.operand).items()}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return _poly_add(walk(node.left), walk(node.right))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            return _poly_add(
                walk(node.left),
                {signature: -coefficient for signature, coefficient in walk(node.right).items()},
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return _poly_multiply(walk(node.left), walk(node.right))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            numerator, denominator = walk(node.left), walk(node.right)
            if set(denominator) != {zero} or denominator[zero] == 0:
                raise ValueError("polynomial division is allowed only by a nonzero constant")
            return {
                signature: coefficient / denominator[zero]
                for signature, coefficient in numerator.items()
            }
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant):
                raise ValueError("polynomial exponent must be a literal integer")
            exponent = node.right.value
            if isinstance(exponent, bool) or int(exponent) != exponent or not 0 <= exponent <= 64:
                raise ValueError("polynomial exponent must be an integer from 0 to 64")
            return _poly_power(walk(node.left), int(exponent), zero)
        raise ValueError("expression is not a polynomial in ambient coordinates")

    root = ast.parse(expression, mode="eval")
    terms = []
    contributions: dict[Signature, list[tuple[int, Fraction]]] = {}
    for index, node in enumerate(_additive_nodes(root.body)):
        polynomial = walk(node)
        constant = polynomial.pop(zero, Fraction(0))
        rendered = ast.unparse(ast.fix_missing_locations(node))
        term = AmbientTermTransport(index, rendered, constant, polynomial)
        terms.append(term)
        for signature, coefficient in polynomial.items():
            contributions.setdefault(signature, []).append((index, coefficient))

    lineage = tuple(
        EdgeMonomialLineage(
            signature,
            sum((coefficient for _, coefficient in items), start=Fraction(0)),
            tuple(items),
        )
        for signature, items in sorted(contributions.items())
    )
    return AmbientTransport(
        expression=expression,
        axes=axes,
        vertex=exact_vertex,
        generators=MappingProxyType(exact_generators),
        terms=tuple(terms),
        lineage=lineage,
    )


def compile_ambient_face_selection(
    expression: str,
    chart: EdgeCoordinateChart,
    principal: WeightedPrincipalPart,
    *,
    hypotheses: LawHypotheses | None = None,
    exact_vertex: Sequence[int | float | str | Fraction] | None = None,
    exact_generators: Mapping[
        str, Sequence[int | float | str | Fraction]
    ] | None = None,
) -> AmbientFaceCompilation:
    """Run the complete exact ambient-to-face-to-exponent hierarchy."""
    transport = transport_ambient_polynomial(
        expression,
        chart.vertex if exact_vertex is None else exact_vertex,
        chart.generators if exact_generators is None else exact_generators,
    )
    if not transport.polynomial:
        return AmbientFaceCompilation(transport, None)
    perturbation = PolynomialPerturbation(tuple(
        PerturbationMonomial(
            coefficient, _powers(signature, transport.axes)
        )
        for signature, coefficient in sorted(transport.polynomial.items())
    ), cancellation_tolerance=0.0)
    problem = FaceSelectionProblem(
        chart=chart,
        principal=principal,
        perturbation=perturbation,
        hypotheses=hypotheses or LawHypotheses(),
    )
    return AmbientFaceCompilation(transport, problem.select())


__all__ = [
    "AmbientFaceCompilation",
    "AmbientTermTransport",
    "AmbientTransport",
    "EdgeMonomialLineage",
    "ExactPolynomial",
    "MAX_TRANSPORTED_MONOMIALS",
    "Signature",
    "compile_ambient_face_selection",
    "exact_chart_from_active_constraints",
    "transport_ambient_polynomial",
]
