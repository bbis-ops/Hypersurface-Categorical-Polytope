#!/usr/bin/env python3
"""Run quadratic + nonlinear experiments and optional plots."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    py = sys.executable
    scripts = [
        ROOT / "experiments" / "run_experiments.py",
        ROOT / "experiments" / "nonlinear_experiments.py",
    ]
    for script in scripts:
        print(f"\n--- {script.name} ---")
        subprocess.run([py, str(script)], check=True, cwd=str(ROOT))

    for plotter in ("plot_results.py", "plot_nonlinear.py"):
        p = ROOT / "experiments" / plotter
        if p.exists():
            print(f"\n--- {plotter} ---")
            subprocess.run([py, str(p)], cwd=str(ROOT))

    report = ROOT / "experiments" / "generate_report.py"
    if report.exists():
        print(f"\n--- generate_report.py ---")
        subprocess.run([py, str(report)], cwd=str(ROOT))

    discover = ROOT / "experiments" / "run_discoveries.py"
    if discover.exists():
        print(f"\n--- run_discoveries.py ---")
        subprocess.run([py, str(discover)], cwd=str(ROOT))

    research = ROOT / "experiments" / "run_research_probes.py"
    if research.exists():
        print(f"\n--- run_research_probes.py ---")
        subprocess.run([py, str(research)], cwd=str(ROOT))

    friday = ROOT / "experiments" / "run_friday_probes.py"
    if friday.exists():
        print(f"\n--- run_friday_probes.py ---")
        subprocess.run([py, str(friday)], cwd=str(ROOT))

    tutor = ROOT / "experiments" / "run_category_tutor.py"
    if tutor.exists():
        print(f"\n--- run_category_tutor.py ---")
        subprocess.run([py, str(tutor)], cwd=str(ROOT))

    coverage = ROOT / "experiments" / "run_coverage_correlation.py"
    coverage_inputs = (
        ROOT / "experiments" / "combined_law.json",
        ROOT / "experiments" / "SAFETY_INSTANCES.md",
    )
    if coverage.exists() and all(path.exists() for path in coverage_inputs):
        print(f"\n--- {coverage.name} ---")
        subprocess.run([py, str(coverage)], check=True, cwd=str(ROOT))

    eval_design = ROOT / "experiments" / "run_eval_design_recommendations.py"
    if eval_design.exists():
        print(f"\n--- {eval_design.name} ---")
        subprocess.run([py, str(eval_design)], check=True, cwd=str(ROOT))

    distributional_audit = ROOT / "experiments" / "run_distributional_coverage_audit.py"
    if distributional_audit.exists():
        print(f"\n--- {distributional_audit.name} ---")
        subprocess.run([py, str(distributional_audit)], check=True, cwd=str(ROOT))

    checklist = ROOT / "experiments" / "run_eval_checklist.py"
    if checklist.exists():
        print(f"\n--- {checklist.name} ---")
        subprocess.run([py, str(checklist)], check=True, cwd=str(ROOT))

    print("\nAll experiments complete.")
    print(f"  {ROOT / 'experiments' / 'results.json'}")
    print(f"  {ROOT / 'experiments' / 'nonlinear_results.json'}")


if __name__ == "__main__":
    main()
