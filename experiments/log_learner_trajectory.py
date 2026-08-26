#!/usr/bin/env python3
"""
Log or simulate a learner trajectory on the diagram polytope.

  python experiments/log_learner_trajectory.py
  python experiments/log_learner_trajectory.py --out experiments/sample_learner_log.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.learner_diagram import LearnerDiagramState, LearnerTrajectoryLog


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(ROOT / "experiments" / "sample_learner_log.json"),
        help="JSON output path",
    )
    ap.add_argument("--steps", type=int, default=14)
    ap.add_argument("--interaction", default="face_bowl")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    log = LearnerTrajectoryLog.simulate_random_walk(
        n_steps=args.steps,
        interaction=args.interaction,
        seed=args.seed,
    )
    out = Path(args.out)
    log.save_json(out)
    print(f"Wrote {out} ({len(log.steps)} steps)")
    first = log.first_interior_step()
    if first:
        print(
            f"  First INTERIOR_SEARCH: step={first.step} "
            f"eps={first.epsilon:.4f} gap={first.gap_vertex_grid:.4f}"
        )
    else:
        print("  No interior search triggered on this trajectory.")


if __name__ == "__main__":
    main()
