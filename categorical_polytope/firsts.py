"""
Four deliverables entry point: theorem, algorithm, experiment, note pointers.
"""

from __future__ import annotations

from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]


def deliverables_manifest() -> str:
    root = PKG_ROOT
    return (
        "Fisher-controlled extremal toolkit — deliverables\n"
        f"  1. Theorem:     {root / 'docs' / 'FORMAL_THEOREMS.md'}\n"
        f"  2. Algorithm:   vertex_probe.py + fisher_pruned_search.py\n"
        f"  3. Numerics:    experiments/run_all.py\n"
        f"  4. Note:        {root / 'docs' / 'SHORT_NOTE.md'}\n"
        f"  5. Nonlinear:   nonlinear_objective.py + nonlinear_results.json\n"
        f"  Runbook:        {root / 'docs' / 'RUNBOOK.md'}\n"
        f"  Demo:           python -m categorical_polytope\n"
    )


def run_numerical_firsts() -> None:
    import subprocess
    import sys

    script = PKG_ROOT / "experiments" / "run_all.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(PKG_ROOT))
