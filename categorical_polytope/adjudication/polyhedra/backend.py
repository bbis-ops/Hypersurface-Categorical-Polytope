"""Production boundary for the face-selection asset.

The mathematical core lives in :mod:`categorical_polytope.face_selection` and
the measured general-polyhedron predictor lives in :mod:`.predict`.  This
module turns the latter into a stable, JSON-safe backend capability with three
explicit stages:

``localization``
    Replace the global polyhedron by the selected simple vertex, its tangent
    cone and the active constraints.

``selection``
    Rank admissible tangent-cone faces by weighted degree, retain the minimum
    and explain every filtered face.

``scaling``
    Convert the winning degree to the response exponent and attach the measured
    leading coefficient when it has settled.

The response never hides scope.  An algebraic prediction whose analytic
hypotheses are not licensed is returned with status ``unlicensed``; a setting
outside the mechanism is returned as ``refused``; malformed requests become an
``invalid_request`` envelope rather than an exception crossing the boundary.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from ...ambient_face_compiler import (
    compile_ambient_face_selection,
    exact_chart_from_active_constraints,
    transport_ambient_polynomial,
)
from ...face_selection import BasePower, EdgeCoordinateChart, WeightedPrincipalPart
from ...face_selection_phase import problem_from_mapping as phase_problem_from_mapping
from .domain import PolyhedronDomain
from .predict import (
    CRITICAL,
    INACTIVE,
    RELEVANT,
    RULE,
    SUBLEADING,
    Face,
    Prediction,
    calibrate,
    consistent_faces,
    predict,
)


SCHEMA_VERSION = "face-selection.backend.v1"
ASSET_VERSION = "portable-principle.v7"
OPERATION = "polyhedral_face_selection"
PORTFOLIO_OPERATION = "polyhedral_face_selection_portfolio"
PHASE_OPERATION = "polyhedral_face_selection_phase_diagram"
DISCOVERY_OPERATION = "polyhedral_face_selection_discovery"
MAX_EXPRESSION_LENGTH = 20_000
MAX_PERTURBATION_TERMS = 64
MAX_PORTFOLIO_CASES = 256
MAX_PHASE_EVALUATIONS = 256
TERM_DOMINANCE_TOLERANCE = 5e-3

CAPABILITIES: tuple[str, ...] = (
    "organizes_theory",
    "explains_mechanism",
    "predicts_exponent",
    "filters_irrelevant_directions",
    "classifies_perturbations",
    "reveals_active_constraints",
    "generalizes_across_simple_polyhedral_vertices",
    "reports_mathematical_warrant",
    "compares_universality_classes",
    "detects_active_constraint_transitions",
    "computes_exact_universality_phase_diagrams",
    "derives_parametric_newton_weights",
    "reports_transition_robustness",
    "stratifies_dynamic_qualification_walls",
    "certifies_qualified_selection_consequences",
    "constructs_mixed_sign_binomial_witnesses",
    "compiles_exact_ambient_to_face_transport",
    "retains_ambient_term_provenance_and_cancellation",
    "compares_ambient_transport_across_geometries",
    "discovers_candidate_exponent_laws",
    "screens_large_perturbation_families",
    "diagnoses_observed_exponent_mechanisms",
)

PRINCIPLES: tuple[dict[str, str], ...] = (
    {
        "stage": "localization",
        "principle": "the tangent cone replaces the original global geometry",
        "input": "polyhedron, base objective and perturbation",
        "output": "simple maximizing vertex, edge coordinates and active constraints",
    },
    {
        "stage": "selection",
        "principle": "admissible faces are ranked by weighted degree",
        "input": "tangent-cone faces and face-restricted perturbation",
        "output": "q_star, winning faces and rejected-face reasons",
    },
    {
        "stage": "scaling",
        "principle": "the winning degree is converted into the response exponent",
        "input": "q_star in the open unit interval",
        "output": "gamma = 1 / (1 - q_star) and the leading gap profile",
    },
)


class RequestValidationError(ValueError):
    """The JSON envelope does not satisfy the public request contract."""


@dataclass(frozen=True)
class FaceSelectionRequest:
    """One backend request.

    ``system`` is the predictor's literal ``([[...]], [...])`` representation
    of ``Ax <= b``.  ``base`` and ``perturbation`` use the existing safe
    arithmetic-expression whitelist.  ``observed_exponent`` activates the
    inverse law and reports which faces are consistent with the observation.
    """

    system: str
    base: str
    perturbation: str
    observed_exponent: float | None = None
    observation_tolerance: float = 0.05
    request_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("system", "base", "perturbation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise RequestValidationError(f"{name} must be a non-empty string")
            if len(value) > MAX_EXPRESSION_LENGTH:
                raise RequestValidationError(
                    f"{name} exceeds the {MAX_EXPRESSION_LENGTH}-character limit"
                )
        if self.request_id is not None:
            if not isinstance(self.request_id, str) or not self.request_id.strip():
                raise RequestValidationError("request_id must be a non-empty string")
            if len(self.request_id) > 128:
                raise RequestValidationError("request_id exceeds 128 characters")
        if self.observed_exponent is not None:
            try:
                observed = float(self.observed_exponent)
            except (TypeError, ValueError) as exc:
                raise RequestValidationError("observed_exponent must be numeric") from exc
            if not math.isfinite(observed):
                raise RequestValidationError("observed_exponent must be finite")
            object.__setattr__(self, "observed_exponent", observed)
        try:
            tolerance = float(self.observation_tolerance)
        except (TypeError, ValueError) as exc:
            raise RequestValidationError("observation_tolerance must be numeric") from exc
        if not math.isfinite(tolerance) or tolerance < 0.0:
            raise RequestValidationError(
                "observation_tolerance must be finite and nonnegative"
            )
        object.__setattr__(self, "observation_tolerance", tolerance)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "FaceSelectionRequest":
        if not isinstance(payload, Mapping):
            raise RequestValidationError("request must be a JSON object")
        perturbation = payload.get("perturbation", payload.get("pert"))
        return cls(
            system=payload.get("system"),
            base=payload.get("base"),
            perturbation=perturbation,
            observed_exponent=payload.get("observed_exponent"),
            observation_tolerance=payload.get("observation_tolerance", 0.05),
            request_id=payload.get("request_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "system": self.system,
            "base": self.base,
            "perturbation": self.perturbation,
            "observed_exponent": self.observed_exponent,
            "observation_tolerance": self.observation_tolerance,
        }


@dataclass(frozen=True)
class DiscoveryCandidate:
    """One perturbation submitted to family screening."""

    candidate_id: str
    expression: str
    observed_exponent: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise RequestValidationError("discovery candidate id must be non-empty")
        if len(self.candidate_id) > 128:
            raise RequestValidationError("discovery candidate id exceeds 128 characters")
        if not isinstance(self.expression, str) or not self.expression.strip():
            raise RequestValidationError(
                f"discovery candidate {self.candidate_id!r} needs an expression"
            )
        if len(self.expression) > MAX_EXPRESSION_LENGTH:
            raise RequestValidationError(
                f"discovery candidate {self.candidate_id!r} exceeds the expression limit"
            )
        if self.observed_exponent is not None:
            observed = float(self.observed_exponent)
            if not math.isfinite(observed):
                raise RequestValidationError("observed_exponent must be finite")
            object.__setattr__(self, "observed_exponent", observed)
        if not isinstance(self.metadata, Mapping):
            raise RequestValidationError("discovery candidate metadata must be an object")
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass
class FaceSelectionBackend:
    """Stateful backend facade that can reuse one adjudication domain."""

    domain: PolyhedronDomain = field(default_factory=PolyhedronDomain)

    def analyze(self, request: FaceSelectionRequest) -> dict[str, Any]:
        prediction = predict(
            request.system,
            request.base,
            request.perturbation,
            domain=self.domain,
        )
        return _response(request, prediction, domain=self.domain)

    def handle(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Validate and analyze one payload without leaking request exceptions."""
        request_id = payload.get("request_id") if isinstance(payload, Mapping) else None
        if isinstance(payload, Mapping) and payload.get("operation") in {
            "discover", "discovery", DISCOVERY_OPERATION
        }:
            return self.handle_discovery(payload)
        if isinstance(payload, Mapping) and payload.get("operation") in {
            "phase", "phase_diagram", PHASE_OPERATION
        }:
            return self.handle_phase_diagram(payload)
        if isinstance(payload, Mapping) and payload.get("operation") in {
            "portfolio", "compare", PORTFOLIO_OPERATION
        }:
            return self.handle_portfolio(payload)
        try:
            request = FaceSelectionRequest.from_mapping(payload)
        except (RequestValidationError, TypeError, ValueError) as exc:
            return _error_response("invalid_request", str(exc), request_id=request_id)
        try:
            return self.analyze(request)
        except Exception as exc:  # the backend boundary must remain total
            return _error_response(
                "analysis_error",
                f"{type(exc).__name__}: {exc}",
                request_id=request.request_id,
            )

    def handle_many(self, payloads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Analyze a batch independently; one bad item never aborts the rest."""
        return [self.handle(payload) for payload in payloads]

    def handle_portfolio(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Compare related cases and identify universality-class transitions."""
        request_id = payload.get("request_id")
        cases = payload.get("cases")
        if not isinstance(cases, list) or not cases:
            return _error_response(
                "invalid_request", "portfolio cases must be a non-empty JSON array",
                request_id=request_id,
            )
        if len(cases) > MAX_PORTFOLIO_CASES:
            return _error_response(
                "invalid_request",
                f"portfolio exceeds the {MAX_PORTFOLIO_CASES}-case limit",
                request_id=request_id,
            )
        responses = [
            (
                _error_response(
                    "invalid_request", "nested portfolios are not supported",
                    request_id=case.get("request_id"),
                )
                if isinstance(case, Mapping) and case.get("operation") in {
                    "portfolio", "compare", PORTFOLIO_OPERATION
                }
                else self.handle(case)
            ) if isinstance(case, Mapping)
            else _error_response("invalid_request", "portfolio cases must be JSON objects")
            for case in cases
        ]
        return _portfolio_response(responses, request_id=request_id)

    def handle_discovery(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Compile and screen a perturbation family for candidate exponent laws."""
        request_id = payload.get("request_id")
        system, base = payload.get("system"), payload.get("base")
        if not isinstance(system, str) or not system.strip():
            return _error_response(
                "invalid_request", "discovery system must be a non-empty string",
                request_id=request_id, operation=DISCOVERY_OPERATION,
            )
        if not isinstance(base, str) or not base.strip():
            return _error_response(
                "invalid_request", "discovery base must be a non-empty string",
                request_id=request_id, operation=DISCOVERY_OPERATION,
            )
        try:
            candidates = _discovery_candidates(payload, domain=self.domain)
            raw_known = payload.get("known_class_ids", ())
            if not isinstance(raw_known, Sequence) or isinstance(raw_known, (str, bytes)):
                raise RequestValidationError("known_class_ids must be a JSON array")
            known_class_ids = {
                str(class_id) for class_id in raw_known
                if isinstance(class_id, str) and class_id
            }
            if len(known_class_ids) != len(raw_known):
                raise RequestValidationError(
                    "known_class_ids entries must be distinct non-empty strings"
                )
            include_cases = payload.get("include_cases", False)
            if not isinstance(include_cases, bool):
                raise RequestValidationError("include_cases must be boolean")
        except (RequestValidationError, TypeError, ValueError, ArithmeticError) as exc:
            return _error_response(
                "invalid_request", str(exc), request_id=request_id,
                operation=DISCOVERY_OPERATION,
            )

        responses = []
        for candidate in candidates:
            candidate_payload: dict[str, Any] = {
                "request_id": candidate.candidate_id,
                "system": system,
                "base": base,
                "perturbation": candidate.expression,
            }
            if candidate.observed_exponent is not None:
                candidate_payload["observed_exponent"] = candidate.observed_exponent
            responses.append(self.handle(candidate_payload))
        return _discovery_response(
            candidates,
            responses,
            request_id=request_id,
            known_class_ids=known_class_ids,
            registry_supplied="known_class_ids" in payload,
            include_cases=include_cases,
        )

    def handle_phase_diagram(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Compute an exact continuum of face-selection transitions."""
        request_id = payload.get("request_id")
        raw_mechanisms = payload.get("mechanisms", payload.get("candidates"))
        if isinstance(raw_mechanisms, Sequence) and not isinstance(
            raw_mechanisms, (str, bytes)
        ) and len(raw_mechanisms) > MAX_PORTFOLIO_CASES:
            return _error_response(
                "invalid_request",
                f"phase diagram exceeds the {MAX_PORTFOLIO_CASES}-mechanism limit",
                request_id=request_id,
                operation=PHASE_OPERATION,
            )
        assumptions = payload.get("assumptions", {})
        if not isinstance(assumptions, Mapping):
            return _error_response(
                "invalid_request", "phase assumptions must be a JSON object",
                request_id=request_id, operation=PHASE_OPERATION,
            )
        try:
            problem = phase_problem_from_mapping(payload)
            diagram = problem.solve()
            raw_evaluations = payload.get("evaluate_at", ())
            if not isinstance(raw_evaluations, Sequence) or isinstance(
                raw_evaluations, (str, bytes)
            ):
                raise ValueError("evaluate_at must be a JSON array")
            if len(raw_evaluations) > MAX_PHASE_EVALUATIONS:
                raise ValueError(
                    f"evaluate_at exceeds the {MAX_PHASE_EVALUATIONS}-point limit"
                )
            evaluations = [diagram.evaluate(value).to_dict() for value in raw_evaluations]
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            return _error_response(
                "invalid_request", str(exc), request_id=request_id,
                operation=PHASE_OPERATION,
            )
        dynamic_qualification = any(
            mechanism.coefficient is not None for mechanism in problem.mechanisms
        )
        fixed_admissibility = assumptions.get("fixed_admissibility") is True
        coefficient_qualification_verified = (
            assumptions.get("coefficient_qualification_verified") is True
        )
        affine_degrees_verified = assumptions.get("affine_degrees_verified") is True
        uniform_local_base_maximality = (
            assumptions.get("uniform_local_base_maximality") is True
        )
        uniform_principal_remainder = (
            assumptions.get("uniform_principal_remainder") is True
        )
        uniform_global_isolation = (
            assumptions.get("uniform_global_isolation") is True
        )
        qualification_licensed = fixed_admissibility and (
            coefficient_qualification_verified if dynamic_qualification else True
        )
        licensed = all((
            qualification_licensed,
            affine_degrees_verified,
            uniform_local_base_maximality,
            uniform_principal_remainder,
            uniform_global_isolation,
        ))
        blockers = []
        if dynamic_qualification and not coefficient_qualification_verified:
            blockers.append(
                "coefficient qualification is not verified across the parameter domain"
            )
        if not fixed_admissibility:
            blockers.append(
                "fixed_admissibility is not verified across the parameter domain"
            )
        if not affine_degrees_verified:
            blockers.append(
                "affine weighted-degree laws are not verified across the parameter domain"
            )
        if not uniform_local_base_maximality:
            blockers.append("local base maximality is not verified uniformly")
        if not uniform_principal_remainder:
            blockers.append("principal remainder control is not verified uniformly")
        if not uniform_global_isolation:
            blockers.append("global isolation is not verified uniformly")
        return {
            "schema_version": SCHEMA_VERSION,
            "asset_version": ASSET_VERSION,
            "operation": PHASE_OPERATION,
            "request_id": request_id if isinstance(request_id, str) else None,
            "status": "licensed" if licensed else "unlicensed",
            "answered": True,
            "licensed": licensed,
            "capabilities": list(CAPABILITIES),
            "principles": [dict(principle) for principle in PRINCIPLES],
            "theorem": {
                "name": "stratified qualified-selection phase-fan law",
                "result": (
                    "the qualified winning face is constant between affine-degree, "
                    "relevance, and coefficient-qualification walls"
                ),
                "qualification": (
                    "a mechanism competes only when its face is admitted, its "
                    "coefficient is positive, and 0 < q_face(parameter) < 1"
                ),
                "selection": "q_star(parameter) = min qualified q_face(parameter)",
                "scaling": "gamma(parameter) = 1 / (1 - q_star(parameter))",
                "mult_parameter_extension": (
                    "degree equalities become affine hyperplanes forming a phase fan"
                ),
            },
            "phase_diagram": diagram.to_dict(),
            "evaluations": evaluations,
            "scope": {
                "licensed": licensed,
                "assumptions": {
                    "fixed_admissibility": fixed_admissibility,
                    "dynamic_coefficient_qualification": dynamic_qualification,
                    "coefficient_qualification_verified": (
                        coefficient_qualification_verified
                    ),
                    "affine_degrees_verified": affine_degrees_verified,
                    "uniform_local_base_maximality": uniform_local_base_maximality,
                    "uniform_principal_remainder": uniform_principal_remainder,
                    "uniform_global_isolation": uniform_global_isolation,
                },
                "blockers": blockers,
                "boundary": (
                    "affine coefficient walls and distinct mixed-sign binomials are "
                    "resolved exactly; larger mixed-sign forms and changing geometry "
                    "require explicit strata"
                ),
            },
            "audit": {
                "engine": "face_selection_phase.ParametricFaceSelectionProblem",
                "arithmetic": "exact rational",
                "degree_compiler": "q(parameter) = sum alpha_i(parameter) / beta_i",
                "wall_rule": (
                    "q_i=q_j together with q_i=0, q_i=1, and coefficient_i=0"
                ),
                "selection_rule": "minimum weighted degree among qualified mechanisms",
                "backend_contract": SCHEMA_VERSION,
                "asset_version": ASSET_VERSION,
            },
        }


def analyze_face_selection(
    payload: Mapping[str, Any], *, backend: FaceSelectionBackend | None = None
) -> dict[str, Any]:
    """Convenience function for frameworks that prefer a pure handler."""
    return (backend or FaceSelectionBackend()).handle(payload)


def _response(
    request: FaceSelectionRequest,
    prediction: Prediction,
    *,
    domain: PolyhedronDomain,
) -> dict[str, Any]:
    licensed = _backend_licensed(prediction)
    status = (
        "refused" if not prediction.answered
        else "licensed" if licensed
        else "unlicensed"
    )
    faces = [_face_dict(face) for face in prediction.faces]
    groups = prediction.by_relevance()
    hypotheses, blockers = _scope(prediction)
    invariants = _effective_invariants(request, prediction)
    universality = _universality_class(prediction, invariants)
    mechanism = _mechanism(prediction, invariants)
    perturbation_analysis = _classify_perturbation_terms(
        request, prediction, domain=domain,
        effective_weight=invariants["weighted_degree"],
    )

    localization = {
        "status": "localized" if prediction.vertex else "not_localized",
        "vertex": [_clean_zero(value) for value in prediction.vertex],
        "tangent_cone_face_count": len(prediction.faces),
        "constraints": {
            "binding": list(prediction.binding),
            "released": list(prediction.released),
        },
    }
    selection = {
        "status": "selected" if prediction.answered else "not_selected",
        "weighted_degree": invariants["weighted_degree"],
        "measured_weighted_degree": prediction.weighted_degree,
        "invariant_source": invariants["source"],
        "winning_faces": [list(face) for face in prediction.winning_faces],
        "faces": faces,
        "relevance_classes": {
            name: [_face_dict(face) for face in groups[name]]
            for name in (RELEVANT, CRITICAL, SUBLEADING, INACTIVE)
        },
        "filtered_face_count": sum(not face.admitted for face in prediction.faces),
    }
    scaling = {
        "status": "scaled" if prediction.answered else "not_scaled",
        "response_exponent": invariants["response_exponent"],
        "measured_response_exponent": prediction.exponent,
        "law": (
            {
                "kind": "theta_power",
                "expression": "gap = Theta(s**gamma)",
                "gamma": invariants["response_exponent"],
                "from_weighted_degree": "gamma = 1 / (1 - q_star)",
            }
            if prediction.answered else None
        ),
        "leading_coefficient": {
            "value": prediction.coefficient,
            "settled": prediction.coefficient_settled,
            "interpretation": "model-specific local geometry and amplitude",
        },
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "asset_version": ASSET_VERSION,
        "operation": OPERATION,
        "request_id": request.request_id,
        "status": status,
        "answered": prediction.answered,
        "licensed": licensed,
        "capabilities": list(CAPABILITIES),
        "principles": [dict(principle) for principle in PRINCIPLES],
        "localization": localization,
        "selection": selection,
        "scaling": scaling,
        "active_constraints": {
            "binding": list(prediction.binding),
            "released": list(prediction.released),
            "interpretation": (
                "released constraints open the winning asymptotic channel; "
                "binding constraints define its face"
            ),
        },
        "mechanism": mechanism,
        "ambient_hierarchy": invariants["ambient_hierarchy"],
        "perturbation_analysis": perturbation_analysis,
        "universality_class": universality,
        "exact_refinement": invariants["refinement"],
        "scope": {
            "licensed": licensed,
            "hypotheses": hypotheses,
            "blockers": blockers,
            "refusal": prediction.refusal or None,
        },
        "inverse": _inverse(request, prediction),
        "audit": {
            "rule": RULE,
            "engine": "adjudication.polyhedra.predict",
            "selection_rule": "minimum admissible face weight",
            "backend_contract": SCHEMA_VERSION,
            "asset_version": ASSET_VERSION,
        },
    }


def _effective_invariants(
    request: FaceSelectionRequest, prediction: Prediction
) -> dict[str, Any]:
    measured_q = prediction.weighted_degree
    measured_gamma = prediction.exponent
    refinement: dict[str, Any] = {
        "status": "not_available",
        "source": "numerical face-restriction predictor",
        "measured_weighted_degree": measured_q,
        "measured_response_exponent": measured_gamma,
    }
    unavailable_hierarchy: dict[str, Any] = {
        "status": "not_available",
        "chain": [
            "ambient_polynomial",
            "exact_edge_chart_pullback",
            "feasible_face_restriction",
            "weighted_degree_selection",
            "response_exponent",
        ],
    }
    symbolic = _symbolic_term_classification(
        request.perturbation,
        prediction,
        system=request.system,
        base_expression=request.base,
    )
    if not prediction.answered:
        if symbolic is None:
            ambient_hierarchy = unavailable_hierarchy
        else:
            ambient_hierarchy = _ambient_hierarchy(
                request,
                prediction,
                symbolic,
                weighted_degree=symbolic.get("weighted_degree"),
                response_exponent=symbolic.get("response_exponent"),
            )
            refinement.update({
                "status": "classified_outside_scaling_regime",
                "source": "exact polynomial transport to edge coordinates",
                "symbolic_relevance": symbolic.get("relevance"),
                "weighted_degree": symbolic.get("weighted_degree"),
            })
        return {
            "weighted_degree": measured_q,
            "response_exponent": measured_gamma,
            "source": "numerical_face_restriction",
            "refinement": refinement,
            "ambient_hierarchy": ambient_hierarchy,
        }

    if symbolic is None:
        refinement["status"] = "non_polynomial_fallback"
        ambient_hierarchy = {
            **unavailable_hierarchy,
            "status": "non_polynomial_fallback",
            "fallback": "safe numerical face-restriction predictor",
        }
    elif symbolic["relevance"] != "relevant":
        ambient_hierarchy = _ambient_hierarchy(
            request, prediction, symbolic,
            weighted_degree=measured_q, response_exponent=measured_gamma,
        )
        refinement.update({
            "status": "not_applied",
            "reason": f"full symbolic perturbation classified as {symbolic['relevance']}",
        })
    elif not symbolic.get("selection_complete", False):
        ambient_hierarchy = _ambient_hierarchy(
            request, prediction, symbolic,
            weighted_degree=measured_q, response_exponent=measured_gamma,
        )
        refinement.update({
            "status": "incomplete",
            "reason": "at least one symbolic face still needs positivity evidence",
            "unresolved_faces": symbolic.get("unresolved_faces", []),
        })
    else:
        exact_q = float(symbolic["weighted_degree"])
        exact_gamma = float(symbolic["response_exponent"])
        ambient_hierarchy = _ambient_hierarchy(
            request, prediction, symbolic,
            weighted_degree=exact_q, response_exponent=exact_gamma,
        )
        refinement.update({
            "status": "applied",
            "source": "exact polynomial transport to edge coordinates",
            "weighted_degree": exact_q,
            "response_exponent": exact_gamma,
            "supporting_faces": symbolic["supporting_faces"],
            "positivity_certificates": symbolic.get("positivity_certificates", []),
            "weighted_degree_correction": (
                None if measured_q is None else exact_q - measured_q
            ),
            "response_exponent_correction": (
                None if measured_gamma is None else exact_gamma - measured_gamma
            ),
        })
        return {
            "weighted_degree": exact_q,
            "response_exponent": exact_gamma,
            "source": "exact_polynomial_transport",
            "refinement": refinement,
            "ambient_hierarchy": ambient_hierarchy,
        }
    return {
        "weighted_degree": measured_q,
        "response_exponent": measured_gamma,
        "source": "numerical_face_restriction",
        "refinement": refinement,
        "ambient_hierarchy": ambient_hierarchy,
    }


def _localized_compiler_inputs(
    prediction: Prediction,
    *,
    system: str | None = None,
    base_expression: str | None = None,
) -> tuple[
    EdgeCoordinateChart,
    WeightedPrincipalPart,
    Sequence[int | float | str | Fraction],
    Mapping[str, Sequence[int | float | str | Fraction]],
    str,
    str,
] | None:
    """Build the feasible edge chart and its detected Newton weights."""
    vertex = tuple(prediction.vertex)
    edges = tuple(tuple(edge) for edge in prediction.metrics.get("edges") or ())
    betas = tuple(prediction.metrics.get("betas") or ())
    if not vertex or not edges or len(edges) != len(betas):
        return None
    axes = tuple(f"c{i}" for i in range(len(edges)))
    exact_vertex: Sequence[int | float | str | Fraction] = vertex
    exact_generators: Mapping[
        str, Sequence[int | float | str | Fraction]
    ] = {axis: edge for axis, edge in zip(axes, edges)}
    chart_source = "rounded predictor metrics"
    if system is not None:
        try:
            raw_system = ast.literal_eval(system)
            rows, rhs = raw_system
            exact_vertex, exact_generators = exact_chart_from_active_constraints(
                rows,
                rhs,
                prediction.metrics.get("active_constraints") or (),
                axes=axes,
            )
            chart_source = "exact active-constraint solve"
        except (SyntaxError, TypeError, ValueError, ArithmeticError):
            pass
    weight_source = "numerical directional-order detection"
    if base_expression is not None:
        try:
            base_transport = transport_ambient_polynomial(
                base_expression, exact_vertex, exact_generators
            )
            exact_orders = base_transport.axial_orders
            if all(
                exact_orders.get(axis) is not None
                and exact_orders[axis] > 1
                for axis in axes
            ):
                betas = tuple(exact_orders[axis] for axis in axes)
                weight_source = "exact base-pullback axial orders"
        except (SyntaxError, TypeError, ValueError, OverflowError, ArithmeticError):
            pass
    try:
        chart = EdgeCoordinateChart(
            vertex=tuple(float(value) for value in exact_vertex),
            generators={
                axis: tuple(float(value) for value in exact_generators[axis])
                for axis in axes
            },
        )
        principal = WeightedPrincipalPart({
            axis: BasePower(1.0, beta)
            for axis, beta in zip(axes, betas)
        })
    except (TypeError, ValueError, ArithmeticError):
        return None
    return (
        chart,
        principal,
        exact_vertex,
        exact_generators,
        chart_source,
        weight_source,
    )


def _ambient_hierarchy(
    request: FaceSelectionRequest,
    prediction: Prediction,
    symbolic: Mapping[str, Any],
    *,
    weighted_degree: float | None,
    response_exponent: float | None,
) -> dict[str, Any]:
    """Expose ambient -> face -> weight -> exponent as one audit object."""
    inputs = _localized_compiler_inputs(
        prediction, system=request.system, base_expression=request.base
    )
    perturbation = symbolic.get("ambient_transport")
    chain = [
        "ambient_polynomial",
        "exact_edge_chart_pullback",
        "feasible_face_restriction",
        "weighted_degree_selection",
        "response_exponent",
    ]
    if inputs is None:
        return {
            "status": "not_available",
            "chain": chain,
            "perturbation_pullback": perturbation,
        }
    (
        chart,
        principal,
        exact_vertex,
        exact_generators,
        chart_source,
        weight_source,
    ) = inputs
    try:
        base = transport_ambient_polynomial(
            request.base, exact_vertex, exact_generators
        ).to_dict(principal)
    except (SyntaxError, TypeError, ValueError, OverflowError, ArithmeticError) as exc:
        base = {
            "status": "non_polynomial_fallback",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    base_orders = (base.get("summary") or {}).get("axial_orders", {})
    detected_orders = {
        axis: float(power.order) for axis, power in principal.powers.items()
    }
    agreement = {
        axis: (
            base_orders.get(axis) is not None
            and abs(float(base_orders[axis]) - detected_orders[axis]) <= 5e-3
        )
        for axis in principal.axes
    }
    return {
        "status": "compiled" if perturbation else "partial",
        "arithmetic": "exact rational relative to the localized chart",
        "chart_source": chart_source,
        "chain": chain,
        "base_pullback": base,
        "perturbation_pullback": perturbation,
        "weight_layer": {
            "weight_source": weight_source,
            "detected_base_orders": detected_orders,
            "exact_pullback_axial_orders": base_orders,
            "orders_agree": agreement,
            "weights": {
                axis: {
                    "exact": str(power.weight),
                    "value": float(power.weight),
                }
                for axis, power in principal.powers.items()
            },
        },
        "selection_layer": {
            "rule": "minimum qualified weighted degree after feasible-face restriction",
            "q_star": weighted_degree,
            "winning_faces": symbolic.get("supporting_faces", []),
            "full_perturbation_authoritative": True,
        },
        "exponent_layer": {
            "formula": "gamma = 1 / (1 - q_star)",
            "response_exponent": response_exponent,
        },
        "counterexample_resolution": (
            "ambient coordinate-axis orders are not used; Newton data is computed "
            "only after exact pullback to feasible edge coordinates"
        ),
    }


def _mechanism(
    prediction: Prediction, invariants: Mapping[str, Any]
) -> dict[str, Any]:
    measured_relevant = {
        float(face.degree) for face in prediction.faces
        if face.admitted and face.degree is not None and 0.0 < face.degree < 1.0
    }
    q_star = invariants["weighted_degree"] if prediction.answered else None
    relevant_degrees = sorted({
        (q_star if q_star is not None and abs(degree - q_star) <= TERM_DOMINANCE_TOLERANCE
         else degree)
        for degree in measured_relevant
    })
    higher = [degree for degree in relevant_degrees
              if q_star is not None and degree > q_star + 1e-6]
    next_degree = min(higher) if higher else None
    margin = None if q_star is None or next_degree is None else next_degree - q_star
    filtered = [face for face in prediction.faces if not face.admitted]
    return {
        "hierarchy": [
            "ambient_polynomial",
            "exact_edge_chart_pullback",
            "feasible_face_restrictions",
            "weighted_degree_selection",
            "response_exponent_gamma",
        ],
        "localization": (
            "the selected vertex and tangent cone contain all geometry used by the law"
        ),
        "selection": {
            "rule": "minimum admissible weighted degree",
            "q_star": q_star,
            "relevant_degrees": relevant_degrees,
            "next_competing_degree": next_degree,
            "selection_margin": margin,
            "tied_minimal_channels": len(prediction.winning_faces),
            "robust_to_higher_weight_terms": q_star is not None,
        },
        "scaling": {
            "formula": "gamma = 1 / (1 - q_star)",
            "gamma": invariants["response_exponent"],
            "monotonicity": (
                "gamma increases with q on (0,1); for small s the smallest gamma "
                "produces the largest gap"
            ),
        },
        "geometry_filter": {
            "examined_faces": len(prediction.faces),
            "filtered_faces": len(filtered),
            "reasons": sorted({face.reason for face in filtered if face.reason}),
        },
        "active_set": {
            "winning_faces": [list(face) for face in prediction.winning_faces],
            "binding_constraints": list(prediction.binding),
            "released_constraints": list(prediction.released),
        },
        "coefficient_semantics": (
            "q_star determines the universality class; the leading coefficient "
            "retains local geometry and amplitude"
        ),
    }


def _universality_class(
    prediction: Prediction, invariants: Mapping[str, Any]
) -> dict[str, Any] | None:
    q_star = invariants["weighted_degree"]
    exponent = invariants["response_exponent"]
    if not prediction.answered or q_star is None:
        return None
    q_label = _number_label(q_star)
    gamma_label = _number_label(exponent)
    return {
        "id": f"face-weight:{q_label}|response:{gamma_label}",
        "weighted_degree": q_star,
        "weighted_degree_label": q_label,
        "response_exponent": exponent,
        "response_exponent_label": gamma_label,
        "invariant": "minimum admissible tangent-cone face weight",
        "coefficient_independent": True,
        "coefficient": prediction.coefficient,
        "invariant_source": invariants["source"],
        "interpretation": (
            "problems with this winning admissible weight share the same leading "
            "response exponent even when coefficients and polyhedra differ"
        ),
    }


def _number_label(value: float | None) -> str:
    if value is None:
        return "none"
    # Small rational labels are readable invariants (1/4, 4/3). A large
    # denominator is usually a numerical approximation pretending to be exact.
    fraction = Fraction(float(value)).limit_denominator(256)
    if abs(float(fraction) - float(value)) <= 1e-7:
        return str(fraction)
    return f"{float(value):.8g}"


def _classify_perturbation_terms(
    request: FaceSelectionRequest,
    prediction: Prediction,
    *,
    domain: PolyhedronDomain,
    effective_weight: float | None,
) -> dict[str, Any]:
    try:
        expressions = _top_level_terms(request.perturbation)
    except (SyntaxError, ValueError) as exc:
        return {
            "status": "not_decomposed",
            "basis": "top-level additive decomposition",
            "reason": f"{type(exc).__name__}: {exc}",
            "terms": [],
        }
    if len(expressions) > MAX_PERTURBATION_TERMS:
        return {
            "status": "not_decomposed",
            "basis": "top-level additive decomposition",
            "reason": f"more than {MAX_PERTURBATION_TERMS} additive terms",
            "terms": [],
        }

    classified: list[dict[str, Any]] = []
    for index, expression in enumerate(expressions):
        symbolic = _symbolic_term_classification(
            expression,
            prediction,
            system=request.system,
            base_expression=request.base,
        )
        term_prediction = None if symbolic is not None else predict(
            request.system, request.base, expression, domain=domain
        )
        classified.append(
            _term_classification(
                index, expression, term_prediction, prediction,
                symbolic=symbolic, total_weight=effective_weight,
            )
        )
    dominant = [term["index"] for term in classified if term["role"] == "dominant"]
    return {
        "status": "classified",
        "basis": (
            "top-level additive terms are screened independently; the full-sum "
            "selection remains authoritative because terms may cancel"
        ),
        "term_count": len(classified),
        "dominant_term_indices": dominant,
        "terms": classified,
    }


def _top_level_terms(expression: str) -> tuple[str, ...]:
    root = ast.parse(expression, mode="eval")
    nodes: list[ast.AST] = []

    def collect(node: ast.AST, sign: int = 1) -> None:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            collect(node.left, sign)
            collect(node.right, sign)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            collect(node.left, sign)
            collect(node.right, -sign)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            collect(node.operand, -sign)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            collect(node.operand, sign)
        else:
            nodes.append(node if sign > 0 else ast.UnaryOp(op=ast.USub(), operand=node))

    collect(root.body)
    return tuple(ast.unparse(ast.fix_missing_locations(node)) for node in nodes)


def _term_classification(
    index: int,
    expression: str,
    term_prediction: Prediction | None,
    total_prediction: Prediction,
    *,
    symbolic: dict[str, Any] | None,
    total_weight: float | None,
) -> dict[str, Any]:
    if symbolic is not None:
        degree = symbolic["weighted_degree"]
        relevance = symbolic["relevance"]
        reason = symbolic["reason"]
        supporting_faces = symbolic["supporting_faces"]
        winning_faces = supporting_faces if relevance == "relevant" else []
        response_exponent = symbolic["response_exponent"]
        classification_basis = "exact polynomial transport to edge coordinates"
        classification_licensed = bool(
            total_prediction.hypotheses is not None
            and total_prediction.hypotheses.licensed
        )
    else:
        assert term_prediction is not None
        degrees = sorted({
            float(face.degree) for face in term_prediction.faces
            if face.degree is not None
        })
        degree = term_prediction.weighted_degree
        if degree is None and degrees:
            degree = degrees[0]
        relevances = {face.relevance for face in term_prediction.faces}
        if term_prediction.answered:
            relevance = "relevant"
            reason = "survives positively on an admissible face with 0 < q < 1"
        elif CRITICAL in relevances:
            relevance = "critical"
            reason = "q = 1 requires a different balance"
        elif SUBLEADING in relevances:
            relevance = "subleading"
            reason = "q > 1 cannot control this fractional-power mechanism"
        else:
            relevance = "inactive"
            rejected = [face.reason for face in term_prediction.faces if face.reason]
            reason = rejected[0] if rejected else term_prediction.refusal or "no active face"
        if degree is None:
            supporting_faces = []
        else:
            carrying = tuple(
                face.edges for face in term_prediction.faces
                if face.degree is not None and abs(face.degree - degree) <= 1e-6
            )
            supporting_faces = [list(face) for face in _minimal_faces(carrying)]
        winning_faces = (
            [list(face) for face in term_prediction.winning_faces]
            if relevance == "relevant" else []
        )
        response_exponent = term_prediction.exponent
        classification_basis = "numerical face-restriction probe"
        classification_licensed = _classification_licensed(term_prediction)

    total_q = total_weight if total_prediction.answered else None
    if relevance == "relevant" and total_q is not None and degree is not None:
        if abs(degree - total_q) <= TERM_DOMINANCE_TOLERANCE:
            role = "dominant"
        elif degree > total_q:
            role = "higher_order"
        else:
            role = "cancelled_or_suppressed_in_sum"
    else:
        role = "excluded" if relevance != "relevant" else "undetermined"

    return {
        "index": index,
        "expression": expression,
        "relevance": relevance,
        "role": role,
        "weighted_degree": degree,
        "weighted_degree_label": None if degree is None else _number_label(degree),
        "response_exponent": response_exponent,
        "supporting_faces": supporting_faces,
        "winning_faces": winning_faces,
        "reason": reason,
        "classification_basis": classification_basis,
        "classification_licensed": classification_licensed,
        "weight_source": (
            symbolic.get("weight_source")
            if symbolic is not None else "numerical directional-order detection"
        ),
        "ambient_transport": (
            symbolic.get("ambient_transport")
            if symbolic is not None else {
                "status": "non_polynomial_fallback",
                "fallback": "safe numerical face-restriction predictor",
            }
        ),
        "positivity_certificates": (
            symbolic.get("positivity_certificates", [])
            if symbolic is not None else []
        ),
        "licensed_individually": bool(
            relevance == "relevant" and classification_licensed
        ),
    }


def _symbolic_term_classification(
    expression: str,
    prediction: Prediction,
    *,
    system: str | None = None,
    base_expression: str | None = None,
) -> dict[str, Any] | None:
    """Classify polynomial terms exactly after transport to edge coordinates.

    This is the bridge between the automatic polyhedron localizer and the exact
    face-selection core. It is deliberately a fallback-capable recognizer: a
    non-polynomial expression returns ``None`` and keeps the numerical path.
    """
    inputs = _localized_compiler_inputs(
        prediction, system=system, base_expression=base_expression
    )
    if inputs is None:
        return None
    (
        chart,
        principal,
        exact_vertex,
        exact_generators,
        _chart_source,
        weight_source,
    ) = inputs
    try:
        compilation = compile_ambient_face_selection(
            expression,
            chart,
            principal,
            exact_vertex=exact_vertex,
            exact_generators=exact_generators,
        )
        ambient_transport = compilation.to_dict(principal)
    except (SyntaxError, TypeError, ValueError, OverflowError, ArithmeticError):
        return None
    if compilation.selection is None:
        return {
            "weighted_degree": 0.0,
            "relevance": "inactive",
            "reason": (
                "term is constant or geometrically suppressed after exact localization "
                "and cannot drive displacement"
            ),
            "supporting_faces": [],
            "response_exponent": None,
            "selection_complete": True,
            "unresolved_faces": [],
            "ambient_transport": ambient_transport,
            "weight_source": weight_source,
        }

    from ...face_selection import FaceStatus

    result = compilation.selection

    with_degree = [analysis for analysis in result.analyses
                   if analysis.degree is not None and analysis.degree > 0]
    if not with_degree:
        return {
            "weighted_degree": 0.0,
            "relevance": "inactive",
            "reason": "no nonzero weighted layer survives on a feasible face",
            "supporting_faces": [],
            "response_exponent": None,
            "selection_complete": True,
            "unresolved_faces": [],
            "ambient_transport": ambient_transport,
            "weight_source": weight_source,
        }
    minimum = min(analysis.degree for analysis in with_degree if analysis.degree is not None)
    at_minimum = [analysis for analysis in with_degree if analysis.degree == minimum]
    statuses = {analysis.status for analysis in at_minimum}
    if FaceStatus.ADMISSIBLE in statuses:
        relevance = "relevant"
        reason = "exact edge polynomial is positive on an admissible face with 0 < q < 1"
        exponent = float(1 / (1 - minimum))
    elif FaceStatus.CRITICAL in statuses:
        relevance, reason, exponent = (
            "critical", "exact edge-polynomial degree is q = 1", None
        )
    elif FaceStatus.SUBLEADING in statuses:
        relevance, reason, exponent = (
            "subleading", "exact edge-polynomial degree is q > 1", None
        )
    elif FaceStatus.POSITIVITY_UNRESOLVED in statuses:
        relevance, reason, exponent = (
            "unresolved",
            "general mixed-sign initial form needs a positivity witness",
            None,
        )
    else:
        relevance, reason, exponent = (
            "inactive", "exact initial form is non-positive or cancels on every face", None
        )

    target_statuses = {
        "relevant": {FaceStatus.ADMISSIBLE},
        "critical": {FaceStatus.CRITICAL},
        "subleading": {FaceStatus.SUBLEADING},
        "unresolved": {FaceStatus.POSITIVITY_UNRESOLVED},
        "inactive": {
            FaceStatus.NON_POSITIVE,
            FaceStatus.CANCELLED_INITIAL_FORM,
            FaceStatus.NO_SURVIVING_MONOMIAL,
            FaceStatus.ZERO_WEIGHT,
        },
    }[relevance]
    candidate_faces = tuple(
        analysis.face for analysis in at_minimum
        if analysis.status in target_statuses
    )
    minimal_faces = tuple(
        face for face in candidate_faces
        if not any(other < face for other in candidate_faces)
    )
    supporting_faces = [
        [int(axis[1:]) for axis in sorted(face, key=lambda name: int(name[1:]))]
        for face in minimal_faces
    ]
    unresolved_faces = [
        [int(axis[1:]) for axis in sorted(
            analysis.face, key=lambda name: int(name[1:])
        )]
        for analysis in result.unresolved_faces
    ]
    positivity_certificates = [
        {
            "face": [
                int(axis[1:]) for axis in sorted(
                    analysis.face, key=lambda name: int(name[1:])
                )
            ],
            "provenance": analysis.witness.provenance,
            "coordinates": {
                axis: value for axis, value in analysis.witness.coordinates.items()
            },
            "initial_form_value": analysis.initial_form.evaluate(
                analysis.witness.coordinates
            ),
        }
        for analysis in result.analyses
        if analysis.witness is not None and analysis.initial_form is not None
    ]
    return {
        "weighted_degree": float(minimum),
        "relevance": relevance,
        "reason": reason,
        "supporting_faces": supporting_faces,
        "response_exponent": exponent,
        "selection_complete": not unresolved_faces,
        "unresolved_faces": unresolved_faces,
        "positivity_certificates": positivity_certificates,
        "ambient_transport": ambient_transport,
        "weight_source": weight_source,
    }


def _scope(prediction: Prediction) -> tuple[dict[str, Any] | None, list[str]]:
    hypotheses = prediction.hypotheses
    if hypotheses is None:
        return None, ["analytic hypotheses were not reached"]
    unsettled = [list(face) for face in prediction.metrics.get("unsettled_faces") or ()]
    selection_settled = bool(
        prediction.metrics.get("weighted_degree_settled", True) and not unsettled
    )
    payload = {
        "simple_vertex": hypotheses.simple_vertex,
        "edge_orders": list(hypotheses.edge_orders),
        "orders_above_one": hypotheses.orders_above_one,
        "base_homogeneity": hypotheses.base_homogeneity,
        "weighted_principal_part": hypotheses.homogeneous,
        "isolation_margin": hypotheses.isolation_margin,
        "isolated_maximizer": hypotheses.isolated,
        "face_selection_settled": selection_settled,
        "unsettled_faces": unsettled,
    }
    blockers = list(hypotheses.unmet())
    if not selection_settled:
        blockers.append(f"weighted degree is unsettled on faces {unsettled}")
    return payload, blockers


def _backend_licensed(prediction: Prediction) -> bool:
    """A backend answer needs both analytic scope and settled face selection."""
    return bool(prediction.answered and _classification_licensed(prediction))


def _classification_licensed(prediction: Prediction) -> bool:
    """The evidence may license an inactive/critical class without an exponent."""
    if prediction.hypotheses is None or not prediction.hypotheses.licensed:
        return False
    unsettled = prediction.metrics.get("unsettled_faces") or ()
    return bool(prediction.metrics.get("weighted_degree_settled", True) and not unsettled)


def _clean_zero(value: float) -> float:
    return 0.0 if value == 0.0 else value


def _face_dict(face: Face) -> dict[str, Any]:
    return {
        "edges": list(face.edges),
        "degree": face.degree,
        "relevance": face.relevance,
        "admitted": face.admitted,
        "reason": face.reason or None,
    }


def _inverse(
    request: FaceSelectionRequest, prediction: Prediction
) -> dict[str, Any] | None:
    observed = request.observed_exponent
    if observed is None:
        return None
    try:
        effective_weight = calibrate(observed)
    except ValueError as exc:
        return {
            "status": "outside_scope",
            "observed_exponent": observed,
            "error": str(exc),
            "effective_weight": None,
            "consistent_faces": [],
            "minimal_consistent_faces": [],
        }
    matches = consistent_faces(
        prediction, observed, tolerance=request.observation_tolerance
    )
    edge_sets = tuple(face.edges for face in matches)
    minimal = _minimal_faces(edge_sets)
    return {
        "status": "matched" if matches else "no_face_match",
        "observed_exponent": observed,
        "effective_weight": effective_weight,
        "formula": "q_star = 1 - 1 / gamma",
        "tolerance": request.observation_tolerance,
        "consistent_faces": [list(face.edges) for face in matches],
        "minimal_consistent_faces": [list(face) for face in minimal],
        "identifiability": (
            "unique" if len(minimal) == 1
            else "ambiguous" if minimal
            else "inconsistent_with_tangent_cone"
        ),
    }


def _minimal_faces(faces: Sequence[tuple[int, ...]]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        face for face in faces
        if not any(set(other) < set(face) for other in faces)
    )


def _discovery_candidates(
    payload: Mapping[str, Any], *, domain: PolyhedronDomain
) -> tuple[DiscoveryCandidate, ...]:
    raw_candidates = payload.get("candidates", payload.get("perturbations"))
    family = payload.get("family")
    if raw_candidates is not None and family is not None:
        raise RequestValidationError("supply candidates or family, not both")
    candidates: list[DiscoveryCandidate] = []
    if raw_candidates is not None:
        if not isinstance(raw_candidates, Sequence) or isinstance(
            raw_candidates, (str, bytes)
        ) or not raw_candidates:
            raise RequestValidationError("discovery candidates must be a non-empty array")
        for index, raw in enumerate(raw_candidates):
            if isinstance(raw, str):
                candidates.append(DiscoveryCandidate(
                    candidate_id=f"candidate-{index + 1:04d}",
                    expression=raw,
                ))
                continue
            if not isinstance(raw, Mapping):
                raise RequestValidationError(
                    "discovery candidates must be strings or JSON objects"
                )
            candidates.append(DiscoveryCandidate(
                candidate_id=raw.get("id", raw.get("request_id", f"candidate-{index + 1:04d}")),
                expression=raw.get("expression", raw.get("perturbation")),
                observed_exponent=raw.get("observed_exponent"),
                metadata=raw.get("metadata", {}),
            ))
    elif family is not None:
        if not isinstance(family, Mapping):
            raise RequestValidationError("discovery family must be a JSON object")
        kind = family.get("kind", "ambient_monomials")
        if kind not in {"ambient_monomials", "monomial_grid"}:
            raise RequestValidationError(f"unsupported discovery family kind: {kind}")
        try:
            dimension = domain.parse_system(str(payload.get("system"))).dim
        except Exception as exc:
            raise RequestValidationError(f"unusable discovery system: {exc}") from exc
        raw_variables = family.get(
            "variables", [f"x{index}" for index in range(dimension)]
        )
        if not isinstance(raw_variables, Sequence) or isinstance(
            raw_variables, (str, bytes)
        ) or not raw_variables:
            raise RequestValidationError("family variables must be a non-empty array")
        variables = tuple(str(variable) for variable in raw_variables)
        if len(set(variables)) != len(variables) or any(
            not variable.startswith("x")
            or not variable[1:].isdigit()
            or int(variable[1:]) >= dimension
            for variable in variables
        ):
            raise RequestValidationError(
                "family variables must be distinct ambient names within the system dimension"
            )
        minimum = family.get("min_total_degree", 1)
        maximum = family.get("max_total_degree", 4)
        if (
            isinstance(minimum, bool) or isinstance(maximum, bool)
            or int(minimum) != minimum or int(maximum) != maximum
            or not 1 <= int(minimum) <= int(maximum) <= 16
        ):
            raise RequestValidationError(
                "family total degrees must be integers with 1 <= min <= max <= 16"
            )
        minimum, maximum = int(minimum), int(maximum)
        include_mixed = family.get("include_mixed", True)
        if not isinstance(include_mixed, bool):
            raise RequestValidationError("family include_mixed must be boolean")
        raw_coefficients = family.get("coefficients", [1])
        if not isinstance(raw_coefficients, Sequence) or isinstance(
            raw_coefficients, (str, bytes)
        ) or not raw_coefficients:
            raise RequestValidationError("family coefficients must be a non-empty array")
        coefficients = []
        for raw_coefficient in raw_coefficients:
            if isinstance(raw_coefficient, bool):
                raise RequestValidationError("family coefficients must be nonzero rationals")
            try:
                coefficient = Fraction(str(raw_coefficient))
            except (ValueError, ZeroDivisionError) as exc:
                raise RequestValidationError(
                    "family coefficients must be nonzero rationals"
                ) from exc
            if coefficient == 0:
                raise RequestValidationError("family coefficients must be nonzero rationals")
            coefficients.append(coefficient)
        for exponents in product(range(maximum + 1), repeat=len(variables)):
            total = sum(exponents)
            if not minimum <= total <= maximum:
                continue
            if not include_mixed and sum(power > 0 for power in exponents) > 1:
                continue
            monomial = "*".join(
                variable if power == 1 else f"{variable}**{power}"
                for variable, power in zip(variables, exponents) if power
            )
            for coefficient in coefficients:
                label = (
                    str(coefficient.numerator)
                    if coefficient.denominator == 1
                    else f"{coefficient.numerator}/{coefficient.denominator}"
                )
                expression = (
                    monomial if coefficient == 1
                    else f"-{monomial}" if coefficient == -1
                    else f"({label})*{monomial}"
                )
                powers_id = "_".join(
                    f"{variable}^{power}"
                    for variable, power in zip(variables, exponents) if power
                )
                candidates.append(DiscoveryCandidate(
                    candidate_id=f"monomial:{powers_id}:coef={label}",
                    expression=expression,
                    metadata={
                        "generated": True,
                        "powers": {
                            variable: power
                            for variable, power in zip(variables, exponents) if power
                        },
                        "coefficient": label,
                    },
                ))
                if len(candidates) > MAX_PORTFOLIO_CASES:
                    raise RequestValidationError(
                        f"discovery family exceeds the {MAX_PORTFOLIO_CASES}-candidate limit"
                    )
    else:
        raise RequestValidationError("discovery requires candidates or a family")

    if len(candidates) > MAX_PORTFOLIO_CASES:
        raise RequestValidationError(
            f"discovery exceeds the {MAX_PORTFOLIO_CASES}-candidate limit"
        )
    identifiers = [candidate.candidate_id for candidate in candidates]
    if len(set(identifiers)) != len(identifiers):
        raise RequestValidationError("discovery candidate ids must be distinct")
    return tuple(candidates)


def _discovery_case_summary(
    candidate: DiscoveryCandidate, response: Mapping[str, Any]
) -> dict[str, Any]:
    universality = response.get("universality_class") or {}
    refinement = response.get("exact_refinement") or {}
    hierarchy = response.get("ambient_hierarchy") or {}
    pullback = hierarchy.get("perturbation_pullback") or {}
    transport_summary = pullback.get("summary") or {}
    selection_layer = hierarchy.get("selection_layer") or {}
    if universality:
        relevance = "relevant"
    elif refinement.get("symbolic_relevance"):
        relevance = refinement["symbolic_relevance"]
    else:
        terms = ((response.get("perturbation_analysis") or {}).get("terms") or [])
        relevance = terms[0].get("relevance") if len(terms) == 1 else "unresolved"
    weighted_degree = universality.get("weighted_degree")
    if weighted_degree is None:
        weighted_degree = refinement.get("weighted_degree")
    if weighted_degree is None:
        weighted_degree = selection_layer.get("q_star")
    response_exponent = universality.get("response_exponent")
    if response_exponent is None:
        response_exponent = ((response.get("scaling") or {}).get("response_exponent"))
    winning_faces = selection_layer.get("winning_faces", [])
    weights = ((hierarchy.get("weight_layer") or {}).get("weights") or {})
    fingerprint = json.dumps({
        "weights": {axis: item.get("exact") for axis, item in weights.items()},
        "winning_faces": winning_faces,
        "weighted_degree": None if weighted_degree is None else _number_label(weighted_degree),
        "transport_signature": transport_summary.get("transport_signature"),
    }, sort_keys=True, separators=(",", ":"))

    reasons = []
    cancellation_count = transport_summary.get("cancelled_edge_monomial_count", 0) or 0
    suppressed = transport_summary.get("geometrically_suppressed_term_indices", []) or []
    if cancellation_count:
        reasons.append("exact edge-monomial cancellation")
    if suppressed:
        reasons.append("geometric suppression after localization")
    if len(winning_faces) > 1:
        reasons.append("tied qualified mechanisms")
    correction = refinement.get("response_exponent_correction")
    if correction is not None and abs(float(correction)) > 1e-7:
        reasons.append("exact transport corrected the numerical exponent")
    inverse = response.get("inverse")
    if isinstance(inverse, Mapping) and inverse.get("status") == "no_face_match":
        reasons.append("observed exponent is inconsistent with compiled feasible faces")
    if relevance == "critical":
        reasons.append("critical q=1 boundary requires a different balance law")
    if relevance == "unresolved":
        reasons.append("positivity or mechanism classification remains unresolved")
    if response.get("status") == "unlicensed":
        reasons.append("analytic hypotheses are not fully licensed")
    return {
        "id": candidate.candidate_id,
        "expression": candidate.expression,
        "metadata": dict(candidate.metadata),
        "backend_status": response.get("status"),
        "screening_class": relevance,
        "universality_class_id": universality.get("id"),
        "weighted_degree": weighted_degree,
        "weighted_degree_label": (
            None if weighted_degree is None else _number_label(weighted_degree)
        ),
        "response_exponent": response_exponent,
        "response_exponent_label": (
            None if response_exponent is None else _number_label(response_exponent)
        ),
        "winning_faces": winning_faces,
        "mechanism_fingerprint": fingerprint,
        "transport_signature": transport_summary.get("transport_signature"),
        "cancelled_edge_monomial_count": cancellation_count,
        "geometrically_suppressed_term_indices": suppressed,
        "diagnostic_reasons": reasons,
        "licensed": bool(response.get("licensed")),
    }


def _discovery_response(
    candidates: Sequence[DiscoveryCandidate],
    responses: Sequence[dict[str, Any]],
    *,
    request_id: Any,
    known_class_ids: set[str],
    registry_supplied: bool,
    include_cases: bool,
) -> dict[str, Any]:
    summaries = [
        _discovery_case_summary(candidate, response)
        for candidate, response in zip(candidates, responses)
    ]
    boundary_errors = [
        summary for summary in summaries
        if summary["backend_status"] in {"invalid_request", "analysis_error"}
    ]
    groups: dict[str, dict[str, Any]] = {}
    for summary in summaries:
        class_id = summary["universality_class_id"]
        if not class_id:
            continue
        group = groups.setdefault(class_id, {
            "id": class_id,
            "weighted_degree": summary["weighted_degree"],
            "weighted_degree_label": summary["weighted_degree_label"],
            "response_exponent": summary["response_exponent"],
            "response_exponent_label": summary["response_exponent_label"],
            "member_ids": [],
            "representative_id": summary["id"],
            "mechanism_fingerprints": [],
            "licensed_member_count": 0,
            "registry_status": "known" if class_id in known_class_ids else "unregistered",
        })
        group["member_ids"].append(summary["id"])
        if summary["mechanism_fingerprint"] not in group["mechanism_fingerprints"]:
            group["mechanism_fingerprints"].append(summary["mechanism_fingerprint"])
        if summary["licensed"]:
            group["licensed_member_count"] += 1

    classes = sorted(
        groups.values(),
        key=lambda item: (
            float("inf") if item["weighted_degree"] is None
            else float(item["weighted_degree"]),
            item["id"],
        ),
    )
    spectrum = []
    for left, right in zip(classes, classes[1:]):
        spectrum.append({
            "from_class": left["id"],
            "to_class": right["id"],
            "weighted_degree_gap": (
                float(right["weighted_degree"]) - float(left["weighted_degree"])
            ),
            "response_exponent_gap": (
                float(right["response_exponent"]) - float(left["response_exponent"])
            ),
            "interpretation": (
                "an adjacent exponent-law class in the screened discrete family; "
                "a continuous phase wall requires a parametric family"
            ),
        })
    screening_counts: dict[str, int] = {}
    for summary in summaries:
        key = str(summary["screening_class"] or "unresolved")
        screening_counts[key] = screening_counts.get(key, 0) + 1
    diagnostic_candidates = [
        {
            "id": summary["id"],
            "reasons": summary["diagnostic_reasons"],
            "mechanism_fingerprint": summary["mechanism_fingerprint"],
        }
        for summary in summaries if summary["diagnostic_reasons"]
    ]
    law_candidates = [
        {
            "class_id": group["id"],
            "representative_id": group["representative_id"],
            "weighted_degree": group["weighted_degree"],
            "response_exponent": group["response_exponent"],
            "registry_status": group["registry_status"],
            "claim_level": "candidate" if group["registry_status"] == "unregistered" else "known",
        }
        for group in classes if group["registry_status"] == "unregistered"
    ]
    status = "complete" if not boundary_errors else (
        "partial" if len(boundary_errors) < len(summaries) else "failed"
    )
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "asset_version": ASSET_VERSION,
        "operation": DISCOVERY_OPERATION,
        "request_id": request_id if isinstance(request_id, str) else None,
        "status": status,
        "answered": status == "complete",
        "licensed": bool(responses) and all(response.get("licensed") for response in responses),
        "capabilities": list(CAPABILITIES),
        "principles": [dict(principle) for principle in PRINCIPLES],
        "candidate_count": len(candidates),
        "screened_candidate_count": len(candidates) - len(boundary_errors),
        "screening": {
            "counts": screening_counts,
            "rule": (
                "compile the full ambient perturbation exactly, then classify it as "
                "relevant, critical, subleading, inactive, or unresolved"
            ),
        },
        "universality_classes": classes,
        "exponent_law_spectrum": spectrum,
        "law_candidates": law_candidates,
        "diagnostic_candidates": diagnostic_candidates,
        "case_summaries": summaries,
        "novelty": {
            "registry_supplied": registry_supplied,
            "known_class_ids": sorted(known_class_ids),
            "unregistered_class_count": sum(
                group["registry_status"] == "unregistered" for group in classes
            ),
            "interpretation": (
                "unregistered means absent from the caller-supplied registry; it is "
                "a theorem candidate, not a claim of literature novelty"
            ),
        },
        "summary": {
            "universality_class_count": len(classes),
            "law_candidate_count": len(law_candidates),
            "diagnostic_candidate_count": len(diagnostic_candidates),
            "boundary_error_count": len(boundary_errors),
        },
        "audit": {
            "compiler": "ambient_face_compiler",
            "chart_rule": "exact active-constraint solve",
            "weight_rule": "exact base-pullback axial orders when available",
            "selection_rule": "minimum qualified feasible-face weighted degree",
            "novelty_rule": "registry-relative only",
            "backend_contract": SCHEMA_VERSION,
            "asset_version": ASSET_VERSION,
        },
    }
    if include_cases:
        result["cases"] = list(responses)
    return result


def _portfolio_response(
    responses: Sequence[dict[str, Any]], *, request_id: Any = None
) -> dict[str, Any]:
    answered = [response for response in responses if response.get("answered")]
    if len(answered) == len(responses):
        status = "complete"
    elif answered:
        status = "partial"
    else:
        status = "failed"

    groups: dict[str, dict[str, Any]] = {}
    for index, response in enumerate(responses):
        universality = response.get("universality_class")
        if not universality:
            continue
        class_id = universality["id"]
        group = groups.setdefault(class_id, {
            "id": class_id,
            "weighted_degree": universality["weighted_degree"],
            "response_exponent": universality["response_exponent"],
            "member_indices": [],
            "member_request_ids": [],
            "licensed_member_count": 0,
        })
        group["member_indices"].append(index)
        group["member_request_ids"].append(response.get("request_id"))
        if response.get("licensed"):
            group["licensed_member_count"] += 1

    transitions = [
        _portfolio_transition(index, responses[index], responses[index + 1])
        for index in range(len(responses) - 1)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_version": ASSET_VERSION,
        "operation": PORTFOLIO_OPERATION,
        "request_id": request_id if isinstance(request_id, str) else None,
        "status": status,
        "answered": len(answered) == len(responses),
        "licensed": bool(responses) and all(
            response.get("licensed") for response in responses
        ),
        "capabilities": list(CAPABILITIES),
        "principles": [dict(principle) for principle in PRINCIPLES],
        "case_count": len(responses),
        "answered_case_count": len(answered),
        "cases": list(responses),
        "universality_classes": list(groups.values()),
        "transitions": transitions,
        "summary": {
            "class_count": len(groups),
            "transition_count": sum(
                transition["kind"] == "universality_class_transition"
                for transition in transitions
            ),
            "stable_pair_count": sum(
                transition["kind"] == "same_universality_class"
                for transition in transitions
            ),
        },
        "audit": {
            "selection_rule": "minimum admissible face weight",
            "comparison_rule": "consecutive cases are compared by universality id",
            "backend_contract": SCHEMA_VERSION,
            "asset_version": ASSET_VERSION,
        },
    }


def _portfolio_transition(
    index: int, before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    before_class = before.get("universality_class")
    after_class = after.get("universality_class")
    if not before_class or not after_class:
        kind = "unresolved_transition"
    elif before_class["id"] == after_class["id"]:
        kind = "same_universality_class"
    else:
        kind = "universality_class_transition"

    before_active = before.get("active_constraints") or {}
    after_active = after.get("active_constraints") or {}
    before_binding = set(before_active.get("binding") or ())
    after_binding = set(after_active.get("binding") or ())
    before_released = set(before_active.get("released") or ())
    after_released = set(after_active.get("released") or ())
    before_transport = (
        ((before.get("ambient_hierarchy") or {}).get("perturbation_pullback") or {})
    )
    after_transport = (
        ((after.get("ambient_hierarchy") or {}).get("perturbation_pullback") or {})
    )
    before_transport_summary = before_transport.get("summary") or {}
    after_transport_summary = after_transport.get("summary") or {}
    before_chart = (before_transport.get("chart") or {}).get("generators")
    after_chart = (after_transport.get("chart") or {}).get("generators")
    return {
        "from_index": index,
        "to_index": index + 1,
        "from_request_id": before.get("request_id"),
        "to_request_id": after.get("request_id"),
        "kind": kind,
        "from_class": None if not before_class else before_class["id"],
        "to_class": None if not after_class else after_class["id"],
        "weighted_degree_shift": _difference(before_class, after_class, "weighted_degree"),
        "response_exponent_shift": _difference(
            before_class, after_class, "response_exponent"
        ),
        "active_constraint_change": {
            "became_binding": sorted(after_binding - before_binding),
            "ceased_binding": sorted(before_binding - after_binding),
            "became_released": sorted(after_released - before_released),
            "ceased_released": sorted(before_released - after_released),
            "comparison_basis": "constraint indices supplied by each related system",
        },
        "ambient_transport_change": {
            "changed": (
                before_transport_summary.get("transport_signature")
                != after_transport_summary.get("transport_signature")
                or before_chart != after_chart
            ),
            "from_signature": before_transport_summary.get("transport_signature"),
            "to_signature": after_transport_summary.get("transport_signature"),
            "from_chart_generators": before_chart,
            "to_chart_generators": after_chart,
            "from_geometrically_suppressed_term_indices": (
                before_transport_summary.get(
                    "geometrically_suppressed_term_indices", []
                )
            ),
            "to_geometrically_suppressed_term_indices": (
                after_transport_summary.get(
                    "geometrically_suppressed_term_indices", []
                )
            ),
            "from_cancelled_edge_monomial_count": (
                before_transport_summary.get("cancelled_edge_monomial_count")
            ),
            "to_cancelled_edge_monomial_count": (
                after_transport_summary.get("cancelled_edge_monomial_count")
            ),
            "comparison_basis": (
                "exact ambient-polynomial pullback into each localized feasible chart"
            ),
        },
    }


def _difference(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    field: str,
) -> float | None:
    if not before or not after:
        return None
    left, right = before.get(field), after.get(field)
    if left is None or right is None:
        return None
    return float(right) - float(left)


def _error_response(
    status: str,
    detail: str,
    *,
    request_id: Any = None,
    operation: str = OPERATION,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_version": ASSET_VERSION,
        "operation": operation,
        "request_id": request_id if isinstance(request_id, str) else None,
        "status": status,
        "answered": False,
        "licensed": False,
        "error": {"code": status, "detail": detail},
        "capabilities": list(CAPABILITIES),
        "principles": [dict(principle) for principle in PRINCIPLES],
    }


def handle_json(
    document: str, *, backend: FaceSelectionBackend | None = None
) -> str:
    """Handle one JSON object or an array of objects and return compact JSON."""
    engine = backend or FaceSelectionBackend()
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        return json.dumps(_error_response("invalid_json", str(exc)), sort_keys=True)
    if isinstance(payload, list):
        results = [
            engine.handle(item) if isinstance(item, Mapping)
            else _error_response("invalid_request", "batch items must be JSON objects")
            for item in payload
        ]
        return json.dumps(results, separators=(",", ":"), sort_keys=True)
    if not isinstance(payload, Mapping):
        result = _error_response("invalid_request", "request must be a JSON object")
    else:
        result = engine.handle(payload)
    return json.dumps(result, separators=(",", ":"), sort_keys=True)


def main(argv: Sequence[str] | None = None, *, stdin: TextIO | None = None) -> int:
    """JSON stdin/file CLI suitable for subprocess or local service adapters."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m categorical_polytope.adjudication.polyhedra.backend",
        description=(
            "Run localization, admissible-face selection and exponent scaling "
            "through the face-selection backend contract."
        ),
    )
    parser.add_argument(
        "--input", type=Path, default=None,
        help="JSON request file; omit to read one request or batch from stdin",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)

    source = args.input.read_text(encoding="utf-8") if args.input else (stdin or sys.stdin).read()
    output = handle_json(source)
    parsed = json.loads(output)
    print(json.dumps(parsed, indent=2 if args.pretty else None, sort_keys=True))

    responses = parsed if isinstance(parsed, list) else [parsed]
    return 0 if all(
        item.get("status") in {"licensed", "unlicensed", "complete"}
        for item in responses
    ) else 1


__all__ = [
    "ASSET_VERSION",
    "CAPABILITIES",
    "DISCOVERY_OPERATION",
    "DiscoveryCandidate",
    "FaceSelectionBackend",
    "FaceSelectionRequest",
    "MAX_EXPRESSION_LENGTH",
    "MAX_PERTURBATION_TERMS",
    "MAX_PHASE_EVALUATIONS",
    "MAX_PORTFOLIO_CASES",
    "OPERATION",
    "PHASE_OPERATION",
    "PORTFOLIO_OPERATION",
    "PRINCIPLES",
    "RequestValidationError",
    "SCHEMA_VERSION",
    "analyze_face_selection",
    "handle_json",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
