"""Tests for concrete evaluation-design recommendations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.eval_design import (
    anisotropic_grid,
    distributional_samples,
    distributional_miss_bound,
    lipschitz_certificate,
    mixed_space_grid_samples,
    shift_robust_distributional_samples,
)


class TestAnisotropicGrid(unittest.TestCase):
    def test_linf_counts_each_axis(self) -> None:
        design = anisotropic_grid((0.05, 0.10), norm="linf")
        self.assertEqual(design.points_per_axis, (11, 6))
        self.assertEqual(design.total_points, 66)

    def test_l2_reduces_to_existing_one_dimensional_count(self) -> None:
        design = anisotropic_grid((0.05,), norm="l2")
        self.assertEqual(design.points_per_axis, (11,))

    def test_invalid_grid_inputs(self) -> None:
        for radii in ((), (0.0,), (-0.1, 0.2)):
            with self.assertRaises(ValueError):
                anisotropic_grid(radii)
        with self.assertRaises(ValueError):
            anisotropic_grid((0.1,), norm="l1")


class TestAlternativeEvalStructures(unittest.TestCase):
    def test_distributional_exact_miss_probability(self) -> None:
        n = distributional_samples(0.01, 0.05)
        self.assertAlmostEqual(distributional_miss_bound(n, 0.01), 0.99**n)
        self.assertLessEqual((1.0 - 0.01) ** n, 0.05)
        self.assertGreater((1.0 - 0.01) ** (n - 1), 0.05)

    def test_distributional_sensitivity_and_shift(self) -> None:
        noisy = distributional_samples(0.01, 0.05, detection_sensitivity=0.8)
        self.assertLessEqual((1.0 - 0.008) ** noisy, 0.05)
        shifted = shift_robust_distributional_samples(0.01, 0.05, 5.0)
        self.assertLessEqual((1.0 - 0.002) ** shifted, 0.05)

    def test_lipschitz_margin_certificate(self) -> None:
        safe = lipschitz_certificate(-0.2, 2.0, 0.05)
        unsafe = lipschitz_certificate(-0.05, 2.0, 0.05)
        self.assertTrue(safe.certified)
        self.assertAlmostEqual(safe.global_upper_bound, -0.1)
        self.assertFalse(unsafe.certified)

    def test_mixed_space_requires_each_stratum(self) -> None:
        self.assertEqual(mixed_space_grid_samples(7, 1, 0.05), 7 * 11)

    def test_invalid_probabilities_and_constants(self) -> None:
        for mu, alpha in ((0.0, 0.1), (1.0, 0.1), (0.1, 0.0), (0.1, 1.0)):
            with self.assertRaises(ValueError):
                distributional_samples(mu, alpha)
        with self.assertRaises(ValueError):
            lipschitz_certificate(0.0, -1.0, 0.1)
        with self.assertRaises(ValueError):
            distributional_samples(0.1, 0.1, detection_sensitivity=0.0)
        with self.assertRaises(ValueError):
            distributional_miss_bound(-1, 0.1)
        with self.assertRaises(ValueError):
            shift_robust_distributional_samples(0.1, 0.1, 0.5)
        with self.assertRaises(ValueError):
            mixed_space_grid_samples(0, 2, 0.1)


if __name__ == "__main__":
    unittest.main()
