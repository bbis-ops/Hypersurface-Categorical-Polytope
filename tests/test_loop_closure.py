"""Loop closure vignette."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.loop_closure import (
    LoopClosureSession,
    LearnerDiagramReport,
    probe_diagram_state,
    scripted_learner,
)


class TestLoopClosure(unittest.TestCase):
    def test_probe_runs(self) -> None:
        st = LearnerDiagramReport.from_json(
            {"lam": 0.8, "sigma": 0.3, "b": 2, "k": 3, "confusion": 0.4, "topic": "t", "quote": "q"}
        ).to_state()
        p = probe_diagram_state(st)
        self.assertIn(p.search_mode, ("CORNER_HUNTING", "BLOCK_COORDINATE", "INTERIOR_SEARCH"))

    def test_session_closure(self) -> None:
        s = LoopClosureSession()
        s.run()
        self.assertIsNotNone(s.closure_turn())
        self.assertLess(s.closure_turn() or 99, 6)

    def test_scripted_arc(self) -> None:
        r = scripted_learner(4, "")
        self.assertIn("interior", r.quote.lower() + r.topic.lower())


if __name__ == "__main__":
    unittest.main()
