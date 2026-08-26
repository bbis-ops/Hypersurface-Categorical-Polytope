#!/usr/bin/env python3
"""Run turn-based category tutor with live epsilon logging."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.category_tutor import CategoryLearningTutor


def main() -> None:
    tutor = CategoryLearningTutor()
    tutor.run_scripted_dialogue()
    jp, mp = tutor.save(ROOT / "experiments")
    s = tutor.summary()
    print(f"Wrote {jp}")
    print(f"Wrote {mp}")
    print(f"Turns: {s['n_turns']}, first interior: turn {s['first_interior_turn']}")
    for t in tutor.turns:
        print(f"  [{t.turn}] {t.search_mode} eps={t.epsilon:.4f} gap={t.gap_vertex_grid:.4f}")


if __name__ == "__main__":
    main()
