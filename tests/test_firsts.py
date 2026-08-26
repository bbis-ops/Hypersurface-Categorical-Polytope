"""Tests for theorem bounds, vertex search, and certification."""

from __future__ import annotations

import unittest

from categorical_polytope.formal_bounds import (
    TheoremConstants,
    certify_suboptimality,
    epsilon_0_explicit,
)
from categorical_polytope.fisher_factorization import (
    BlockLayout,
    QuadraticJointObjective,
    build_block_fisher,
)
from categorical_polytope.fisher_pruned_search import FisherPrunedVertexSearch
from categorical_polytope.hypersurface_box import BoxBounds
from categorical_polytope.set_category import cardinality_obstruction
from categorical_polytope.vertex_probe import VertexProbeAlgorithm


class TestFormalBounds(unittest.TestCase):
    def test_phi_zero_at_zero(self) -> None:
        c = TheoremConstants(0.1, 1.0, 2.0, 2.0)
        self.assertEqual(c.Phi(0.0), 0.0)

    def test_certify_small_epsilon(self) -> None:
        c = TheoremConstants(epsilon_0=0.15, lambda_min_diag=1.0, theta_norm=2.0, frobenius_diag=2.0)
        ok, phi, _ = certify_suboptimality(0.05, 0.01, c)
        self.assertTrue(ok)
        self.assertGreater(phi, 0.0)

    def test_certify_fails_large_gap(self) -> None:
        c = TheoremConstants(epsilon_0=0.1, lambda_min_diag=1.0, theta_norm=2.0, frobenius_diag=2.0)
        ok, _, reason = certify_suboptimality(0.35, 1.5, c)
        self.assertFalse(ok)
        self.assertTrue("gap" in reason.lower() or "epsilon" in reason.lower())


class TestVertexSearch(unittest.TestCase):
    def test_corner_maximizer(self) -> None:
        probe = VertexProbeAlgorithm(cross_info_bound=0.25).find_near_optimal_probe()
        t = probe.theta
        self.assertAlmostEqual(t.lam, 1.0)
        self.assertAlmostEqual(t.sigma, 0.0)
        self.assertAlmostEqual(t.b, 2.0)
        self.assertAlmostEqual(t.k, 3.0)

    def test_coexponential_absent(self) -> None:
        r = cardinality_obstruction(2, 2)
        self.assertIn("mismatch", r.reason.lower())


class TestFactorization(unittest.TestCase):
    def test_exact_at_zero_coupling(self) -> None:
        layout = BlockLayout(("A", "B"), (2, 2))
        obj = QuadraticJointObjective(
            fisher=build_block_fisher(layout, off_diag_coupling=0.0),
            linear=(1.0, 0.5, 2.0, 3.0),
        )
        a = obj.factorization_analysis()
        self.assertAlmostEqual(a.gap, 0.0, places=6)

    def test_gap_grows_with_coupling(self) -> None:
        layout = BlockLayout(("A", "B"), (2, 2))
        gaps = []
        for c in (0.0, 0.15, 0.35):
            obj = QuadraticJointObjective(
                fisher=build_block_fisher(layout, off_diag_coupling=c),
                linear=(1.0, 0.5, 2.0, 3.0),
            )
            gaps.append(obj.factorization_analysis().gap)
        self.assertLessEqual(gaps[0], gaps[1])
        self.assertLess(gaps[1], gaps[2])


class TestPrunedSearch(unittest.TestCase):
    def test_pruned_matches_vertex_at_low_epsilon(self) -> None:
        r = FisherPrunedVertexSearch(
            fisher_epsilon=0.25,
            top_k=4,
            cross_info_bound=0.25,
        ).run()
        self.assertAlmostEqual(r.objective_value, r.full_vertex_value, places=4)

    def test_certification_strict_at_high_epsilon(self) -> None:
        r = FisherPrunedVertexSearch(fisher_epsilon=0.35, top_k=4).run()
        self.assertFalse(r.certified)


if __name__ == "__main__":
    unittest.main()
