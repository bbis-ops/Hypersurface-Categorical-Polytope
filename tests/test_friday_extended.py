"""Friday extensions: tutor, larger site, formal proofs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.category_tutor import CategoryLearningTutor
from categorical_polytope.discoveries_friday import run_friday_discoveries
from categorical_polytope.formal_proofs_friday import (
    FRIDAY_PROOF_REGISTRY,
    verify_friday_evidence,
)
from categorical_polytope.presheaf_site import larger_site
from categorical_polytope.sheaf_certificate import full_sheaf_report


class TestFridayExtended(unittest.TestCase):
    def test_friday_count(self) -> None:
        self.assertEqual(len(run_friday_discoveries()), 5)

    def test_tutor_interior(self) -> None:
        t = CategoryLearningTutor()
        t.run_scripted_dialogue()
        self.assertIsNotNone(t.log.first_interior_step())

    def test_larger_site(self) -> None:
        site = larger_site()
        self.assertEqual(len(site.objects), 5)

    def test_sheaf_report(self) -> None:
        r = full_sheaf_report()
        self.assertIn("sites", r)

    def test_friday_proofs_verify(self) -> None:
        by_id = {d.id: d.evidence for d in run_friday_discoveries()}
        for s in FRIDAY_PROOF_REGISTRY:
            if s.discovery_id not in by_id:
                continue
            ok, _ = verify_friday_evidence(s.discovery_id, by_id[s.discovery_id])
            self.assertTrue(ok, s.discovery_id)


if __name__ == "__main__":
    unittest.main()
