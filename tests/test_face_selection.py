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
