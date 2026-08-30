"""V.21: finite perturbation families become auditable exponent-law searches."""

from __future__ import annotations

import io
import json

import pytest

from categorical_polytope.adjudication.polyhedra.backend import (
    ASSET_VERSION,
    DISCOVERY_OPERATION,
    FaceSelectionBackend,
    main as backend_cli,
)


PRODUCT = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
PRODUCT_BASE = "-(x0**2 + x1**4)"


def discovery(**overrides):
    payload = {
        "operation": "discover",
        "request_id": "finite-law-search",
        "system": PRODUCT,
        "base": PRODUCT_BASE,
        "candidates": [
            {"id": "linear-y", "expression": "x1"},
            {"id": "linear-x", "expression": "x0"},
            {"id": "quadratic-y", "expression": "x1**2"},
            {"id": "mixed", "expression": "x0*x1"},
            {"id": "critical-x", "expression": "x0**2"},
            {"id": "cancelled-linear", "expression": "x1-x1+x0"},
        ],
        "known_class_ids": ["face-weight:1/4|response:4/3"],
    }
    payload.update(overrides)
    return payload


def test_discovery_screens_and_groups_exact_exponent_laws():
    out = FaceSelectionBackend().handle(discovery())

    assert out["operation"] == DISCOVERY_OPERATION
    assert out["asset_version"] == ASSET_VERSION == "portable-principle.v7"
    assert out["status"] == "complete"
    assert out["candidate_count"] == 6
    assert out["screening"]["counts"] == {"relevant": 5, "critical": 1}
    assert [group["weighted_degree_label"] for group in out["universality_classes"]] == [
        "1/4", "1/2", "3/4"
    ]
    half = out["universality_classes"][1]
    assert half["member_ids"] == ["linear-x", "quadratic-y", "cancelled-linear"]
    assert len(half["mechanism_fingerprints"]) == 2
    assert out["summary"] == {
        "universality_class_count": 3,
        "law_candidate_count": 2,
        "diagnostic_candidate_count": 2,
        "boundary_error_count": 0,
    }


def test_discovery_marks_novelty_as_registry_relative_only():
    out = FaceSelectionBackend().handle(discovery())

    assert out["universality_classes"][0]["registry_status"] == "known"
    assert [candidate["class_id"] for candidate in out["law_candidates"]] == [
        "face-weight:1/2|response:2",
        "face-weight:3/4|response:4",
    ]
    assert out["novelty"]["registry_supplied"]
    assert "not a claim of literature novelty" in out["novelty"]["interpretation"]


def test_discovery_elevates_cancellation_and_critical_boundaries_for_diagnosis():
    out = FaceSelectionBackend().handle(discovery())
    diagnostics = {item["id"]: item["reasons"] for item in out["diagnostic_candidates"]}

    assert diagnostics["cancelled-linear"] == ["exact edge-monomial cancellation"]
    assert diagnostics["critical-x"] == [
        "critical q=1 boundary requires a different balance law"
    ]
    cancelled = next(
        item for item in out["case_summaries"] if item["id"] == "cancelled-linear"
    )
    assert cancelled["cancelled_edge_monomial_count"] == 1


def test_generated_monomial_grid_discovers_the_expected_spectrum():
    out = FaceSelectionBackend().handle({
        "operation": "discovery",
        "system": PRODUCT,
        "base": PRODUCT_BASE,
        "family": {
            "kind": "ambient_monomials",
            "max_total_degree": 2,
        },
    })

    assert out["status"] == "complete"
    assert out["candidate_count"] == 5
    assert out["screening"]["counts"] == {"relevant": 4, "critical": 1}
    assert [group["weighted_degree_label"] for group in out["universality_classes"]] == [
        "1/4", "1/2", "3/4"
    ]
    assert [wall["weighted_degree_gap"] for wall in out["exponent_law_spectrum"]] == [
        pytest.approx(1 / 4), pytest.approx(1 / 4)
    ]
    assert "cases" not in out


def test_observed_exponent_mismatch_becomes_a_diagnostic_candidate():
    out = FaceSelectionBackend().handle(discovery(
        candidates=[{
            "id": "linear-y-observed-two",
            "expression": "x1",
            "observed_exponent": 2,
        }],
        known_class_ids=[],
    ))

    assert out["diagnostic_candidates"][0]["id"] == "linear-y-observed-two"
    assert out["diagnostic_candidates"][0]["reasons"] == [
        "observed exponent is inconsistent with compiled feasible faces"
    ]


def test_discovery_can_include_full_case_evidence_on_request():
    out = FaceSelectionBackend().handle(discovery(
        candidates=["x1"], include_cases=True, known_class_ids=[]
    ))
    assert len(out["cases"]) == 1
    assert out["cases"][0]["ambient_hierarchy"]["status"] == "compiled"


def test_discovery_rejects_oversized_generated_families():
    out = FaceSelectionBackend().handle({
        "operation": "discover",
        "system": PRODUCT,
        "base": PRODUCT_BASE,
        "family": {"max_total_degree": 16, "coefficients": [1, -1]},
    })
    assert out["status"] == "invalid_request"
    assert out["operation"] == DISCOVERY_OPERATION
    assert "candidate limit" in out["error"]["detail"]


def test_discovery_is_available_through_the_json_cli(capsys):
    code = backend_cli([], stdin=io.StringIO(json.dumps(discovery(
        candidates=["x1"], known_class_ids=[]
    ))))
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["operation"] == DISCOVERY_OPERATION
    assert out["summary"]["universality_class_count"] == 1
