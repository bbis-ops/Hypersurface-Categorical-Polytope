"""Candidate screening, expression whitelist, and the fractional exponent law."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.hypersurface_box import Theta
from categorical_polytope.interaction_search import (
    BUILTIN_CANDIDATES,
    Candidate,
    UnsafeExpression,
    compile_expression,
    parse_proposals,
    screen_all,
    screen_candidate,
)
from categorical_polytope.vertex_threshold import fractional_exponent_law, gap_exponent

HOSTILE = (
    "__import__('os').system('echo pwned')",
    "open('/etc/passwd').read()",
    "(lambda: 1)()",
    "lam.__class__.__mro__",
    "sigma if lam else b",
    "[x for x in (1,2)]",
    "globals()",
    "lam := 3",
    "exec('1')",
    "lam**999",
    "unknown_name",
    "sigma; b",
)


class TestWhitelist(unittest.TestCase):
    def test_hostile_input_is_rejected(self) -> None:
        for expr in HOSTILE:
            with self.assertRaises(UnsafeExpression, msg=expr):
                compile_expression(expr)

    def test_legitimate_expressions_compile(self) -> None:
        for expr in ("sigma", "lam*sigma + b*k", "sin(pi*lam)*cos(pi*sigma)*b",
                     "sqrt(sigma)", "exp(-lam)", "(1-(lam-0.5)**2)"):
            fn = compile_expression(expr)
            self.assertIsInstance(fn(Theta(1.0, 0.25, 2.0, 3.0)), float)

    def test_evaluation_matches_arithmetic(self) -> None:
        fn = compile_expression("lam*sigma + b*k")
        self.assertAlmostEqual(fn(Theta(0.5, 0.4, 2.0, 3.0)), 0.5 * 0.4 + 2.0 * 3.0)

    def test_over_long_expression_rejected(self) -> None:
        with self.assertRaises(UnsafeExpression):
            compile_expression("sigma+" * 200 + "sigma")


class TestProposalParsing(unittest.TestCase):
    def test_drops_unsafe_keeps_valid(self) -> None:
        reply = """{"candidates":[
            {"name":"good","expr":"sqrt(sigma)","why":"non-smooth"},
            {"name":"evil","expr":"__import__('os').system('x')","why":"nope"},
            {"name":"ok2","expr":"lam*sigma"}]}"""
        got = parse_proposals(reply)
        self.assertEqual([c.expr for c in got], ["sqrt(sigma)", "lam*sigma"])
        self.assertTrue(all(c.source == "model" for c in got))

    def test_garbage_yields_nothing(self) -> None:
        for reply in ("not json at all", "{}", '{"candidates": "nope"}', ""):
            self.assertEqual(parse_proposals(reply), [])

    def test_extracts_json_from_prose(self) -> None:
        self.assertEqual(
            [c.expr for c in parse_proposals('here you go {"candidates":[{"expr":"sigma"}]} done')],
            ["sigma"],
        )


class TestScreen(unittest.TestCase):
    def test_builtin_bank_classification(self) -> None:
        rows = {r.candidate.name: r for r in screen_all(s=0.01)}
        for name in ("bilinear", "trig", "face_bowl", "linear_sigma", "sqrt_sigma"):
            self.assertTrue(rows[name].breaks, msg=name)
        for name in ("triple", "sigma_sq", "cos_pi_sigma"):
            self.assertFalse(rows[name].breaks, msg=name)

    def test_quadratic_law_holds_for_quadratic_regime(self) -> None:
        for r in screen_all(s=0.01):
            if r.ok and r.regime in ("quadratic", "coupled"):
                self.assertTrue(r.law_holds, msg=f"{r.candidate.name} {r.measured_gap}")

    def test_nonsmooth_flagged_and_not_fitted(self) -> None:
        for name in ("sqrt_sigma", "cbrt_sigma"):
            r = {x.candidate.name: x for x in screen_all(s=0.01)}[name]
            self.assertFalse(r.smooth, msg=name)
            self.assertEqual(r.regime, "fractional", msg=name)
            self.assertFalse(r.law_holds, msg=name)

    def test_nonsmooth_beats_every_quadratic_candidate(self) -> None:
        """Fractional (alpha<1) terms open a bigger gap than any quadratic one."""
        rows = screen_all(s=0.01)
        worst_quadratic = max(
            r.measured_gap for r in rows if r.ok and r.regime in ("quadratic", "coupled")
        )
        for name in ("sqrt_sigma", "cbrt_sigma"):
            r = {x.candidate.name: x for x in rows}[name]
            self.assertGreater(r.measured_gap, worst_quadratic, msg=name)

    def test_unsafe_candidate_is_rejected_not_run(self) -> None:
        r = screen_candidate(Candidate("evil", "__import__('os').system('x')"))
        self.assertFalse(r.ok)
        self.assertFalse(r.breaks)

    def test_push_on_non_flat_axis_does_not_break(self) -> None:
        """abs(b-2) pushes inward on b, but b is not flat: no gap, not coupled."""
        r = screen_candidate(Candidate("b_kink", "abs(b-2)"), s=0.01)
        self.assertTrue(r.ok)
        self.assertFalse(r.breaks)
        self.assertFalse(r.coupled)
        self.assertEqual(r.predicted_gap, 0.0)

    def test_coupled_candidate_scored_by_directional_law(self) -> None:
        """Model-proposed cone/kink terms: additive over-predicts, directional holds."""
        for expr in ("((1-lam)**2 + sigma**2)**0.5", "abs(sigma - (1-lam))"):
            r = screen_candidate(Candidate("c", expr), s=0.01)
            self.assertTrue(r.ok and r.breaks and r.smooth, msg=expr)
            self.assertTrue(r.coupled, msg=expr)
            self.assertTrue(r.law_holds, msg=expr)
            self.assertGreater(r.predicted_gap, r.directional_gap, msg=expr)
            self.assertAlmostEqual(
                r.measured_gap / r.directional_gap, 1.0, places=2, msg=expr
            )


class TestFractionalExponentLaw(unittest.TestCase):
    def test_matches_measurement(self) -> None:
        for alpha in (1.0, 0.75, 0.5, 1.0 / 3.0, 0.25):
            _, pred = fractional_exponent_law(alpha, 0.01)
            got = screen_candidate(
                Candidate(f"a{alpha:.3f}", f"sigma**{alpha!r}"), s=0.01
            ).measured_gap
            self.assertAlmostEqual(got / pred, 1.0, places=3, msg=f"alpha={alpha}")

    def test_exponent_interpolates(self) -> None:
        self.assertAlmostEqual(gap_exponent(1.0), 2.0)
        self.assertAlmostEqual(gap_exponent(0.5), 4.0 / 3.0)
        self.assertAlmostEqual(gap_exponent(1.0 / 3.0), 1.2)
        self.assertLess(gap_exponent(0.01), 1.02)

    def test_recovers_quadratic_law_at_alpha_one(self) -> None:
        """alpha=1, gamma=1, c=2 must give s^2/4, the bilinear closed form."""
        for s in (0.005, 0.01, 0.02):
            _, gap = fractional_exponent_law(1.0, s)
            self.assertAlmostEqual(gap, s * s / 4.0, places=12)

    def test_smaller_alpha_gives_bigger_gap(self) -> None:
        s = 0.01
        gaps = [fractional_exponent_law(a, s)[1] for a in (1.0, 0.75, 0.5, 0.25)]
        self.assertEqual(gaps, sorted(gaps))

    def test_rejects_bad_parameters(self) -> None:
        for alpha in (0.0, -0.5, 2.0, 2.5):
            with self.assertRaises(ValueError):
                fractional_exponent_law(alpha, 0.01)

    def test_law_extends_to_c1_regime(self) -> None:
        """V.10: 1 < alpha < 2 (C^1 but not C^2) follows the same exponent."""
        from categorical_polytope.vertex_threshold import gap_exponent

        for alpha in (1.25, 1.5, 1.75):
            self.assertAlmostEqual(gap_exponent(alpha), 2.0 / (2.0 - alpha))
            _, gap = fractional_exponent_law(alpha, 0.01)
            self.assertGreater(gap, 0.0)
        # exponent strictly increasing past 2 as alpha rises through (1,2)
        self.assertGreater(gap_exponent(1.75), gap_exponent(1.5))
        self.assertGreater(gap_exponent(1.5), 2.0)


class TestRegimeClassification(unittest.TestCase):
    """The screen sorts breakers into quadratic / coupled / fractional / saturating."""

    def _regime(self, expr: str) -> str:
        return screen_candidate(Candidate("t", expr), s=0.01).regime

    def test_regimes(self) -> None:
        self.assertEqual(self._regime("sigma"), "quadratic")
        self.assertEqual(self._regime("sin(pi*lam)*cos(pi*sigma)*b"), "quadratic")
        self.assertEqual(self._regime("((1-lam)**2 + sigma**2)**0.5"), "coupled")
        self.assertEqual(self._regime("sqrt(sigma)"), "fractional")
        self.assertEqual(self._regime("sigma**1.5"), "fractional")
        self.assertEqual(self._regime("atan(sigma/((1-lam)+0.002))"), "saturating")
        self.assertEqual(self._regime("sigma**2"), "safe")

    def test_saturating_prediction_exceeds_amplitude(self) -> None:
        r = screen_candidate(Candidate("atan", "atan(sigma/((1-lam)+0.002))"), s=0.01)
        self.assertTrue(r.saturating)
        self.assertGreater(r.best_prediction, r.amp_bound)
        self.assertLessEqual(r.measured_gap, r.amp_bound * 1.05)

    def test_fractional_alpha_recovered(self) -> None:
        self.assertAlmostEqual(
            screen_candidate(Candidate("t", "sqrt(sigma)"), s=0.01).alpha, 0.5, places=1
        )
        self.assertAlmostEqual(
            screen_candidate(Candidate("t", "sigma**1.5"), s=0.01).alpha, 1.5, places=1
        )

    def test_remote_gate_is_finite_scale_not_asymptotic_violation(self) -> None:
        expr = (
            "tanh(50*(0.95-lam))*tanh(50*(0.05-sigma))*(b/2)*(k/3)"
        )
        coarse = screen_candidate(Candidate("cliff", expr), s=0.01)
        asymptotic = screen_candidate(Candidate("cliff", expr), s=0.00125)
        self.assertEqual(coarse.regime, "finite-scale")
        self.assertEqual(asymptotic.regime, "quadratic")
        self.assertTrue(asymptotic.law_holds)
        self.assertLess(abs(asymptotic.measured_gap / asymptotic.best_prediction - 1.0), 0.1)


if __name__ == "__main__":
    unittest.main()
