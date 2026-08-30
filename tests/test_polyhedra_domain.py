"""
Domain three: the exponent laws on a general polyhedron.

Domain one's box is a hypercube, where a vertex's edges *are* the coordinate
axes, so the two ways of measuring flatness are the same instruction. These
tests pin the geometry that removes that coincidence, and the finding it
produces: the law survives in edge coordinates and fails in ambient ones at a
tilted vertex.
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest

from categorical_polytope.adjudication import Ledger, Status
from categorical_polytope.adjudication.domain import Domain, Generative
from categorical_polytope.adjudication.polyhedra import (
    GeometryError,
    Polyhedron,
    PolyhedronDomain,
    box,
    simplex,
)
from categorical_polytope.adjudication.polyhedra import laws
from categorical_polytope.adjudication.polyhedra.seeds import SEEDS

CORPUS = Path(__file__).resolve().parents[1] / "experiments" / "polyhedra.json"

SIMPLEX_SYS = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
BOX_SYS = "([[1,0],[-1,0],[0,1],[0,-1]], [1,0,1,0])"
#: Quadratic along one edge, quartic along the other. The two coordinate
#: systems disagree about the flatness order, which is the whole experiment.
SPLIT_BASE = "-((x0+x1-1)**2 + x0**4)"

EDGE = "polyhedron/edge_exponent_law"
AMBIENT = "polyhedron/ambient_exponent_law"
LINEAR = "polyhedron/linear_max_at_vertex"


@pytest.fixture(scope="module")
def domain() -> PolyhedronDomain:
    return PolyhedronDomain()


# ---------------------------------------------------------------- geometry ---


def test_box_vertices_are_all_axis_aligned():
    # This is what domain one has always run on, restated as Ax <= b.
    vertices = box(2).vertices()
    assert len(vertices) == 4
    assert all(v.is_simple and v.is_axis_aligned for v in vertices)


def test_simplex_has_tilted_vertices():
    vertices = simplex(2).vertices()
    assert len(vertices) == 3
    tilted = [v for v in vertices if not v.is_axis_aligned]
    assert tilted, "a simplex must have vertices whose edges are not axes"


def test_edge_directions_point_inward():
    poly = simplex(2)
    for vertex in poly.vertices():
        for edge in vertex.edges:
            stepped = [c + 1e-7 * d for c, d in zip(vertex.point, edge)]
            assert poly.contains(stepped), "an edge direction must enter the polytope"


def test_unboundedness_is_detected():
    # The non-negative quadrant: no upper constraint, so no maximum to speak of.
    assert not Polyhedron([[-1, 0], [0, -1]], [0, 0]).is_bounded()
    assert simplex(2).is_bounded()
    assert box(3).is_bounded()


def test_malformed_systems_are_refused():
    for rows, rhs in (([[1, 0], [0, 1, 1]], [1, 1]), ([[1]], [1]), ([[1, 0]], [1, 2])):
        with pytest.raises(GeometryError):
            Polyhedron(rows, rhs)


# --------------------------------------------------------------- the finding ---


def test_on_a_box_the_two_coordinate_systems_agree(domain):
    """The control. At a box vertex the inward axes are the edges."""
    base, pert = "-((1-x0)**2 + (1-x1)**2)", "(1-x0)"
    edge = domain.adjudicate(EDGE, BOX_SYS, base, pert)
    ambient = domain.adjudicate(AMBIENT, BOX_SYS, base, pert)
    assert edge.status is Status.VERIFIED
    assert ambient.status is Status.VERIFIED
    assert ambient.metrics["infeasible_axes"] == []
    assert abs(edge.metrics["predicted_exponent"]
               - ambient.metrics["predicted_exponent"]) < 1e-6


def test_on_a_tilted_vertex_the_edge_law_holds_and_the_ambient_one_fails(domain):
    """The finding: same geometry, same expressions, different coordinates."""
    edge = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    ambient = domain.adjudicate(AMBIENT, SIMPLEX_SYS, SPLIT_BASE, "x0")

    assert edge.status is Status.VERIFIED
    assert ambient.status is Status.COUNTEREXAMPLE
    # Both measure the same gap; only the prediction differs.
    assert abs(edge.metrics["measured_exponent"]
               - ambient.metrics["measured_exponent"]) < 0.05
    assert edge.metrics["predicted_exponent"] < ambient.metrics["predicted_exponent"]
    assert not edge.metrics["axis_aligned"]


def test_the_measured_exponent_matches_the_hand_calculation(domain):
    # Base drops as t^2 along one edge and t^4 along the other; the linear push
    # gives q = 1/4, so the law predicts 1/(1 - 1/4) = 4/3.
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert verdict.metrics["predicted_exponent"] == pytest.approx(4 / 3, abs=0.02)
    assert verdict.metrics["measured_exponent"] == pytest.approx(4 / 3, abs=0.05)


def test_a_tangent_axis_is_recorded_not_hidden(domain):
    # At the simplex vertex (0,1) the x0 axis leaves the set in both
    # orientations. That is kept and flagged rather than quietly dropped.
    ambient = domain.adjudicate(AMBIENT, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert ambient.metrics["infeasible_axes"] == [0]


def test_the_linear_control_never_fails(domain):
    """LP's fundamental theorem. Counterexamples here mean the harness is broken."""
    for system, objective in ((SIMPLEX_SYS, "2*x0 - 3*x1"), (BOX_SYS, "x0 + x1"),
                              (SIMPLEX_SYS, "-x0 + 4*x1"), (BOX_SYS, "-2*x0 - x1")):
        assert domain.adjudicate(LINEAR, system, objective, "0").status is Status.VERIFIED


# ------------------------------------------------------------------- scope ---


def test_unbounded_system_is_out_of_scope_not_a_failure(domain):
    verdict = domain.adjudicate(EDGE, "([[-1,0],[0,-1]], [0,0])", "-(x0**2 + x1**2)", "x0")
    assert verdict.status is Status.OUTSIDE_SCOPE
    assert "unbounded" in verdict.reason


def test_narrow_recession_cone_is_not_missed_by_boundedness_gate(domain):
    # The old 96-direction sampler stepped by 3.75 degrees and missed this
    # entire recession cone between one and two degrees.
    import math

    lo, hi = math.radians(1), math.radians(2)
    system = repr(([
        [math.sin(lo), -math.cos(lo)],
        [-math.sin(hi), math.cos(hi)],
    ], [0, 0]))

    verdict = domain.adjudicate(EDGE, system, "-(x0**2+x1**2)", "x0")

    assert verdict.status is Status.OUTSIDE_SCOPE
    assert "unbounded" in verdict.reason


def test_linear_control_rejects_nonlinear_objective(domain):
    nonlinear = "-x0 + 10*exp(-100*(x0-0.5)**2)"

    verdict = domain.adjudicate(LINEAR, BOX_SYS, nonlinear, "0")

    assert verdict.status is Status.OUTSIDE_SCOPE
    assert "affine" in verdict.reason


def test_a_base_with_no_maximising_vertex_is_out_of_scope(domain):
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, "x0 + x1", "x0")
    assert verdict.status is Status.OUTSIDE_SCOPE


def test_weighted_degree_outside_the_unit_interval_is_out_of_scope(domain):
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, "-((x0+x1-1)**2 + x0**2)", "x0**3")
    assert verdict.status is Status.OUTSIDE_SCOPE


def test_scope_cannot_consult_a_measured_exponent(domain):
    # Same structural guarantee as the other domains: no status reaches scope,
    # so admission cannot be withdrawn once the number is inconvenient.
    assert list(inspect.signature(domain.scope).parameters) == [
        "rule_id", "system", "base_expr", "pert_expr"]
    row = {"rule_id": AMBIENT,
           "payload": {"system": SIMPLEX_SYS, "base": SPLIT_BASE, "pert": "x0"},
           "status": "verified"}
    assert str(domain.readjudicate(row).status) == "counterexample"


# --------------------------------------------------------- parse boundary ---


def test_hostile_system_is_rejected_not_executed(domain, tmp_path):
    marker = tmp_path / "pwned.txt"
    payload = f"__import__('pathlib').Path({str(marker)!r}).write_text('x')"
    assert domain.adjudicate(EDGE, payload, "-(x0**2)", "x0").status is Status.REJECTED
    assert not marker.exists()


def test_expressions_outside_the_whitelist_are_rejected(domain):
    for expr in ("__import__('os').getcwd()", "open('x')", "lambda: 1"):
        assert domain.adjudicate(EDGE, SIMPLEX_SYS, expr, "x0").status is Status.REJECTED


def test_unknown_rule_is_rejected(domain):
    assert domain.adjudicate("polyhedron/no_such", SIMPLEX_SYS, "-(x0**2)", "x0").status \
        is Status.REJECTED


def test_expression_compiler_refuses_unsafe_input():
    for expr in ("__import__('os')", "x0.__class__", "[i for i in range(3)]", "x0**99"):
        with pytest.raises(laws.UnsafeExpression):
            laws.compile_expr(expr, 2)


# ------------------------------------------------------------- integration ---


def test_domain_satisfies_both_protocols(domain):
    assert isinstance(domain, Domain)
    assert isinstance(domain, Generative)


def test_identity_is_scoped_by_rule(domain):
    payload = {"system": SIMPLEX_SYS, "base": SPLIT_BASE, "pert": "x0"}
    assert domain.identity({"rule_id": EDGE, "payload": payload}) != \
        domain.identity({"rule_id": AMBIENT, "payload": payload})


def test_the_shared_ledger_drives_this_domain(domain):
    ledger = Ledger({"records": [], "verifier_version": domain.verifier_version})
    rows = [domain.to_row(s.rule_id, s.name, s.system, s.base, s.pert, s.note)
            for s in SEEDS[:6]]
    assert len(ledger.admit(domain, rows)) == 6
    assert len(ledger.admit(domain, rows)) == 0
    ledger.validate()


@pytest.fixture(scope="module")
def corpus() -> Ledger:
    if not CORPUS.exists():
        pytest.skip("run experiments/run_polyhedra.py first")
    return Ledger.load(CORPUS)


def test_live_corpus_validates_and_keeps_an_honest_denominator(corpus, domain):
    corpus.validate()
    counts = corpus.counts(domain)
    undecided = counts["outside_scope"] + counts["rejected"] + counts["inconclusive"]
    assert undecided > 0
    assert corpus.in_scope_total(domain) < len(corpus)


def test_the_ambient_rule_is_where_the_counterexamples_live(corpus):
    by_rule: dict[str, int] = {}
    for row in corpus.records:
        if row["status"] == "counterexample":
            by_rule[row["rule_id"]] = by_rule.get(row["rule_id"], 0) + 1
    assert by_rule.get(AMBIENT, 0) > 0
    assert by_rule.get(EDGE, 0) == 0, "the edge law should survive"
    assert by_rule.get(LINEAR, 0) == 0, "a counterexample to LP means the harness broke"


# ------------------------------------------------- resolution of the probe ---

#: A 3-D vertex where the asymptotic regime starts several decades below the
#: strength the probe used to sample. Measured at s=1e-2 alone it reads 1.125
#: against a predicted 4/3 and looks like a falsification; walked down the
#: ladder it settles on 4/3. The adversarial prompt asks for exactly this
#: shape, so the corpus has to survive it.
LATE_ASYMPTOTIC_SYS = "([[-1,0,0],[0,-1,0],[0,0,-1],[1,1,1]], [0,0,0,1])"
LATE_ASYMPTOTIC_BASE = "-((x0 - x1)**4 + (x0 + 2*x1 + x2 - 1)**2)"

#: Two edges each contributing 1/2, so q = 1 exactly in exact arithmetic and
#: 0.9999999999999999 in float. The law predicts 1/(1-q), which diverges.
DEGENERATE_Q_SYS = (
    "([[-5,1,0],[10,-2,0],[2,-10,0],[-2,10,0],[0,0,-1],[0,0,1]], "
    "[0,96,0,96,0,0.001])"
)


def test_the_exponent_is_read_from_the_deepest_resolved_strength(domain):
    """The fixed top-rung pair is not the asymptotic exponent, and says so."""
    _, _, _, m = domain.scope(EDGE, LATE_ASYMPTOTIC_SYS, LATE_ASYMPTOTIC_BASE, "x0")
    top_rung, _, _ = laws.gap_exponent(
        m["base_fn"], m["pert_fn"], m["poly"], m["vertex_obj"],
        strengths=(0.01, 0.0025),
    )
    ladder, _, _ = laws.gap_exponent(
        m["base_fn"], m["pert_fn"], m["poly"], m["vertex_obj"]
    )

    # Read at the top rung alone this is a mismatch well outside the 0.15
    # tolerance - 1.125 when this was first measured - and so a counterexample.
    # The property, not that number, is what has to hold.
    assert abs(top_rung - 4 / 3) > 0.15, "the reading that misled"
    assert ladder == pytest.approx(4 / 3, abs=0.02)


def test_a_late_asymptotic_geometry_is_not_a_counterexample(domain):
    verdict = domain.adjudicate(EDGE, LATE_ASYMPTOTIC_SYS, LATE_ASYMPTOTIC_BASE, "x0")
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["measured_exponent"] == pytest.approx(4 / 3, abs=0.02)


def test_an_unsettled_slope_cannot_become_a_counterexample(domain, monkeypatch):
    """A mismatch is only a finding once the measurement has stopped moving."""
    monkeypatch.setattr(laws, "gap_exponent", lambda *a, **k: (9.0, (1e-3, 1e-4), False))
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert verdict.status is Status.INCONCLUSIVE
    assert "drifting" in verdict.reason


def test_a_settled_mismatch_is_still_a_counterexample(domain, monkeypatch):
    """The guard must not cost the finding: same numbers, settled, still fails."""
    monkeypatch.setattr(laws, "gap_exponent", lambda *a, **k: (9.0, (1e-3, 1e-4), True))
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert verdict.status is Status.COUNTEREXAMPLE


def test_the_recorded_counterexample_rests_on_a_settled_measurement(domain):
    verdict = domain.adjudicate(AMBIENT, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert verdict.status is Status.COUNTEREXAMPLE
    assert verdict.metrics["exponent_converged"] is True


def test_a_weighted_degree_of_one_or_more_is_out_of_scope(domain):
    """
    Theorem V.16 selects over monomials with q_j < 1. A perturbation whose
    every branch sits at or above 1 has no admissible branch, and 1/(1-q)
    would diverge.

    `x0*x1` against a quadratic base has q = 1/2 + 1/2 on its one supporting
    face, so this is the boundary itself rather than a rounding artifact.
    """
    verdict = domain.adjudicate(
        EDGE, "([[-1,0,0],[0,-1,0],[0,0,-1],[1,1,1]], [0,0,0,1])",
        "-(x0**2 + x1**2 + x2**2)", "x0*x1")
    assert verdict.status is Status.OUTSIDE_SCOPE
    assert verdict.metrics["weighted_degree"] >= 1.0
    # The bug this replaces: admitted, then 1/(1-q) came out at 2**53.
    assert "predicted_exponent" not in verdict.metrics


def test_a_linear_push_is_selected_not_summed(domain):
    """
    The regression that cost eight corpus rows.

    `x0` is nonzero on both rays of this vertex, so summing alpha_i/beta_i gave
    1/2 + 1/2 = 1 and the row was discarded as out of scope. V.16 selects the
    minimum instead: q* = 1/2, predicting 2, which is what the gap measures.
    """
    verdict = domain.adjudicate(EDGE, DEGENERATE_Q_SYS, "-(x0**2 + x1**2 + x2**2)", "x0")
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["weighted_degree"] == pytest.approx(0.5, abs=1e-6)
    assert verdict.metrics["predicted_exponent"] == pytest.approx(2.0, abs=1e-6)
    assert verdict.metrics["measured_exponent"] == pytest.approx(2.0, abs=0.05)


def test_the_minimum_is_taken_over_faces_not_the_maximum(domain):
    """
    Two admissible faces that disagree, which is what separates the rules.

    Box vertex at the origin, base quadratic on one ray and quartic on the
    other, push `x0 + x1` surviving on both: the rays give q = 1/2 and q = 1/4.
    The objective is separable, so the true gap is s^2/4 + 0.4725*s^(4/3) and
    the 4/3 branch dominates as s falls. Minimum is right; maximum would say 2
    and the old sum said 4.
    """
    verdict = domain.adjudicate(EDGE, PRODUCT_SYS, PRODUCT_BASE, "x0 + x1")
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["weighted_degree"] == pytest.approx(0.25, abs=1e-3)
    assert verdict.metrics["measured_exponent"] == pytest.approx(4 / 3, abs=0.05)


def test_a_face_where_the_push_is_negative_is_not_a_branch(domain):
    """
    V.16's proof fixes a direction with W(z) > 0. Admissibility needs that sign.

    On this sheared 3-D vertex the face spanned by rays 0 and 1 is feasible but
    reaches x0 < 0, where the push lowers the objective. Counting it as a
    branch selects q = 1/4 and predicts 4/3 against a measured 2.
    """
    verdict = domain.adjudicate(
        EDGE, "([[-1,-1,0],[0,-1,0],[0,0,-1],[1,2,1]], [0,0,0,1])",
        "-((x0 + x1)**2 + (x1)**4 + (x2)**6)", "x0")
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["weighted_degree"] == pytest.approx(0.5, abs=1e-3)
    assert verdict.metrics["measured_exponent"] == pytest.approx(2.0, abs=0.05)
    # Only single-ray face 0 survives; anything spanning ray 1 goes negative.
    assert all(0 in face for face, _ in verdict.metrics["admissible_faces"])


# --------------------------------------------- the product-monomial regime ---

#: FORMAL_VERTEX_THRESHOLD section 15 derives q = sum_i alpha_i/beta_i for a
#: product monomial P = gamma * prod_i x_i**alpha_i. This is that case, and the
#: only one in which the sum is the derived answer: the unit-box vertex at the
#: origin, base quadratic along x0 and quartic along x1 (beta = 2, 4), and the
#: product perturbation x0*x1 (alpha = 1, 1). Derived q = 1/2 + 1/4 = 3/4, so
#: gamma = 1/(1-q) = 4 - and the optimum is closed form, which makes this the
#: one place the law can be checked without trusting any probe.
PRODUCT_SYS = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
PRODUCT_BASE = "-(x0**2 + x1**4)"
PRODUCT_PERT = "x0*x1"


def _origin_vertex(poly):
    return next(v for v in poly.vertices() if max(abs(c) for c in v.point) < 1e-9)


def _product_pieces(domain):
    poly = domain.parse_system(PRODUCT_SYS)
    return (poly, laws.compile_expr(PRODUCT_BASE, 2),
            laws.compile_expr(PRODUCT_PERT, 2), _origin_vertex(poly))


def test_the_product_monomial_gap_matches_the_closed_form(domain):
    """
    Ground truth for the regime section 15 derives, owing nothing to a probe.

    Maximising -(x0^2 + x1^4) + s*x0*x1 puts the optimum at
    x1 = s/(2*sqrt 2), x0 = s*x1/2, worth exactly s^4/64. The gap is therefore
    s^4: gamma = 4, which is the *sum* 1/(1 - 3/4). A minimum over the cone
    would give 1/(1 - 1/2) = 2 and be wrong here.
    """
    poly, base, pert, vertex = _product_pieces(domain)
    assert [laws.directional_order(base, vertex, e, rising=False)
            for e in vertex.edges] == pytest.approx([2.0, 4.0], abs=1e-6)

    for s in (0.5, 0.25, 0.125):
        x1 = s / (2 * math.sqrt(2))
        best = base([s * x1 / 2, x1]) + s * pert([s * x1 / 2, x1])
        assert best == pytest.approx(s**4 / 64, rel=1e-9)


def test_a_product_monomial_is_admitted_and_matches_the_closed_form(domain):
    """
    Section 15's own regime, reachable end to end.

    Per-ray measurement could not admit this at all - the monomial vanishes on
    every ray - so the sum was never once exercised on the case it was derived
    for. Selecting over faces, the only admissible one is the 2-D face, where
    q = 1/2 + 1/4 = 3/4 and the sum reappears correctly scoped to a single
    face. The closed form gives gamma = 4.
    """
    verdict = domain.adjudicate(EDGE, PRODUCT_SYS, PRODUCT_BASE, PRODUCT_PERT)
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["weighted_degree"] == pytest.approx(0.75, abs=1e-3)
    assert verdict.metrics["predicted_exponent"] == pytest.approx(4.0, abs=1e-2)
    assert verdict.metrics["measured_exponent"] == pytest.approx(4.0, abs=0.05)
    assert [face for face, _ in verdict.metrics["admissible_faces"]] == [[0, 1]]


def test_the_vertex_probe_finds_the_product_monomial_gap(domain):
    """
    The gap is real and the probe has to reach it.

    Coordinate descent alone could not: it starts at the vertex, and for a
    product perturbation every single-edge step and the equal-step diagonal are
    worse than staying put, so the sweep shrank to nothing and reported zero
    against a true gap of s^4/64. The seed scan over an independent ladder per
    edge reaches the lopsided combination that gains.
    """
    poly, base, pert, vertex = _product_pieces(domain)
    s = 0.5

    def combined(point):
        return base(point) + s * pert(point)

    x1 = s / (2 * math.sqrt(2))
    real_gap = s**4 / 64
    assert combined([s * x1 / 2, x1]) == pytest.approx(real_gap, rel=1e-9)
    # Each edge on its own leads downhill, which is what defeats the search.
    assert combined([0.25, 0.0]) < 0.0
    assert combined([0.0, 0.25]) < 0.0
    found = laws.local_max_near_vertex(combined, poly, vertex, radius=0.25)
    assert found == pytest.approx(real_gap, rel=1e-6)


# ------------------------------------------ hypotheses the corpus records ---

#: Box vertex at the origin, quadratic along one edge and quartic along the
#: other. Outside a ball of radius r the base is largest on the quartic edge at
#: exactly r, so the isolation margin is r**4 with nothing left to estimate.
ISOLATED_SYS = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
ISOLATED_BASE = "-(x0**2 + x1**4)"

#: A symmetric double well along x0. The two box corners (0,0) and (1,0) are
#: both maxima and both worth zero, so the unperturbed maximiser is not unique
#: and Lemma 1's localisation does not hold, however well the row measures.
TIED_BASE = "-(x0**2*(x0-1)**2) - x1**2"


def _corner_at_origin(domain, system):
    poly = domain.parse_system(system)
    return poly, next(v for v in poly.vertices()
                      if all(abs(c) < 1e-12 for c in v.point))


def test_the_isolation_margin_matches_the_hand_calculation(domain):
    """`eta` for an explicit neighbourhood, not a yes/no on an assumption."""
    poly, vertex = _corner_at_origin(domain, ISOLATED_SYS)
    base = laws.compile_expr(ISOLATED_BASE, 2)
    # On the quadratic edge r**2 is lost, on the quartic edge only r**4, and
    # off the edges the circle is worse than both. So max over P outside U is
    # -(1/4)**4, and the vertex is worth 0.
    assert laws.rival_margin(base, poly, vertex, radius=0.25) == pytest.approx(
        0.25**4, rel=1e-9)


def test_a_higher_maximiser_elsewhere_is_measured_not_assumed(domain):
    """The hypothesis is uniqueness, so a rival has to come back negative."""
    poly, vertex = _corner_at_origin(domain, ISOLATED_SYS)
    base = laws.compile_expr("-(x0-1)**2", 2)
    # The origin is worth -1; the opposite corner is worth 0.
    assert laws.rival_margin(base, poly, vertex) == pytest.approx(-1.0, abs=1e-9)


def test_a_tie_between_two_maxima_breaks_isolation(domain):
    poly, vertex = _corner_at_origin(domain, ISOLATED_SYS)
    base = laws.compile_expr(TIED_BASE, 2)
    assert laws.rival_margin(base, poly, vertex) <= 0.0


def test_the_isolation_probe_cannot_walk_back_into_its_own_neighbourhood(domain):
    """
    Regression. `local_max_near_vertex` seeds inside its radius but the pattern
    search that follows steps from the seed's own scale and is not confined, so
    a probe started at a far corner walked all the way to `vertex` and returned
    the vertex's own value. Every margin came out as exactly 0.0 - reported as
    a failure of isolation on rows that are in fact isolated, which is the one
    direction a diagnostic must not err in if anyone is to act on it.
    """
    poly = domain.parse_system(SIMPLEX_SYS)
    base = laws.compile_expr(SPLIT_BASE, 2)
    vertex = next(v for v in poly.vertices() if abs(v.point[1] - 1.0) < 1e-12)
    assert laws.rival_margin(base, poly, vertex) > 0.0


def test_an_acceptance_test_is_the_only_thing_that_changes_the_probe(domain):
    """Rows measured before v8 stay comparable: the default path is untouched."""
    poly, base, pert, vertex = _product_pieces(domain)

    def combined(point):
        return base(point) + 0.5 * pert(point)

    plain = laws.local_max_near_vertex(combined, poly, vertex, radius=0.25)
    passthrough = laws.local_max_near_vertex(
        combined, poly, vertex, radius=0.25, accept=lambda point: True)
    assert plain == passthrough


def test_a_row_records_whether_it_tests_the_selection_clause(domain):
    """
    Faces disagreeing is not enough. The rival rule has to predict a finite
    exponent too, or measurement merely rejects a divergence and any selection
    rule at all would have survived the row.
    """
    discriminating = domain.adjudicate(EDGE, PRODUCT_SYS, PRODUCT_BASE, "x0 + x1")
    assert discriminating.metrics["rival_max_degree"] == pytest.approx(0.5, abs=1e-3)
    assert discriminating.metrics["selection_discriminates"] is True
    assert discriminating.metrics["hypotheses_licensed"] is True

    # Same disagreement, but the rival face sits at q = 1.38: the maximum rule
    # predicts a negative exponent there, so the row cannot choose between two
    # numbers and does not carry the selection.
    diverging = domain.adjudicate(
        EDGE, "([[-1,-1,0],[0,-1,0],[0,0,-1],[1,2,1]], [0,0,0,1])",
        "-((x0 + x1)**2 + (x1)**4 + (x2)**6)", "x0")
    assert diverging.metrics["rival_max_degree"] > 1.0
    assert diverging.metrics["selection_discriminates"] is False


def test_the_recorded_hypotheses_never_gate_a_verdict(domain, monkeypatch):
    """
    `rival_margin` says the row's own hypothesis fails, and the verdict does
    not move. That is deliberate: a diagnostic that could flip a status would
    let the corpus quietly drop the rows that are hardest for the law, and the
    denominator would stop meaning anything.
    """
    before = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    monkeypatch.setattr(laws, "rival_margin", lambda *a, **k: -99.0)
    after = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert after.metrics["rival_margin"] == -99.0
    assert after.status is before.status
    assert after.metrics["predicted_exponent"] == before.metrics["predicted_exponent"]


def test_v8_invalidates_the_rules_that_gained_the_diagnostics(domain):
    invalidated = domain.rules_invalidated_between(7, 8)
    assert invalidated == {EDGE, AMBIENT}
    assert LINEAR not in invalidated, "the control never computes a face degree"


# ------------------------------------ v11: the probe's limits are not findings ---

#: The three payloads a steered campaign round produced, which between them
#: gave the edge law the first counterexamples it ever had. All three were the
#: probe failing, not the law.
ORDER8_SYS = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
ORDER8_BASE = "-(x0**8 + x1**2)"
DRIFTING_SYS = "([[ -2, -1],[1, -1],[1, 2]],[0,0,1])"
DRIFTING_BASE = "-((2*x0 + x1)**4 + (-x0 + x1)**5)"


def test_a_complex_value_raises_the_error_callers_already_guard():
    """
    A negative base under a fractional power is complex in Python, and the
    complex went on to `math.isfinite`, which raises TypeError - a type no
    caller guards. It killed a campaign round outright.
    """
    f = laws.compile_expr("(-8 - x0)**0.5", 1)
    with pytest.raises(ValueError):
        f([0.0])


def test_an_expression_with_no_real_value_is_a_verdict_not_a_traceback(domain):
    """
    Adjudicating an untrusted proposal must not be able to raise. The guard in
    `compile_expr` alone was not enough: `directional_order` evaluates at the
    vertex before `scope` has anything wrapped, so the error simply moved.
    """
    verdict = domain.adjudicate(
        EDGE, SIMPLEX_SYS, "-((x0+x1-1)**2 + (x0-0.5)**0.5)", "x0")
    assert verdict.status in (Status.OUTSIDE_SCOPE, Status.REJECTED)
    assert verdict.status is not Status.COUNTEREXAMPLE


def test_an_unresolved_base_order_is_undecided_not_a_degree_of_zero(domain):
    """
    `directional_order` documents 0.0 as "no scale pair resolved", to be
    treated as undecided. A base term of order 8 underflows its floor and read
    as 0, and the row was then adjudicated against a prediction the law never
    made - the honest exponent was 8/7 and it was compared against 2.
    """
    verdict = domain.adjudicate(EDGE, ORDER8_SYS, ORDER8_BASE, "x0 + x1")
    assert verdict.status is Status.OUTSIDE_SCOPE
    assert "did not resolve" in verdict.reason
    assert verdict.status is not Status.COUNTEREXAMPLE


def test_an_unsettled_winning_degree_cannot_become_a_counterexample(domain):
    """
    The other half of v3's discipline, which the face probe never got. Here the
    two-ray face reported q = 0.333 while its degree was still climbing through
    0.7, 0.78, 0.94 - a false minimum, and so a false counterexample. The
    optimiser in fact sits on the single-ray face at every strength.
    """
    verdict = domain.adjudicate(EDGE, DRIFTING_SYS, DRIFTING_BASE, "x0**2 + x1**3")
    assert verdict.status is Status.INCONCLUSIVE
    assert "still drifting" in verdict.reason
    assert verdict.metrics["weighted_degree_settled"] is False
    assert [0, 1] in verdict.metrics["unsettled_faces"]


def test_a_settled_row_says_so(domain):
    verdict = domain.adjudicate(EDGE, SIMPLEX_SYS, SPLIT_BASE, "x0")
    assert verdict.status is Status.VERIFIED
    assert verdict.metrics["weighted_degree_settled"] is True
    assert verdict.metrics["unsettled_faces"] == []


def test_the_ambient_finding_survives_every_guard(domain):
    """
    The guards exist to remove FALSE counterexamples. The domain's actual
    finding - that the box recipe fails at a tilted vertex - has to come
    through untouched, or the fix has thrown away the result with the noise.
    """
    for system, base in (
        (SIMPLEX_SYS, "-((x0+x1-1)**2 + x0**4)"),
        ("([[-1,0],[0,-1],[1,2]], [0,0,2])", "-((x0+2*x1-2)**2 + x0**4)"),
    ):
        verdict = domain.adjudicate(AMBIENT, system, base, "x0")
        assert verdict.status is Status.COUNTEREXAMPLE, system
        assert verdict.metrics["weighted_degree_settled"] is True
