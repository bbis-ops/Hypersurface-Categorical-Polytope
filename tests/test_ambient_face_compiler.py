"""V.20: exact ambient pullback is the authority before face selection."""

from __future__ import annotations

from fractions import Fraction

import pytest

from categorical_polytope.ambient_face_compiler import (
    compile_ambient_face_selection,
    exact_chart_from_active_constraints,
    transport_ambient_polynomial,
)
from categorical_polytope.adjudication.polyhedra.backend import (
    ASSET_VERSION,
    FaceSelectionBackend,
    analyze_face_selection,
)
from categorical_polytope.face_selection import (
    BasePower,
    EdgeCoordinateChart,
    HypothesisStatus,
    LawHypotheses,
    WeightedPrincipalPart,
)


SIMPLEX = ([[-1, 0], [0, -1], [1, 1]], [0, 0, 1])
SHEARED = ([[-1, 0], [0, -1], [1, 2]], [0, 0, 2])
SIMPLEX_TEXT = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
SHEARED_TEXT = "([[-1,0],[0,-1],[1,2]], [0,0,2])"
SIMPLEX_BASE = "-((x0+x1-1)**2 + x0**4)"
SHEARED_BASE = "-((x0+2*x1-2)**2 + x0**4)"
LICENSED = LawHypotheses(*((HypothesisStatus.VERIFIED,) * 3))


def _compile_counterexample(system, base):
    rows, rhs = system
    vertex, generators = exact_chart_from_active_constraints(
        rows, rhs, (0, 2), axes=("c0", "c1")
    )
    chart = EdgeCoordinateChart(
        tuple(float(value) for value in vertex),
        {
            axis: tuple(float(value) for value in vector)
            for axis, vector in generators.items()
        },
    )
    principal = WeightedPrincipalPart({
        "c0": BasePower(1, 4),
        "c1": BasePower(1, 2),
    })
    base_transport = transport_ambient_polynomial(base, vertex, generators)
    perturbation = compile_ambient_face_selection(
        "x0",
        chart,
        principal,
        hypotheses=LICENSED,
        exact_vertex=vertex,
        exact_generators=generators,
    )
    return base_transport, perturbation.to_dict(principal)


@pytest.mark.parametrize(
    ("system", "base"),
    [(SIMPLEX, SIMPLEX_BASE), (SHEARED, SHEARED_BASE)],
    ids=("simplex_quartic_ambient", "sheared_quartic_ambient"),
)
def test_the_two_ambient_counterexamples_are_resolved_by_exact_feasible_pullback(
    system, base
):
    base_transport, out = _compile_counterexample(system, base)

    assert dict(base_transport.polynomial) == {
        (0, 2): Fraction(-1),
        (4, 0): Fraction(-1),
    }
    assert dict(base_transport.axial_orders) == {"c0": 4, "c1": 2}
    assert out["selection"]["q_star"]["exact"] == "1/4"
    assert out["selection"]["response_exponent"]["exact"] == "4/3"
    assert out["selection"]["response_exponent"]["value"] != 2.0


def test_transport_retains_exact_top_level_cancellation_lineage():
    vertex, generators = exact_chart_from_active_constraints(
        *SIMPLEX, (0, 2), axes=("c0", "c1")
    )
    out = transport_ambient_polynomial(
        "x0 - x0 + x0**2", vertex, generators
    ).to_dict()

    assert out["summary"]["ambient_term_count"] == 3
    assert out["summary"]["cancelled_edge_monomial_count"] == 1
    cancellation = out["cancellations"][0]
    assert cancellation["signature"] == [1, 0]
    assert cancellation["coefficient"]["exact"] == "0"
    assert [item["term_index"] for item in cancellation["ambient_contributions"]] == [0, 1]
    assert out["edge_monomials"][0]["signature"] == [2, 0]


@pytest.mark.parametrize("coefficient", ("1e-20", "1e-400"))
def test_exact_nonzero_coefficients_survive_transport_and_selection(coefficient):
    chart = EdgeCoordinateChart(
        (0.0, 0.0), {"c0": (1.0, 0.0), "c1": (0.0, 1.0)}
    )
    principal = WeightedPrincipalPart({
        "c0": BasePower(1, 2),
        "c1": BasePower(1, 2),
    })

    compilation = compile_ambient_face_selection(
        f"{coefficient}*x0", chart, principal, hypotheses=LICENSED
    )

    assert compilation.transport.polynomial[(1, 0)] == Fraction(coefficient)
    assert compilation.selection is not None
    assert compilation.selection.q_star == Fraction(1, 2)
    assert compilation.selection.response_exponent == 2


def test_python_integer_literal_forms_remain_supported():
    transport = transport_ambient_polynomial(
        "0x10*x0 + 0b10*x1",
        (0, 0),
        {"c0": (1, 0), "c1": (0, 1)},
    )

    assert dict(transport.polynomial) == {
        (0, 1): Fraction(2),
        (1, 0): Fraction(16),
    }


def test_face_restrictions_report_geometric_suppression_independently():
    _, out = _compile_counterexample(SIMPLEX, SIMPLEX_BASE)
    c1_face = next(
        face for face in out["face_restrictions"] if face["face"] == ["c1"]
    )

    assert c1_face["status"] == "zero_restriction"
    assert c1_face["ambient_terms"] == [
        {"term_index": 0, "status": "geometrically_suppressed"}
    ]


@pytest.mark.parametrize(
    ("request_id", "system", "base"),
    [
        ("simplex_quartic_ambient", SIMPLEX_TEXT, SIMPLEX_BASE),
        ("sheared_quartic_ambient", SHEARED_TEXT, SHEARED_BASE),
    ],
)
def test_backend_promotes_the_counterexample_resolution_to_a_first_class_asset(
    request_id, system, base
):
    out = analyze_face_selection({
        "request_id": request_id,
        "system": system,
        "base": base,
        "perturbation": "x0 + x0**8",
    })

    assert out["asset_version"] == ASSET_VERSION == "portable-principle.v7"
    assert out["ambient_hierarchy"]["chart_source"] == "exact active-constraint solve"
    assert out["ambient_hierarchy"]["weight_layer"]["exact_pullback_axial_orders"] == {
        "c0": 4,
        "c1": 2,
    }
    assert out["ambient_hierarchy"]["weight_layer"]["weight_source"] == (
        "exact base-pullback axial orders"
    )
    assert out["ambient_hierarchy"]["weight_layer"]["orders_agree"] == {
        "c0": True,
        "c1": True,
    }
    assert out["selection"]["weighted_degree"] == pytest.approx(1 / 4)
    assert out["scaling"]["response_exponent"] == pytest.approx(4 / 3)
    high_order = out["perturbation_analysis"]["terms"][1]
    assert high_order["classification_basis"] == "exact polynomial transport to edge coordinates"
    assert high_order["ambient_transport"]["edge_monomials"][0]["signature"] == [8, 0]
    assert high_order["relevance"] == "subleading"


def test_portfolio_pins_same_law_but_distinct_chart_transport():
    cases = [
        {
            "request_id": "simplex_quartic_ambient",
            "system": SIMPLEX_TEXT,
            "base": SIMPLEX_BASE,
            "perturbation": "x0",
        },
        {
            "request_id": "sheared_quartic_ambient",
            "system": SHEARED_TEXT,
            "base": SHEARED_BASE,
            "perturbation": "x0",
        },
    ]
    out = FaceSelectionBackend().handle({"operation": "portfolio", "cases": cases})
    transition = out["transitions"][0]

    assert transition["kind"] == "same_universality_class"
    assert transition["ambient_transport_change"]["changed"]
    assert transition["ambient_transport_change"]["from_signature"] == "1,0:1"
    assert transition["ambient_transport_change"]["to_signature"] == "1,0:1"
