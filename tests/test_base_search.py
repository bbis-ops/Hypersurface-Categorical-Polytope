"""V.12 master law: gap exponent 2m/(2m-alpha) as the BASE flatness order varies."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.base_search import (
    BUILTIN_BASES,
    Candidate,
    CustomBase,
    base_flatness_order,
    screen_base,
    screen_bases,
)
from categorical_polytope.interaction_search import compile_expression
from categorical_polytope.nonlinear_objective import default_nonlinear_bounds
from categorical_polytope.vertex_threshold import vertex_maximize

BOUNDS = default_nonlinear_bounds()


class TestFlatnessOrder(unittest.TestCase):
    def test_recovers_even_orders(self) -> None:
        corner, _ = vertex_maximize(CustomBase(compile_expression("-(1-lam)**2 - sigma**2")), BOUNDS)
        for p in (2, 4, 6, 8):
            base = CustomBase(compile_expression(f"-(1-lam)**{p} - sigma**{p}"))
            got = base_flatness_order(base, corner, BOUNDS, "lam")
            self.assertAlmostEqual(got, float(p), places=1, msg=f"order {p}")

    def test_strict_corner_reports_order_one(self) -> None:
        base = CustomBase(compile_expression("lam - sigma"))
        corner, _ = vertex_maximize(base, BOUNDS)
        # linear slope -> the "drop" is linear -> order ~ 1 (not a flat corner)
        self.assertAlmostEqual(base_flatness_order(base, corner, BOUNDS, "lam"), 1.0, places=1)


class TestMasterLaw(unittest.TestCase):
    def test_builtin_bases_match_prediction(self) -> None:
        rows = {r.candidate.name: r for r in screen_bases()}
        for name, order, p in (("quadratic", 2, 2.0), ("quartic", 4, 4 / 3),
                               ("sextic", 6, 6 / 5), ("mixed_24", 4, 4 / 3)):
            r = rows[name]
            self.assertTrue(r.breaks, msg=name)
            self.assertAlmostEqual(r.flatness_order, order, places=1, msg=name)
            self.assertAlmostEqual(r.predicted_exponent, p, places=3, msg=name)
            self.assertTrue(r.law_holds, msg=f"{name}: meas {r.measured_exponent}")

    def test_flatter_base_breaks_harder(self) -> None:
        """Larger flatness order -> smaller exponent -> bigger gap for small s."""
        rows = {r.candidate.name: r for r in screen_bases()}
        self.assertGreater(rows["quadratic"].predicted_exponent,
                           rows["quartic"].predicted_exponent)
        self.assertGreater(rows["quartic"].predicted_exponent,
                           rows["sextic"].predicted_exponent)

    def test_strict_corner_does_not_break(self) -> None:
        for name in ("strict", "strict_curved"):
            r = screen_base({c.name: c for c in BUILTIN_BASES}[name])
            self.assertTrue(r.ok)
            self.assertFalse(r.breaks, msg=name)
            self.assertFalse(r.base_self_fails, msg=name)

    def test_exponent_reduces_to_v7_at_quadratic(self) -> None:
        r = {x.candidate.name: x for x in screen_bases()}["quadratic"]
        self.assertAlmostEqual(r.predicted_exponent, 2.0, places=6)


class TestOddOrderAndSelfFailure(unittest.TestCase):
    """The two model-surfaced findings: odd flatness order, and base self-failure."""

    def test_odd_order_three(self) -> None:
        """beta need not be even: |x|^3 gives order 3, exponent 3/2."""
        r = screen_base({c.name: c for c in BUILTIN_BASES}["odd_cubic"])
        self.assertTrue(r.ok and r.breaks)
        self.assertAlmostEqual(r.flatness_order, 3.0, places=1)
        self.assertAlmostEqual(r.predicted_exponent, 1.5, places=3)
        self.assertTrue(r.law_holds)

    def test_non_integer_orders(self) -> None:
        for beta, p in ((2.5, 5 / 3), (3.5, 3.5 / 2.5)):
            r = screen_base(Candidate("t", f"-(abs(1-lam))**{beta} - (abs(sigma))**{beta}"))
            self.assertAlmostEqual(r.flatness_order, beta, places=1, msg=str(beta))
            self.assertAlmostEqual(r.predicted_exponent, p, places=2, msg=str(beta))
            self.assertTrue(r.law_holds, msg=str(beta))

    def test_small_coefficient_base_uses_adaptive_strength(self) -> None:
        r = screen_base(Candidate(
            "tiny_cubic", "1-sinh(0.01*(1-lam))**3-sinh(0.01*sigma)**3"
        ))
        self.assertAlmostEqual(r.flatness_order, 3.0, places=2)
        self.assertAlmostEqual(r.measured_exponent, 1.5, places=2)
        self.assertTrue(r.law_holds)

    def test_essential_term_does_not_contaminate_deep_order(self) -> None:
        r = screen_base(Candidate(
            "essential", "1-(1-lam)**5-sigma**3-exp(-1/((1-lam)+sigma+0.000000001))"
        ))
        self.assertAlmostEqual(r.flatness_order, 5.0, places=2)
        self.assertTrue(r.law_holds)

    def test_base_self_fails_on_interior_max(self) -> None:
        r = screen_base({c.name: c for c in BUILTIN_BASES}["interior_max"])
        self.assertTrue(r.ok)
        self.assertTrue(r.base_self_fails)
        self.assertTrue(r.breaks)

    def test_ordinary_base_does_not_self_fail(self) -> None:
        for name in ("quadratic", "quartic", "sextic"):
            r = screen_base({c.name: c for c in BUILTIN_BASES}[name])
            self.assertFalse(r.base_self_fails, msg=name)


class TestUnifiedLaw(unittest.TestCase):
    """V.14: p=1/(1-q), including beta/(beta-alpha) as the isotropic case."""

    def _screen(self, base_expr: str, pert_expr: str):
        from categorical_polytope.base_search import combined_screen
        return combined_screen(Candidate("b", base_expr), Candidate("p", pert_expr))

    def test_grid_of_combinations(self) -> None:
        cases = [
            ("-(1-lam)**2 - sigma**2", "sigma", 2.0),
            ("-(1-lam)**2 - sigma**2", "sqrt(sigma)", 4 / 3),
            ("-(1-lam)**4 - sigma**4", "sigma", 4 / 3),
            ("-(1-lam)**4 - sigma**4", "sqrt(sigma)", 8 / 7),
            ("-(1-lam)**6 - sigma**6", "sigma**0.3333333333333333", 6 / 5.6666666666),
        ]
        for base_expr, pert_expr, p in cases:
            r = self._screen(base_expr, pert_expr)
            self.assertTrue(r.ok and r.breaks, msg=f"{base_expr} x {pert_expr}")
            self.assertAlmostEqual(r.predicted_exponent, p, places=2,
                                   msg=f"{base_expr} x {pert_expr}")
            self.assertTrue(r.law_holds, msg=f"meas {r.measured_exponent} vs {p}")

    def test_isotropic_coupling_changes_coefficient_not_exponent(self) -> None:
        """On an isotropic base, coupling does not alter the exponent."""
        lin = self._screen("-(1-lam)**4 - sigma**4", "sigma")
        cone = self._screen("-(1-lam)**4 - sigma**4", "((1-lam)**2+sigma**2)**0.5")
        self.assertAlmostEqual(lin.measured_exponent, cone.measured_exponent, places=1)

    def test_anisotropic_base_uses_flatter_pushed_axis(self) -> None:
        # base flat order 2 in lam, 6 in sigma; a sigma-perturbation sees beta=6
        r = self._screen("-(1-lam)**2 - sigma**6", "sqrt(sigma)")
        self.assertAlmostEqual(r.beta, 6.0, places=1)
        self.assertAlmostEqual(r.alpha, 0.5, places=1)
        self.assertTrue(r.law_holds)

    def test_anisotropic_coupling_uses_weighted_degree(self) -> None:
        # q=(1/2)/2+(1/2)/6=1/3, hence p=1/(1-q)=3/2.  The old
        # coordinate-axis rule incorrectly predicted p=2 from the separate x term.
        r = self._screen("-(1-lam)**2 - sigma**6",
                         "b*sqrt((1-lam)*sigma) + k*(1-lam)")
        self.assertEqual(r.active_axes, ("lam", "sigma"))
        self.assertAlmostEqual(r.weighted_degree, 1 / 3, places=2)
        self.assertAlmostEqual(r.predicted_exponent, 1.5, places=2)
        self.assertTrue(r.law_holds,
                        msg=f"meas {r.measured_exponent} vs {r.predicted_exponent}")

    def test_unpenalized_base_face_is_outside_weighted_law(self) -> None:
        r = self._screen("-(1-lam)**8", "k*sqrt(sigma)+(1-lam)**0.9")
        self.assertTrue(r.ok)
        self.assertFalse(r.breaks)
        self.assertIn("non-coercive", r.reason)

    def test_cusp_cancellation_ray_does_not_fake_weighted_degree(self) -> None:
        r = self._screen("-(1-lam)**2-sigma**2",
                         "(b+k)*abs(1-lam-sigma)**0.5")
        self.assertAlmostEqual(r.weighted_degree, 0.25, places=2)
        self.assertAlmostEqual(r.predicted_exponent, 4 / 3, places=2)
        self.assertTrue(r.law_holds)

    def test_pair_parser_drops_unsafe(self) -> None:
        from categorical_polytope.base_search import parse_pairs
        reply = ('{"pairs":[{"name":"ok","base":"-(1-lam)**2 - sigma**2","pert":"sqrt(sigma)"},'
                 '{"name":"evil","base":"__import__(\'os\')","pert":"sigma"}]}')
        got = parse_pairs(reply)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0].expr, "-(1-lam)**2 - sigma**2")


class TestSafety(unittest.TestCase):
    def test_hostile_base_rejected(self) -> None:
        r = screen_base(Candidate("evil", "__import__('os').system('x')"))
        self.assertFalse(r.ok)
        self.assertFalse(r.breaks)


if __name__ == "__main__":
    unittest.main()
