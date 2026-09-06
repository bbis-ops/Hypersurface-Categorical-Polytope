"""Independent finite-scale bounds, feasibility, and exact JSON decisions."""

from fractions import Fraction as Q
import json

import pytest

from categorical_polytope.adjudication.polyhedra.backend import FaceSelectionBackend, handle_json
from categorical_polytope.curved_finite_scale import (
    FiniteScaleRequest, _bernstein, _power_interval, _subdivide,
)


BOX = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"


def request(s="1/100", tolerance="1/10", **overrides):
    payload = {
        "operation": "curved_reduction", "system": BOX,
        "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2",
        "finite_scale": {"s": s, "relative_tolerance": tolerance},
    }
    payload.update(overrides)
    return payload


def bounds(interval):
    return Q(interval["lower"]["exact"]), Q(interval["upper"]["exact"])


def cancellation(s):
    return request(s, perturbation="-x0**2+x0*x1**2-x1**4/4+x1**4/1000000000+x1**5")


def test_near_cancellation_is_outside_tolerance_without_revoking_the_law():
    result = FaceSelectionBackend().handle(cancellation("1e-9"))
    assert result["licensed"] and result["status"] == "licensed"
    assert result["scaling"]["response_exponent_exact"] == "3"
    assert Q(result["scaling"]["leading_coefficient"]["exact"]) == Q(4, 27) * Q(1, 10**27)
    cert = result["finite_scale"]
    assert cert["status"] == "outside_tolerance" and cert["bounds_certified"]
    s = Q(1, 10**9)
    # Independent closed-form sandwich at lambda=1, not an optimizer fit.
    analytic_upper = Q(1280, 729) * s**6
    analytic_lower = analytic_upper - Q(8, 9)**6 * s**12
    lo, hi = bounds(cert["gap_interval"])
    assert lo <= analytic_upper and hi >= analytic_lower
    assert bounds(cert["gap_to_prediction_ratio"])[0] > Q(11, 10)


def test_same_coefficient_has_certified_accuracy_at_a_smaller_scale():
    result = FaceSelectionBackend().handle(cancellation("1e-12"))
    cert = result["finite_scale"]
    assert result["licensed"] and cert["status"] == "within_tolerance"
    lo, hi = bounds(cert["gap_to_prediction_ratio"])
    assert Q(9, 10) <= lo <= hi <= Q(11, 10)
    assert Q(cert["relative_error_bound"]["exact"]) <= Q(1, 10)


def test_cancellation_endpoint_preserves_its_sixth_order_law():
    result = FaceSelectionBackend().handle(request(
        "1/10", "1/1000000", perturbation="-x0**2+x0*x1**2-x1**4/4+x1**5"))
    assert result["scaling"]["response_exponent_exact"] == "6"
    assert result["finite_scale"]["status"] == "within_tolerance"


@pytest.mark.parametrize("system,base,perturbation", [
    ("([[-1,0],[1,-1],[1,0],[-1,1]], [0,0,1,1])",
     "-(x0**6+(x1-x0)**6)", "-x0**2+x0*(x1-x0)**2"),
    ("([[-2,0],[0,-3],[1,0],[0,1]], [0,0,1,1])",
     "-(x0**6+x1**6)", "-x0**2+x0*x1**2"),
    ("([[-1,0],[0,-1],[1,0],[0,1]], [-2,-3,3,4])",
     "7-((x0-2)**6+(x1-3)**6)", "5-(x0-2)**2+(x0-2)*(x1-3)**2"),
    ("([[-1,0],[0,-1],[1,1]], [0,0,1])",
     "-(x0**6+x1**6)", "-x0**2+x0*x1**2"),
    (BOX, "-(x0**6+x1**6)", "-x1**2+x1*x0**2"),
])
def test_finite_bounds_transport_across_charts_and_axis_orientations(system, base, perturbation):
    result = FaceSelectionBackend().handle(request(system=system, base=base, perturbation=perturbation))
    cert = result["finite_scale"]
    assert cert["status"] == "within_tolerance"
    witness = cert["witness"]
    assert all(Q(slack) >= 0 for slack in witness["constraint_slacks_exact"])
    assert all(Q(c) >= 0 for c in witness["coordinates_exact"].values())
    assert Q(witness["objective_gain"]["exact"]) == bounds(cert["gap_interval"])[0]
    # Reconstruct the ambient point and check every original inequality too.
    import ast
    rows, rhs = ast.literal_eval(system)
    chart = result["localization"]
    ambient = [Q(c) for c in chart["vertex_exact"]]
    for axis, coordinate in witness["coordinates_exact"].items():
        ambient = [v + Q(coordinate)*Q(u)
                   for v, u in zip(ambient, chart["generators_exact"][axis])]
    assert all(sum(Q(a)*v for a, v in zip(row, ambient)) <= Q(b) for row, b in zip(rows, rhs))


def test_retained_projection_uses_coupled_constraints():
    system = "([[-1,0],[0,-1],[1,1],[-1,2]], [0,0,1,1])"
    cert = FaceSelectionBackend().handle(request(system=system))["finite_scale"]
    assert bounds(cert["envelope"]["retained_projection"]) == (0, Q(2, 3))


def test_infeasible_square_center_is_clipped_and_full_penalty_is_charged():
    result = FaceSelectionBackend().handle(request(
        "100", base="-(x0**8+x1**6)", perturbation="-x0**2+4*x0*x1"))
    cert = result["finite_scale"]
    witness = cert["witness"]
    assert witness["kind"] == "clipped_square_center"
    assert witness["coordinates_exact"] == {"c0": "1", "c1": "1"}
    assert Q(witness["square_penalty_cost"]["exact"]) == 100
    # The full objective is increasing towards (1,1) in this case: max=298.
    lo, hi = bounds(cert["gap_interval"])
    assert lo == 298 and hi >= 298
    assert cert["status"] == "outside_tolerance"


def test_negative_driver_remainder_and_signed_envelope_still_bound_every_sample():
    result = FaceSelectionBackend().handle(request(
        "3/5", perturbation="-x0**2+x0*(x1**2-10*x1**3)+5*x1**5-25*x1**6"))
    cert = result["finite_scale"]
    assert cert["bounds_certified"]
    lo, hi = bounds(cert["gap_interval"])
    for i in range(11):
        for j in range(11):
            x, y = Q(i, 10), Q(j, 10)
            gain = -x*x+x*(y*y-10*y**3)+5*y**5-25*y**6
            value = -x**6-y**6+Q(3, 5)*gain
            assert value <= hi
    assert lo >= 0


def test_irrational_prediction_is_enclosed_by_rational_arithmetic():
    cert = FaceSelectionBackend().handle(request(base="-(x0**8+x1**7)"))["finite_scale"]
    assert cert["status"] == "within_tolerance"
    lo, hi = bounds(cert["prediction_interval"])
    s = Q(1, 100)
    exact_cube = (Q(3, 28)*s)**3 * (s/7)**4
    assert 0 < lo < hi and lo**3 <= exact_cube <= hi**3


def test_underflowed_display_values_do_not_decide_the_certificate():
    cert = FaceSelectionBackend().handle(request("1e-120"))["finite_scale"]
    assert cert["status"] == "within_tolerance"
    assert cert["prediction_interval"]["lower"]["value"] is None
    assert Q(cert["prediction_interval"]["lower"]["exact"]) > 0
    json.dumps(cert, allow_nan=False)


def test_budget_exhaustion_returns_a_valid_unresolved_interval():
    payload = request()
    payload["finite_scale"]["max_subdivisions"] = 0
    result = FaceSelectionBackend().handle(payload)
    cert = result["finite_scale"]
    assert result["licensed"] and cert["bounds_certified"]
    assert cert["status"] == "not_resolved" and cert["reason"] == "subdivision_limit"
    lo, hi = bounds(cert["gap_interval"])
    assert lo == 0 and hi >= Q(1, 432) * Q(1, 100)**3


def test_tight_envelope_with_material_omitted_cost_remains_unresolved():
    cert = FaceSelectionBackend().handle(request("1", "1/1000000"))["finite_scale"]
    assert cert["bounds_certified"] and cert["status"] == "not_resolved"
    assert cert["reason"] == "envelope_relaxation_gap"


def test_size_guard_during_refinement_keeps_the_global_upper_bound(monkeypatch):
    import categorical_polytope.curved_finite_scale as finite
    monkeypatch.setattr(finite, "MAX_WORKING_BITS", 32)
    result = FaceSelectionBackend().handle(request())
    cert = result["finite_scale"]
    assert result["licensed"] and cert["bounds_certified"]
    assert cert["reason"] == "rational_size_limit"
    s = Q(1, 100)
    lo, hi = bounds(cert["gap_interval"])
    assert lo <= s**3/432 and hi >= s**3/432-s**6/12**6
    assert cert["witness"]["feasible"]


def test_documented_batch_runs_through_cli(capsys):
    from pathlib import Path
    from categorical_polytope.adjudication.polyhedra.backend import main
    source = Path(__file__).resolve().parents[1] / "experiments" / "curved_finite_scale_requests.json"
    assert main(["--input", str(source)]) == 0
    results = json.loads(capsys.readouterr().out)
    assert [r["finite_scale"]["status"] for r in results] == ["outside_tolerance", "within_tolerance"]


@pytest.mark.parametrize("payload,reason", [
    (request(base="-(x0**40+x1**6)"), "degree_limit"),
    (request("1e-1000"), "rational_size_limit"),
])
def test_finite_resource_guards_preserve_the_asymptotic_license(payload, reason):
    result = FaceSelectionBackend().handle(payload)
    assert result["licensed"] and result["scaling"]["response_exponent_exact"] == "3"
    assert result["finite_scale"]["status"] == "not_resolved"
    assert result["finite_scale"]["reason"] == reason
    assert not result["finite_scale"]["bounds_certified"]


def test_omitted_request_and_outside_scope_have_explicit_finite_status():
    payload = request()
    payload.pop("finite_scale")
    ordinary = FaceSelectionBackend().handle(payload)
    assert ordinary["finite_scale"]["status"] == "not_requested"
    assert ordinary["scaling"]["uniform_in_coefficients"] is False
    outside = FaceSelectionBackend().handle(request(base="-(x0**3+x1**6)"))
    assert outside["finite_scale"]["status"] == "not_available"
    assert not outside["licensed"]


@pytest.mark.parametrize("finite", [
    None, [], {}, {"s": True}, {"s": False}, {"s": 0}, {"s": "-1"},
    {"s": "NaN"}, {"s": "Infinity"}, {"s": float("nan")}, {"s": "1/0"},
    {"s": "1e999999999"}, {"s": "1"*257}, {"s": "__import__('os')"},
    {"s": "1", "relative_tolerance": -1}, {"s": "1", "relative_tolerance": 1},
    {"s": "1", "relative_tolerance": True}, {"s": "1", "max_subdivisions": -1},
    {"s": "1", "max_subdivisions": 1025}, {"s": "1", "max_subdivisions": True},
    {"s": "1", "max_subdivisions": 1.5}, {"s": "1", "tolerence": ".1"},
])
def test_invalid_finite_requests_are_validation_errors(finite):
    result = FaceSelectionBackend().handle(request(finite_scale=finite))
    assert result["status"] == "invalid_request" and not result["licensed"]


def test_json_batch_preserves_independent_asymptotic_and_finite_statuses():
    batch = [cancellation("1e-9"), cancellation("1e-12"), request(finite_scale={"s": 0})]
    results = json.loads(handle_json(json.dumps(batch)))
    assert [r["status"] for r in results] == ["licensed", "licensed", "invalid_request"]
    assert [r["finite_scale"]["status"] for r in results[:2]] == ["outside_tolerance", "within_tolerance"]


def test_request_accepts_exact_decimals_and_rationals():
    assert FiniteScaleRequest("1e-9").s == Q(1, 10**9)
    assert FiniteScaleRequest("1/3", ".01").relative_tolerance == Q(1, 100)


@pytest.mark.parametrize("base,power", [(Q(2), Q(1, 2)), (Q(1, 27), Q(2, 3)),
                                          (Q(1, 10**120), Q(4, 3)), (Q(64), Q(1, 3))])
def test_rational_power_bounds_prove_their_own_root_inequalities(base, power):
    lo, hi = _power_interval(base, power)
    assert 0 < lo <= hi
    assert lo**power.denominator <= base**power.numerator <= hi**power.denominator


def test_bernstein_bounds_and_subdivision_represent_the_same_polynomial():
    terms = {0: Q(2), 1: Q(-3), 3: Q(7), 5: Q(-9)}
    extent = Q(7, 3)
    coeffs = _bernstein(terms, extent)
    children = _subdivide(coeffs)
    from math import comb
    def evaluate_bernstein(coefficients, t):
        degree = len(coefficients) - 1
        return sum(c*comb(degree, i)*t**i*(1-t)**(degree-i) for i, c in enumerate(coefficients))
    for i in range(21):
        t = Q(i, 20)
        actual = sum(c*(extent*t)**k for k, c in terms.items())
        assert evaluate_bernstein(coeffs, t) == actual
        assert min(coeffs) <= actual <= max(coeffs)
        child, local = (children[0], 2*t) if t <= Q(1, 2) else (children[1], 2*t-1)
        assert evaluate_bernstein(child, local) == actual
        assert min(child) <= actual <= max(child)
