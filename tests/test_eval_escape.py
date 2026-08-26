"""Evaluation-escape model: coverage theorem + the six conditional claims."""

from __future__ import annotations

import random
import sys
import unittest
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.eval_escape import (
    Claim,
    adversarial_miss_radius,
    all_claims,
    grid_miss_radius,
    samples_to_catch,
    unit_ball_volume,
)


class TestCoverageTheorem(unittest.TestCase):
    def test_grid_actually_misses_ball_below_bound(self) -> None:
        """A grid in d=2 misses a ball just under the miss-radius, catches one above."""
        for m in (4, 6, 8):
            n = m * m
            r, mm = grid_miss_radius(n, 2)
            self.assertEqual(mm, m)
            pts = [(i / (m - 1), j / (m - 1)) for i in range(m) for j in range(m)]
            cell_center = (1 / (m - 1) / 2, 1 / (m - 1) / 2)

            def missed(radius: float) -> bool:
                return all(
                    (p[0] - cell_center[0]) ** 2 + (p[1] - cell_center[1]) ** 2 > radius * radius
                    for p in pts
                )

            self.assertTrue(missed(r * 0.98), msg=f"m={m}")
            self.assertFalse(missed(r * 1.10), msg=f"m={m}")

    def test_samples_exponential_in_dimension(self) -> None:
        prev = 0
        for d in (1, 2, 3, 5, 10):
            n = samples_to_catch(0.05, d)
            self.assertGreater(n, prev)
            prev = n
        self.assertGreater(samples_to_catch(0.05, 20), 10**30)
        self.assertEqual(samples_to_catch(0.05, 1), 11)
        self.assertEqual(samples_to_catch(0.05, 20), 46**20)

    def test_samples_catch_is_sufficient(self) -> None:
        """The prescribed n really does drive the grid miss-radius below delta."""
        for d, delta in ((1, 0.05), (2, 0.1), (3, 0.15)):
            n = samples_to_catch(delta, d)
            r, _ = grid_miss_radius(n, d)
            self.assertLessEqual(r, delta + 1e-9, msg=f"d={d}")

    def test_adversarial_bound_shrinks_slowly_in_high_d(self) -> None:
        # For fixed n, the missable radius stays large as d grows (curse of dim).
        self.assertGreater(adversarial_miss_radius(10**6, 10), 0.1)
        self.assertLess(adversarial_miss_radius(10**6, 1), 1e-5)

    def test_arbitrary_sample_bound_is_volume_bound(self) -> None:
        self.assertAlmostEqual(unit_ball_volume(1), 2.0)
        self.assertAlmostEqual(unit_ball_volume(2), 3.141592653589793)
        self.assertAlmostEqual(adversarial_miss_radius(10, 1), 0.05)
        self.assertAlmostEqual(
            adversarial_miss_radius(50, 2),
            (1.0 / (50.0 * 3.141592653589793)) ** 0.5,
        )

    def test_invalid_coverage_parameters_rejected(self) -> None:
        for n, d in ((0, 1), (1, 0), (-1, 2)):
            with self.assertRaises(ValueError):
                adversarial_miss_radius(n, d)
            with self.assertRaises(ValueError):
                grid_miss_radius(n, d)
        with self.assertRaises(ValueError):
            samples_to_catch(0.0, 2)

    def test_covering_radius_lower_bounds_any_sample(self) -> None:
        """Random samples cannot beat the covering-radius bound in d=2."""
        random.seed(0)
        n = 50
        pts = [(random.random(), random.random()) for _ in range(n)]
        bound = adversarial_miss_radius(n, 2)
        # some cell of a fine grid must be at least `bound` from every sample
        worst = 0.0
        g = 200
        for i in range(g + 1):
            for j in range(g + 1):
                x, y = i / g, j / g
                nearest = min(sqrt((x - a) ** 2 + (y - b) ** 2) for a, b in pts)
                worst = max(worst, nearest)
        self.assertGreater(worst, bound * 0.8)


class TestClaims(unittest.TestCase):
    def test_six_modes_present(self) -> None:
        claims = all_claims()
        self.assertEqual(len(claims), 6)
        for c in claims:
            self.assertIsInstance(c, Claim)
            for field in (c.model_assumption, c.proven, c.quantitative,
                          c.operational, c.ethical):
                self.assertTrue(field and isinstance(field, str))

    def test_every_claim_labels_its_assumption(self) -> None:
        # The honesty contract: each claim must state a MODEL assumption.
        for c in all_claims():
            self.assertGreater(len(c.model_assumption), 10, msg=c.mode)

    def test_render_includes_all_facets(self) -> None:
        text = "\n".join(all_claims()[0].render())
        for tag in ("MODEL assumption", "Proven", "Quantitative", "Operational", "Ethical"):
            self.assertIn(tag, text)


if __name__ == "__main__":
    unittest.main()
