"""Friday immediate probes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.discoveries_friday import run_friday_discoveries
from categorical_polytope.enriched_coexp import probe_enriched_universal_property
from categorical_polytope.coexponential_alternatives import CategoricalSetting
from categorical_polytope.lawvere_face_bowl import probe_lawvere_face_bowl_onset
from categorical_polytope.sheaf_certificate import build_certificate_sheaf
from categorical_polytope.category_learning_session import CategoryLearningSession


class TestFridayProbes(unittest.TestCase):
    def test_friday_registry(self) -> None:
        self.assertGreaterEqual(len(run_friday_discoveries()), 4)

    def test_enriched_up_runs(self) -> None:
        p = probe_enriched_universal_property(CategoricalSetting.PRESHEAF_TOY)
        self.assertIsNotNone(p.reason)

    def test_sheaf_gluing(self) -> None:
        sh = build_certificate_sheaf(coupling=0.1)
        self.assertGreaterEqual(len(sh.sections), 2)

    def test_lawvere_probe(self) -> None:
        r = probe_lawvere_face_bowl_onset()
        self.assertIn("onsets_by_distance", r)

    def test_category_session_interior(self) -> None:
        s = CategoryLearningSession()
        s.run()
        self.assertIsNotNone(s.log.first_interior_step())


if __name__ == "__main__":
    unittest.main()
