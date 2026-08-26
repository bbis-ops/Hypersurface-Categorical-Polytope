#!/usr/bin/env python3
"""Run the versioned normal-form coverage layer for V.7--V.14."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "experiments" / "candidate_coverage_certificate.json"
OUT_MD = ROOT / "docs" / "CANDIDATE_COVERAGE_CERTIFICATE.md"
OPEN_CAMPAIGN = ROOT / "experiments" / "verification_campaign.json"


def _open_campaign_counts() -> tuple[int, int]:
    if not OPEN_CAMPAIGN.exists():
        return 0, 0
    payload = json.loads(OPEN_CAMPAIGN.read_text(encoding="utf-8"))
    return len(payload.get("requests", [])), len(payload.get("records", []))


def _render(payload: dict) -> str:
    calls, candidates = _open_campaign_counts()
    lines = [
        "# Registered candidate-space coverage certificate",
        "",
        "This is the missing metric bridge for the V.7–V.14 campaign. It is a",
        "**restricted normal-form coverage claim**, not a claim that arbitrary model-generated",
        "expressions or prompts form a finite-dimensional Cartesian space.",
        "",
        "## Two-layer design",
        "",
        f"- **Open adversarial layer:** currently {calls} logged API request batches and {candidates} unique",
        "  generated candidates. This measures demonstrated adversarial-search behavior but has no",
        "  exhaustive covering-radius claim.",
        "- **Registered coverage layer (registry v1):** the bounded families below. Within a family, the normalized",
        "  parameter vector is the candidate and the metric is Euclidean distance on `[0,1]^d`.",
        "",
        "Registry v1 was designed after the open campaign and calibrated with boundary probes, so this",
        "run is an **exploratory calibration certificate**, not a retrospectively claimed preregistration.",
        "The code and ranges now provide a frozen target for an unchanged confirmatory rerun.",
        "",
        "## Certificate theorem and regularity assumption",
        "",
        "For an endpoint-including Cartesian grid with `m` points per normalized parameter axis,",
        "the exact covering radius is",
        "",
        "`rho = sqrt(d)/(2(m-1))`.",
        "",
        "**Minimum-width assumption R(rho):** within each registered family, every relevant",
        "counterexample set contains a closed relative metric ball of radius at least `rho`.",
        "If every grid point is conclusively verified and R(rho) holds, every relevant",
        "counterexample in that registered family would be detected. This is conditional on R(rho);",
        "the experiment does not estimate or silently assume it.",
        "",
        "Equivalently, a margin formulation may replace R: if a violation functional `H` is",
        "`L`-Lipschitz and every relevant failure has margin at least `eta`, it is enough that",
        "`rho < eta/L`. No numerical `L` or `eta` is claimed here.",
        "",
        "## Results",
        "",
        "| Law | Registered family | d | Grid | Exact rho | verified | counterexamples | unresolved | Outcome |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["families"]:
        lines.append(
            f"| {row['law']} | {row['family']} | {row['dimension']} | "
            f"{row['points_per_axis']}^{row['dimension']}={row['grid_points']} | "
            f"{row['covering_radius']:.6f} | {row['status_counts'].get('verified', 0)} | "
            f"{row['status_counts'].get('counterexample', 0)} | {row['unresolved']} | "
            f"{row['certificate_status']} |"
        )
    lines += ["", "## Registered domains", ""]
    for row in payload["families"]:
        lines += [
            f"### {row['law']} — {row['family']}", "",
            f"- Formula: `{row['formula']}`",
            f"- Scope: {row['scope']}",
            "- Normalization: " + "; ".join(
                f"`{axis['name']}` in [{axis['lower']}, {axis['upper']}] ({axis['scale']}) -> [0,1]"
                for axis in row["axes"]
            ),
            f"- Exact normalized Euclidean covering radius: `{row['covering_radius']:.12g}`.",
            f"- Status: **{row['certificate_status']}**.", "",
        ]
        if row["non_verified"]:
            lines.append("Non-verified grid points:")
            lines.append("")
            for item in row["non_verified"][:20]:
                lines.append(
                    f"- `{item['status']}` at `{json.dumps(item['parameters'], sort_keys=True)}`: "
                    f"{item['reason']}"
                )
            if len(row["non_verified"]) > 20:
                lines.append(f"- …and {len(row['non_verified']) - 20} more in the JSON artifact.")
            lines.append("")
    lines += [
        "## Claim boundary", "",
        "The certificate covers only the explicitly registered normal-form families and parameter",
        "ranges above. The open API corpus remains valuable adversarial evidence and can discover",
        "failures outside these families, but its candidate count must not be substituted for `m^d`.",
        "A theorem proved analytically retains the scope of its proof; this grid tests the executable",
        "implementation and supplies conditional finite-family detection evidence.",
        "",
        "## Reproduce", "",
        "`python experiments/run_candidate_coverage.py --points-per-axis 3`", "",
    ]
    return "\n".join(lines)


def main() -> None:
    from categorical_polytope.candidate_coverage import (
        REGISTERED_FAMILIES,
        cartesian_covering_radius,
        cartesian_unit_grid,
        coverage_certificate_status,
    )

    ap = argparse.ArgumentParser()
    ap.add_argument("--points-per-axis", type=int, default=3)
    ap.add_argument("--laws", nargs="+", choices=[f"V.{i}" for i in range(7, 15)])
    ap.add_argument("--report-only", action="store_true",
                    help="rerender the existing JSON without reevaluating grid points")
    args = ap.parse_args()
    if args.points_per_axis < 2:
        ap.error("--points-per-axis must be at least 2")

    if args.report_only:
        if not OUT_JSON.exists():
            ap.error(f"no existing artifact at {OUT_JSON}")
        payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        payload["registry_version"] = 1
        payload["phase"] = "exploratory calibration; freeze before confirmatory reuse"
        payload["claim"] = "Conditional detection coverage over versioned normal-form parameter families."
        for row in payload.get("families", []):
            row["certificate_status"], row["unresolved"] = coverage_certificate_status(
                row.get("status_counts", {})
            )
        OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        OUT_MD.write_text(_render(payload), encoding="utf-8")
        print(f"Wrote {OUT_JSON}")
        print(f"Wrote {OUT_MD}")
        return

    selected = [family for family in REGISTERED_FAMILIES if not args.laws or family.law in args.laws]
    rows = []
    for family in selected:
        points = cartesian_unit_grid(family.dimension, args.points_per_axis)
        records = []
        for index, point in enumerate(points, 1):
            parameters = family.parameters(point)
            record = family.evaluate(point).as_dict()
            records.append({"unit_point": list(point), "parameters": parameters, "record": record})
            print(f"{family.law} {index}/{len(points)}: {record['status']}", flush=True)
        counts = Counter(item["record"]["status"] for item in records)
        certificate_status, unresolved = coverage_certificate_status(dict(counts))
        rows.append({
            "law": family.law,
            "family": family.family,
            "dimension": family.dimension,
            "metric": "Euclidean on independently normalized [0,1] parameter coordinates",
            "axes": [axis.__dict__ for axis in family.axes],
            "formula": family.formula,
            "scope": family.scope,
            "points_per_axis": args.points_per_axis,
            "grid_points": len(points),
            "covering_radius": cartesian_covering_radius(family.dimension, args.points_per_axis),
            "regularity_assumption": "Every relevant failure set contains a closed relative ball of radius rho.",
            "status_counts": dict(counts),
            "unresolved": unresolved,
            "certificate_status": certificate_status,
            "non_verified": [
                {"unit_point": item["unit_point"], "parameters": item["parameters"],
                 "status": item["record"]["status"], "reason": item["record"]["reason"]}
                for item in records if item["record"]["status"] != "verified"
            ],
            "records": records,
        })

    payload = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "registry_version": 1,
        "phase": "exploratory calibration; freeze before confirmatory reuse",
        "claim": "Conditional detection coverage over versioned normal-form parameter families.",
        "excludes": "Arbitrary expressions, candidate-function space as a whole, prompt space, and deployed-model behavior.",
        "families": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_MD.write_text(_render(payload), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
