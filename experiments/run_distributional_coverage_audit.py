#!/usr/bin/env python3
"""API adversarial audit of distributional and shift-aware detection bounds."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "experiments" / "distributional_coverage_audit.json"
OUT_MD = ROOT / "docs" / "DISTRIBUTIONAL_COVERAGE_AUDIT.md"

PROMPT = r"""Act as a hostile probability-theory referee. Audit these claims:

IID theorem. Inputs X_i are IID from P_eval. A fixed failure set F has
P_eval(F)>=mu. Conditional on X_i in F, the evaluator detects failure with
probability at least q, independently across draws. Then each draw detects with
probability at least mu*q and P(no detection in n draws)<=(1-mu*q)^n.

Shift corollary. If P_deploy is absolutely continuous w.r.t. P_eval and
dP_deploy/dP_eval <= W almost surely, then P_deploy(F)>=mu_dep implies
P_eval(F)>=mu_dep/W, hence miss probability <=(1-mu_dep*q/W)^n.

Adaptive conditional theorem. Independence is not necessary if, on every
no-detection history H_(i-1), the next conditional detection probability obeys
P(D_i | H_(i-1), no earlier D)>=p almost surely. Iterated conditioning gives
P(no detection through n)<=(1-p)^n.

These are conditional mathematical statements. Estimating mu,q,W,p is separate
and uncertainty must be propagated; no claim transfers when absolute continuity,
finite W, or the conditional lower bound is unjustified.

Return the strongest objections: check inequality direction, independence,
conditioning/filtrations, fixed-vs-adaptive failure sets, detector dependence,
optional stopping, density-ratio support, and estimation-vs-theorem confusion.
JSON only:
{"objections":[{"id":"slug","target":"iid|shift|adaptive|interpretation",
"objection":"...","verdict":"valid|invalid|needs-assumption","repair":"...",
"severity":"fatal|major|minor"}]}
"""


def parse_objections(text: Any) -> list[dict[str, str]]:
    if not isinstance(text, str):
        return []
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict) or not isinstance(payload.get("objections"), list):
        return []
    rows = []
    for index, item in enumerate(payload["objections"]):
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "needs-assumption")).lower()
        severity = str(item.get("severity", "major")).lower()
        rows.append(
            {
                "id": re.sub(r"[^a-z0-9_]+", "_", str(item.get("id", f"obj_{index}")).lower())[:60],
                "target": str(item.get("target", ""))[:100],
                "objection": str(item.get("objection", ""))[:2000],
                "model_verdict": verdict if verdict in {"valid", "invalid", "needs-assumption"} else "needs-assumption",
                "repair": str(item.get("repair", ""))[:2000],
                "severity": severity if severity in {"fatal", "major", "minor"} else "major",
                "local_status": "pending adjudication",
                "local_reason": "",
            }
        )
    return rows


def write_outputs(backend: str, objections: list[dict[str, str]]) -> None:
    from categorical_polytope.eval_design import (
        distributional_miss_bound,
        distributional_samples,
        shift_robust_distributional_samples,
    )

    iid_n = distributional_samples(0.01, 0.05, detection_sensitivity=0.9)
    shift_n = shift_robust_distributional_samples(
        0.01, 0.05, 5.0, detection_sensitivity=0.9
    )
    payload = {
        "backend": backend,
        "theorem_checks": {
            "iid_mu_001_q_09_alpha_005": {
                "n": iid_n,
                "miss_bound": distributional_miss_bound(
                    iid_n, 0.01, detection_sensitivity=0.9
                ),
            },
            "shift_mu_001_q_09_W_5_alpha_005": {"n": shift_n},
        },
        "objections": objections,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    objection_lines = ["_No API objections returned._"]
    if objections:
        objection_lines = []
        for item in objections:
            objection_lines += [
                f"### {item['id']} ({item['severity']})",
                "",
                f"- Target: {item['target']}",
                f"- Objection: {item['objection']}",
                f"- Model verdict: {item['model_verdict']}",
                f"- Proposed repair: {item['repair']}",
                f"- Local status: **{item['local_status']}**",
                f"- Local reason: {item['local_reason']}",
                "",
            ]
    body = f"""# Distributional coverage: theorem and API audit

## Theorem D.1 — IID detection

For a failure set `F` fixed independently of the evaluation sample, IID draws
from `P_eval`, failure mass at least `mu`, and fresh detector randomness with
per-failure sensitivity at least `q`, independent across draws,

`P(no detection in n draws) <= (1-mu*q)^n`.

Thus `mu=0.01`, `q=0.9`, and target miss probability `0.05` require **{iid_n}**
draws; the computed upper bound is
`{distributional_miss_bound(iid_n, 0.01, detection_sensitivity=0.9):.6f}`.

## Corollary D.2 — bounded deployment shift

If `P_deploy << P_eval` and `dP_deploy/dP_eval <= W` for a certified finite
upper bound `W`, then deployment failure
mass `mu_dep` implies eval mass at least `mu_dep/W`. Substitute this into D.1.
For `mu_dep=0.01`, `q=0.9`, `W=5`, and miss probability `0.05`, the requirement
is **{shift_n}** IID draws.

This covers reweighting within eval support. It does not cover deployment-only
failure modes: those violate absolute continuity or force an unbounded ratio.

## Theorem D.3 — adaptive conditional detection

Let `F_i` contain all inputs, evaluator choices, detector state, and outcomes
through step `i`, and let `A_i` be no detection through that step. If on every
reachable history in `A_(i-1)`, `P(D_i | F_(i-1)) >= p` almost surely, then the
tower property gives

`P(A_n) = product_i P(no D_i | A_(i-1)) <= (1-p)^n`.

This permits adaptive/dependent selection only when the conditional lower bound
is valid uniformly over every surviving history. Optional stopping requires a
sequentially valid guarantee; a fixed-`n` formula cannot be reused after choosing
`n` from the observed data.

## Scope

The failure set is fixed before sampling. `mu`, `q`, `W`, and `p` are theorem
parameters, not automatically valid estimates. If calibration data give
simultaneous bounds `mu>=mu_L`, `q>=q_L`, and `W<=W_U` with failure probability
`delta_cal`, then a conservative unconditional statement is

`P(miss) <= (1-mu_L*q_L/W_U)^n + delta_cal`.

Scorer errors correlated across samples must be absorbed into a justified
conditional `p`; otherwise D.3 does not apply. A budgeted or stateful detector
does not inherit a constant `q` merely because inputs are IID.

## Ox Alpha adversarial review

Backend: `{backend}`. API output is untrusted until locally adjudicated.

{chr(10).join(objection_lines)}

## Reproduce

`python experiments/run_distributional_coverage_audit.py --api --model stealth/ox-alpha`
"""
    OUT_MD.write_text(body, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    objections: list[dict[str, str]] = []
    backend = "not requested"
    previous_by_id: dict[str, dict[str, str]] = {}
    if OUT_JSON.exists():
        try:
            previous = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            backend = str(previous.get("backend", backend))
            objections = [
                item for item in previous.get("objections", []) if isinstance(item, dict)
            ]
            previous_by_id = {
                str(item.get("id", "")): item for item in objections if item.get("id")
            }
        except (json.JSONDecodeError, OSError):
            objections = []
    write_outputs(backend, objections)
    if args.api:
        from categorical_polytope.interaction_search import propose_candidates

        objections, backend = propose_candidates(
            1,
            model=args.model,
            base_url=args.base_url,
            prompt=PROMPT,
            parser=parse_objections,
        )
        for item in objections:
            prior = previous_by_id.get(item["id"])
            if prior:
                item["local_status"] = str(prior.get("local_status", item["local_status"]))
                item["local_reason"] = str(prior.get("local_reason", ""))
        write_outputs(backend, objections)
        print(f"  API distributional audit: {len(objections)} objections ({backend})")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
