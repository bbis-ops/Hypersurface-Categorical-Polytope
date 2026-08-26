"""Tests for the Newton-tropical master law (V.15 sharp constant, V.16 selection).

Every closed form is checked against `orthant_gap`, an independent direct
maximization over the nonneg orthant. Stdlib `unittest` only.
"""

from __future__ import annotations

import unittest

from categorical_polytope.newton_tropical import (
    Monomial,
    measured_exponent,
    newton_tropical_face,
    orthant_gap,
    sharp_gap_constant,
    sharp_single_axis_gap,
    tropical_exponent,
    tropical_gap_leading,
)


class TestSharpConstant(unittest.TestCase):
    """V.15: Delta(s) ~ C s^p to machine precision on one flat axis."""

    def test_face_bowl_per_axis_constant(self):
        # face_bowl pushes gamma=3/4 on each of lam, sigma over a beta=2 base.
        p, C = sharp_gap_constant(1.0, 2.0, 0.75, 1.0)
        self.assertAlmostEqual(p, 2.0, places=12)
        self.assertAlmostEqual(C, 9.0 / 64.0, places=12)  # two axes -> 9/32 (V.4)

    def test_bilinear_exact(self):
        p, C = sharp_gap_constant(1.0, 2.0, 1.0, 1.0)
        self.assertAlmostEqual(p, 2.0, places=12)
        self.assertAlmostEqual(C, 0.25, places=12)  # bilinear s^2/4

    def test_constant_matches_direct_maximization(self):
        cases = [
            (1.0, 2.0, 0.75, 1.0),
            (0.5, 2.0, 1.0, 1.0),
            (1.0, 3.0, 1.0, 1.0),
            (0.5, 6.0, 2.0, 1.0),
            (1.5, 4.0, 0.9, 2.0),
        ]
        s = 1e-4
        for alpha, beta, gamma, A in cases:
            predicted = sharp_single_axis_gap(alpha, beta, gamma, A, s)
            measured = orthant_gap({"x": beta}, [Monomial(gamma, {"x": alpha})], s, A={"x": A})
            self.assertAlmostEqual(measured / predicted, 1.0, delta=3e-3,
                                   msg=f"(alpha={alpha}, beta={beta}, gamma={gamma}, A={A})")

    def test_two_axes_add(self):
        # Independent flat axes contribute additively (V.7 / V.15 additivity).
        s = 1e-4
        P = [Monomial(0.75, {"x": 1.0}), Monomial(0.75, {"y": 1.0})]
        base = {"x": 2.0, "y": 2.0}
        gap, exact = tropical_gap_leading(P, base, s)
        self.assertTrue(exact)
        measured = orthant_gap(base, P, s)
        self.assertAlmostEqual(measured / gap, 1.0, delta=3e-3)
        self.assertAlmostEqual(gap / s ** 2, 9.0 / 32.0, places=9)


class TestTropicalSelection(unittest.TestCase):
    """V.16: the least base-weighted degree sets the exponent; amplitude does not."""

    def test_min_weighted_degree_wins(self):
        base = {"x": 2.0, "y": 6.0}
        P = [
            Monomial(1.0, {"x": 0.5, "y": 0.5}),  # q = 1/3
            Monomial(1.0, {"x": 1.0}),            # q = 1/2
            Monomial(1.0, {"y": 1.0}),            # q = 1/6  <- winner
        ]
        face = newton_tropical_face(P, base)
        self.assertAlmostEqual(face.q_star, 1.0 / 6.0, places=9)
        self.assertAlmostEqual(face.exponent, 1.2, places=9)
        self.assertEqual(len(face.winners), 1)
        self.assertEqual(face.winners[0].powers, {"y": 1.0})

    def test_exponent_matches_measured_slope(self):
        base = {"x": 2.0}
        P = [Monomial(3.0, {"x": 0.5}), Monomial(1.0, {"x": 1.0})]  # min q = 1/4 -> p = 4/3
        p = tropical_exponent(P, base)
        self.assertAlmostEqual(p, 4.0 / 3.0, places=9)
        # measured slope converges to p from above; at s in [1e-6,1e-4] within ~1%.
        self.assertAlmostEqual(measured_exponent(base, P, s_hi=1e-4, s_lo=1e-6), p, delta=0.02)

    def test_weaker_but_more_singular_term_dominates(self):
        # 100*x (q=1/2, p=2) vs 0.001*sqrt(x) (q=1/4, p=4/3): the weak term wins.
        base = {"x": 2.0}
        P = [Monomial(100.0, {"x": 1.0}), Monomial(0.001, {"x": 0.5})]
        face = newton_tropical_face(P, base)
        self.assertAlmostEqual(face.q_star, 0.25, places=9)
        self.assertAlmostEqual(face.exponent, 4.0 / 3.0, places=9)
        self.assertEqual(face.winners[0].powers, {"x": 0.5})

    def test_coupled_face_exponent_matches(self):
        # r = -x^2 - y^6, P = 2*sqrt(x*y) + 3*x : weighted degrees q(sqrt(xy))=1/3,
        # q(x)=1/2 -> the coupled sqrt term wins, p = 1/(1-1/3) = 3/2 (V.14 row).
        base = {"x": 2.0, "y": 6.0}
        P = [Monomial(2.0, {"x": 0.5, "y": 0.5}), Monomial(3.0, {"x": 1.0})]
        face = newton_tropical_face(P, base)
        self.assertAlmostEqual(face.exponent, 1.5, places=9)
        self.assertFalse(face.separable)
        self.assertAlmostEqual(measured_exponent(base, P, s_hi=1e-4, s_lo=1e-6), 1.5, delta=0.03)

    def test_coupled_constant_matches_direct(self):
        # Constant obtained via the reduced projective maximisation vs direct.
        base = {"x": 2.0, "y": 2.0}
        P = [Monomial(1.0, {"x": 0.5, "y": 0.5})]  # cone-like coupled monomial
        s = 1e-4
        gap, exact = tropical_gap_leading(P, base, s)
        self.assertFalse(exact)
        measured = orthant_gap(base, P, s)
        self.assertAlmostEqual(measured / gap, 1.0, delta=1e-2)


class TestGuards(unittest.TestCase):
    def test_no_singular_term_raises(self):
        # A perturbation that only pushes at order >= base (q >= 1) opens no gap.
        with self.assertRaises(ValueError):
            newton_tropical_face([Monomial(1.0, {"x": 2.0})], {"x": 2.0})

    def test_alpha_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            sharp_gap_constant(2.0, 2.0, 1.0, 1.0)  # alpha == beta
        with self.assertRaises(ValueError):
            sharp_gap_constant(1.0, 2.0, -1.0, 1.0)  # gamma <= 0


if __name__ == "__main__":
    unittest.main()
