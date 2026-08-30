"""The portable-principle extension of the backend asset."""

from __future__ import annotations

import io
import json

import pytest

from categorical_polytope.adjudication.polyhedra.backend import (
    ASSET_VERSION,
    PORTFOLIO_OPERATION,
    FaceSelectionBackend,
    analyze_face_selection,
    main as backend_cli,
)


SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
SIMPLEX_BASE = "-((x0+x1-1)**2 + x0**4)"
PRODUCT = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
PRODUCT_BASE = "-(x0**2 + x1**4)"


def case(perturbation: str, *, request_id: str | None = None):
    return {
        "request_id": request_id,
        "system": SIMPLEX,
        "base": SIMPLEX_BASE,
        "perturbation": perturbation,
    }


def test_mechanism_is_a_machine_readable_explanation():
    out = analyze_face_selection(case("x0"))
    mechanism = out["mechanism"]

    assert out["asset_version"] == ASSET_VERSION
    assert mechanism["hierarchy"] == [
        "ambient_polynomial",
        "exact_edge_chart_pullback",
        "feasible_face_restrictions",
        "weighted_degree_selection",
        "response_exponent_gamma",
    ]
    assert mechanism["selection"]["rule"] == "minimum admissible weighted degree"
    assert mechanism["selection"]["q_star"] == pytest.approx(0.25)
    assert mechanism["geometry_filter"]["filtered_faces"] == 1
    assert mechanism["active_set"]["binding_constraints"] == [2]


def test_universality_class_is_exactly_identified_for_the_worked_case():
    out = analyze_face_selection(case("x0"))
    universality = out["universality_class"]
    assert universality["id"] == "face-weight:1/4|response:4/3"
    assert universality["weighted_degree_label"] == "1/4"
    assert universality["response_exponent_label"] == "4/3"
    assert universality["coefficient_independent"]


def test_lowest_weight_term_wins_regardless_of_amplitude():
    out = analyze_face_selection({
        "system": PRODUCT,
        "base": PRODUCT_BASE,
        "perturbation": "100000*x0 + 0.001*x1",
    })
    analysis = out["perturbation_analysis"]
    assert analysis["status"] == "classified"
    assert analysis["dominant_term_indices"] == [1]
    assert analysis["terms"][0]["weighted_degree"] == pytest.approx(0.5, abs=1e-3)
    assert analysis["terms"][0]["role"] == "higher_order"
    assert analysis["terms"][1]["weighted_degree"] == pytest.approx(0.25, abs=1e-3)
    assert analysis["terms"][1]["role"] == "dominant"


def test_terms_are_classified_as_relevant_critical_subleading_or_inactive():
    out = analyze_face_selection(case("x0 + x0**4 + x0**8 - x0**2"))
    terms = out["perturbation_analysis"]["terms"]
    assert [term["relevance"] for term in terms] == [
        "relevant", "critical", "subleading", "inactive"
    ]
    assert terms[0]["role"] == "dominant"
    assert all(term["role"] == "excluded" for term in terms[1:])


def test_exact_full_polynomial_refines_the_public_universality_invariant():
    out = analyze_face_selection(case("x0 + x0**4 + x0**8 - x0**2"))
    assert out["selection"]["weighted_degree"] == pytest.approx(0.25, abs=1e-12)
    assert out["selection"]["measured_weighted_degree"] != pytest.approx(
        0.25, abs=1e-6
    )
    assert out["selection"]["invariant_source"] == "exact_polynomial_transport"
    assert out["exact_refinement"]["status"] == "applied"
    assert out["universality_class"]["id"] == "face-weight:1/4|response:4/3"


def test_non_polynomial_terms_keep_the_safe_numerical_fallback():
    out = analyze_face_selection(case("x0**0.5"))
    assert out["exact_refinement"]["status"] == "non_polynomial_fallback"
    term = out["perturbation_analysis"]["terms"][0]
    assert term["classification_basis"] == "numerical face-restriction probe"
    assert term["relevance"] == "relevant"


def test_global_sum_remains_authoritative_when_terms_cancel():
    out = analyze_face_selection(case("x0 - x0 + x0**2"))
    assert out["selection"]["weighted_degree"] == pytest.approx(0.5, abs=1e-3)
    terms = out["perturbation_analysis"]["terms"]
    assert terms[0]["weighted_degree"] == pytest.approx(0.25, abs=1e-3)
    assert terms[0]["role"] == "cancelled_or_suppressed_in_sum"
    assert terms[2]["role"] == "dominant"
    assert "full-sum selection remains authoritative" in out["perturbation_analysis"]["basis"]


def test_mixed_sign_binomial_gets_an_automatic_backend_positivity_certificate():
    out = analyze_face_selection({
        "system": PRODUCT,
        "base": PRODUCT_BASE,
        "perturbation": "-2*x0 + x1**2",
    })

    assert out["status"] == "licensed"
    assert out["exact_refinement"]["status"] == "applied"
    assert out["selection"]["weighted_degree"] == pytest.approx(0.5)
    assert out["scaling"]["response_exponent"] == pytest.approx(2.0)
    certificates = out["exact_refinement"]["positivity_certificates"]
    binomial = [
        item for item in certificates
        if item["provenance"] == "mixed-sign binomial ratio certificate"
    ]
    assert len(binomial) == 1
    assert binomial[0]["face"] == [0, 1]
    assert binomial[0]["initial_form_value"] > 0


def test_portfolio_groups_universality_classes_and_detects_transitions():
    out = FaceSelectionBackend().handle({
        "operation": "portfolio",
        "request_id": "coefficient-and-order-study",
        "cases": [
            case("x0", request_id="linear"),
            case("100*x0", request_id="linear-rescaled"),
            case("x0**2", request_id="quadratic"),
        ],
    })
    assert out["operation"] == PORTFOLIO_OPERATION
    assert out["status"] == "complete"
    assert out["summary"] == {
        "class_count": 2,
        "transition_count": 1,
        "stable_pair_count": 1,
    }
    assert len(out["universality_classes"]) == 2
    assert out["transitions"][0]["kind"] == "same_universality_class"
    assert out["transitions"][1]["kind"] == "universality_class_transition"
    assert out["transitions"][1]["weighted_degree_shift"] == pytest.approx(0.25)
    assert out["transitions"][1]["response_exponent_shift"] == pytest.approx(2 / 3)


def test_portfolio_is_partial_when_one_case_is_invalid():
    out = FaceSelectionBackend().handle({
        "operation": "compare",
        "cases": [case("x0"), {"system": SIMPLEX}],
    })
    assert out["status"] == "partial"
    assert out["answered_case_count"] == 1
    assert out["cases"][1]["status"] == "invalid_request"
    assert out["transitions"][0]["kind"] == "unresolved_transition"


def test_nested_portfolios_are_refused_without_recursion():
    out = FaceSelectionBackend().handle({
        "operation": "portfolio",
        "cases": [{"operation": "portfolio", "cases": [case("x0")]}],
    })
    assert out["status"] == "failed"
    assert out["cases"][0]["status"] == "invalid_request"
    assert "nested portfolios" in out["cases"][0]["error"]["detail"]


def test_complete_portfolio_is_a_successful_cli_operation(capsys):
    payload = {
        "operation": "portfolio",
        "cases": [case("x0"), case("x0**2")],
    }
    code = backend_cli([], stdin=io.StringIO(json.dumps(payload)))
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"
