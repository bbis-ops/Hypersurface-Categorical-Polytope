"""Exact tests for the face-selection universality phase-fan law."""

from __future__ import annotations

from fractions import Fraction

from categorical_polytope import (
    AffineWeightedDegree,
    ParametricFaceMechanism,
    ParametricFaceSelectionProblem,
    weighted_degree_from_exponents,
)
from categorical_polytope.adjudication.polyhedra.backend import (
    ASSET_VERSION,
    PHASE_OPERATION,
    FaceSelectionBackend,
    handle_json,
)


def mechanism(identifier: str, intercept, slope=0, *, admitted=True):
    return ParametricFaceMechanism(
        identifier,
        AffineWeightedDegree(intercept, slope),
        face=(identifier,),
        admitted=admitted,
    )


def test_exact_crossing_partitions_the_continuum_into_universality_chambers():
    diagram = ParametricFaceSelectionProblem(
        mechanisms=(
            mechanism("face-a", "1/4", "1/2"),
            mechanism("face-b", "1/2", "-1/2"),
        ),
        lower=0,
        upper="3/4",
        parameter_name="theta",
    ).solve()

    assert diagram.breakpoints == (Fraction(0), Fraction(1, 4), Fraction(3, 4))
    assert [chamber.winners for chamber in diagram.chambers] == [
        ("face-a",), ("face-b",)
    ]
    assert diagram.walls[1].winners == ("face-a", "face-b")
    assert diagram.walls[1].degree == Fraction(3, 8)
    assert len(diagram.transitions) == 1
    assert diagram.transitions[0].kind == "universality_class_transition"
    assert diagram.transitions[0].parameter == Fraction(1, 4)


def test_response_law_is_exactly_composed_with_the_lower_envelope():
    payload = ParametricFaceSelectionProblem(
        mechanisms=(mechanism("moving", "1/4", "1/4"),),
        lower=0,
        upper=1,
        parameter_name="lambda",
    ).solve().to_dict()

    chamber = payload["chambers"][0]
    assert chamber["weighted_degree_law"]["intercept"]["exact"] == "1/4"
    assert chamber["weighted_degree_law"]["slope"]["exact"] == "1/4"
    assert chamber["response_exponent_law"]["expression"] == (
        "1 / (1 - (1/4 + 1/4*lambda))"
    )


def test_newton_weight_is_derived_from_affine_exponents_and_base_orders():
    degree = weighted_degree_from_exponents(
        {
            "x": AffineWeightedDegree(1, 2),
            "y": AffineWeightedDegree("1/2", "-1/2"),
        },
        {"x": 4, "y": 2},
    )
    assert degree.intercept == Fraction(1, 2)
    assert degree.slope == Fraction(1, 4)


def test_relevance_wall_creates_an_exact_mechanism_activation():
    diagram = ParametricFaceSelectionProblem(
        mechanisms=(mechanism("emergent", "-1/4", 1),),
        lower=0,
        upper=1,
    ).solve()

    assert diagram.breakpoints == (Fraction(0), Fraction(1, 4), Fraction(1))
    assert diagram.chambers[0].winners == ()
    assert diagram.chambers[1].winners == ("emergent",)
    assert diagram.walls[1].winners == ()  # q=0 is a wall, not relevant
    assert diagram.transitions[0].kind == "mechanism_activation"


def test_coefficient_zero_wall_changes_the_qualified_winner_exactly():
    diagram = ParametricFaceSelectionProblem(
        mechanisms=(
            ParametricFaceMechanism(
                "emerging-low-face",
                AffineWeightedDegree("1/4"),
                coefficient=AffineWeightedDegree("-1/3", 1),
            ),
            mechanism("positive-fallback", "1/2"),
        ),
        lower=0,
        upper=1,
        parameter_name="theta",
    ).solve()

    assert diagram.breakpoints == (Fraction(0), Fraction(1, 3), Fraction(1))
    assert diagram.chambers[0].winners == ("positive-fallback",)
    assert diagram.walls[1].winners == ("positive-fallback",)
    assert diagram.chambers[1].winners == ("emerging-low-face",)
    transition = diagram.transitions[0]
    assert transition.parameter == Fraction(1, 3)
    assert transition.before == ("positive-fallback",)
    assert transition.at == ("positive-fallback",)
    assert transition.after == ("emerging-low-face",)

    evaluation = diagram.evaluate("1/3").to_dict()
    qualifications = {
        item["id"]: item for item in evaluation["qualified_selection"]["mechanisms"]
    }
    assert qualifications["emerging-low-face"]["status"] == "cancelled"
    assert not qualifications["emerging-low-face"]["qualified"]
    assert qualifications["positive-fallback"]["status"] == "qualified"
    assert evaluation["response_exponent"]["exact"] == "2"


def test_identical_degree_laws_remain_tied_throughout_a_chamber():
    diagram = ParametricFaceSelectionProblem(
        mechanisms=(
            mechanism("left-face", "1/3", "1/7"),
            mechanism("right-face", "1/3", "1/7"),
            mechanism("filtered", "1/5", 0, admitted=False),
        ),
        lower=0,
        upper=1,
    ).solve()

    assert diagram.chambers[0].winners == ("left-face", "right-face")
    assert not diagram.transitions


def test_backend_exposes_a_licensed_exact_phase_diagram():
    out = FaceSelectionBackend().handle({
        "operation": "phase_diagram",
        "request_id": "two-face-transition",
        "parameter": "theta",
        "domain": ["0", "3/4"],
        "mechanisms": [
            {
                "id": "face-a",
                "face": ["x"],
                "degree": {"intercept": "1/4", "slope": "1/2"},
            },
            {
                "id": "face-b",
                "face": ["y"],
                "degree": {"intercept": "1/2", "slope": "-1/2"},
            },
        ],
        "assumptions": {
            "fixed_admissibility": True,
            "affine_degrees_verified": True,
            "uniform_local_base_maximality": True,
            "uniform_principal_remainder": True,
            "uniform_global_isolation": True,
        },
    })

    assert out["operation"] == PHASE_OPERATION
    assert out["asset_version"] == ASSET_VERSION
    assert out["status"] == "licensed"
    assert out["answered"] and out["licensed"]
    assert out["phase_diagram"]["summary"]["transition_count"] == 1
    transition = out["phase_diagram"]["transitions"][0]
    assert transition["parameter"]["exact"] == "1/4"
    assert transition["before"] == ["face-a"]
    assert transition["at_wall"] == ["face-a", "face-b"]
    assert transition["after"] == ["face-b"]


def test_backend_derives_degrees_and_reports_exact_transition_robustness():
    out = FaceSelectionBackend().handle({
        "operation": "phase_diagram",
        "parameter": "theta",
        "domain": ["0", "3/4"],
        "base_orders": {"x": 4, "y": 2},
        "mechanisms": [
            {
                "id": "face-a",
                "exponents": {
                    "x": {"intercept": 1, "slope": 2}
                },
            },
            {
                "id": "face-b",
                "exponents": {
                    "y": {"intercept": 1, "slope": -1}
                },
            },
        ],
        "evaluate_at": ["0", "1/8", "1/4", "1/2"],
        "assumptions": {
            "fixed_admissibility": True,
            "affine_degrees_verified": True,
            "uniform_local_base_maximality": True,
            "uniform_principal_remainder": True,
            "uniform_global_isolation": True,
        },
    })

    assert out["status"] == "licensed"
    assert out["phase_diagram"]["transitions"][0]["parameter"]["exact"] == "1/4"
    at_zero, before, at_wall, after = out["evaluations"]
    assert at_zero["weighted_degree"]["exact"] == "1/4"
    assert before["winning_mechanisms"] == ["face-a"]
    assert before["robustness"]["parameter_distance"]["exact"] == "1/8"
    assert at_wall["location"] == "transition_wall"
    assert at_wall["winning_mechanisms"] == ["face-a", "face-b"]
    assert at_wall["response_exponent"]["exact"] == "8/5"
    assert at_wall["robustness"]["parameter_distance"]["exact"] == "0"
    assert after["winning_mechanisms"] == ["face-b"]
    assert after["robustness"]["parameter_distance"]["exact"] == "1/4"


def test_backend_v18_returns_the_qualified_selection_consequence():
    out = FaceSelectionBackend().handle({
        "operation": "phase_diagram",
        "parameter": "theta",
        "domain": [0, 1],
        "mechanisms": [
            {
                "id": "emerging-low-face",
                "degree": {"intercept": "1/4"},
                "coefficient": {"intercept": "-1/3", "slope": 1},
            },
            {
                "id": "positive-fallback",
                "degree": {"intercept": "1/2"},
            },
        ],
        "evaluate_at": ["1/4", "1/3", "1/2"],
        "assumptions": {
            "fixed_admissibility": True,
            "coefficient_qualification_verified": True,
            "affine_degrees_verified": True,
            "uniform_local_base_maximality": True,
            "uniform_principal_remainder": True,
            "uniform_global_isolation": True,
        },
    })

    assert out["asset_version"] == "portable-principle.v7"
    assert out["status"] == "licensed"
    assert out["phase_diagram"]["summary"]["dynamic_qualification_count"] == 1
    transition = out["phase_diagram"]["transitions"][0]
    assert transition["parameter"]["exact"] == "1/3"
    assert transition["before"] == ["positive-fallback"]
    assert transition["after"] == ["emerging-low-face"]

    before, at_wall, after = out["evaluations"]
    assert before["winning_mechanisms"] == ["positive-fallback"]
    assert before["response_exponent"]["exact"] == "2"
    assert at_wall["winning_mechanisms"] == ["positive-fallback"]
    assert at_wall["qualified_selection"]["mechanisms"][0]["status"] == "cancelled"
    assert after["winning_mechanisms"] == ["emerging-low-face"]
    assert after["response_exponent"]["exact"] == "4/3"


def test_dynamic_phase_withholds_consequence_without_uniform_hypotheses():
    out = FaceSelectionBackend().handle({
        "operation": "phase_diagram",
        "domain": [0, 1],
        "mechanisms": [{
            "id": "moving",
            "degree": {"intercept": "1/4"},
            "coefficient": {"intercept": "-1/2", "slope": 1},
        }],
        "assumptions": {
            "fixed_admissibility": True,
            "coefficient_qualification_verified": True,
            "affine_degrees_verified": True,
        },
    })
    assert out["answered"]
    assert out["status"] == "unlicensed"
    assert out["scope"]["blockers"] == [
        "local base maximality is not verified uniformly",
        "principal remainder control is not verified uniformly",
        "global isolation is not verified uniformly",
    ]


def test_exponent_derived_phase_input_rejects_invalid_newton_data():
    backend = FaceSelectionBackend()
    missing_axis = backend.handle({
        "operation": "phase_diagram",
        "domain": [0, 1],
        "base_orders": {"x": 4},
        "mechanisms": [{
            "id": "bad", "exponents": {"y": {"intercept": 1}}
        }],
    })
    assert missing_axis["status"] == "invalid_request"
    assert "absent from base_orders" in missing_axis["error"]["detail"]

    competing_models = backend.handle({
        "operation": "phase_diagram",
        "domain": [0, 1],
        "base_orders": {"x": 4},
        "mechanisms": [{
            "id": "bad",
            "degree": {"intercept": "1/4"},
            "exponents": {"x": {"intercept": 1}},
        }],
    })
    assert competing_models["status"] == "invalid_request"
    assert "not both" in competing_models["error"]["detail"]


def test_backend_keeps_the_computation_but_withholds_theorem_license():
    out = FaceSelectionBackend().handle({
        "operation": PHASE_OPERATION,
        "domain": [0, 1],
        "candidates": [
            {"id": "candidate", "degree": {"intercept": "1/2"}}
        ],
    })

    assert out["status"] == "unlicensed"
    assert out["answered"]
    assert not out["licensed"]
    assert len(out["scope"]["blockers"]) == 5


def test_phase_operation_is_available_through_the_json_boundary():
    document = """{
      "operation": "phase",
      "domain": [0, 1],
      "mechanisms": [
        {"id": "fixed", "degree": {"intercept": "1/2"}}
      ]
    }"""
    out = __import__("json").loads(handle_json(document))
    assert out["operation"] == PHASE_OPERATION
    assert out["phase_diagram"]["chambers"][0]["winning_mechanisms"] == ["fixed"]


def test_invalid_phase_request_is_total_at_the_backend_boundary():
    out = FaceSelectionBackend().handle({
        "operation": "phase_diagram",
        "domain": [1, 0],
        "mechanisms": [],
    })
    assert out["operation"] == PHASE_OPERATION
    assert out["status"] == "invalid_request"
    assert not out["answered"]
