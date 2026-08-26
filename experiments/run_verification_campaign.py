#!/usr/bin/env python3
"""Checkpointed adversarial API corpus for V.7--V.14."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATE = ROOT / "experiments" / "verification_campaign.json"
CERTIFICATE = ROOT / "docs" / "VERIFICATION_CERTIFICATE.md"
COUNTEREXAMPLES = ROOT / "experiments" / "verification_counterexamples.json"
GUARD_FAILURES = ROOT / "experiments" / "verification_guard_failures.json"
RAW_API_LOG = ROOT / "experiments" / "verification_api_raw.jsonl"
VERIFIER_VERSION = 15
# Laws whose adjudicator semantics changed at each version.  This prevents a
# theorem-local repair from needlessly recomputing the entire multi-law corpus.
REVERIFY_LAWS_BY_VERSION = {
    6: {"V.14"},
    7: {"V.14"},
    8: {"V.14"},
    9: {"V.9"},
    10: {"V.10", "V.12"},
    11: {"V.10", "V.12", "V.13", "V.14"},
    12: {"V.14"},
    13: {"V.10"},
    14: {"V.10"},
    15: {"V.10"},
}

PROMPTS = {
    "V.7": """Generate {n} distinct perturbations P(lam,sigma,b,k) designed to falsify the V.7 quadratic gap law. Fixed base is -(1-lam)^2-sigma^2 at corner (1,0). Stay IN SCOPE: P must have finite positive inward slope, be locally degree one, and be separable over x=1-lam and y=sigma. Add large smooth higher-order distractions to stress the asymptotic screen. Use lam/sigma, not x/y. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"attack"}}]}}""",
    "V.8": """Generate {n} distinct perturbations designed to falsify V.8: a homogeneous inward term of degree 0<alpha<1 has gap exponent 2/(2-alpha). Choose EXACTLY ONE alpha per expression from 0.15,0.25,0.33,0.5,0.75,0.9. Use sigma**alpha, (1-lam)**alpha, or both with the SAME alpha. Never mix degrees and never add linear/lower-degree terms. Higher-order distractions may have degree >=2 only. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state alpha and attempted failure"}}]}}""",
    "V.9": """Generate {n} distinct degree-one positively homogeneous COUPLED perturbations around (lam,sigma)=(1,0) to break V.9. Every expression must be a nonseparable norm or crease, patterned on sqrt(a*(1-lam)**2+b*sigma**2) or abs(a*(1-lam)-b*sigma), with positive numeric a,b. No linear sums, products of degree 2, b/k variables, smooth distractions, gates, or saturation. Allowed + - * / ** sqrt abs; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"identify coupled ray geometry"}}]}}""",
    "V.10": """Generate {n} distinct perturbations designed to falsify V.10 for 1<alpha<2. Choose EXACTLY ONE alpha per expression from 1.1,1.2,1.35,1.5,1.65,1.8,1.9. Use sigma**alpha, (1-lam)**alpha, or both with the SAME alpha. Never mix degrees and never add constants, linear, or lower-degree terms. Distractions may have degree >=2 only and must be bounded. Allowed + - * / ** sin cos exp log abs tanh atan; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state alpha and attempted failure"}}]}}""",
    "V.11": """Generate {n} bounded finite perturbations P designed to violate the V.11 amplitude ceiling. Require P(1,0,2,3)=0 and a positive inward push. Use tanh, atan, sin, exp narrow gates, angular ridges with positive numeric denominator floors, and coupled bounded peaks. Never use tan, variable denominators without a positive floor, or unbounded singularities. Allowed + - * / ** sin cos exp sqrt abs tanh atan; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state bounded range and attack"}}]}}""",
    "V.12": """Generate {n} base objectives r(lam,sigma) designed to falsify V.12. Stay in scope: global maximum at corner (1,0), flat there with leading order beta>1, then a linear inward perturbation should yield exponent beta/(beta-1). Vary beta 2.2 through 10, odd, anisotropic, mixed leading orders, and smooth distractions. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"r","why":"attack"}}]}}""",
    "V.13": """Generate {n} base objectives r(lam,sigma) whose true maximum is interior, on an edge, or in a very thin off-corner spike. Attack the current deterministic guard: coprime grids of sizes 10,11,13,17,33 plus 4096 Halton points; seek narrow, aliased, oblique, or boundary maxima it misses. Make each finite on [0,1]^2. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"r","why":"attack"}}]}}""",
}

COMPACT_RULE = "\nCritical syntax rule: every expr must be at most 150 characters and contain only the expression. The only variable identifiers allowed are lam, sigma, b, k. Write (1-lam) literally; never use shorthand x, y, r, atan2, or assignment prefixes such as P(...)= and r(...)=."


def _load() -> dict[str, Any]:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "backend": "", "requests": [], "records": []}


def _write(state: dict[str, Any]) -> None:
    state["updated_utc"] = datetime.now(timezone.utc).isoformat()
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE)
    counterexamples = [r for r in state["records"] if r["status"] == "counterexample"]
    COUNTEREXAMPLES.write_text(json.dumps(counterexamples, indent=2), encoding="utf-8")
    guard_failures = [
        r for r in state["records"]
        if (r.get("metrics") or {}).get("legacy_grid_missed")
        or (r.get("metrics") or {}).get("adversarial_guard_missed")
    ]
    GUARD_FAILURES.write_text(json.dumps(guard_failures, indent=2), encoding="utf-8")
    _write_certificate(state)


def _write_certificate(state: dict[str, Any]) -> None:
    laws = [f"V.{i}" for i in range(7, 15)]
    lines = [
        "# Adversarial verification certificate: V.7--V.14", "",
        f"Backend: `{state.get('backend') or 'not requested'}`. Generated candidates are untrusted data; every retained expression passes the AST whitelist and is adjudicated locally.", "",
        f"Local adjudicator version: **{state.get('verifier_version', VERIFIER_VERSION)}**.", "",
        "This certificate distinguishes parse-valid proposals from candidates satisfying a theorem's hypotheses. `outside_scope` is never counted as a verification. A `counterexample` is a numerical survivor requiring independent analytic review; it is not silently deleted.", "",
        "| Law | parse-valid corpus | in-scope verified | counterexamples | outside scope | rejected/inconclusive |", "|---|---:|---:|---:|---:|---:|",
    ]
    for law in laws:
        rows = [r for r in state["records"] if r["law"] == law]
        c = Counter(r["status"] for r in rows)
        lines.append(f"| {law} | {len(rows)} | {c['verified']} | {c['counterexample']} | {c['outside_scope']} | {c['rejected'] + c['inconclusive']} |")
    total = Counter(r["status"] for r in state["records"])
    requested = sum(int(x.get("requested", 0)) for x in state["requests"])
    returned = sum(int(x.get("returned", 0)) for x in state["requests"])
    usage = Counter()
    if RAW_API_LOG.exists():
        for raw_line in RAW_API_LOG.read_text(encoding="utf-8").splitlines():
            try:
                raw_usage = json.loads(raw_line).get("usage", {})
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    usage[key] += int(raw_usage.get(key, 0) or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    lines += ["", "## Campaign accounting", "",
              f"- API items requested across small rate-safe batches: **{requested}**",
              f"- Parse-valid items returned before deduplication: **{returned}**",
              f"- Unique retained corpus: **{len(state['records'])}**",
              f"- Provider-reported prompt tokens: **{usage['prompt_tokens']:,}**",
              f"- Provider-reported completion tokens: **{usage['completion_tokens']:,}**",
              f"- Provider-reported total tokens: **{usage['total_tokens']:,}**",
              f"- In-scope verified: **{total['verified']}**",
              f"- Numerical counterexamples requiring review: **{total['counterexample']}**",
              f"- Outside theorem hypotheses: **{total['outside_scope']}**",
              "", "## Counterexample ledger", ""]
    survivors = [r for r in state["records"] if r["status"] == "counterexample"]
    if survivors:
        for r in survivors:
            lines += [f"### {r['law']} / {r['name']}", "", f"- Expression: `{r['expr']}`",
                      *( [f"- Base: `{r['base_expr']}`"] if r.get("base_expr") else [] ),
                      f"- Reason: {r['reason']}", f"- Metrics: `{json.dumps(r.get('metrics', {}), sort_keys=True)}`", ""]
    else:
        lines.append("No numerical survivor is currently logged.")
    guard_failures = [
        r for r in state["records"]
        if (r.get("metrics") or {}).get("legacy_grid_missed")
        or (r.get("metrics") or {}).get("adversarial_guard_missed")
    ]
    lines += ["", "## Finite-guard failures", "",
              f"The adversarial search found **{len(guard_failures)}** bases with an independently confirmed off-vertex maximum that at least one finite guard missed. These confirm V.13 while refuting exhaustive interpretations of the detection algorithm; they remain in `verification_guard_failures.json`."]
    resolved = [r for r in state["records"] if any(
        h.get("from") == "counterexample" and h.get("to") != "counterexample"
        for h in r.get("adjudication_history", [])
    )]
    lines += ["", "## Resolved apparent counterexamples", ""]
    if resolved:
        for r in resolved:
            last = r["adjudication_history"][-1]
            lines.append(f"- **{r['law']} / {r['name']}**: {last['from']} -> {last['to']}; {last['reason']}")
    else:
        lines.append("None yet.")
    lines += ["", "## Reproduce or resume", "",
              "`python experiments/run_verification_campaign.py --api --per-law 64 --in-scope-per-law 64 --batch-size 32 --model stealth/ox-alpha`", "",
              "Rerunning resumes from the JSON checkpoint and does not erase prior candidates or counterexamples."]
    CERTIFICATE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--per-law", type=int, default=64, help="minimum parse-valid corpus per law")
    ap.add_argument("--in-scope-per-law", type=int, default=64,
                    help="minimum verified-plus-counterexample denominator per law")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-attempts-per-law", type=int, default=32)
    ap.add_argument("--model", default="stealth/ox-alpha")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--retries", type=int, default=8)
    ap.add_argument("--laws", nargs="+", choices=[f"V.{i}" for i in range(7, 15)],
                    help="optional theorem subset; the default is V.7 through V.14")
    ap.add_argument("--focus-counterexamples", action="store_true",
                    help="ask for mutations of live numerical survivors for the selected law")
    args = ap.parse_args()
    if min(args.per_law, args.in_scope_per_law, args.batch_size, args.max_attempts_per_law) < 1:
        ap.error("campaign sizes must be positive")

    from categorical_polytope.base_search import Candidate, propose_pairs
    from categorical_polytope.interaction_search import propose_candidates
    from categorical_polytope.verification_campaign import verify_base, verify_combined, verify_interaction

    state = _load()
    # Re-adjudicate only after the verifier version changes. The current legacy
    # checkpoint was already fully refreshed before versioning was introduced.
    prior_version = int(state.get("verifier_version", VERIFIER_VERSION))
    if prior_version != VERIFIER_VERSION:
        affected_laws = set().union(*(
            REVERIFY_LAWS_BY_VERSION.get(version, set())
            for version in range(prior_version + 1, VERIFIER_VERSION + 1)
        ))
        refreshed = []
        for old in state["records"]:
            if old["law"] not in affected_laws:
                refreshed.append(old)
                continue
            note = old.get("note", "")
            if old["law"] == "V.14":
                new = verify_combined(Candidate(old["name"] + "_b", old["base_expr"], "model", note),
                                      Candidate(old["name"] + "_p", old["expr"], "model", note))
            elif old["law"] in ("V.12", "V.13"):
                new = verify_base(old["law"], Candidate(old["name"], old["expr"], "model", note))
            else:
                new = verify_interaction(old["law"], Candidate(old["name"], old["expr"], "model", note))
            row = new.as_dict()
            history = list(old.get("adjudication_history", []))
            if old.get("status") != row["status"]:
                history.append({"utc": datetime.now(timezone.utc).isoformat(), "from": old.get("status"),
                                "to": row["status"], "reason": row["reason"]})
            if history:
                row["adjudication_history"] = history
                row["initial_status"] = old.get("initial_status", old.get("status"))
            refreshed.append(row)
        state["records"] = refreshed
    state["verifier_version"] = VERIFIER_VERSION
    _write(state)
    if not args.api:
        print(f"Loaded {len(state['records'])} records; wrote {CERTIFICATE}")
        return

    laws = args.laws or [f"V.{i}" for i in range(7, 15)]
    seen = {(r["law"], r.get("base_expr", ""), r["expr"]) for r in state["records"]}
    for law in laws:
        retained = sum(1 for r in state["records"] if r["law"] == law)
        in_scope = sum(1 for r in state["records"] if r["law"] == law and r["status"] in ("verified", "counterexample"))
        attempts = 0
        while (retained < args.per_law or in_scope < args.in_scope_per_law) and attempts < args.max_attempts_per_law:
            attempts += 1
            ask = args.batch_size
            if law == "V.14":
                focus = ""
                if args.focus_counterexamples:
                    survivors = [r for r in state["records"] if r["law"] == law and r["status"] == "counterexample"]
                    if survivors:
                        exemplar = survivors[-1]
                        focus = (f"\nA current numerical survivor uses base {exemplar['base_expr']} and perturbation {exemplar['expr']}. Generate weighted-homogeneous, coefficient, cancellation, and scale variants that preserve the corrected theorem hypotheses and try to reproduce its mismatch.")
                proposed, backend = propose_pairs(ask, model=args.model, base_url=args.base_url,
                                                  focus=focus)
                records = [verify_combined(b, p) for b, p in proposed]
            else:
                focus = ""
                if args.focus_counterexamples:
                    survivors = [r for r in state["records"] if r["law"] == law and r["status"] == "counterexample"]
                    if survivors:
                        exemplar = survivors[-1]
                        focus = (f"\nA current numerical survivor is {exemplar['expr']}. Generate coefficient, scale, and functional variants that preserve the theorem hypotheses and try to reproduce its mismatch.")
                proposed, backend = propose_candidates(
                    ask, model=args.model, base_url=args.base_url,
                    prompt=PROMPTS[law].format(n=ask) + focus + COMPACT_RULE,
                    retries=args.retries,
                )
                records = ([verify_base(law, c) for c in proposed] if law in ("V.12", "V.13")
                           else [verify_interaction(law, c) for c in proposed])
            state["backend"] = backend
            state["requests"].append({"utc": datetime.now(timezone.utc).isoformat(), "law": law,
                                      "requested": ask, "returned": len(records), "backend": backend})
            fresh = []
            for record in records:
                key = (record.law, record.base_expr, record.expr)
                if key not in seen:
                    seen.add(key)
                    fresh.append(record.as_dict())
            state["records"].extend(fresh)
            retained += len(fresh)
            _write(state)
            counts = Counter(r["status"] for r in state["records"] if r["law"] == law)
            in_scope = counts["verified"] + counts["counterexample"]
            print(f"{law} batch {attempts}: returned {len(records)}/{ask}, fresh {len(fresh)}, corpus {retained}/{args.per_law}, in-scope {in_scope}/{args.in_scope_per_law}, verified {counts['verified']}, counterexamples {counts['counterexample']}", flush=True)
        if retained < args.per_law or in_scope < args.in_scope_per_law:
            print(f"{law}: stopped after {attempts} attempts with corpus {retained}/{args.per_law}, in-scope {in_scope}/{args.in_scope_per_law}", flush=True)
    _write(state)
    print(f"Wrote {STATE}")
    print(f"Wrote {COUNTEREXAMPLES}")
    print(f"Wrote {CERTIFICATE}")


if __name__ == "__main__":
    main()
