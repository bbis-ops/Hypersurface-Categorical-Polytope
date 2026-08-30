"""
Loop closure with the coupling coordinate measured instead of self-reported.

The learner protocol asks the model to emit its own `confusion` value, so the
geometry has been driven by a self-assessment with nothing to check it against.
Scoring the learner's prose against the proposition ledger gives an independent
estimate, and the gap between the two is itself a reading: the calibration
error of self-report.

The discriminating test is `test_overclaiming_learner_does_not_close`. A learner
that reports mounting confusion while saying only separable, corner-consistent
things closes the loop under self-report and must not close it under measurement.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.confusion_scorer import ConfusionScorer
from categorical_polytope.loop_closure import (
    LearnerDiagramReport,
    LoopClosureSession,
    loop_closure_markdown,
    scripted_learner,
)

# Closure turns on the scripted arc, pinned so a change of either the ledger or
# the geometry has to be acknowledged rather than absorbed.
SELF_REPORT_CLOSURE = 3
MEASURED_CLOSURE = 4


def _overclaiming_learner(turn: int, prompt: str) -> LearnerDiagramReport:
    """Reports mounting confusion while its prose stays entirely separable."""
    return LearnerDiagramReport.from_json(
        {
            "lam": 1.0,
            "sigma": 0.0,
            "b": 2.0,
            "k": 3.0,
            "confusion": min(0.9, 0.10 + turn * 0.12),
            "topic": "separable",
            "quote": "The blocks factor cleanly and the maximum sits at a corner.",
        }
    )


def _session(scorer: ConfusionScorer | None, learner=scripted_learner) -> LoopClosureSession:
    sess = LoopClosureSession(learner_fn=learner, score_confusion=scorer)
    sess.run()
    return sess


class TestSelfReportBaseline(unittest.TestCase):
    def test_default_is_self_report(self) -> None:
        sess = _session(None)
        self.assertEqual(sess.summary()["confusion_source"], "self_report")
        self.assertIsNone(sess.divergence())
        for turn in sess.turns:
            self.assertIsNone(turn.confusion_measured)

    def test_scripted_closure_pinned(self) -> None:
        self.assertEqual(_session(None).closure_turn(), SELF_REPORT_CLOSURE)

    def test_self_report_closes_on_an_overclaiming_learner(self) -> None:
        """Precondition for the discriminating test below."""
        self.assertIsNotNone(_session(None, _overclaiming_learner).closure_turn())


class TestMeasuredRun(unittest.TestCase):
    def test_summary_marks_the_source(self) -> None:
        self.assertEqual(
            _session(ConfusionScorer()).summary()["confusion_source"], "measured"
        )

    def test_measured_closure_pinned(self) -> None:
        self.assertEqual(_session(ConfusionScorer()).closure_turn(), MEASURED_CLOSURE)

    def test_loop_still_closes_when_measured(self) -> None:
        """Proposition H.3 must survive losing the self-reported coordinate."""
        self.assertIsNotNone(_session(ConfusionScorer()).closure_turn())

    def test_measurement_delays_closure_on_the_scripted_arc(self) -> None:
        """The arc's own words lag the confusion it declares."""
        self.assertGreater(
            _session(ConfusionScorer()).closure_turn(),
            _session(None).closure_turn(),
        )

    def test_overclaiming_learner_does_not_close(self) -> None:
        """The discriminating test: prose, not the declared number, drives the loop."""
        self.assertIsNone(
            _session(ConfusionScorer(), _overclaiming_learner).closure_turn(),
            "a learner saying only separable things must not reach INTERIOR_SEARCH",
        )

    def test_reported_value_is_preserved(self) -> None:
        """A measured run stays comparable to a self-reported one."""
        measured = _session(ConfusionScorer())
        baseline = _session(None)
        for lhs, rhs in zip(measured.turns, baseline.turns):
            self.assertAlmostEqual(lhs.confusion_reported, rhs.confusion_reported)
            self.assertIsNotNone(lhs.confusion_measured)


class TestDivergence(unittest.TestCase):
    def test_scripted_arc_overclaims_throughout(self) -> None:
        div = _session(ConfusionScorer()).divergence()
        self.assertIsNotNone(div)
        self.assertEqual(div["underclaims"], 0)
        self.assertEqual(div["overclaims"], div["n_pairs"])
        self.assertGreater(div["mean_abs_error"], 0.0)

    def test_divergence_arrays_align(self) -> None:
        div = _session(ConfusionScorer()).divergence()
        self.assertEqual(len(div["reported"]), len(div["measured"]))
        self.assertLessEqual(div["mean_abs_error"], div["max_abs_error"])

    def test_worst_turn_is_a_real_turn(self) -> None:
        sess = _session(ConfusionScorer())
        div = sess.divergence()
        self.assertIn(div["worst_turn"], [t.turn for t in sess.turns])


class TestReportOverride(unittest.TestCase):
    def test_to_state_override_replaces_only_the_coupling(self) -> None:
        report = LearnerDiagramReport.from_json(
            {"lam": 0.8, "sigma": 0.3, "b": 2, "k": 3, "confusion": 0.9,
             "topic": "t", "quote": "q"}
        )
        state = report.to_state(0.12)
        self.assertAlmostEqual(state.interaction_strength, 0.12)
        self.assertAlmostEqual(state.lam, 0.8)
        self.assertAlmostEqual(state.sigma, 0.3)

    def test_to_state_override_is_clamped(self) -> None:
        report = scripted_learner(0, "")
        self.assertAlmostEqual(report.to_state(5.0).interaction_strength, 1.0)
        self.assertAlmostEqual(report.to_state(-3.0).interaction_strength, 0.0)

    def test_to_state_without_override_uses_self_report(self) -> None:
        report = scripted_learner(3, "")
        self.assertAlmostEqual(
            report.to_state().interaction_strength, report.confusion
        )


class TestArtifact(unittest.TestCase):
    def test_markdown_declares_the_coupling_source(self) -> None:
        measured = loop_closure_markdown(_session(ConfusionScorer()))
        baseline = loop_closure_markdown(_session(None))
        self.assertIn("measured", measured)
        self.assertIn("self_report", baseline)

    def test_markdown_shows_both_columns_only_when_measured(self) -> None:
        measured = loop_closure_markdown(_session(ConfusionScorer()))
        baseline = loop_closure_markdown(_session(None))
        self.assertIn("| reported | measured |", measured)
        self.assertNotIn("| reported | measured |", baseline)

    def test_measured_disclaimer_does_not_claim_activations(self) -> None:
        md = loop_closure_markdown(_session(ConfusionScorer()))
        self.assertIn("proposition ledger", md)
        self.assertIn("activations", md)


if __name__ == "__main__":
    unittest.main()
