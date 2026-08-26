#!/usr/bin/env python3
"""Plot nonlinear_results.json: face_bowl grid vs vertex gap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "nonlinear_results.json"
OUT_DIR = ROOT / "experiments" / "figures"


def main() -> None:
    if not RESULTS.exists():
        print("Run experiments/nonlinear_experiments.py first.")
        sys.exit(1)

    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    bowl = [r for r in rows if r["interaction"] == "face_bowl" and r.get("gap_vs_grid") is not None]
    if not bowl:
        print("No face_bowl rows with gap_vs_grid.")
        return

    strengths = [r["strength"] for r in bowl]
    gaps = [r["gap_vs_grid"] for r in bowl]

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. face_bowl gap_vs_grid:")
        for s, g in zip(strengths, gaps):
            print(f"  strength={s}  grid_beats_vertex={g}")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([str(s) for s in strengths], gaps, color="coral", edgecolor="black")
    ax.set_xlabel("face_bowl interaction strength")
    ax.set_ylabel("grid max - vertex max")
    ax.set_title("Nonlinear: when vertices fail (Theorem 1 breakdown)")
    ax.axhline(0, color="gray", linewidth=0.8)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "nonlinear_face_bowl.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
