"""
Layer-2 confusion scorer: calibration and regression against the turn ramp.

The discriminating test is `test_separable_control_does_not_switch`. The legacy
ramp is a function of the turn index alone, so it fires the corner -> interior
mode switch at turn 5 no matter what the learner says. A measured scorer must
not: on a control dialogue where the learner never perceives any coupling, it
has to stay in CORNER_HUNTING. That contrast is what separates an instrument
from an illustration of one.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.category_tutor import (
    SCRIPTED_PROMPTS,
    CategoryLearningTutor,
)
from categorical_polytope.confusion_scorer import (
    LEDGER,
    LEDGER_BY_KEY,
    ConfusionScorer,
    Stance,
    detect_stance,
    score_dialogue,
    score_text,
)

# Reference: the turn at which the legacy ramp leaves CORNER_HUNTING on the
# canonical dialogue. Pinned so a geometry change cannot silently move it.
REFERENCE_SWITCH_TURN = 5

# A learner who stays separable throughout: every utterance either asserts a
# corner/factoring stance or engages nothing. Same length as SCRIPTED_PROMPTS.
SEPARABLE_CONTROL: tuple[str, ...] = (
    "Product and curry are clear to me.",
    "Coproduct is the disjoint union in Set.",
    "The blocks factor cleanly here.",
    "I will keep the separable decomposition.",
    "The maximum sits at a corner of the box.",
    "Vertex search is enough for this problem.",
    "Each block has independent structure.",
    "Corner probing certified the bound.",
)


def _switch_turn(prompts: tuple[str, ...], scorer: ConfusionScorer | None) -> int | None:
    """Turn index at which the tutor first recommends INTERIOR_SEARCH."""
    tutor = CategoryLearningTutor(score_confusion=scorer)
    tutor.run_scripted_dialogue(prompts)
    step = tutor.log.first_interior_step()
    return step.step if step else None


class TestRampReference(unittest.TestCase):
    """The baseline the scorer is calibrated against."""

    def test_ramp_reference_pinned(self) -> None:
        self.assertEqual(_switch_turn(SCRIPTED_PROMPTS, None), REFERENCE_SWITCH_TURN)

    def test_ramp_is_content_blind(self) -> None:
        """The ramp fires at the same turn on a dialogue with zero coupling."""
        self.assertEqual(
            _switch_turn(SEPARABLE_CONTROL, None),
            _switch_turn(SCRIPTED_PROMPTS, None),
        )


class TestScorerRegression(unittest.TestCase):
    def test_scripted_dialogue_reproduces_reference_switch(self) -> None:
        """Calibration: measured confusion must land the switch where the ramp did."""
        self.assertEqual(
            _switch_turn(SCRIPTED_PROMPTS, ConfusionScorer()),
            REFERENCE_SWITCH_TURN,
        )

    def test_separable_control_does_not_switch(self) -> None:
        """The discriminating test: content, not the turn counter, drives the switch."""
        self.assertIsNotNone(
            _switch_turn(SEPARABLE_CONTROL, None),
            "precondition: the ramp does switch on the control dialogue",
        )
        self.assertIsNone(
            _switch_turn(SEPARABLE_CONTROL, ConfusionScorer()),
            "measured scorer must stay in CORNER_HUNTING on a separable learner",
        )

    def test_control_coupling_decays(self) -> None:
        scorer = score_dialogue(SEPARABLE_CONTROL)
        traj = scorer.summary()["trajectory"]
        self.assertLess(traj[-1], traj[0])
        self.assertEqual(scorer.summary()["misconceptions"], [])

    def test_scripted_coupling_rises(self) -> None:
        scorer = score_dialogue(SCRIPTED_PROMPTS)
        traj = scorer.summary()["trajectory"]
        self.assertGreater(traj[-1], 4.0 * traj[0])

    def test_default_tutor_behaviour_unchanged(self) -> None:
        """No scorer supplied -> the legacy ramp, exactly as before."""
        tutor = CategoryLearningTutor()
        tutor.run_scripted_dialogue()
        for i, turn in enumerate(tutor.turns):
            self.assertAlmostEqual(turn.confusion, min(0.95, 0.05 + i * 0.04))

    def test_explicit_confusion_overrides_scorer(self) -> None:
        tutor = CategoryLearningTutor(score_confusion=ConfusionScorer())
        turn = tutor.process_turn("Cross-naturality couples my blocks.", confusion=0.42)
        self.assertAlmostEqual(turn.confusion, 0.42)


class TestScorerProperties(unittest.TestCase):
    def test_deterministic(self) -> None:
        a = score_dialogue(SCRIPTED_PROMPTS).summary()["trajectory"]
        b = score_dialogue(SCRIPTED_PROMPTS).summary()["trajectory"]
        self.assertEqual(a, b)

    def test_bounded(self) -> None:
        loud = ("Cross-naturality couples my blocks!",) * 40
        for value in score_dialogue(loud).summary()["trajectory"]:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 0.95)

    def test_reset_restores_initial_state(self) -> None:
        scorer = ConfusionScorer()
        first = scorer("Cross-naturality couples my blocks.")
        scorer.reset()
        self.assertEqual(scorer.history, [])
        self.assertAlmostEqual(scorer("Cross-naturality couples my blocks."), first)

    def test_empty_and_offtopic_text_is_inert(self) -> None:
        raw, commitment, accuracy, engagements = score_text("Thanks, that helps.")
        self.assertEqual(raw, 0.0)
        self.assertEqual(engagements, ())
        self.assertEqual(commitment, 0.0)
        self.assertEqual(accuracy, 1.0)


class TestStanceDetection(unittest.TestCase):
    def test_assert_deny_question_absent(self) -> None:
        prop = LEDGER_BY_KEY["max_at_corner"]
        cases = {
            "The maximum sits at a corner.": Stance.ASSERT,
            "The best point is not at a corner.": Stance.DENY,
            "Should I stay at the corner?": Stance.QUESTION,
            "Adjoint functors reverse arrows.": Stance.ABSENT,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertIs(detect_stance(text, prop), expected)

    def test_coproduct_does_not_match_product(self) -> None:
        """Word boundaries must keep `coproduct` out of the CCC proposition."""
        ccc = LEDGER_BY_KEY["ccc_curry"]
        self.assertIs(detect_stance("Coproduct is a disjoint union.", ccc), Stance.ABSENT)

    def test_sentiment_negation_counts_as_denial(self) -> None:
        prop = LEDGER_BY_KEY["max_at_corner"]
        text = "I keep trying corners but they feel wrong."
        self.assertIs(detect_stance(text, prop), Stance.DENY)


class TestAdjudication(unittest.TestCase):
    def test_false_presupposition_is_a_misconception(self) -> None:
        """'Where is the coexponential?' presupposes a claim Set refutes."""
        scorer = score_dialogue(SCRIPTED_PROMPTS)
        self.assertIn("coexp_exists", scorer.summary()["misconceptions"])
        self.assertIn("arrow_reversal", scorer.summary()["misconceptions"])

    def test_coupling_and_error_are_orthogonal(self) -> None:
        """High coupling with zero error: correctly perceiving entanglement."""
        raw, _, accuracy, engagements = score_text(
            "Cross-naturality seems to mix my blocks."
        )
        self.assertGreater(raw, 0.4)
        self.assertEqual(accuracy, 1.0)
        self.assertFalse(any(e.erroneous for e in engagements))

    def test_context_dependent_props_are_never_errors(self) -> None:
        for prop in LEDGER:
            if prop.truth is None:
                for text in ("The max is at a corner.", "The max is not at a corner."):
                    _, _, accuracy, _ = score_text(text)
                    self.assertEqual(accuracy, 1.0)

    def test_every_proposition_names_a_local_witness(self) -> None:
        for prop in LEDGER:
            with self.subTest(key=prop.key):
                self.assertTrue(prop.witness.strip())
                self.assertTrue(prop.patterns)


if __name__ == "__main__":
    unittest.main()
