"""Contract and safety tests for the face-selection backend asset."""

from __future__ import annotations

import io
import json

import pytest

from categorical_polytope.adjudication.polyhedra.backend import (
    CAPABILITIES,
    PRINCIPLES,
    SCHEMA_VERSION,
    FaceSelectionBackend,
    FaceSelectionRequest,
    analyze_face_selection,
    handle_json,
    main as backend_cli,
)


SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
SIMPLEX_BASE = "-((x0+x1-1)**2 + x0**4)"


def request(**overrides):
    payload = {
        "request_id": "tilted-simplex",
        "system": SIMPLEX,
        "base": SIMPLEX_BASE,
        "perturbation": "x0",
    }
    payload.update(overrides)
    return payload


def test_backend_exposes_the_three_stage_asset():
    out = analyze_face_selection(request())

    assert out["schema_version"] == SCHEMA_VERSION
    assert out["status"] == "licensed"
    assert out["answered"] and out["licensed"]
    assert [principle["stage"] for principle in out["principles"]] == [
        "localization", "selection", "scaling"
    ]
    assert out["localization"]["vertex"] == pytest.approx([0.0, 1.0])
    assert out["selection"]["weighted_degree"] == pytest.approx(0.25)
    assert out["selection"]["winning_faces"] == [[0]]
    assert out["scaling"]["response_exponent"] == pytest.approx(4 / 3)
    assert out["scaling"]["leading_coefficient"]["value"] == pytest.approx(
        3 / 4 ** (4 / 3), rel=1e-9
    )


def test_backend_names_active_and_irrelevant_directions():
    out = analyze_face_selection(request())
    assert out["active_constraints"]["released"] == [0]
    assert out["active_constraints"]["binding"] == [2]
    inactive = out["selection"]["relevance_classes"]["inactive"]
    assert any(face["edges"] == [1] and "vanishes" in face["reason"] for face in inactive)
    assert out["selection"]["filtered_face_count"] >= 1


def test_capability_contract_contains_the_full_portable_principle():
    assert tuple(CAPABILITIES) == (
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
    assert len(PRINCIPLES) == 3


def test_inverse_mode_turns_an_observation_into_geometry():
    out = analyze_face_selection(request(observed_exponent=4 / 3))
    inverse = out["inverse"]
    assert inverse["status"] == "matched"
    assert inverse["effective_weight"] == pytest.approx(0.25)
    assert inverse["minimal_consistent_faces"] == [[0]]
    assert inverse["identifiability"] == "unique"


def test_inverse_mode_reports_an_exponent_from_no_feasible_face():
    out = analyze_face_selection(request(observed_exponent=2.0))
    assert out["inverse"]["status"] == "no_face_match"
    assert out["inverse"]["identifiability"] == "inconsistent_with_tangent_cone"


def test_unlicensed_prediction_returns_the_answer_and_its_blocker():
    out = analyze_face_selection({
        "system": "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
        "base": "-(x0**2*(x0-1)**2) - x1**2",
        "perturbation": "x0 + x1",
    })
    assert out["status"] == "unlicensed"
    assert out["answered"] and not out["licensed"]
    assert out["scaling"]["response_exponent"] is not None
    assert "isolated maximiser" in out["scope"]["blockers"]


def test_an_unsettled_face_degree_cannot_be_backend_licensed():
    out = analyze_face_selection({
        "system": "([[ -2, -1],[1, -1],[1, 2]],[0,0,1])",
        "base": "-((2*x0 + x1)**4 + (-x0 + x1)**5)",
        "perturbation": "x0**2 + x1**3",
    })
    assert out["answered"]
    assert out["status"] == "unlicensed"
    assert not out["licensed"]
    assert not out["scope"]["hypotheses"]["face_selection_settled"]
    assert out["scope"]["hypotheses"]["unsettled_faces"]
    assert any("weighted degree is unsettled" in item for item in out["scope"]["blockers"])


def test_outside_scope_geometry_is_a_structured_refusal():
    out = analyze_face_selection({
        "system": "([[-1,0],[0,-1]], [0,0])",
        "base": "-(x0**2 + x1**2)",
        "perturbation": "x0",
    })
    assert out["status"] == "refused"
    assert not out["answered"]
    assert "unbounded" in out["scope"]["refusal"]
    assert out["selection"]["status"] == "not_selected"
    assert out["scaling"]["status"] == "not_scaled"


def test_invalid_request_does_not_raise_across_the_backend_boundary():
    out = FaceSelectionBackend().handle({"system": SIMPLEX})
    assert out["status"] == "invalid_request"
    assert out["error"]["code"] == "invalid_request"
    assert not out["answered"]


def test_hostile_expression_is_never_executed(monkeypatch):
    import os

    monkeypatch.setattr(os, "system", lambda *_: pytest.fail("hostile expression executed"))
    out = analyze_face_selection(request(
        perturbation="__import__('os').system('echo owned')"
    ))
    assert out["status"] in {"refused", "analysis_error"}
    assert not out["answered"]


def test_batch_json_isolated_errors_and_preserves_order():
    document = json.dumps([
        request(request_id="good"),
        {"request_id": "bad", "system": SIMPLEX},
    ])
    out = json.loads(handle_json(document))
    assert [item["request_id"] for item in out] == ["good", "bad"]
    assert [item["status"] for item in out] == ["licensed", "invalid_request"]


def test_json_cli_reads_stdin_and_returns_machine_output(capsys):
    code = backend_cli([], stdin=io.StringIO(json.dumps(request())))
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "licensed"
    assert out["audit"]["selection_rule"] == "minimum admissible face weight"


def test_request_alias_and_round_trip():
    parsed = FaceSelectionRequest.from_mapping({
        "system": SIMPLEX,
        "base": SIMPLEX_BASE,
        "pert": "x0",
        "request_id": "alias",
    })
    assert parsed.perturbation == "x0"
    assert parsed.to_dict()["request_id"] == "alias"
