from categorical_polytope.base_search import Candidate
from categorical_polytope.verification_campaign import verify_base, verify_combined, verify_interaction


def test_v7_fixture_verifies():
    assert verify_interaction("V.7", Candidate("linear", "sigma")).status == "verified"


def test_v8_and_v10_fixtures_verify():
    assert verify_interaction("V.8", Candidate("sqrt", "sqrt(sigma)")).status == "verified"
    assert verify_interaction("V.10", Candidate("three_halves", "sigma**1.5")).status == "verified"


def test_v10_higher_order_distraction_stays_at_local_scale():
    row = verify_interaction(
        "V.10", Candidate("distracted", "sigma**1.35-(1-lam)**1.35+sin(b*k*sigma**2)")
    )
    assert row.status == "verified", row.metrics


def test_v10_uses_fractional_prediction_when_generic_screen_marks_coupled():
    row = verify_interaction(
        "V.10", Candidate("live_s11", "sigma**1.1 + sigma**2.1*cos(k)")
    )
    assert row.status == "verified", row.metrics
    assert abs(row.metrics["predicted_exponent"] - 2.0 / 0.9) < 0.01


def test_v10_quadratic_distractions_do_not_bias_local_alpha():
    fixtures = [
        "(1-lam)**1.65*atan(abs(k))/(1+abs(k))+(1-lam)**2*lam",
        "sigma**1.65 + (1-lam)**1.65 - tanh(k*sigma**2)",
    ]
    for index, expr in enumerate(fixtures):
        row = verify_interaction("V.10", Candidate(f"live_165_{index}", expr))
        assert row.status == "verified", (expr, row.metrics)
        assert abs(row.metrics["theorem_alpha"] - 1.65) < 0.02


def test_complex_fractional_candidate_is_rejected_not_raised():
    row = verify_interaction("V.8", Candidate("complex", "(1-lam-2*sigma)**0.5"))
    assert row.status == "rejected"


def test_v9_fixture_verifies():
    row = verify_interaction("V.9", Candidate("cone", "((1-lam)**2+sigma**2)**0.5"))
    assert row.status == "verified"


def test_v9_global_polar_measurement_crosses_crease_branches():
    fixtures = [
        "abs(4*(1-lam)-7*sigma)",
        "abs(abs(2*(1-lam))-3*sigma)",
        "abs(sqrt(2)*(1-lam)-sqrt(3)*sigma)",
    ]
    for index, expr in enumerate(fixtures):
        row = verify_interaction("V.9", Candidate(f"crease_{index}", expr))
        assert row.status == "verified", (expr, row.metrics)
        assert abs(row.metrics["measured_exponent_asymptotic"] - 2.0) < 0.02


def test_v12_and_v13_fixtures_verify():
    assert verify_base("V.12", Candidate("quartic", "-(1-lam)**4-sigma**4")).status == "verified"
    assert verify_base("V.13", Candidate("inside", "-((1-lam)-0.25)**2-(sigma-0.35)**2")).status == "verified"


def test_v13_adversarial_guard_catches_narrow_and_aliased_peaks():
    fixtures = [
        "exp(-50000*((lam-0.03)**2+(sigma-0.03)**2))",
        "sin(16*pi*lam)*sin(16*pi*sigma)",
    ]
    for index, expr in enumerate(fixtures):
        row = verify_base("V.13", Candidate(f"guard_{index}", expr))
        assert row.status == "verified"
        assert row.metrics["legacy_grid_missed"] is True


def test_v14_fixture_verifies():
    row = verify_combined(Candidate("pair_b", "-(1-lam)**4-sigma**4"), Candidate("pair_p", "sqrt(sigma)"))
    assert row.status == "verified"


def test_v14_anisotropic_coupled_survivor_is_resolved_by_weighted_law():
    row = verify_combined(
        Candidate("aniso_b", "-(1-lam)**2-sigma**6"),
        Candidate("aniso_p", "b*sqrt((1-lam)*sigma)+k*(1-lam)"),
    )
    assert row.status == "verified"
    assert abs(row.metrics["weighted_degree"] - 1 / 3) < 0.01
    assert abs(row.metrics["predicted_exponent"] - 1.5) < 0.02


def test_v14_diagonal_cusp_ignores_zero_coefficient_ray():
    row = verify_combined(
        Candidate("cusp_b", "-(1-lam)**2-sigma**2"),
        Candidate("cusp_p", "(b+k)*abs(1-lam-sigma)**0.5"),
    )
    assert row.status == "verified"
    assert abs(row.metrics["weighted_degree"] - 0.25) < 0.01
