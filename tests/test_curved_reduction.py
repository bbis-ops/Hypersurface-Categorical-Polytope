"""Independent algebra, sharp bounds, and scope tests for curved reduction."""

from fractions import Fraction as Q

import pytest

from categorical_polytope.curved_reduction import (
    ReductionNotApplicable,
    reduce_quadratic_channel,
)


BASE = {(6, 0): Q(1), (0, 6): Q(1)}
PERT = {(2, 0): Q(-1), (1, 2): Q(1)}


def evaluate(poly, x, y):
    return sum(c * x**i * y**j for (i, j), c in poly.items())


def test_original_counterexample_has_exact_exponent_and_amplitude():
    cert = reduce_quadratic_channel(BASE, PERT)
    assert cert.exponent == 3
    assert cert.effective_weight == Q(2, 3)
    assert cert.leading_coefficient()["exact"] == "1/432"
    assert cert.reduced == {4: Q(1, 4)}
    assert cert.omitted_base_exponent == 6
    assert cert.witness(0.06) == pytest.approx({"x": 0.005, "y": 0.1})


def test_certificate_matches_exact_global_upper_bound_and_feasible_lower_bound():
    cert = reduce_quadratic_channel(BASE, PERT)
    C = Q(cert.leading_coefficient()["exact"])
    for t in (Q(1, 10), Q(1, 100), Q(1, 1000)):
        s, x, y = 6 * t**2, t**2 / 2, t
        value = -evaluate(BASE, x, y) + s * evaluate(PERT, x, y)
        assert value == C * s**3 - s**6 / 12**6
        for u, v in ((t, t), (t / 2, t / 3), (Q(0), t), (t, Q(0))):
            residual = ((v**2 - s / 6)**2 * (v**2 + s / 12)
                        + s * (u - v**2 / 2)**2 + u**6)
            assert C * s**3 - (-evaluate(BASE, u, v) + s * evaluate(PERT, u, v)) == residual
            assert residual >= 0


@pytest.mark.parametrize("p,q,r", [(6, 6, 2), (8, 10, 3), (5, 7, 2), (9, 12, 4)])
def test_counterexample_family(p, q, r):
    cert = reduce_quadratic_channel({(p, 0): 1, (0, q): 1}, {(2, 0): -1, (1, r): 1})
    assert cert.exponent == Q(q, q - 2*r)
    assert cert.omitted_base_exponent > cert.exponent
    assert cert.to_dict()["checks"]["order_margin"] == p*r - q


def test_coefficients_and_base_amplitudes_are_not_assumed_to_be_one():
    cert = reduce_quadratic_channel({(7, 0): 17, (0, 6): 2}, {(2, 0): -2, (1, 2): 3})
    assert cert.reduced == {4: Q(9, 8)}
    assert cert.leading_coefficient()["exact"] == "27/512"


def test_both_axis_orientations_are_detected():
    cert = reduce_quadratic_channel(BASE, {(0, 2): -1, (2, 1): 1}, axes=("u", "v"))
    assert (cert.eliminated_axis, cert.retained_axis) == ("v", "u")
    assert cert.exponent == 3


def test_polynomial_driver_identity_with_mixed_sign_higher_terms():
    pert = {(2, 0): -2, (1, 2): 3, (1, 3): -1, (0, 5): 7, (0, 6): -1}
    cert = reduce_quadratic_channel(BASE, pert)
    for x, y in ((Q(1, 10), Q(1, 7)), (Q(2), Q(3)), (Q(0), Q(1))):
        H = sum(c * y**k for k, c in cert.driver.items())
        S = sum(c * y**k for k, c in cert.reduced.items())
        assert evaluate(pert, x, y) == S - 2 * (x - H / 4)**2


def test_reduced_cancellation_exposes_the_next_degree_exactly():
    cert = reduce_quadratic_channel(BASE, {**PERT, (0, 4): Q(-1, 4), (0, 5): 1})
    assert cert.reduced == {5: 1}
    assert cert.exponent == 6
    assert cert.leading_coefficient()["exact"] == "3125/46656"


def test_extra_y_fifth_power_does_not_hide_the_curved_cubic_response():
    cert = reduce_quadratic_channel(BASE, {**PERT, (0, 5): 1})
    assert cert.exponent == 3
    assert cert.leading_coefficient()["exact"] == "1/432"


@pytest.mark.parametrize("p,q,r", [(3, 6, 2), (3, 7, 2)])
def test_equal_or_dominant_omitted_base_cost_is_rejected(p, q, r):
    with pytest.raises(ReductionNotApplicable, match="omitted base cost is not subleading"):
        reduce_quadratic_channel({(p, 0): 1, (0, q): 1}, {(2, 0): -1, (1, r): 1})


@pytest.mark.parametrize("pert,reason", [
    ({(2, 0): -1, (1, 2): -1}, "not positive near the origin"),
    ({**PERT, (0, 4): Q(-1, 4)}, "no positive initial layer"),
    ({**PERT, (0, 4): -1}, "no positive initial layer"),
    ({(2, 0): -1, (1, 3): 1}, "strictly between"),
    ({**PERT, (3, 0): 1}, "requires -a"),
    ({(2, 0): -1, (1, 0): 1}, "requires -a"),
])
def test_unsupported_signs_shapes_and_criticality_remain_unresolved(pert, reason):
    with pytest.raises(ReductionNotApplicable, match=reason):
        reduce_quadratic_channel(BASE, pert)


def test_arbitrary_base_remainders_cannot_borrow_the_certificate():
    with pytest.raises(ReductionNotApplicable, match="full base loss"):
        reduce_quadratic_channel({**BASE, (1, 1): 1}, PERT)


def test_exact_expression_is_retained_when_amplitude_is_irrational():
    cert = reduce_quadratic_channel({(6, 0): 1, (0, 7): 1}, PERT)
    coefficient = cert.leading_coefficient()
    assert coefficient["exact"] == "(3/28) * (1/7)**(4/3)"
    assert coefficient["value"] == pytest.approx((3 / 28) * (1 / 7)**(4 / 3))


def test_tiny_rational_coefficients_are_not_cancelled_by_a_tolerance():
    tiny = Q(1, 10**400)
    cert = reduce_quadratic_channel(BASE, {(2, 0): -1, (1, 2): tiny})
    assert cert.exponent == 3
    assert cert.reduced[4] == tiny**2 / 4
    assert cert.leading_coefficient()["value"] is None


@pytest.mark.parametrize("signature", [(1,), (-1, 2), (True, 2), (1.0, 2)])
def test_invalid_exponents_are_rejected(signature):
    with pytest.raises(ValueError, match="nonnegative integer"):
        reduce_quadratic_channel(BASE, {signature: 1})
