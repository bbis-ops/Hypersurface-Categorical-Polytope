#!/usr/bin/env python3
"""Plot loop_closure_session.json timeline (optional matplotlib)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "loop_closure_session.json"
OUT = ROOT / "experiments" / "figures" / "loop_closure_timeline.png"


def main() -> None:
    if not DATA.exists():
        print(f"Missing {DATA}; run: python experiments/run_loop_closure.py")
        sys.exit(1)
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    turns = payload["turns"]
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skip figure")
        return

    xs = [t["turn"] for t in turns]
    eps = [t["probe"]["epsilon"] for t in turns]
    gaps = [t["probe"]["gap_vertex_grid"] for t in turns]
    modes = [t["probe"]["search_mode"] for t in turns]
    closure = payload["summary"].get("closure_turn")

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(xs, eps, "o-", color="steelblue", label="epsilon (live)")
    ax1.plot(xs, gaps, "s-", color="coral", label="gap grid - vertex")
    ax1.set_xlabel("turn")
    ax1.set_ylabel("probe values")
    ax1.axhline(0.01, color="gray", linestyle=":", alpha=0.6, label="interior tol")
    if closure is not None:
        ax1.axvline(closure, color="green", linestyle="--", label="loop closure")
    for i, m in enumerate(modes):
        if m == "INTERIOR_SEARCH":
            ax1.axvspan(i - 0.45, i + 0.45, alpha=0.15, color="green")
    ax1.legend(loc="upper left")
    ax1.set_title("Live polytope probe during coexp learning")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=120)
    plt.close()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
