"""Exact vertex-localization threshold: s* = 0 for face_bowl."""

from __future__ import annotations

import sys
import unittest
from math import pi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.hypersurface_box import Theta
from categorical_polytope.nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    grid_maximize,
    vertex_maximize,
)
from categorical_polytope.vertex_threshold import (
    InteractionOnly,
    displacement,
    displacement_asymptote,
    face_objective,
    gap_asymptote,
    grid_resolution_needed,
    grid_resolution_to_resolve,
    inward_curvatures,
    is_strictly_concave_on_face,
    optimality_gap,
    perturbation_threshold,
    screen_interactions,
    t_star,
    universal_gap,
    vertex_margin,
)

BOUNDS = default_nonlinear_bounds()
STRENGTHS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0)


def _obj(s: float) -> HypersurfacePlusInteraction:
    return HypersurfacePlusInteraction(BOUNDS, strength=s, interaction="face_bowl")


def _obj_mode(mode: str, s: float) -> HypersurfacePlusInteraction:
    return HypersurfacePlusInteraction(BOUNDS, strength=s, interaction=mode)


def _from_face(s: float, u: float, w: float) -> float:
    """Evaluate the real objective at the (u,w) face point, b and k at maxima."""
    return _obj(s)(Theta(u + 0.5, 0.5 - w, BOUNDS.b_max, BOUNDS.k_max))


class TestClosedForm(unittest.TestCase):
    def test_face_objective_matches_module(self) -> None:
        for s in STRENGTHS:
            for u in (-0.5, -0.17, 0.0, 0.3, 0.5):
                for w in (-0.5, 0.0, 0.42, 0.5):
                    self.assertAlmostEqual(
                        face_objective(s, u, w), _from_face(s, u, w), places=12
                    )

    def test_symmetric_in_u_w(self) -> None:
        for s in STRENGTHS:
            for u in (-0.5, -0.2, 0.11, 0.5):
                for w in (-0.5, 0.07, 0.33, 0.5):
                    self.assertAlmostEqual(
                        face_objective(s, u, w), face_objective(s, w, u), places=12
                    )

    def test_strictly_concave_for_all_s(self) -> None:
        for s in (0.0, *STRENGTHS, 10.0, 100.0):
            self.assertTrue(is_strictly_concave_on_face(s), msg=f"s={s}")


class TestCubicRoot(unittest.TestCase):
    def test_root_satisfies_cubic(self) -> None:
        for s in STRENGTHS:
            t = t_star(s)
            self.assertAlmostEqual(2 * s * t**3 - 2 * (1 + s) * t + 1, 0.0, places=10)
            self.assertGreaterEqual(t, 0.0)
            self.assertLessEqual(t, 0.5)

    def test_root_is_the_face_maximiser(self) -> None:
        """Fine 2-D sweep must not beat the diagonal cubic root."""
        for s in STRENGTHS:
            best = face_objective(s, t_star(s), t_star(s))
            n = 241
            for i in range(n):
                u = -0.5 + i / (n - 1)
                for j in range(n):
                    w = -0.5 + j / (n - 1)
                    self.assertLessEqual(face_objective(s, u, w), best + 1e-9)


class TestThresholdIsZero(unittest.TestCase):
    def test_gap_strictly_positive_for_every_s(self) -> None:
        """The headline claim: no positive threshold exists."""
        for s in (1e-6, 1e-4, 0.001, *STRENGTHS):
            self.assertGreater(optimality_gap(s), 0.0, msg=f"s={s}")
            self.assertGreater(displacement(s), 0.0, msg=f"s={s}")

    def test_gap_vanishes_only_at_zero(self) -> None:
        self.assertEqual(displacement(0.0), 0.0)
        self.assertAlmostEqual(optimality_gap(0.0), 0.0, places=12)

    def test_maximiser_beats_every_vertex(self) -> None:
        """Compare against the repo's own exhaustive ext(H) search."""
        for s in STRENGTHS:
            _, vval = vertex_maximize(_obj(s), BOUNDS)
            t = t_star(s)
            self.assertGreater(_from_face(s, t, t), vval)

    def test_base_vertex_is_degenerate(self) -> None:
        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        vm = vertex_margin(base, BOUNDS)
        self.assertTrue(vm.degenerate)
        self.assertAlmostEqual(vm.derivatives["lam"], 0.0, places=8)
        self.assertAlmostEqual(vm.derivatives["sigma"], 0.0, places=8)
        # b and k are strictly monotone, so those axes are not degenerate.
        self.assertAlmostEqual(vm.derivatives["b"], -1.0, places=6)
        self.assertAlmostEqual(vm.derivatives["k"], -1.0, places=6)

    def test_threshold_zero_from_general_criterion(self) -> None:
        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        bowl = HypersurfacePlusInteraction(BOUNDS, strength=1.0, interaction="face_bowl")
        self.assertEqual(perturbation_threshold(base, bowl, BOUNDS), 0.0)


class TestAsymptotics(unittest.TestCase):
    def test_displacement_leading_order_three_eighths(self) -> None:
        for s in (1e-5, 1e-4, 1e-3):
            self.assertAlmostEqual(displacement(s) / s, 0.375, places=3)

    def test_gap_leading_order_nine_thirtyseconds(self) -> None:
        for s in (1e-4, 1e-3, 1e-2):
            self.assertAlmostEqual(optimality_gap(s) / (s * s), 9.0 / 32.0, places=2)

    def test_pade_approximants_track_closely_for_small_s(self) -> None:
        for s in (0.01, 0.05, 0.1):
            self.assertLess(abs(displacement(s) - displacement_asymptote(s)), 2e-3)
            self.assertLess(abs(optimality_gap(s) - gap_asymptote(s)), 2e-4)


class TestGridBlindness(unittest.TestCase):
    def test_coarse_grid_misses_it(self) -> None:
        """steps=7 (the repo default) reports exactly zero gap at s=0.05."""
        s = 0.05
        obj = _obj(s)
        _, vval = vertex_maximize(obj, BOUNDS)
        _, gval = grid_maximize(obj, BOUNDS, steps=7)
        self.assertAlmostEqual(gval - vval, 0.0, places=12)
        self.assertGreater(optimality_gap(s), 0.0)

    def test_detection_threshold_is_exact(self) -> None:
        """n = ceil(1 + 1/(2 delta)) is the coarsest grid reporting any gap."""
        for s, expected in ((0.05, 29), (0.1, 15), (0.25, 7)):
            self.assertEqual(grid_resolution_needed(s), expected, msg=f"s={s}")
            obj = _obj(s)
            _, vval = vertex_maximize(obj, BOUNDS)
            _, below = grid_maximize(obj, BOUNDS, steps=expected - 1)
            self.assertAlmostEqual(below - vval, 0.0, places=12, msg=f"s={s}")

    def test_resolving_grid_recovers_the_gap(self) -> None:
        """The finer n >= 1 + 1/delta grid gets the magnitude roughly right."""
        s = 0.25
        self.assertEqual(grid_resolution_to_resolve(s), 13)
        obj = _obj(s)
        _, vval = vertex_maximize(obj, BOUNDS)
        _, fine = grid_maximize(obj, BOUNDS, steps=13)
        self.assertGreater(fine - vval, 0.9 * optimality_gap(s))

    def test_resolution_grows_like_one_over_s(self) -> None:
        self.assertGreater(grid_resolution_needed(0.01), 100)
        self.assertGreater(grid_resolution_needed(0.05), 25)
        self.assertLess(grid_resolution_needed(2.0), 6)


class TestUniversalLaw(unittest.TestCase):
    """Delta(s) = s^2 sum_i gamma_i^2/(2 c_i) reproduces every interaction mode."""

    CLOSED = {
        "bilinear": lambda s: s * s / 4.0,        # gamma=1 on sigma, c=2
        "trig": lambda s: pi * pi * s * s,        # gamma=2pi on lam, c=2
        "face_bowl": lambda s: 9.0 * s * s / 32.0,  # gamma=3/4 on lam and sigma
        "triple": lambda s: 0.0,
        "softplus": lambda s: 0.0,
    }

    def test_matches_closed_forms(self) -> None:
        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        for mode, closed in self.CLOSED.items():
            pert = InteractionOnly(BOUNDS, mode)
            for s in (0.005, 0.01):
                got, want = universal_gap(base, pert, BOUNDS, s), closed(s)
                if want == 0.0:
                    self.assertAlmostEqual(got, 0.0, places=12, msg=mode)
                else:
                    self.assertAlmostEqual(got / want, 1.0, places=4, msg=f"{mode} s={s}")

    def test_bilinear_gap_is_exact(self) -> None:
        """bilinear is exactly quadratic, so the leading order is the whole answer."""
        s = 0.02
        obj = _obj_mode("bilinear", s)
        _, vval = vertex_maximize(obj, BOUNDS)
        best = max(
            obj(Theta(1.0, j / 20000.0, BOUNDS.b_max, BOUNDS.k_max))
            for j in range(20001)
        )
        self.assertAlmostEqual(best - vval, s * s / 4.0, places=9)

    def test_screen_classifies_all_modes(self) -> None:
        rows = {m: (star, gap, breaks) for m, star, gap, breaks in screen_interactions()}
        for mode in ("bilinear", "trig", "face_bowl"):
            self.assertEqual(rows[mode][0], 0.0, msg=mode)
            self.assertTrue(rows[mode][2], msg=mode)
        for mode in ("triple", "softplus"):
            self.assertEqual(rows[mode][0], float("inf"), msg=mode)
            self.assertFalse(rows[mode][2], msg=mode)

    def test_curvature_of_default_r_is_two(self) -> None:
        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        curv = inward_curvatures(base, Theta(1.0, 0.0, BOUNDS.b_max, BOUNDS.k_max), BOUNDS)
        self.assertAlmostEqual(curv["lam"], 2.0, places=6)
        self.assertAlmostEqual(curv["sigma"], 2.0, places=6)


class TestDirectionalLaw(unittest.TestCase):
    """V.9: coupled perturbations follow the directional law, not the additive one."""

    def _measure(self, expr: str, s: float = 0.01) -> float:
        from categorical_polytope.interaction_search import Candidate, screen_candidate

        return screen_candidate(Candidate("t", expr), s=s).measured_gap

    def test_cone_and_kink_are_coupled(self) -> None:
        from categorical_polytope.interaction_search import compile_expression
        from categorical_polytope.vertex_threshold import is_coupled

        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        for expr in ("((1-lam)**2 + sigma**2)**0.5", "abs(sigma - (1-lam))"):
            pert = compile_expression(expr)
            self.assertTrue(is_coupled(base, pert, BOUNDS), msg=expr)

    def test_separable_is_not_coupled(self) -> None:
        from categorical_polytope.interaction_search import compile_expression
        from categorical_polytope.vertex_threshold import is_coupled

        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        for expr in ("sigma", "1-lam", "lam*sigma + b*k", "sin(pi*lam)"):
            pert = compile_expression(expr)
            self.assertFalse(is_coupled(base, pert, BOUNDS), msg=expr)

    def test_directional_law_matches_measured_when_coupled(self) -> None:
        from categorical_polytope.interaction_search import compile_expression
        from categorical_polytope.vertex_threshold import directional_gap

        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        for expr in ("((1-lam)**2 + sigma**2)**0.5", "abs(sigma - (1-lam))"):
            pert = compile_expression(expr)
            pred = directional_gap(base, pert, BOUNDS, 0.01)
            self.assertAlmostEqual(pred / self._measure(expr), 1.0, places=2, msg=expr)

    def test_additive_over_predicts_coupled_by_two(self) -> None:
        from categorical_polytope.interaction_search import compile_expression
        from categorical_polytope.vertex_threshold import directional_gap, universal_gap

        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        pert = compile_expression("((1-lam)**2 + sigma**2)**0.5")
        add = universal_gap(base, pert, BOUNDS, 0.01)
        dirc = directional_gap(base, pert, BOUNDS, 0.01)
        self.assertAlmostEqual(add / dirc, 2.0, places=2)

    def test_directional_reduces_to_additive_when_separable(self) -> None:
        from categorical_polytope.interaction_search import compile_expression
        from categorical_polytope.vertex_threshold import directional_gap, universal_gap

        base = HypersurfacePlusInteraction(BOUNDS, strength=0.0, interaction="bilinear")
        for expr in ("sigma", "sin(pi*lam)", "1-lam"):
            pert = compile_expression(expr)
            add = universal_gap(base, pert, BOUNDS, 0.01)
            dirc = directional_gap(base, pert, BOUNDS, 0.01)
            self.assertAlmostEqual(add, dirc, places=6, msg=expr)


if __name__ == "__main__":
    unittest.main()
