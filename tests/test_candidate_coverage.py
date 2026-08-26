from math import sqrt

import pytest

from categorical_polytope.candidate_coverage import (
    REGISTERED_FAMILIES,
    ParameterAxis,
    cartesian_covering_radius,
    cartesian_unit_grid,
    coverage_certificate_status,
    family_by_law,
)


def test_axis_normalization_linear_and_log():
    assert ParameterAxis("x", 2.0, 6.0).value(0.25) == 3.0
    assert ParameterAxis("x", 1.0, 100.0, "log10").value(0.5) == pytest.approx(10.0)


def test_cartesian_grid_and_exact_radius():
    points = cartesian_unit_grid(2, 3)
    assert len(points) == 9
    assert (0.0, 0.0) in points and (1.0, 1.0) in points
    assert cartesian_covering_radius(2, 3) == pytest.approx(sqrt(2) / 4)


def test_registered_laws_are_complete_and_bounded():
    assert [family.law for family in REGISTERED_FAMILIES] == [f"V.{i}" for i in range(7, 15)]
    for family in REGISTERED_FAMILIES:
        assert family.dimension >= 1
        assert all(axis.lower < axis.upper for axis in family.axes)
        assert family_by_law(family.law) is family


def test_registered_fixtures_reach_verifier():
    # One central point per law is enough to guard formula construction here;
    # the full Cartesian campaign is exercised by run_candidate_coverage.py.
    for family in REGISTERED_FAMILIES:
        record = family.evaluate([0.5] * family.dimension)
        assert record.law == family.law
        assert record.status in {"verified", "counterexample", "outside_scope", "inconclusive", "rejected"}


def test_invalid_grid_configuration_fails_closed():
    with pytest.raises(ValueError):
        cartesian_unit_grid(2, 1)
    with pytest.raises(ValueError):
        cartesian_covering_radius(0, 3)


def test_certificate_decision_fails_closed():
    assert coverage_certificate_status({"verified": 9}) == ("CONDITIONAL PASS under R(rho)", 0)
    status, unresolved = coverage_certificate_status({"verified": 8, "outside_scope": 1})
    assert status.startswith("WITHHELD") and unresolved == 1
    status, unresolved = coverage_certificate_status({"counterexample": 1, "inconclusive": 2})
    assert status.startswith("NUMERICAL SURVIVOR") and unresolved == 2
