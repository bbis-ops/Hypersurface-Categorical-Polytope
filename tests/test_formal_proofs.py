"""Formal proof registry matches discoveries and numeric checks pass."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.discoveries import run_all_discoveries
from categorical_polytope.formal_proofs import (
    PROOF_REGISTRY,
    REGISTRY_BY_ID,
    formal_discoveries_markdown,
    verify_all_proofs,
)


class TestFormalProofs(unittest.TestCase):
    def test_registry_covers_discoveries(self) -> None:
        ids = {d.id for d in run_all_discoveries()}
        for sid in ids:
            self.assertIn(sid, REGISTRY_BY_ID, f"missing formal proof for {sid}")

    def test_ten_propositions(self) -> None:
        self.assertEqual(len(PROOF_REGISTRY), 10)

    def test_all_numeric_checks_pass(self) -> None:
        results = verify_all_proofs()
        failed = [(a, b, d) for a, b, c, d in results if not c]
        self.assertEqual(failed, [], msg=str(failed))

    def test_markdown_contains_labels(self) -> None:
        md = formal_discoveries_markdown()
        self.assertIn("Proposition A.1", md)
        self.assertIn("Theorem C.1", md)
        self.assertIn("face_bowl violates vertex localization", md)


if __name__ == "__main__":
    unittest.main()
