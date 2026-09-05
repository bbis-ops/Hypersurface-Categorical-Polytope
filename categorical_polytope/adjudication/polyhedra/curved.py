"""Exact two-dimensional polyhedral boundary for quadratic elimination."""

from __future__ import annotations

import ast
from fractions import Fraction
from itertools import combinations
from typing import Any, Sequence

from ...ambient_face_compiler import (
    exact_chart_from_active_constraints,
    transport_ambient_polynomial,
)
from ...curved_reduction import ReductionNotApplicable, reduce_quadratic_channel
from .domain import PolyhedronDomain


OPERATION = "polyhedral_curved_reduction"


def _bounded_in_edge_chart(rows: Sequence[Sequence[Fraction]]) -> bool:
    """Exactly exclude recession directions c>=0 by normalizing c0+c1=1.

    Write c=(t,1-t). Each row gives one affine inequality in t. The
    polyhedron is bounded precisely when their intersection with [0,1]
    is empty. Feasibility and a full-dimensional simple chart are checked
    by the caller.
    """
    lower, upper = Fraction(0), Fraction(1)
    for first, second in rows:
        slope = first - second
        if slope > 0:
            upper = min(upper, -second / slope)
        elif slope < 0:
            lower = max(lower, -second / slope)
        elif second > 0:
            return True
        if lower > upper:
            return True
    return False


def analyze_curved_polyhedron(
    system: str, base_expression: str, perturbation_expression: str,
    *, request_id: str | None = None,
) -> dict[str, Any]:
    """License the reduction only after exact global and local checks.

    Vertex selection uses the base alone: an exact positive diagonal loss
    proves that the candidate is its unique global maximizer. No optimizer
    fit, sampled order, or observed exponent is used in the certificate.
    """
    poly = PolyhedronDomain.parse_system(system)  # input size/dimension guards
    result: dict[str, Any] = {
        "schema_version": "curved-reduction.backend.v1",
        "operation": OPERATION,
        "request_id": request_id,
        "status": "outside_scope",
        "answered": False,
        "licensed": False,
        "scope": {"licensed": False, "blockers": []},
    }
    if poly.dim != 2:
        result["scope"]["blockers"] = ["quadratic elimination currently requires dimension two"]
        return result
    raw_rows, raw_rhs = ast.literal_eval(system)
    rows = [tuple(Fraction(str(entry)) for entry in row) for row in raw_rows]
    rhs = [Fraction(str(entry)) for entry in raw_rhs]
    axes = ("c0", "c1")
    attempts = []
    for active in combinations(range(len(rows)), 2):
        try:
            vertex, generators = exact_chart_from_active_constraints(rows, rhs, active, axes=axes)
        except ValueError:  # singular active matrix
            continue
        slacks = [bound - sum(a * x for a, x in zip(row, vertex))
                  for row, bound in zip(rows, rhs)]
        if any(slack < 0 for slack in slacks):
            continue
        if tuple(i for i, slack in enumerate(slacks) if slack == 0) != active:
            continue  # extra active constraints: not a simple chart
        chart_rows = [tuple(sum(a * u for a, u in zip(row, generators[axis]))
                            for axis in axes) for row in rows]
        if not _bounded_in_edge_chart(chart_rows):
            result["scope"]["blockers"] = ["exact recession test finds an unbounded polyhedron"]
            return result
        base = transport_ambient_polynomial(base_expression, vertex, generators)
        perturbation = transport_ambient_polynomial(perturbation_expression, vertex, generators)
        loss = {signature: -coefficient for signature, coefficient in base.polynomial.items()
                if signature != (0, 0)}
        gain = {signature: coefficient for signature, coefficient in perturbation.polynomial.items()
                if signature != (0, 0)}
        try:
            certificate = reduce_quadratic_channel(loss, gain, axes=axes)
        except ReductionNotApplicable as exc:
            attempts.append({"vertex_exact": [str(x) for x in vertex], "reason": str(exc)})
            continue
        evidence = certificate.to_dict()
        return {
            **result,
            "status": "licensed",
            "answered": True,
            "licensed": True,
            "localization": {
                "vertex": [float(x) for x in vertex],
                "vertex_exact": [str(x) for x in vertex],
                "active_constraints": list(active),
                "generators_exact": {axis: [str(x) for x in generators[axis]] for axis in axes},
                "constraint_slacks_exact": [str(slack) for slack in slacks],
                "base_vertex_value_exact": str(base.polynomial.get((0, 0), Fraction(0))),
                "perturbation_vertex_value_exact": str(perturbation.polynomial.get((0, 0), Fraction(0))),
            },
            "reduction": evidence,
            "scaling": {
                "kind": "asymptotic_equivalent",
                "response_exponent": float(certificate.exponent),
                "response_exponent_exact": str(certificate.exponent),
                "effective_weight_exact": str(certificate.effective_weight),
                "leading_coefficient": evidence["leading_coefficient"],
                "law": "M(s)-F(v)-s*G(v) ~ C*s**gamma",
            },
            "scope": {
                "licensed": True,
                "blockers": [],
                "proof_basis": "exact full-polynomial transport and quadratic elimination",
                "checks": {
                    "exact_feasible_simple_vertex": True,
                    "exact_bounded_recession_cone": True,
                    "exact_global_base_loss": True,
                    "unique_global_base_maximizer": True,
                    "polynomial_remainders": True,
                    "positive_witness_eventually_feasible": True,
                    "omitted_base_is_subleading": True,
                },
                "limitation": "witness coordinate rates need not be exact optimizer coordinate rates",
            },
        }
    result["scope"]["blockers"] = ["no exact feasible simple vertex satisfies the quadratic-reduction hypotheses"]
    result["attempts"] = attempts
    return result
