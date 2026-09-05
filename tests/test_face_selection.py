"""Executable specification of the simple-vertex face-selection law."""

from __future__ import annotations

import unittest
from fractions import Fraction

from categorical_polytope.face_selection import (
    BasePower,
    EdgeCoordinateChart,
    FaceSelectionProblem,
    FaceStatus,
    HypothesisStatus,
    LawHypotheses,
    PerturbationMonomial,
    PolynomialPerturbation,
    PositivityWitness,
    WeightedPrincipalPart,
    infer_weight_from_exponent,
    tilted_simplex_problem,
)


LICENSED = LawHypotheses(
    local_base_maximality=HypothesisStatus.VERIFIED,
    uniform_principal_remainder=HypothesisStatus.VERIFIED,
    global_isolation=HypothesisStatus.VERIFIED,
)


def _orthant_problem(
    terms: tuple[PerturbationMonomial, ...],
    *,
    orders: tuple[int, int] = (4, 2),
    hypotheses: LawHypotheses = LICENSED,
) -> FaceSelectionProblem:
    return FaceSelectionProblem(
        chart=EdgeCoordinateChart(
            vertex=(0.0, 0.0),
            generators={"x": (1.0, 0.0), "y": (0.0, 1.0)},
        ),
        principal=WeightedPrincipalPart(
            {"x": BasePower(1.0, orders[0]), "y": BasePower(1.0, orders[1])}
        ),
        perturbation=PolynomialPerturbation(terms),
        hypotheses=hypotheses,
    )


class TestTiltedSimplex(unittest.TestCase):
    def test_complete_selection_pipeline(self) -> None:
        problem = tilted_simplex_problem(hypotheses=LICENSED)
        result = problem.select()

        self.assertEqual(result.q_star, Fraction(1, 4))
        self.assertEqual(result.response_exponent, Fraction(4, 3))
        self.assertTrue(result.theorem_licensed)
        self.assertEqual(result.minimal_winning_faces, (frozenset({"c1"}),))
        self.assertEqual(
            result.analysis_for({"c2"}).status,
            FaceStatus.NO_SURVIVING_MONOMIAL,
        )
        self.assertEqual(
            result.analysis_for({"c1", "c2"}).status,
            FaceStatus.ADMISSIBLE,
        )

    def test_chart_and_anisotropic_homogeneity(self) -> None:
        problem = tilted_simplex_problem()
        self.assertEqual(problem.chart.point({"c1": 0.2, "c2": 0.3}), (0.2, 0.5))
        z = {"c1": 0.7, "c2": 1.3}
        tau = 0.03
        dilated = problem.principal.dilate(tau, z)
        self.assertAlmostEqual(
            problem.principal.evaluate(dilated),
            tau * problem.principal.evaluate(z),
            places=12,
        )

    def test_exact_stationary_profile(self) -> None:
        problem = tilted_simplex_problem(hypotheses=LICENSED)
        face = problem.select().analysis_for({"c1"})
        profile = problem.stationary_profile(face, 1e-3)
        expected = 3.0 / (4.0 ** (4.0 / 3.0))
        self.assertAlmostEqual(profile.coefficient, expected, places=12)
        self.assertAlmostEqual(profile.leading_value, expected * 1e-4, places=15)
        self.assertEqual(profile.exponent, Fraction(4, 3))


class TestFaceAlgebra(unittest.TestCase):
    def test_minimum_weight_wins_after_face_restriction(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(1e6, {"y": 1}),  # q=1/2
                PerturbationMonomial(1e-6, {"x": 1}),  # q=1/4, winner
            )
        )
        result = problem.select()
        self.assertEqual(result.q_star, Fraction(1, 4))
        self.assertEqual(result.minimal_winning_faces, (frozenset({"x"}),))

    def test_coupled_monomial_uses_full_dimensional_face(self) -> None:
        problem = _orthant_problem(
            (PerturbationMonomial(1.0, {"x": 1, "y": 1}),),
            orders=(4, 4),
        )
        result = problem.select()
        self.assertEqual(result.q_star, Fraction(1, 2))
        self.assertEqual(result.winning_faces, (frozenset({"x", "y"}),))
        self.assertEqual(result.response_exponent, Fraction(2))

    def test_cancelled_lowest_layer_is_recomputed(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(1.0, {"x": 1}),
                PerturbationMonomial(-1.0, {"x": 1}),
                PerturbationMonomial(2.0, {"x": 2}),
            )
        )
        analysis = problem.select().analysis_for({"x"})
        self.assertEqual(analysis.status, FaceStatus.ADMISSIBLE)
        self.assertEqual(analysis.cancelled_degrees, (Fraction(1, 4),))
        self.assertEqual(analysis.degree, Fraction(1, 2))

    def test_wholly_cancelled_face_is_not_active(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(1.0, {"x": 1}),
                PerturbationMonomial(-1.0, {"x": 1}),
            )
        )
        analysis = problem.select().analysis_for({"x"})
        self.assertEqual(analysis.status, FaceStatus.CANCELLED_INITIAL_FORM)
        self.assertIsNone(analysis.degree)

    def test_nonpositive_face_is_inactive(self) -> None:
        problem = _orthant_problem((PerturbationMonomial(-2.0, {"x": 1}),))
        analysis = problem.select().analysis_for({"x"})
        self.assertEqual(analysis.status, FaceStatus.NON_POSITIVE)

    def test_curved_positive_channel_is_not_discarded(self) -> None:
        # Along x=y**2/2, -x**2+x*y**2=y**4/4. The true gap is
        # s**3/432 + O(s**6), despite every face initial form being <= 0.
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(1, {"x": 1, "y": 2}),
        ), orders=(6, 6)).select()
        self.assertIsNone(result.q_star)
        self.assertFalse(result.theorem_licensed)
        self.assertEqual(result.analysis_for({"x", "y"}).status,
                         FaceStatus.HIGHER_ORDER_UNRESOLVED)
        self.assertEqual(len(result.unresolved_faces), 1)
        self.assertTrue(any("higher_order_unresolved" in b for b in result.scope_blockers))

    def test_exact_curved_channel_upper_bound_and_witness(self) -> None:
        # All arithmetic is rational. Taking s=6*t**2 makes the sharp
        # witness y=t, x=t**2/2 rational as well.
        for t in (Fraction(1, 10), Fraction(1, 100), Fraction(1, 1000)):
            s = 6 * t**2
            upper = s**3 / 432
            for x, y in ((t**2 / 2, t), (t, t / 2), (Fraction(0), t), (t, Fraction(0))):
                value = -x**6 - y**6 + s * (-x**2 + x * y**2)
                certificate = (upper - (y**2 - s / 6)**2 * (y**2 + s / 12)
                               - s * (x - y**2 / 2)**2 - x**6)
                self.assertEqual(value, certificate)
                self.assertLessEqual(value, upper)
            x, y = s / 12, t
            lower = -x**6 - y**6 + s * (-x**2 + x * y**2)
            self.assertEqual(lower, upper - s**6 / 12**6)
            self.assertGreater(lower, 0)
            self.assertLess(1 - lower / upper, s**3)

    def test_curved_channel_blocks_an_incorrect_selected_exponent(self) -> None:
        # y**5 alone predicts exponent 6; the curved channel has exponent 3.
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(1, {"x": 1, "y": 2}),
            PerturbationMonomial(1, {"y": 5}),
        ), orders=(6, 6)).select()
        self.assertEqual(result.response_exponent, Fraction(6))
        self.assertFalse(result.theorem_licensed)
        self.assertTrue(result.unresolved_faces)

    def test_divisible_positive_remainder_is_absorbed(self) -> None:
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(100, {"x": 3, "y": 1}),
        ), orders=(6, 6)).select()
        self.assertFalse(result.unresolved_faces)
        self.assertEqual(result.analysis_for({"x", "y"}).status, FaceStatus.NON_POSITIVE)

    def test_selected_degree_controls_positive_remainders(self) -> None:
        # R <= y**3 gives the upper bound; x=0 gives the matching lower bound.
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(1, {"y": 3}),
        ), orders=(6, 6)).select()
        self.assertEqual(result.response_exponent, Fraction(2))
        self.assertTrue(result.theorem_licensed)

    def test_cancelled_higher_layer_does_not_create_an_obstruction(self) -> None:
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(1, {"x": 1, "y": 2}),
            PerturbationMonomial(-1, {"x": 1, "y": 2}),
        ), orders=(6, 6)).select()
        self.assertFalse(result.unresolved_faces)

    def test_critical_positive_remainder_is_bounded_by_base_cost(self) -> None:
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(1, {"x": 1, "y": 5}),
        ), orders=(6, 6)).select()
        self.assertFalse(result.unresolved_faces)

    def test_interior_zero_locus_remains_unresolved(self) -> None:
        result = _orthant_problem((
            PerturbationMonomial(-1, {"x": 2}),
            PerturbationMonomial(2, {"x": 1, "y": 1}),
            PerturbationMonomial(-1, {"y": 2}),
            PerturbationMonomial(1, {"x": 3}),
        ), orders=(4, 4)).select()
        self.assertFalse(result.theorem_licensed)
        self.assertEqual(result.analysis_for({"x", "y"}).status,
                         FaceStatus.POSITIVITY_UNRESOLVED)

    def test_mixed_sign_binomial_gets_constructive_evidence(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(-2.0, {"x": 1}),
                PerturbationMonomial(1.0, {"y": 2}),
            ),
            orders=(4, 8),  # both terms have q=1/4
        )
        full = frozenset({"x", "y"})
        automatic = problem.select()
        resolved = automatic.analysis_for(full)
        self.assertEqual(resolved.status, FaceStatus.ADMISSIBLE)
        self.assertEqual(
            resolved.witness.provenance,
            "mixed-sign binomial ratio certificate",
        )
        self.assertGreater(resolved.initial_form.evaluate(resolved.witness.coordinates), 0)
        self.assertTrue(automatic.theorem_licensed)

        result = problem.select(
            positivity_witnesses={
                full: PositivityWitness({"x": 0.1, "y": 1.0}, "analytic witness")
            }
        )
        resolved = result.analysis_for(full)
        self.assertEqual(resolved.status, FaceStatus.ADMISSIBLE)
        self.assertEqual(resolved.witness.provenance, "analytic witness")
        self.assertTrue(result.theorem_licensed)

    def test_general_mixed_sign_form_remains_unresolved(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(-1.0, {"x": 2}),
                PerturbationMonomial(1.0, {"x": 1, "y": 2}),
                PerturbationMonomial(-1.0, {"y": 4}),
            ),
            orders=(4, 8),  # every term has q=1/2
        )
        analysis = problem.select().analysis_for({"x", "y"})
        self.assertEqual(analysis.status, FaceStatus.POSITIVITY_UNRESOLVED)
        self.assertIn("positivity is unresolved", problem.select().scope_blockers[0])

    def test_invalid_witness_is_rejected(self) -> None:
        problem = _orthant_problem(
            (
                PerturbationMonomial(-2.0, {"x": 1}),
                PerturbationMonomial(1.0, {"y": 2}),
            ),
            orders=(4, 8),
        )
        full = frozenset({"x", "y"})
        with self.assertRaisesRegex(ValueError, "initial form positive"):
            problem.select(positivity_witnesses={full: {"x": 1.0, "y": 1.0}})

    def test_relevance_classes_are_explicit(self) -> None:
        zero = _orthant_problem((PerturbationMonomial(1.0, {}),))
        critical = _orthant_problem((PerturbationMonomial(1.0, {"y": 2}),))
        subleading = _orthant_problem((PerturbationMonomial(1.0, {"y": 3}),))
        self.assertEqual(zero.select().analysis_for({"x"}).status, FaceStatus.ZERO_WEIGHT)
        self.assertEqual(
            critical.select().analysis_for({"y"}).status, FaceStatus.CRITICAL
        )
        self.assertEqual(
            subleading.select().analysis_for({"y"}).status, FaceStatus.SUBLEADING
        )


class TestScopeAndValidation(unittest.TestCase):
    def test_prediction_does_not_imply_theorem_license(self) -> None:
        result = tilted_simplex_problem().select()
        self.assertEqual(result.response_exponent, Fraction(4, 3))
        self.assertFalse(result.theorem_licensed)
        self.assertEqual(len(result.scope_blockers), 3)
        self.assertIn("conditional/unlicensed", result.conclusion())

    def test_assumptions_license_conditional_use_but_remain_visible(self) -> None:
        assumed = LawHypotheses(
            local_base_maximality=HypothesisStatus.ASSUMED,
            uniform_principal_remainder=HypothesisStatus.ASSUMED,
            global_isolation=HypothesisStatus.ASSUMED,
        )
        result = tilted_simplex_problem(hypotheses=assumed).select()
        self.assertTrue(result.theorem_licensed)
        self.assertTrue(all(status is HypothesisStatus.ASSUMED for _, status in assumed.items()))

    def test_nonsimple_chart_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not simple"):
            EdgeCoordinateChart(
                vertex=(0.0, 0.0),
                generators={"x": (1.0, 0.0), "duplicate": (2.0, 0.0)},
            )

    def test_chart_and_principal_axes_must_match(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly the same axes"):
            FaceSelectionProblem(
                chart=EdgeCoordinateChart(
                    vertex=(0.0,), generators={"x": (1.0,)}
                ),
                principal=WeightedPrincipalPart({"y": BasePower(1.0, 2)}),
                perturbation=PolynomialPerturbation(
                    (PerturbationMonomial(1.0, {"x": 1}),)
                ),
            )

    def test_inverse_law_is_exact(self) -> None:
        self.assertEqual(infer_weight_from_exponent(Fraction(4, 3)), Fraction(1, 4))
        with self.assertRaises(ValueError):
            infer_weight_from_exponent(1)


if __name__ == "__main__":
    unittest.main()
