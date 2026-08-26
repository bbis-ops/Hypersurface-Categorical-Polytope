#!/usr/bin/env python3
"""Plot gap vs epsilon from experiments/results.json (optional matplotlib)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results.json"
OUT_DIR = ROOT / "experiments" / "figures"


def load_results() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def plot_matplotlib(data: dict) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    rows = data["toy_2block"]
    eps = [r["epsilon"] for r in rows]
    gaps = [r["gap_joint_sep"] for r in rows]
    phi = [r.get("phi_theorem") or r.get("phi_bound") or 0 for r in rows]
    strict = [r.get("certified_strict", False) for r in rows]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(eps, gaps, "o-", label="gap (joint - separable)")
    if any(phi):
        ax.plot(eps, phi, "s--", label="Phi(epsilon) cert bound", alpha=0.7)
    ax.axvline(0.10, color="green", linestyle=":", label="epsilon_0 safe")
    ax.axvline(0.25, color="orange", linestyle=":", label="epsilon moderate")
    for i, ok in enumerate(strict):
        if not ok and i < len(eps):
            ax.plot(eps[i], gaps[i], "rx", markersize=10)
    ax.set_xlabel("normalized leakage epsilon")
    ax.set_ylabel("objective gap")
    ax.set_title("Coproduct factorization stability")
    ax.legend()
    ax.grid(True, alpha=0.3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "gap_vs_epsilon.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    if not RESULTS.exists():
        print("Run experiments/run_experiments.py first.")
        sys.exit(1)
    data = load_results()
    rows = data["toy_2block"]
    print("gap vs epsilon (table):")
    for r in rows:
        print(
            f"  eps={r['epsilon']:.4f}  gap={r['gap_joint_sep']:.4f}  "
            f"strict={r.get('certified_strict')}"
        )
    path = plot_matplotlib(data)
    if path:
        print(f"Wrote figure: {path}")
    else:
        print("matplotlib not installed; table only.")


if __name__ == "__main__":
    main()
