"""Tests for non-quadratic objectives and empirical Fisher."""

from __future__ import annotations

import unittest

from categorical_polytope.nonlinear_objective import (
    HypersurfacePlusInteraction,
    NonlinearStudy,
    default_nonlinear_bounds,
    empirical_fisher_at,
    vertex_maximize,
)


class TestNonlinear(unittest.TestCase):
    def test_zero_strength_matches_quadratic_regime(self) -> None:
        a = NonlinearStudy().analyze(strength=0.0, interaction="bilinear")
        self.assertAlmostEqual(a.gap, 0.0, places=3)
        self.assertTrue(a.localization_at_vertex)

    def test_empirical_fisher_psd_diagonal(self) -> None:
        obj = HypersurfacePlusInteraction(default_nonlinear_bounds(), strength=0.1)
        theta, _ = vertex_maximize(obj, default_nonlinear_bounds())
        fisher = empirical_fisher_at(obj, theta, default_nonlinear_bounds())
        for i in range(fisher.layout.n):
            self.assertGreater(fisher.matrix[i][i], 0.0)

    def test_bilinear_small_gap(self) -> None:
        a = NonlinearStudy().analyze(strength=0.1, interaction="bilinear")
        self.assertLess(a.gap, 0.5)

    def test_face_bowl_breaks_vertex_localization(self) -> None:
        a = NonlinearStudy().analyze(strength=1.5, interaction="face_bowl")
        self.assertIsNotNone(a.gap_vs_grid)
        self.assertGreater(a.gap_vs_grid or 0.0, 0.05)
        self.assertFalse(a.localization_at_vertex)


if __name__ == "__main__":
    unittest.main()
