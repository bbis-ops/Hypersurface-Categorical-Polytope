#!/usr/bin/env python3
"""
Domain two campaign: drive code-property candidates through the shared ledger.

Without --api this runs the hand-written seed bank and costs nothing. With
--api it asks a model for candidate inputs, adjudicates each one locally
against a reference implementation, and checkpoints after every batch.

Same `Ledger`, same five statuses, same reversal history as the V.7--V.14
campaign; only the `Domain` differs. Model proposals are untrusted data: every
payload goes through `literal_eval`, and a hostile or malformed one is recorded
as `rejected` rather than executed.

Token budget
------------
`--max-tokens` and `--batch-size` move together: raising one without the other
either wastes budget or courts truncation. The right pair is a property of the
model, not something to guess - run `--calibrate` first. It spends one batch,
reports tokens per record, whether the reply parsed whole, and the in-scope
yield, then writes nothing.

A reply truncated at the cap is salvaged rather than discarded, so an oversized
batch degrades instead of costing the whole request.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.adjudication import Ledger  # noqa: E402
from categorical_polytope.adjudication.codeprops import CodePropertyDomain  # noqa: E402
from categorical_polytope.adjudication.codeprops.prompts import (  # noqa: E402
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_TOKENS,
    focus_prompt,
    parse_input_proposals,
    proposal_prompt,
)
from categorical_polytope.adjudication.codeprops.seeds import SEEDS  # noqa: E402
from categorical_polytope.adjudication.status import Status  # noqa: E402

STATE = ROOT / "experiments" / "code_properties.json"
REPORT = ROOT / "docs" / "CODE_PROPERTIES.md"
RAW_API_LOG = ROOT / "experiments" / "code_properties_api_raw.jsonl"
RATE_STATE = ROOT / "experiments" / "code_properties_api_rate_state.json"


def _token_usage() -> Counter:
    """Provider-reported tokens across every logged request."""
    usage: Counter = Counter()
    if not RAW_API_LOG.exists():
        return usage
    for line in RAW_API_LOG.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw = entry.get("usage") or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage[key] += int(raw.get(key, 0) or 0)
        usage["requests"] += 1
        usage["parsed_items"] += int(entry.get("parsed_items", 0) or 0)
    return usage


def _write_report(ledger: Ledger, domain: CodePropertyDomain) -> None:
    total = ledger.counts(domain)
    usage = _token_usage()
    backend = ledger.state.get("backend") or "seed bank only (no API)"
    lines = [
        "# Domain two: generated-code property violation", "",
        f"Backend: `{backend}`. Adjudicator: CPython running a reference implementation.",
        "Model proposals are candidate *inputs* only; every payload passes `literal_eval`",
        "and is adjudicated locally, so no verdict depends on which model produced it.", "",
        f"Local adjudicator version: **{ledger.verifier_version}**.", "",
        "`outside_scope` is decided from the declared contract *before* the property is",
        "run, so a failing input can never be retired as unsupported after the fact.", "",
        "| Rule | corpus | verified | counterexamples | outside contract | rejected/inconclusive |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for rule_id in domain.rule_ids:
        c = ledger.counts(domain, rule_id)
        lines.append(
            f"| `{rule_id}` | {sum(c.values())} | {c['verified']} | {c['counterexample']} "
            f"| {c['outside_scope']} | {c['rejected'] + c['inconclusive']} |"
        )
    lines += ["", "## Denominator", "",
              f"- Retained corpus: **{len(ledger)}**",
              f"- In-scope (verified + counterexample): **{ledger.in_scope_total(domain)}**",
              f"- Out of contract, never counted as a pass: **{total['outside_scope']}**",
              f"- Undecided within budget: **{total['inconclusive']}**",
              f"- Refused at the `literal_eval` boundary: **{total['rejected']}**", ""]

    if usage["requests"]:
        per_request = usage["total_tokens"] / usage["requests"]
        lines += ["## Campaign accounting", "",
                  f"- Requests logged: **{usage['requests']}**",
                  f"- Parse-valid items returned before deduplication: **{usage['parsed_items']}**",
                  f"- Provider-reported prompt tokens: **{usage['prompt_tokens']:,}**",
                  f"- Provider-reported completion tokens: **{usage['completion_tokens']:,}**",
                  f"- Provider-reported total tokens: **{usage['total_tokens']:,}**",
                  f"- Mean tokens per request: **{per_request:,.0f}**", ""]

    survivors = [r for r in ledger.records if r["status"] == "counterexample"]
    lines += ["## Counterexamples", ""]
    if survivors:
        for r in survivors:
            lines += [f"### `{r['rule_id']}` / {r['name']}", "",
                      f"- Input: `{r['payload']['args']}`",
                      f"- Reason: {r['reason']}",
                      *([f"- Note: {r['note']}"] if r.get("note") else []), ""]
    else:
        lines.append("None found.")

    lines += ["", "## Reversals", "",
              f"{len(ledger.reversals())} record(s) have changed verdict since first adjudication.",
              "", "## Reproduce or resume", "",
              "`python experiments/run_code_properties.py --api --preset nemotron`", "",
              "Rerunning resumes from the JSON checkpoint and does not erase prior candidates."]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def _persist(ledger: Ledger, domain: CodePropertyDomain) -> None:
    ledger.save(STATE)
    _write_report(ledger, domain)


def _last_raw_entry() -> dict | None:
    """The most recent logged request, for measuring what a batch actually cost."""
    if not RAW_API_LOG.exists():
        return None
    lines = [ln for ln in RAW_API_LOG.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _calibrate(domain: CodePropertyDomain, rules: list[str], args) -> int:
    """
    Spend one batch per rule and report what it actually bought.

    Batch and token sizing depend on how a specific model behaves - how many
    records it packs into a completion, whether it truncates, and how much of
    its output survives the contract. Guessing those wastes budget; this
    measures them, writes nothing, and prints what the numbers imply.
    """
    from categorical_polytope.interaction_search import propose_candidates

    print(f"calibrating: 1 batch of {args.batch_size} per rule, "
          f"max_tokens={args.max_tokens}\n")
    for rule_id in rules:
        before = _token_usage()
        proposed, backend = propose_candidates(
            args.batch_size,
            model=args.model, base_url=args.base_url, preset=args.preset,
            prompt=proposal_prompt(rule_id, args.batch_size),
            parser=parse_input_proposals(rule_id),
            retries=args.retries,
        )
        after = _token_usage()
        spent = after["total_tokens"] - before["total_tokens"]
        completion = after["completion_tokens"] - before["completion_tokens"]

        entry = _last_raw_entry() or {}
        response = entry.get("response") or ""
        try:
            json.loads(response)
            shape = "clean JSON"
        except (json.JSONDecodeError, TypeError):
            shape = "salvaged (reply did not parse whole)"

        print(f"--- {rule_id} ---")
        print(f"  backend            {backend}")
        print(f"  returned           {len(proposed)}/{args.batch_size} candidates")
        print(f"  reply shape        {shape}")
        print(f"  tokens             {spent:,} total, {completion:,} completion")
        if not proposed:
            print("  no candidates: check the model id, the key, and the rate limit\n")
            continue

        counts = Counter()
        for seed in proposed:
            counts[str(domain.adjudicate(seed.rule_id, seed.args).status)] += 1
        in_scope = counts["verified"] + counts["counterexample"]
        print(f"  adjudicated        {dict(counts)}")
        print(f"  in-scope yield     {in_scope}/{len(proposed)} "
              f"({100.0 * in_scope / len(proposed):.0f}%)")
        if completion:
            per_record = completion / len(proposed)
            fits = int(args.max_tokens / per_record) if per_record else 0
            print(f"  ~{per_record:.0f} completion tokens/record "
                  f"-> ~{fits} records would fill {args.max_tokens:,}")
            if shape.startswith("salvaged"):
                print(f"  SUGGEST: batch is too large for this model; try "
                      f"--batch-size {max(8, len(proposed))}")
            elif completion < args.max_tokens * 0.5:
                print(f"  SUGGEST: budget underused; try --batch-size "
                      f"{int(args.batch_size * 1.8)} or lower --max-tokens")
        print()

    print("calibration only: nothing written")
    return 0


def _survivor_focus(ledger: Ledger, rule_id: str) -> str:
    survivors = [
        r for r in ledger.records
        if ledger.rule_id_of(r) == rule_id and r["status"] == "counterexample"
    ]
    if not survivors:
        return ""
    return focus_prompt(rule_id, survivors[-1]["payload"]["args"])


def main() -> int:
    domain_rules = CodePropertyDomain().rule_ids
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", action="store_true", help="request candidates from a model")
    ap.add_argument("--timeout", type=float, default=3.0,
                    help="wall-clock budget per candidate, in seconds")
    ap.add_argument("--check", action="store_true", help="report without writing")
    ap.add_argument("--no-seeds", action="store_true",
                    help="skip the hand-written seed bank")
    ap.add_argument("--rules", nargs="+", choices=list(domain_rules),
                    help="optional rule subset; default is every rule")
    ap.add_argument("--per-rule", type=int, default=256,
                    help="minimum retained corpus per rule")
    ap.add_argument("--in-scope-per-rule", type=int, default=128,
                    help="minimum verified-plus-counterexample denominator per rule")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                    help="candidates requested per API call")
    ap.add_argument("--max-attempts-per-rule", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                    help="completion cap per request")
    ap.add_argument("--model", default=None, help="any OpenAI-compatible model id")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--preset", default=None,
                    help="named endpoint preset (openai, openrouter, nemotron)")
    ap.add_argument("--retries", type=int, default=8)
    ap.add_argument("--focus-counterexamples", action="store_true",
                    help="ask for mutations of a live counterexample")
    ap.add_argument("--calibrate", action="store_true",
                    help="spend one batch per rule, measure tokens/yield/truncation, write nothing")
    args = ap.parse_args()
    if min(args.per_rule, args.in_scope_per_rule, args.batch_size,
           args.max_attempts_per_rule, args.max_tokens) < 1:
        ap.error("campaign sizes must be positive")

    domain = CodePropertyDomain(timeout=args.timeout)
    ledger = Ledger.load(STATE)
    report = ledger.sync_verifier(domain)
    if report.changed:
        print(report.summary(), flush=True)

    if not args.no_seeds:
        fresh = ledger.admit(
            domain, [domain.to_row(s.rule_id, s.name, s.args, s.note) for s in SEEDS]
        )
        print(f"seed bank: {len(SEEDS)} entries, {len(fresh)} newly admitted", flush=True)

    if args.api:
        # The transport reads its budget and provenance paths from the
        # environment; set them here so a campaign is reproducible from flags.
        os.environ["POLYTOPE_API_MAX_TOKENS"] = str(args.max_tokens)
        os.environ["POLYTOPE_API_RAW_LOG"] = str(RAW_API_LOG)
        os.environ["POLYTOPE_API_RATE_STATE"] = str(RATE_STATE)
        os.environ["POLYTOPE_API_CONFIGURED_BATCH_SIZE"] = str(args.batch_size)
        if args.calibrate:
            return _calibrate(domain, list(args.rules or domain_rules), args)
        from categorical_polytope.interaction_search import propose_candidates

        seen = ledger.seen(domain)
        for rule_id in (args.rules or list(domain_rules)):
            retained = sum(1 for r in ledger.records if ledger.rule_id_of(r) == rule_id)
            in_scope = ledger.in_scope_total(domain, rule_id)
            attempts = 0
            while ((retained < args.per_rule or in_scope < args.in_scope_per_rule)
                   and attempts < args.max_attempts_per_rule):
                attempts += 1
                focus = _survivor_focus(ledger, rule_id) if args.focus_counterexamples else ""
                proposed, backend = propose_candidates(
                    args.batch_size,
                    model=args.model, base_url=args.base_url, preset=args.preset,
                    prompt=proposal_prompt(rule_id, args.batch_size) + focus,
                    parser=parse_input_proposals(rule_id),
                    retries=args.retries,
                )
                ledger.state["backend"] = backend
                rows = [domain.to_row(s.rule_id, s.name, s.args, s.note) for s in proposed]
                fresh = ledger.admit(domain, rows, seen=seen)
                ledger.record_request(rule_id=rule_id, requested=args.batch_size,
                                      returned=len(proposed), fresh=len(fresh),
                                      backend=backend)
                retained += len(fresh)
                _persist(ledger, domain)
                counts = ledger.counts(domain, rule_id)
                in_scope = counts["verified"] + counts["counterexample"]
                print(
                    f"{rule_id} batch {attempts}: returned {len(proposed)}/{args.batch_size}, "
                    f"fresh {len(fresh)}, corpus {retained}/{args.per_rule}, "
                    f"in-scope {in_scope}/{args.in_scope_per_rule}, "
                    f"counterexamples {counts['counterexample']}",
                    flush=True,
                )
                if not proposed:
                    print(f"  no candidates returned ({backend}); moving on", flush=True)
                    break
            if retained < args.per_rule or in_scope < args.in_scope_per_rule:
                print(f"{rule_id}: stopped after {attempts} attempt(s) with corpus "
                      f"{retained}/{args.per_rule}, in-scope {in_scope}/{args.in_scope_per_rule}",
                      flush=True)

    ledger.validate()
    counts = ledger.counts(domain)
    print(f"\ncorpus: {len(ledger)}")
    for status in Status:
        print(f"  {str(status):15} {counts[str(status)]}")
    print(f"  in-scope denominator: {ledger.in_scope_total(domain)}/{len(ledger)}")

    usage = _token_usage()
    if usage["requests"]:
        print(f"  tokens: {usage['total_tokens']:,} over {usage['requests']} request(s) "
              f"({usage['total_tokens'] / usage['requests']:,.0f} per request)")

    missing = [str(s) for s in Status if not counts[str(s)]]
    if missing:
        print(f"WARNING: corpus never produced: {', '.join(missing)}", file=sys.stderr)

    if args.check:
        print("--check: nothing written")
        return 0

    _persist(ledger, domain)
    print(f"wrote {STATE}")
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
