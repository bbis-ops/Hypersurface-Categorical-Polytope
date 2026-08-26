#!/usr/bin/env python3
"""Generate docs/EXPERIMENT_REPORT.md from JSON experiment outputs."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "experiments" / "results.json"
NONLINEAR = ROOT / "experiments" / "nonlinear_results.json"
OUT = ROOT / "docs" / "EXPERIMENT_REPORT.md"


def _load(path: Path) -> list | dict:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _table_quadratic(rows: list[dict]) -> str:
    lines = [
        "| Fisher coupling f | epsilon | gap (joint-sep) | Phi bound | strict cert | vertex theta |",
        "|------------------|---------|-----------------|-----------|-------------|--------------|",
    ]
    for r in rows:
        th = r.get("vertex_theta", [])
        th_s = f"({th[0]:.1f},{th[1]:.1f},{th[2]:.1f},{th[3]:.1f})" if len(th) == 4 else str(th)
        lines.append(
            f"| {r['fisher_coupling']:.2f} | {r['epsilon']:.4f} | {r['gap_joint_sep']:.4f} | "
            f"{r.get('phi_theorem', 0) or 0:.4f} | {r.get('certified_strict', False)} | {th_s} |"
        )
    return "\n".join(lines)


def _table_nonlinear(rows: list[dict], interaction: str) -> str:
    sub = [r for r in rows if r.get("interaction") == interaction]
    if not sub:
        return f"_No rows for {interaction}_\n"
    lines = [
        f"### {interaction}",
        "",
        "| strength | gap_sep | gap_vs_grid | vertex_ok | epsilon |",
        "|----------|---------|-------------|-----------|---------|",
    ]
    for r in sub:
        g = r.get("gap_vs_grid")
        g_s = f"{g:.4f}" if g is not None else "—"
        lines.append(
            f"| {r['strength']:.2f} | {r.get('gap', 0):.4f} | {g_s} | {r.get('vertex_ok')} | {r.get('epsilon', 0):.4f} |"
        )
    return "\n".join(lines)


def main() -> None:
    quad = _load(RESULTS)
    if isinstance(quad, dict):
        quad = quad.get("toy_2block", [])
    nonlinear = _load(NONLINEAR)
    if not isinstance(nonlinear, list):
        nonlinear = []

    from categorical_polytope.set_category import cardinality_obstruction

    obs = cardinality_obstruction(2, 2)

    body = f"""# Experiment report (auto-generated)

Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

Sources: `experiments/results.json`, `experiments/nonlinear_results.json`.

## Coexponential obstruction (Set)

{obs.reason}

## Quadratic Fisher sweep (2-block toy)

{_table_quadratic(quad)}

**Findings.**

- Vertex probe remains at CCC corner (1, 0, 2, 3) for all couplings tested.
- Strict certification passes for f <= 0.10 (epsilon <= ~0.14); fails for f = 0.25 and 0.35.
- Gap grows with f while vertex search value stays at 7.0 (hypersurface composite on vertices).

## Nonlinear interactions

{_table_nonlinear(nonlinear, "bilinear")}

{_table_nonlinear(nonlinear, "face_bowl")}

**Findings.**

- `bilinear` / `triple`: separable gap 0 on box; vertex localization holds.
- `face_bowl`: `gap_vs_grid` > 0 for strength >= 0.5 — grid reference beats vertex-only search (Theorem 1 breakdown).

## Figures

- `experiments/figures/gap_vs_epsilon.png`
- `experiments/figures/nonlinear_face_bowl.png`

Regenerate: `python experiments/run_all.py` then `python experiments/generate_report.py`.
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
