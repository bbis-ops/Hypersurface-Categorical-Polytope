#!/usr/bin/env python3
"""
Checkpointed adversarial API corpus for V.7--V.14.

The storage, deduplication, re-adjudication, and reversal history live in
`categorical_polytope.adjudication.Ledger`, which knows nothing about these
theorems. Everything law-specific is behind `PolytopeDomain`. What is left here
is wiring: the CLI, the proposal loop, and this domain's report rendering.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.adjudication import Ledger  # noqa: E402
from categorical_polytope.adjudication.polytope import (  # noqa: E402
    PAIR_LAW,
    PolytopeDomain,
)

STATE = ROOT / "experiments" / "verification_campaign.json"
CERTIFICATE = ROOT / "docs" / "VERIFICATION_CERTIFICATE.md"
COUNTEREXAMPLES = ROOT / "experiments" / "verification_counterexamples.json"
GUARD_FAILURES = ROOT / "experiments" / "verification_guard_failures.json"
RAW_API_LOG = ROOT / "experiments" / "verification_api_raw.jsonl"


def _guard_failures(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in records
        if (r.get("metrics") or {}).get("legacy_grid_missed")
        or (r.get("metrics") or {}).get("adversarial_guard_missed")
    ]


def _persist(ledger: Ledger, domain: PolytopeDomain) -> None:
    """Checkpoint the corpus, then regenerate every derived artifact from it."""
    ledger.save(STATE)
    survivors = [r for r in ledger.records if r["status"] == "counterexample"]
    COUNTEREXAMPLES.write_text(json.dumps(survivors, indent=2), encoding="utf-8")
    GUARD_FAILURES.write_text(
        json.dumps(_guard_failures(ledger.records), indent=2), encoding="utf-8"
    )
    _write_certificate(ledger, domain)


def _write_certificate(ledger: Ledger, domain: PolytopeDomain) -> None:
    state = ledger.state
    lines = [
        "# Adversarial verification certificate: V.7--V.14", "",
        f"Backend: `{state.get('backend') or 'not requested'}`. Generated candidates are untrusted data; every retained expression passes the AST whitelist and is adjudicated locally.", "",
        f"Local adjudicator version: **{ledger.verifier_version}**.", "",
        "This certificate distinguishes parse-valid proposals from candidates satisfying a theorem's hypotheses. `outside_scope` is never counted as a verification. A `counterexample` is a numerical survivor requiring independent analytic review; it is not silently deleted.", "",
        "| Law | parse-valid corpus | in-scope verified | counterexamples | outside scope | rejected/inconclusive |", "|---|---:|---:|---:|---:|---:|",
    ]
    for law in domain.rule_ids:
        c = ledger.counts(domain, law)
        lines.append(f"| {law} | {sum(c.values())} | {c['verified']} | {c['counterexample']} | {c['outside_scope']} | {c['rejected'] + c['inconclusive']} |")
    total = ledger.counts(domain)
    requested = sum(int(x.get("requested", 0)) for x in ledger.requests)
    returned = sum(int(x.get("returned", 0)) for x in ledger.requests)
    usage: Counter = Counter()
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
              f"- Unique retained corpus: **{len(ledger)}**",
              f"- Provider-reported prompt tokens: **{usage['prompt_tokens']:,}**",
              f"- Provider-reported completion tokens: **{usage['completion_tokens']:,}**",
              f"- Provider-reported total tokens: **{usage['total_tokens']:,}**",
              f"- In-scope verified: **{total['verified']}**",
              f"- Numerical counterexamples requiring review: **{total['counterexample']}**",
              f"- Outside theorem hypotheses: **{total['outside_scope']}**",
              "", "## Counterexample ledger", ""]
    survivors = [r for r in ledger.records if r["status"] == "counterexample"]
    if survivors:
        for r in survivors:
            payload = r["payload"]
            lines += [f"### {r['rule_id']} / {r['name']}", "", f"- Expression: `{payload['expr']}`",
                      *([f"- Base: `{payload['base_expr']}`"] if payload.get("base_expr") else []),
                      f"- Reason: {r['reason']}", f"- Metrics: `{json.dumps(r.get('metrics', {}), sort_keys=True)}`", ""]
    else:
        lines.append("No numerical survivor is currently logged.")
    lines += ["", "## Finite-guard failures", "",
              f"The adversarial search found **{len(_guard_failures(ledger.records))}** bases with an independently confirmed off-vertex maximum that at least one finite guard missed. These confirm V.13 while refuting exhaustive interpretations of the detection algorithm; they remain in `verification_guard_failures.json`."]
    resolved = [r for r in ledger.reversals() if any(
        h.get("from") == "counterexample" and h.get("to") != "counterexample"
        for h in r.get("adjudication_history", [])
    )]
    lines += ["", "## Resolved apparent counterexamples", ""]
    if resolved:
        for r in resolved:
            last = r["adjudication_history"][-1]
            lines.append(f"- **{r['rule_id']} / {r['name']}**: {last['from']} -> {last['to']}; {last['reason']}")
    else:
        lines.append("None yet.")
    lines += ["", "## Reproduce or resume", "",
              "`python experiments/run_verification_campaign.py --api --per-law 64 --in-scope-per-law 64 --batch-size 32`", "",
              "Add `--model` / `--base-url`, or `--preset`, to choose an endpoint; the backend used for this run is recorded above.", "",
              "Rerunning resumes from the JSON checkpoint and does not erase prior candidates or counterexamples."]
    CERTIFICATE.write_text("\n".join(lines), encoding="utf-8")


def _survivor_focus(ledger: Ledger, domain: PolytopeDomain, law: str) -> str:
    """Ask for mutations of a live numerical survivor, if there is one."""
    survivors = [
        r for r in ledger.records
        if ledger.rule_id_of(r) == law and r["status"] == "counterexample"
    ]
    if not survivors:
        return ""
    exemplar = survivors[-1]
    if law == PAIR_LAW:
        return (f"\nA current numerical survivor uses base {exemplar['payload']['base_expr']} and perturbation {exemplar['payload']['expr']}. Generate weighted-homogeneous, coefficient, cancellation, and scale variants that preserve the corrected theorem hypotheses and try to reproduce its mismatch.")
    return (f"\nA current numerical survivor is {exemplar['payload']['expr']}. Generate coefficient, scale, and functional variants that preserve the theorem hypotheses and try to reproduce its mismatch.")


def main() -> None:
    domain = PolytopeDomain()
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--per-law", type=int, default=64, help="minimum parse-valid corpus per law")
    ap.add_argument("--in-scope-per-law", type=int, default=64,
                    help="minimum verified-plus-counterexample denominator per law")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-attempts-per-law", type=int, default=32)
    ap.add_argument("--model", default=None,
                    help="any OpenAI-compatible model id; default resolves from preset/env")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--preset", default=None, help="named endpoint preset (openai, openrouter, nemotron); --model/--base-url override it")
    ap.add_argument("--retries", type=int, default=8)
    ap.add_argument("--laws", nargs="+", choices=list(domain.rule_ids),
                    help="optional theorem subset; the default is V.7 through V.14")
    ap.add_argument("--focus-counterexamples", action="store_true",
                    help="ask for mutations of live numerical survivors for the selected law")
    args = ap.parse_args()
    if min(args.per_law, args.in_scope_per_law, args.batch_size, args.max_attempts_per_law) < 1:
        ap.error("campaign sizes must be positive")

    from categorical_polytope.base_search import propose_pairs
    from categorical_polytope.interaction_search import propose_candidates

    ledger = Ledger.load(STATE)
    # Re-adjudicate only when the adjudicator version has moved. Any reversal is
    # appended to the row's history, never written over it.
    report = ledger.sync_verifier(domain)
    if report.changed:
        print(report.summary(), flush=True)
    _persist(ledger, domain)
    if not args.api:
        print(f"Loaded {len(ledger)} records; wrote {CERTIFICATE}")
        return

    laws = args.laws or list(domain.rule_ids)
    seen = ledger.seen(domain)
    for law in laws:
        retained = sum(1 for r in ledger.records if ledger.rule_id_of(r) == law)
        in_scope = ledger.in_scope_total(domain, law)
        attempts = 0
        while (retained < args.per_law or in_scope < args.in_scope_per_law) and attempts < args.max_attempts_per_law:
            attempts += 1
            ask = args.batch_size
            focus = _survivor_focus(ledger, domain, law) if args.focus_counterexamples else ""
            if law == PAIR_LAW:
                proposed, backend = propose_pairs(ask, model=args.model, base_url=args.base_url,
                                                  preset=args.preset, focus=focus)
                records = [domain.adjudicate_pair(b, p) for b, p in proposed]
            else:
                proposed, backend = propose_candidates(
                    ask, model=args.model, base_url=args.base_url, preset=args.preset,
                    prompt=domain.proposal_prompt(law, ask, focus),
                    retries=args.retries,
                )
                records = [domain.adjudicate(law, c) for c in proposed]
            ledger.state["backend"] = backend
            ledger.record_request(law=law, requested=ask, returned=len(records), backend=backend)
            fresh = ledger.admit(domain, (domain.to_row(r) for r in records), seen=seen)
            retained += len(fresh)
            _persist(ledger, domain)
            counts = ledger.counts(domain, law)
            in_scope = counts["verified"] + counts["counterexample"]
            print(f"{law} batch {attempts}: returned {len(records)}/{ask}, fresh {len(fresh)}, corpus {retained}/{args.per_law}, in-scope {in_scope}/{args.in_scope_per_law}, verified {counts['verified']}, counterexamples {counts['counterexample']}", flush=True)
        if retained < args.per_law or in_scope < args.in_scope_per_law:
            print(f"{law}: stopped after {attempts} attempts with corpus {retained}/{args.per_law}, in-scope {in_scope}/{args.in_scope_per_law}", flush=True)
    _persist(ledger, domain)
    print(f"Wrote {STATE}")
    print(f"Wrote {COUNTEREXAMPLES}")
    print(f"Wrote {CERTIFICATE}")


if __name__ == "__main__":
    main()
