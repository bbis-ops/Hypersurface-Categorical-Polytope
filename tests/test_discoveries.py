"""Smoke tests for automated discovery engine."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.discoveries import (
    discover_certification_boundary,
    discover_face_bowl_onset,
    discover_obstruction_minimal,
    run_all_discoveries,
    write_discovery_artifacts,
)


class TestDiscoveries(unittest.TestCase):
    def test_registry_nonempty(self) -> None:
        items = run_all_discoveries()
        self.assertGreaterEqual(len(items), 8)
        ids = {d.id for d in items}
        self.assertIn("cert_boundary_fisher", ids)
        self.assertIn("face_bowl_onset", ids)

    def test_obstruction_minimal_small(self) -> None:
        d = discover_obstruction_minimal()
        self.assertLessEqual(d.evidence["y"], 3)
        self.assertLessEqual(d.evidence["a"], 3)

    def test_cert_boundary_between_known(self) -> None:
        d = discover_certification_boundary()
        b = d.evidence["boundary_f"]
        self.assertGreater(b, 0.08)
        self.assertLess(b, 0.30)

    def test_face_bowl_onset_positive(self) -> None:
        d = discover_face_bowl_onset()
        self.assertGreater(d.evidence["gap_vs_grid"], 0.0)
        self.assertLess(d.evidence["onset_strength"], 0.6)

    def test_write_artifacts(self) -> None:
        jp, mp, fp = write_discovery_artifacts(ROOT)
        self.assertTrue(jp.exists())
        self.assertTrue(mp.exists())
        self.assertTrue(fp.exists())
        data = json.loads(jp.read_text(encoding="utf-8"))
        self.assertEqual(data["count"], len(data["discoveries"]))
        self.assertIn("formal_proofs", data)
        self.assertGreaterEqual(len(data["formal_proofs"]), 10)


if __name__ == "__main__":
    unittest.main()
