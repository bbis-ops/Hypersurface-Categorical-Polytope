#!/usr/bin/env python3
"""Ask the API to adversarially audit the coverage theorem; save objections as data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROMPT = r"""Act as a hostile mathematical referee. Audit this theorem, not its prose:

Let X=[0,1]^d with Euclidean metric and S={x_1,...,x_n}. Define
rho(S)=max_{x in X} min_{s in S} ||x-s||_2. Compactness gives x* attaining rho.
The open relative ball B_X(x*,rho) contains no point of S, so point evaluation
cannot distinguish an everywhere-safe behavior from one failing only in that ball.
If radius-r Euclidean balls around S cover X, then 1=vol(X) <= n*v_d*r^d,
so rho(S) >= (1/(n*v_d))^(1/d). For the endpoint Cartesian grid with m points
per axis, rho=sqrt(d)/(2(m-1)); hence rho<=delta is achieved by
n=ceil(1+sqrt(d)/(2 delta))^d. For d=20, delta=.05 this is 46^20 ~=1.80e33.

The interpretation explicitly requires a chosen metric. Detecting every failure
set additionally requires that every relevant failure contain a metric ball of
the target radius, or another regularity/margin condition. For deterministic
adaptive testing, derive the finite all-pass query path first and then construct
one fixed failing behavior that returns pass on every query in that path. No
randomized-test probability claim is made here.

Return __N__ distinct, strongest objections. Check quantifiers, open/closed balls,
relative boundary balls, the volume inequality, adaptive/randomized tests,
dimension/metric assumptions, and whether the operational wording overclaims.
Do not merely agree. If an objection fails, explain why; if valid, give the
smallest repair. JSON only:
{"objections":[{"id":"slug","target":"exact clause","objection":"...",
"verdict":"valid|invalid|needs-assumption","repair":"...","severity":"fatal|major|minor"}]}
"""


def parse_objections(text: Any) -> list[dict[str, str]]:
    if not isinstance(text, str):
        return []
    payload: Any = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
    if not isinstance(payload, dict) or not isinstance(payload.get("objections"), list):
        return []
    out: list[dict[str, str]] = []
    for index, item in enumerate(payload["objections"]):
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "needs-assumption")).lower()
        severity = str(item.get("severity", "major")).lower()
        out.append(
            {
                "id": re.sub(r"[^a-z0-9_]+", "_", str(item.get("id", f"obj_{index}" )).lower())[:60],
                "target": str(item.get("target", ""))[:500],
                "objection": str(item.get("objection", ""))[:2000],
                "model_verdict": verdict if verdict in {"valid", "invalid", "needs-assumption"} else "needs-assumption",
                "repair": str(item.get("repair", ""))[:2000],
                "severity": severity if severity in {"fatal", "major", "minor"} else "major",
                "local_status": "pending formal adjudication",
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()
    if args.n < 1 or args.rounds < 1:
        ap.error("--n and --rounds must be positive")

    from categorical_polytope.interaction_search import propose_candidates

    objections: list[dict[str, str]] = []
    backend = "no run"
    seen: set[tuple[str, str]] = set()
    json_path = ROOT / "experiments" / "coverage_proof_audit.json"
    previous_by_id: dict[str, dict[str, str]] = {}
    if json_path.exists():
        try:
            previous = json.loads(json_path.read_text(encoding="utf-8"))
            previous_by_id = {
                str(item.get("id", "")): item
                for item in previous.get("objections", [])
                if isinstance(item, dict) and item.get("id")
            }
        except (json.JSONDecodeError, OSError):
            previous_by_id = {}

    def write_outputs() -> tuple[Path, Path]:
        payload = {
            "backend": backend,
            "requested": args.n * args.rounds,
            "received": len(objections),
            "role": "untrusted adversarial proof review; local verification required",
            "objections": objections,
        }
        json_out = json_path
        json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        lines = [
            "# API adversarial audit: coverage theorem",
            "",
            f"Backend: `{backend}`",
            "",
            "Model output is an untrusted referee report, not a proof. Each item remains",
            "pending until checked against the formal statement and executable tests.",
            "",
        ]
        for index, item in enumerate(objections, 1):
            lines += [
                f"## {index}. {item['id']}",
                "",
                f"- Target: {item['target']}",
                f"- Objection: {item['objection']}",
                f"- Model verdict: {item['model_verdict']} ({item['severity']})",
                f"- Proposed repair: {item['repair']}",
                f"- Local status: **{item['local_status']}**",
                f"- Local reason: {item.get('local_reason', '')}",
                "",
            ]
        md_out = ROOT / "docs" / "COVERAGE_PROOF_AUDIT.md"
        md_out.write_text("\n".join(lines), encoding="utf-8")
        return json_out, md_out

    for round_index in range(args.rounds):
        batch, backend = propose_candidates(
            args.n,
            model=args.model,
            base_url=args.base_url,
            prompt=PROMPT.replace("__N__", str(args.n)),
            parser=parse_objections,
        )
        fresh = []
        for item in batch:
            prior = previous_by_id.get(item["id"])
            if prior:
                item["local_status"] = str(
                    prior.get("local_status", item["local_status"])
                )
                item["local_reason"] = str(prior.get("local_reason", ""))
            else:
                item["local_reason"] = ""
            key = (item["target"], item["objection"])
            if key not in seen:
                seen.add(key)
                fresh.append(item)
        objections.extend(fresh)
        print(
            f"  audit round {round_index + 1}/{args.rounds}: +{len(fresh)} "
            f"objections ({backend})",
            flush=True,
        )
        # Checkpoint every completed API round: a later stalled free-provider
        # request must not erase already received referee objections.
        write_outputs()

    json_out, md_out = write_outputs()
    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
