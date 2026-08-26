#!/usr/bin/env python3
"""Run the six-gate eval checklist and optionally red-team it through Ox Alpha."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT_JSON = ROOT / "experiments" / "eval_checklist_report.json"
OUT_MD = ROOT / "docs" / "EVAL_DESIGN_CHECKLIST.md"

PROMPT = r"""Act as a hostile eval-operations lead. Turn these six conditional
warnings into release gates: (1) separate risk-axis scores can miss interactions,
(2) flat safety boundaries have zero margin, (3) finite samples have a covering
radius, (4) separately tested constraints can fail jointly, (5) smooth tests do
not cover discrete/non-smooth attacks, (6) tolerances can hide positive gaps.

The proposed executable card requires: an interaction map plus joint scoring;
measured inward margin at every declared boundary; a semantically validated
metric and rho <= (1-eta)*minimum_failure_radius; every preregistered coupled
group tested by joint search; every declared non-smooth class tested by discrete
search; and raw scores/positive gaps preserved without tolerance relabeling.
Missing evidence blocks release.

Find concrete ways an evaluator could game or misapply these gates. Each repair
must be an implementable input field, computation, or release rule—not general
advice. JSON only:
{"reviews":[{"id":"slug","gate":"one of six","failure":"...",
"repair":"...","severity":"major|minor"}]}
"""

ADJUDICATIONS = {
    "interaction_map_cherry_pick": ("accepted and enforced", "The card now derives every pair from the declared risk-axis taxonomy and requires all pairs to be tested."),
    "joint_score_weight_gaming": ("accepted and enforced", "The score formula and config hash are now mandatory preregistered evidence."),
    "boundary_margin_measured_outward": ("accepted in principle", "The gate now requires adversarial inward search, a boundary cover, and a retained trace; fixed K and PGD hyperparameters are domain-specific, not theorem consequences."),
    "margin_zero_tolerance_sweep": ("accepted in principle", "The gate now requires a declared boundary resolution and certified margin lower bounds; the proposed surface-area formula and binomial interval are not generally valid for dependent geometric searches."),
    "covering_radius_fabricated_metric": ("accepted and enforced", "Held-out adversarial contrast validation and distinct validation/eval hashes are now mandatory."),
    "eta_inflation_radius_shrink": ("rejected", "The inequality direction is backwards: increasing eta makes rho <= (1-eta)delta stricter, not easier. Preregistration remains sensible but the alleged exploit does not work."),
    "coupled_group_under_registration": ("accepted and enforced", "Groups are structured multi-axis lists, singleton groups are invalid, and declared groups must all appear in tested groups."),
    "joint_search_local_optimum": ("accepted in principle", "The card enforces a preregistered minimum, domain-spanning starts, historical-failure seeds, and a trace. No universal theorem selects M=100."),
    "non_smooth_class_relabeled_smooth": ("accepted and enforced", "Every item must be explicitly nonsmooth and must retain a discrete-search trace."),
    "discrete_search_token_budget_starved": ("accepted with scope", "Each class budget is computed from preregistered minimum per-trial success mass and miss probability under the IID/conditional theorem assumptions."),
    "tolerance_floor_relabeling": ("accepted and enforced", "The release decision must consume immutable raw results and any positive maximum gap blocks."),
    "gap_denominator_normalization": ("accepted with clarification", "The gate consumes the raw gap before display normalization. Domain-specific normalized statistics may still be reported separately."),
}


def parse_reviews(text: Any) -> list[dict[str, str]]:
    if not isinstance(text, str):
        return []
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    rows = []
    for i, item in enumerate(data.get("reviews", []) if isinstance(data, dict) else []):
        if not isinstance(item, dict):
            continue
        rows.append({
            "id": re.sub(r"[^a-z0-9_]+", "_", str(item.get("id", f"item_{i}")).lower())[:60],
            "gate": str(item.get("gate", ""))[:100],
            "failure": str(item.get("failure", ""))[:2000],
            "repair": str(item.get("repair", ""))[:2000],
            "severity": str(item.get("severity", "major")) if str(item.get("severity", "major")) in {"major", "minor"} else "major",
            "local_status": "pending adjudication",
            "local_reason": "",
        })
    return rows


def write(card: dict[str, Any], report: Any, backend: str, reviews: list[dict[str, str]]) -> None:
    for item in reviews:
        if item.get("id") in ADJUDICATIONS:
            item["local_status"], item["local_reason"] = ADJUDICATIONS[item["id"]]
    payload = {"input": card, "result": report.as_dict(), "api_review": {"backend": backend, "items": reviews}}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rows = "\n".join(
        f"| {x.id} | **{x.status.upper()}** | {x.evidence} | {x.action} |"
        for x in report.checks
    )
    review = "_API review not requested._"
    if reviews:
        review = "\n\n".join(
            f"### {x['id']} ({x['severity']})\n\n- Gate: {x['gate']}\n- Failure: {x['failure']}\n- Repair: {x['repair']}\n- Local status: **{x['local_status']}**\n- Local reason: {x['local_reason']}"
            for x in reviews
        )
    verdict = "RELEASABLE under the six declared gates" if report.releasable else "BLOCKED"
    OUT_MD.write_text(f"""# Runnable six-condition eval checklist

This is an operational release gate, not evidence about a deployed model. Every
field must refer to a preregistered evaluation domain and retained evidence.
Missing evidence blocks rather than passes.

The bundled card is a worked schema with placeholder hashes. Its PASS only
demonstrates the computation; replace every example value with retained evidence
before using the verdict for an evaluation release.

## Result: {verdict}

| Gate | Status | Evidence evaluated | Required action |
|---|---|---|---|
{rows}

## Procedure

1. Copy `experiments/eval_checklist_example.json` and replace every example value.
2. Preregister the domain, metric, interaction map, boundaries, coupled groups,
   and non-smooth attack taxonomy before examining outcomes.
3. Run `python experiments/run_eval_checklist.py --config YOUR_CARD.json`.
4. A release claim is allowed only when all six gates pass. Preserve the input
   card, raw samples, raw scores, search traces, and this JSON report.
5. State the claim type separately: these six gates do not themselves turn a
   pointwise test into a distributional or worst-case certificate.

## Ox Alpha application review

Backend: `{backend}`. Suggestions are untrusted until locally adjudicated.

{review}

## Reproduce

`python experiments/run_eval_checklist.py --config experiments/eval_checklist_example.json --api-review --model stealth/ox-alpha`
""", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "experiments" / "eval_checklist_example.json")
    ap.add_argument("--api-review", action="store_true")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    from categorical_polytope.eval_checklist import evaluate_checklist
    card = json.loads(args.config.read_text(encoding="utf-8"))
    report = evaluate_checklist(card)
    backend, reviews = "not requested", []
    previous = {}
    if OUT_JSON.exists():
        try:
            previous = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            old = previous.get("api_review", {})
            backend, reviews = str(old.get("backend", backend)), list(old.get("items", []))
        except (OSError, json.JSONDecodeError):
            pass
    if args.api_review:
        from categorical_polytope.interaction_search import propose_candidates
        fresh, backend = propose_candidates(1, model=args.model, prompt=PROMPT, parser=parse_reviews)
        old_by_id = {x.get("id"): x for x in reviews if isinstance(x, dict)}
        for item in fresh:
            if item["id"] in old_by_id:
                item["local_status"] = old_by_id[item["id"]].get("local_status", item["local_status"])
                item["local_reason"] = old_by_id[item["id"]].get("local_reason", "")
        reviews = fresh
        print(f"API checklist review: {len(reviews)} items ({backend})", flush=True)
    write(card, report, backend, reviews)
    print(f"Checklist: {'PASS' if report.releasable else 'BLOCK'}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
