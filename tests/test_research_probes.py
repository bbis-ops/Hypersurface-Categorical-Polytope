"""Research direction probes."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.coexponential_alternatives import (
    CategoricalSetting,
    probe_setting,
)
from categorical_polytope.discoveries_research import run_research_discoveries
from categorical_polytope.enriched_fisher import compare_epsilon_unweighted_vs_enriched
from categorical_polytope.learner_diagram import LearnerSession, recommend_search_mode


class TestResearchProbes(unittest.TestCase):
    def test_set_obstructed_others_not_all(self) -> None:
        set_rep = probe_setting(CategoricalSetting.FINITE_SET)
        self.assertFalse(set_rep.representable)
        pres = probe_setting(CategoricalSetting.PRESHEAF_TOY)
        self.assertTrue(pres.representable)

    def test_research_registry(self) -> None:
        items = run_research_discoveries()
        self.assertEqual(len(items), 9)
        ids = {d.id for d in items}
        self.assertIn("learner_interior_switch", ids)
        self.assertIn("presheaf_site_exponential", ids)
        self.assertIn("lawvere_metric_epsilon", ids)

    def test_trajectory_log_json(self) -> None:
        from categorical_polytope.learner_diagram import LearnerTrajectoryLog

        log = LearnerTrajectoryLog.simulate_random_walk(n_steps=8, seed=1)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            path = Path(tmpdir) / "_test_traj.json"
            log.save_json(path)
            loaded = LearnerTrajectoryLog.load_json(path)
            self.assertEqual(len(loaded.steps), 8)

    def test_presheaf_site_sweep(self) -> None:
        from categorical_polytope.presheaf_site import sweep_site_exponentials

        rows = sweep_site_exponentials()
        self.assertGreaterEqual(len(rows), 2)

    def test_lawvere_dampens_epsilon(self) -> None:
        from categorical_polytope.lawvere_metric import compare_lawvere_vs_plain

        rows = compare_lawvere_vs_plain((0.15,), (2.0,))
        self.assertTrue(rows[0]["epsilon_lawvere"] < rows[0]["epsilon_plain"])

    def test_enriched_epsilon_changes(self) -> None:
        rows = compare_epsilon_unweighted_vs_enriched((0.1, 0.15, 0.2))
        self.assertTrue(
            any(
                abs(r["epsilon_enriched"] - r["epsilon_unweighted"]) > 1e-6
                for r in rows
            )
        )

    def test_learner_switch_face_bowl(self) -> None:
        det = LearnerSession(interaction="face_bowl").detect_mode_switch()
        self.assertIsNotNone(det["switch_strength"])

    def test_interior_recommendation(self) -> None:
        mode, _ = recommend_search_mode(0.05, gap_vertex_grid=0.05, certified_separable=True, epsilon_0=0.25)
        from categorical_polytope.learner_diagram import SearchMode

        self.assertIs(mode, SearchMode.INTERIOR_SEARCH)


if __name__ == "__main__":
    unittest.main()
