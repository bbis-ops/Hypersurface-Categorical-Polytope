#!/usr/bin/env python3
"""Non-quadratic experiments: interaction strength vs gap and vertex localization."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.nonlinear_objective import NonlinearStudy

OUT = ROOT / "experiments" / "nonlinear_results.json"


def _row(a: object, mode: str, strength: float) -> dict:
    from categorical_polytope.nonlinear_objective import NonlinearAnalysis

    assert isinstance(a, NonlinearAnalysis)
    return {
        "interaction": mode,
        "strength": strength,
        "gap": a.gap,
        "gap_vs_grid": a.gap_vs_grid,
        "epsilon": a.leakage.epsilon,
        "certified": a.certified,
        "vertex_ok": a.localization_at_vertex,
        "theta_vertex": a.theta_vertex.as_corner_tuple(),
        "theta_grid": a.theta_grid.as_corner_tuple() if a.theta_grid else None,
        "value_vertex": a.value_vertex,
        "value_grid": a.value_grid,
        "certify_reason": a.certify_reason,
    }


def main() -> None:
    study = NonlinearStudy()
    rows: list[dict] = []
    for mode in ("bilinear", "triple", "face_bowl"):
        strengths = (0.0, 0.1, 0.25, 0.5, 0.8, 1.0, 1.5, 2.0) if mode == "face_bowl" else (0.0, 0.1, 0.25, 0.5, 0.8, 1.0)
        for strength in strengths:
            a = study.analyze(strength=strength, interaction=mode)
            rows.append(_row(a, mode, strength))

    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")

    print("\nBilinear:")
    for r in rows:
        if r["interaction"] == "bilinear":
            print(f"  s={r['strength']:.1f} gap={r['gap']:.4f} vertex_ok={r['vertex_ok']}")

    print("\nface_bowl (vertex localization stress test):")
    for r in rows:
        if r["interaction"] == "face_bowl":
            g = r.get("gap_vs_grid")
            print(
                f"  s={r['strength']:.1f} grid_beats_vertex={g}  "
                f"theta_g={r.get('theta_grid')}  vertex_ok={r['vertex_ok']}"
            )


if __name__ == "__main__":
    main()
