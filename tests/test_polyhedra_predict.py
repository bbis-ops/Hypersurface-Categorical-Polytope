"""
The face-selection law run forwards, and run backwards.

The domain's own tests pin the verdicts. These pin the other direction: given a
geometry, does the predictor return the exponent, name the branch that carries
it, say which constraints the optimiser slides off, and refuse where the law
makes no claim - and does it say so when a hypothesis is unmet rather than
quietly answering anyway.
"""

from __future__ import annotations

import math

import pytest

# The package re-exports the FUNCTION `predict`, which shadows the module of
# the same name, so the module's other names come through this longer path.
from categorical_polytope.adjudication.polyhedra.predict import (
    CRITICAL,
    INACTIVE,
    RELEVANT,
    SUBLEADING,
    calibrate,
    consistent_faces,
    main as cli,
    predict,
)

#: The worked case of the note. Quartic along the slanted edge, quadratic along
#: the vertical one, linear push. Everything about it is known in closed form.
SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
SIMPLEX_BASE = "-((x0+x1-1)**2 + x0**4)"

#: Box vertex at the origin with orders (2, 4) and a push surviving on both
#: edges: the rays give q = 1/2 and q = 1/4, so minimum and maximum disagree
#: and both predictions are finite.
PRODUCT = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
PRODUCT_BASE = "-(x0**2 + x1**4)"


# ------------------------------------------------------------- forwards ---


def test_the_worked_case_comes_back_exactly():
    """gamma = 4/3 and the coefficient 3/4**(4/3), to the probe's precision."""
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    assert out.answered
    assert out.weighted_degree == pytest.approx(0.25, abs=1e-9)
    assert out.exponent == pytest.approx(4 / 3, abs=1e-9)
    assert out.coefficient == pytest.approx(3 / 4 ** (4 / 3), rel=1e-9)
    assert out.coefficient_settled


def test_the_branch_is_the_minimal_face_not_every_face_that_ties():
    """
    A larger face inherits q* from a smaller one it contains.

    Both {0} and {0,1} read q = 1/4 on the tilted simplex, because the full
    cone supports the same monomial the slanted edge does. Only {0} is a
    branch. Reporting both would say the optimiser leaves the constraint
    x0 + x1 <= 1, which it does not: the whole gain happens along that face.
    """
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    assert out.winning_faces == ((0,),)
    attaining = {f.edges for f in out.faces
                 if f.degree is not None and abs(f.degree - 0.25) < 1e-6}
    assert attaining == {(0,), (0, 1)}, "the tie is real; the branch is not"


def test_it_names_the_constraints_the_optimiser_slides_off():
    """
    Implication 2, concretely. At v = (0,1) the active constraints are
    -x0 <= 0 (index 0) and x0 + x1 <= 1 (index 2). The gain runs along the
    slanted edge, so x0 >= 0 is released and x0 + x1 <= 1 stays tight.
    """
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    assert out.released == (0,)
    assert out.binding == (2,)


def test_an_inactive_face_is_filtered_with_its_reason():
    """The vertical edge is feasible; the perturbation vanishes on it."""
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    vertical = next(f for f in out.faces if f.edges == (1,))
    assert not vertical.admitted
    assert vertical.relevance == INACTIVE
    assert "vanishes" in vertical.reason


def test_the_minimum_is_selected_where_a_maximum_would_differ():
    """Two admissible faces, both finite: q* = 1/4, not 1/2."""
    out = predict(PRODUCT, PRODUCT_BASE, "x0 + x1")
    assert out.weighted_degree == pytest.approx(0.25, abs=1e-3)
    assert out.exponent == pytest.approx(4 / 3, abs=1e-3)
    degrees = sorted(f.degree for f in out.faces if f.degree is not None)
    assert degrees[-1] > 0.4, "a rival face at q = 1/2 has to be present"


def test_faces_are_sorted_into_the_four_relevance_classes():
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    groups = out.by_relevance()
    assert set(groups) == {RELEVANT, CRITICAL, SUBLEADING, INACTIVE}
    assert all(f.degree is not None and f.degree < 1.0 for f in groups[RELEVANT])
    assert groups[RELEVANT], "the worked case has a relevant face"
    assert groups[INACTIVE], "and an inactive one"


# ------------------------------------------------------------ hypotheses ---


def test_the_worked_case_is_licensed_and_says_which_hypotheses_hold():
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    hypotheses = out.hypotheses
    assert hypotheses is not None
    assert hypotheses.edge_orders == (4.0, 2.0)
    assert hypotheses.homogeneous and hypotheses.orders_above_one
    assert hypotheses.isolated and hypotheses.isolation_margin > 0.0
    assert hypotheses.licensed and out.licensed
    assert hypotheses.unmet() == ()


def test_an_unmet_hypothesis_is_named_and_the_exponent_is_still_returned():
    """
    The point of the design. A backend that only ever saw a refusal could not
    tell "the law does not apply" from "the law applies and fails", and a
    backend that only ever saw a number could not tell either. So the number
    comes back and the warrant comes with it.
    """
    # A symmetric double well: the box corners (0,0) and (1,0) are both maxima
    # worth zero, so the maximiser is not unique. Every base order still
    # resolves, so the row IS adjudicated - which is the case worth pinning,
    # since a row that cannot be measured at all is refused instead.
    out = predict("([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
                  "-(x0**2*(x0-1)**2) - x1**2", "x0 + x1")
    assert out.answered, "an unlicensed case still gets an exponent"
    assert not out.licensed
    assert "isolated maximiser" in out.hypotheses.unmet()
    assert out.hypotheses.isolation_margin is not None
    assert out.hypotheses.isolation_margin <= 0.0


# --------------------------------------------------------------- refusals ---


def test_an_unbounded_system_is_refused_with_the_reason():
    out = predict("([[-1,0],[0,-1]], [0,0])", "-(x0**2 + x1**2)", "x0")
    assert not out.answered
    assert out.exponent is None
    assert "unbounded" in out.refusal


def test_a_degree_outside_the_unit_interval_is_refused():
    """Where q >= 1 the law predicts nothing, and the predictor says nothing."""
    out = predict(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "x0**8")
    assert not out.answered
    assert out.refusal


def test_a_refusal_still_reports_the_geometry_it_got_to():
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0**8")
    assert out.vertex == pytest.approx((0.0, 1.0), abs=1e-9)
    assert out.faces, "the faces it examined are still worth showing"


# ------------------------------------------------------------- backwards ---


def test_calibration_inverts_the_exponent():
    assert calibrate(4 / 3) == pytest.approx(0.25, abs=1e-12)
    assert calibrate(2.0) == pytest.approx(0.5, abs=1e-12)


def test_calibration_refuses_an_exponent_the_law_cannot_produce():
    """gamma = 1/(1-q) with q in (0,1) is always above 1."""
    for bad in (1.0, 0.5, 0.0, -3.0, math.inf, math.nan):
        with pytest.raises(ValueError):
            calibrate(bad)


def test_an_observed_exponent_identifies_the_branch():
    """
    Implication 8 used as intended: a measured 4/3 names q = 1/4, and the only
    faces of this cone carrying that degree are the ones that actually do.
    """
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    matches = consistent_faces(out, 4 / 3)
    assert {f.edges for f in matches} == {(0,), (0, 1)}
    assert all(f.degree == pytest.approx(0.25, abs=1e-6) for f in matches)


def test_an_observed_exponent_from_no_face_matches_nothing():
    """
    How the ambient counterexample announces itself. The naive box recipe
    predicts 2 at this vertex; no face of the tangent cone carries q = 1/2, so
    calibration returns nothing rather than inventing a branch.
    """
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    assert consistent_faces(out, 2.0, tolerance=0.05) == ()


def test_calibration_on_an_impossible_exponent_is_empty_not_an_error():
    out = predict(SIMPLEX, SIMPLEX_BASE, "x0")
    assert consistent_faces(out, 0.9) == ()


# ------------------------------------------------------------- reporting ---


def test_the_report_states_the_answer_and_its_warrant():
    text = predict(SIMPLEX, SIMPLEX_BASE, "x0").report()
    for expected in ("gamma", "q* = 0.25", "0.472470394", "released",
                     "binding", "licensed", "isolation eta"):
        assert expected in text, expected
    assert "-0" not in text, "a coordinate solved to -0.0 should not print"


def test_the_cli_returns_nonzero_when_it_cannot_answer(capsys):
    assert cli([SIMPLEX, SIMPLEX_BASE, "x0"]) == 0
    assert cli(["([[-1,0],[0,-1]], [0,0])", "-(x0**2 + x1**2)", "x0"]) == 1
    assert "unbounded" in capsys.readouterr().out


# --------------------------------------------------- agreement with the ledger ---


def test_the_predictor_and_the_adjudicator_admit_exactly_the_same_cases():
    """
    The property the whole module rests on. If prediction admitted a case the
    adjudicator refuses, the backend would answer questions the corpus holds no
    evidence about - and the evidence is the only reason to believe the answer.
    """
    from categorical_polytope.adjudication.polyhedra import PolyhedronDomain
    from categorical_polytope.adjudication.polyhedra.predict import RULE

    domain = PolyhedronDomain()
    cases = [
        (SIMPLEX, SIMPLEX_BASE, "x0"),
        (PRODUCT, PRODUCT_BASE, "x0 + x1"),
        (SIMPLEX, SIMPLEX_BASE, "x0**8"),
        ("([[-1,0],[0,-1]], [0,0])", "-(x0**2 + x1**2)", "x0"),
        (SIMPLEX, "x0 + x1", "x0"),
    ]
    for system, base, pert in cases:
        admitted, _, _, _ = domain.scope(RULE, system, base, pert)
        assert predict(system, base, pert).answered is admitted, (system, base, pert)
