#!/usr/bin/env python3
"""
Multi-domain adversarial campaign.

Drives every registered domain through the same ledger, the same five statuses,
and one shared rate budget. Adding a domain is an entry in
`adjudication.registry` plus a class satisfying `Domain`; this runner does not
change.

    python experiments/run_campaign.py --list
    python experiments/run_campaign.py --api --preset nemotron --calibrate
    python experiments/run_campaign.py --api --preset nemotron
    python experiments/run_campaign.py --domains codeprops --api --preset nemotron

Model proposals are untrusted data in every domain: candidates are parsed under
a whitelist and adjudicated locally, so no verdict depends on which model
produced them. Without --api this re-adjudicates and re-reports existing
corpora and costs nothing.

Round-robin, not sequential
---------------------------
Rules are interleaved across domains rather than draining one domain first.
A campaign that dies halfway leaves every domain partially advanced instead of
one finished and the rest untouched, and a rate limit hit on one domain does
not starve the others.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.adjudication import (  # noqa: E402
    Ledger,
    Screenable,
    Status,
    summarise,
    tally,
)
from categorical_polytope.adjudication.domain import Generative, Transport  # noqa: E402
from categorical_polytope.adjudication.registry import (  # noqa: E402
    DOMAIN_NAMES,
    RATE_STATE,
    REGISTRY,
    DomainSpec,
    resolve,
)

SUMMARY = ROOT / "docs" / "CAMPAIGN.md"


@dataclass
class Active:
    """One domain, loaded and ready to be advanced."""

    spec: DomainSpec
    domain: Any
    ledger: Ledger
    paths: dict[str, Path]
    seen: set

    @property
    def name(self) -> str:
        return self.spec.name

    def rules(self, wanted: list[str] | None) -> list[str]:
        ids = list(self.domain.rule_ids)
        return [r for r in ids if r in wanted] if wanted else ids

    def retained(self, rule_id: str) -> int:
        return sum(1 for r in self.ledger.records if self.ledger.rule_id_of(r) == rule_id)

    def in_scope(self, rule_id: str) -> int:
        return self.ledger.in_scope_total(self.domain, rule_id)

    def survivor_focus(self, rule_id: str) -> str:
        live = [
            r for r in self.ledger.records
            if self.ledger.rule_id_of(r) == rule_id and r["status"] == "counterexample"
        ]
        return self.domain.focus_for(live[-1]) if live else ""


def _load(spec: DomainSpec, timeout: float) -> Active:
    paths = spec.paths(ROOT)
    domain = spec.factory(timeout=timeout)
    ledger = Ledger.load(paths["corpus"])
    report = ledger.sync_verifier(domain)
    if report.changed:
        print(f"[{spec.name}] {report.summary()}", flush=True)
    return Active(spec, domain, ledger, paths, ledger.seen(domain))


def _mix(counts: dict) -> str:
    """The screening breakdown of one batch, compactly."""
    return "/".join(f"{name[:4]}={n}" for name, n in counts.items() if n)


def _token_usage(raw_log: Path) -> Counter:
    usage: Counter = Counter()
    if not raw_log.exists():
        return usage
    for line in raw_log.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        block = entry.get("usage") or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage[key] += int(block.get(key, 0) or 0)
        # Reported per request by OpenRouter; 0 on a free model. Tracked in
        # thousandths of a cent so the Counter stays integral.
        usage["microcents"] += int(round(float(block.get("cost", 0) or 0) * 1e6))
        usage["requests"] += 1
        usage["parsed_items"] += int(entry.get("parsed_items", 0) or 0)
    return usage


def _spend(actives: list["Active"]) -> float:
    """Total provider-reported cost, in dollars, across every domain's log."""
    total = 0
    for active in actives:
        total += _token_usage(active.paths["raw_log"])["microcents"]
    return total / 1e6


def _throttle_interval() -> float:
    """Current shared pacing interval, or 0 when nothing is throttling."""
    try:
        state = json.loads((ROOT / RATE_STATE).read_text(encoding="utf-8"))
        return float(state.get("interval_seconds", 0.0) or 0.0)
    except (OSError, ValueError):
        return 0.0


def _throttle_wait() -> float:
    """Seconds still to wait before the shared pacing allows a request."""
    import time as _time

    try:
        state = json.loads((ROOT / RATE_STATE).read_text(encoding="utf-8"))
        return max(0.0, float(state.get("next_allowed_epoch", 0.0)) - _time.time())
    except (OSError, ValueError):
        return 0.0


def _throttle_count() -> int:
    try:
        state = json.loads((ROOT / RATE_STATE).read_text(encoding="utf-8"))
        return int(state.get("total_throttles", 0) or 0)
    except (OSError, ValueError):
        return 0


def _last_reply(raw_log: Path) -> dict[str, Any]:
    """The most recent logged reply, or {} when there is none to read."""
    if not raw_log.exists():
        return {}
    try:
        lines = [ln for ln in raw_log.read_text(encoding="utf-8").splitlines()
                 if ln.strip()]
        return json.loads(lines[-1])
    except (OSError, ValueError, IndexError):
        return {}


def _hit_the_cap(entry: dict[str, Any], max_tokens: int = 0) -> bool:
    """
    Whether a reply stopped because it ran out of completion budget.

    `finish_reason` is only recorded on logs written from 2026-08-28 on;
    spending the whole cap says the same thing for older entries.
    """
    completion = int((entry.get("usage") or {}).get("completion_tokens", 0) or 0)
    return entry.get("finish_reason") == "length" or (
        max_tokens > 0 and completion >= max_tokens
    )


def _diagnose_empty(
    raw_log: Path, preset: str | None, max_tokens: int = 0
) -> list[str]:
    """
    Say why a batch came back with nothing, from the reply that was logged.

    The expensive failure is a model narrating its plan as ordinary content
    until the cap: the request succeeds, burns the whole budget, and yields
    nothing. That is worth naming precisely rather than leaving as "no
    candidates", and the operator needs to know the reply was *cut off* -
    otherwise a truncated plan reads as a formatting problem.
    """
    if not raw_log.exists():
        return ["  The reply carried no content at all. Check the key and the model id."]
    entry = _last_reply(raw_log)
    if not entry:
        return []
    body = entry.get("response") or ""
    usage = entry.get("usage") or {}
    detail = usage.get("completion_tokens_details") or {}
    thinking = int(detail.get("reasoning_tokens", 0) or 0)
    completion = int(usage.get("completion_tokens", 0) or 0)
    truncated = _hit_the_cap(entry, max_tokens)
    # Match on structure, not on opening words. Keying off "here's a thinking
    # process:" missed a reply that starts straight in on the task ("We need to
    # produce JSON with candidates ...").
    #
    # A reply that is all reasoning and no envelope does NOT mean the model
    # ignored response_format. A model with JSON mode that runs out of budget
    # mid-thought has no final content to return, so the provider sends the
    # partial reasoning trace in `content` instead. Same symptom, and the fix
    # is the budget: reasoning scales with the batch, the cap does not shorten
    # it, so a batch that does not fit will burn the cap however large it is.
    narrated = truncated and '"candidates"' not in body
    out: list[str] = []
    if narrated:
        out += [
            f"  The reply is {len(body):,} chars of reasoning with no JSON envelope, "
            f"cut off at the {completion:,}-token cap",
            f"  ({thinking:,} of those billed as reasoning). The budget ran out before "
            "the model could answer,",
            "  so what came back is its partial thinking, not a formatting failure.",
            "  Reasoning grows with the batch, so cut the batch before raising the cap:",
            f"    --batch-size 4 --max-tokens {max(14000, completion + 6000)}",
            "  Then read the tokens/record line from that run and size the cap from it.",
        ]
    elif truncated:
        out += [
            f"  The reply hit the {completion:,}-token cap mid-record "
            f"({len(body):,} chars) and no complete record survived.",
            "  Raise --max-tokens, or lower --batch-size so a batch fits the cap.",
        ]
    elif not body.strip():
        out.append("  The reply was empty. Try --preset nemotron-super.")
    else:
        out.append(f"  The reply had {len(body):,} chars but no parseable candidates.")
    if preset == "nemotron":
        out.append("  (nemotron = lightning:free, which advertises no response_format.)")
    return out


def _summary_actives(actives: list[Active], timeout: float) -> list[Active]:
    """
    Every registered domain, in registry order, for the summary page.

    `--domains` scopes what a run *advances*; it must not scope what the
    summary *reports*. Writing the page from the selected domains alone
    republishes it as though the rest did not exist - a `--domains polyhedra`
    run once reduced it to one row and printed that domain's 131 records as the
    campaign total, silently dropping 2,403 others.

    Domains this run advanced are reused as loaded, so the page reflects the
    work just done. The rest are read straight off disk and never saved: the
    summary reports what is recorded for them, at whatever verifier version
    they were recorded under.
    """
    advanced = {a.name: a for a in actives}
    full: list[Active] = []
    for name, spec in REGISTRY.items():
        if name in advanced:
            full.append(advanced[name])
            continue
        paths = spec.paths(ROOT)
        try:
            ledger = Ledger.load(paths["corpus"])
        except (OSError, ValueError) as exc:
            print(f"[{name}] left out of the summary: {exc}", file=sys.stderr, flush=True)
            continue
        # `seen` is only for admission; a row that is merely counted needs none.
        full.append(Active(spec, spec.factory(timeout=timeout), ledger, paths, set()))
    return full


def _write_summary(actives: list[Active]) -> None:
    """
    One page across every domain, so the campaign reads as a single result.

    Callers must pass every registered domain, not just the advanced ones -
    see `_summary_actives`.
    """
    lines = [
        "# Multi-domain adversarial campaign", "",
        "Every domain below is adjudicated by a machine that is ground truth for its",
        "own rules - stdlib arithmetic, or CPython running a reference implementation.",
        "No verdict anywhere in this table came from a model's opinion.", "",
        "Only `verified` is a pass. Candidates the adjudicator could not decide stay in",
        "the corpus and stay counted, so the denominator cannot be improved by dropping",
        "the hard cases.", "",
        "| Domain | verifier | corpus | verified | counterexamples | outside scope | undecided | refused | in-scope denominator |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    grand: Counter = Counter()
    for a in actives:
        c = a.ledger.counts(a.domain)
        grand.update(c)
        grand["corpus"] += len(a.ledger)
        lines.append(
            f"| `{a.name}` | v{a.ledger.verifier_version} | {len(a.ledger)} "
            f"| {c['verified']} | {c['counterexample']} | {c['outside_scope']} "
            f"| {c['inconclusive']} | {c['rejected']} "
            f"| {a.ledger.in_scope_total(a.domain)} |"
        )
    lines.append(
        f"| **total** | | **{grand['corpus']}** | **{grand['verified']}** "
        f"| **{grand['counterexample']}** | **{grand['outside_scope']}** "
        f"| **{grand['inconclusive']}** | **{grand['rejected']}** "
        f"| **{grand['verified'] + grand['counterexample']}** |"
    )

    lines += ["", "## Domains", ""]
    for a in actives:
        reversals = len(a.ledger.reversals())
        lines += [
            f"### `{a.name}`", "",
            f"- {a.spec.summary}",
            f"- Rules: {len(list(a.domain.rule_ids))}",
            f"- Reversals retained: {reversals}",
            f"- Report: [`{a.spec.report}`]({Path(a.spec.report).name})", "",
        ]

    usage: Counter = Counter()
    for a in actives:
        usage.update(_token_usage(a.paths["raw_log"]))
    if usage["requests"]:
        lines += ["## Campaign accounting", "",
                  f"- Requests logged: **{usage['requests']}**",
                  f"- Parse-valid items before deduplication: **{usage['parsed_items']}**",
                  f"- Provider-reported total tokens: **{usage['total_tokens']:,}**",
                  f"- Mean tokens per request: **{usage['total_tokens'] / usage['requests']:,.0f}**",
                  ""]

    counterexamples = [
        (a.name, r) for a in actives for r in a.ledger.records
        if r["status"] == "counterexample"
    ]
    lines += ["## Counterexamples across all domains", ""]
    if counterexamples:
        lines += [f"- `{name}` / `{r['rule_id']}` / {r['name']}: {r['reason']}"
                  for name, r in counterexamples]
    else:
        lines.append("None currently logged.")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _report_domain(active: Active) -> None:
    """Regenerate a domain's own report by delegating to its existing runner."""
    import importlib.util

    module_name = {
        "polytope": "run_verification_campaign",
        "codeprops": "run_code_properties",
        "polyhedra": "run_polyhedra",
    }.get(active.name)
    if not module_name:
        return
    path = ROOT / "experiments" / f"{module_name}.py"
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location(f"_report_{module_name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    writer = getattr(module, "_write_certificate", None) or getattr(module, "_write_report", None)
    if writer:
        writer(active.ledger, active.domain)


def _persist(active: Active) -> None:
    active.ledger.save(active.paths["corpus"])
    _report_domain(active)


def _print_totals(actives: list[Active]) -> None:
    print("\n=== campaign ===")
    grand: Counter = Counter()
    for a in actives:
        c = a.ledger.counts(a.domain)
        grand.update(c)
        print(f"  {a.name:14} corpus {len(a.ledger):5}  "
              + "  ".join(f"{str(s)[:6]}={c[str(s)]}" for s in Status)
              + f"  in-scope {a.ledger.in_scope_total(a.domain)}")
    spent = _spend(actives)
    if spent > 0:
        print(f"  {'SPEND':14} ${spent:.2f} provider-reported")
    total = sum(len(a.ledger) for a in actives)
    print(f"  {'TOTAL':14} corpus {total:5}  "
          f"verified={grand['verified']}  counterexample={grand['counterexample']}  "
          f"in-scope={grand['verified'] + grand['counterexample']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="show registered domains and exit")
    ap.add_argument("--domains", nargs="+", choices=list(DOMAIN_NAMES),
                    help="domain subset; default is every registered domain")
    ap.add_argument("--rules", nargs="+",
                    help="rule subset, matched across the selected domains")
    ap.add_argument("--api", action="store_true", help="request candidates from a model")
    ap.add_argument("--calibrate", action="store_true",
                    help="one batch per domain, measure cost and yield, write nothing")
    ap.add_argument("--per-rule", type=int, default=256)
    ap.add_argument("--in-scope-per-rule", type=int, default=128)
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--rounds", type=int, default=8,
                    help="round-robin passes over every (domain, rule) pair")
    ap.add_argument("--max-tokens", type=int, default=10000,
                    help="completion cap per request. A CEILING, not a spend: the model stops when done, so a generous cap costs nothing unless used. It must cover hidden reasoning (~1100 tokens on nemotron) PLUS the candidates, or the reply truncates before the JSON.")
    ap.add_argument("--timeout", type=float, default=3.0,
                    help="per-candidate wall clock, where a domain uses one")
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--preset", default=None)
    ap.add_argument("--retries", type=int, default=8)
    ap.add_argument("--focus-counterexamples", action="store_true")
    ap.add_argument("--no-steer", action="store_true",
                    help="ask blind. By default a domain that can screen also "
                         "describes the candidates its corpus lacks, which is "
                         "what stops a round being spent on proposals that "
                         "could not have distinguished the rule from a rival. "
                         "Steering changes what is asked for, never what is "
                         "kept: every proposal received is still admitted.")
    ap.add_argument("--max-spend", type=float, default=0.0,
                    help="stop once provider-reported cost reaches this many "
                         "dollars; 0 disables the check. Free models report 0 "
                         "cost, so this only bites on a paid backend.")
    ap.add_argument("--max-pace", type=float, default=120.0,
                    help="stop when the shared throttle interval exceeds this "
                         "many seconds; a provider that has started doubling "
                         "is telling you the quota is gone")
    ap.add_argument("--check", action="store_true", help="report without writing")
    args = ap.parse_args()

    if args.list:
        print("registered domains:\n")
        for name, spec in REGISTRY.items():
            print(f"  {name:12} {spec.summary}")
            print(f"  {'':12} corpus: {spec.corpus}")
        return 0
    if min(args.per_rule, args.in_scope_per_rule, args.batch_size,
           args.rounds, args.max_tokens) < 1:
        ap.error("campaign sizes must be positive")

    specs = resolve(args.domains)
    actives = [_load(spec, args.timeout) for spec in specs]

    if args.api:
        # Fail fast. Without a key every request returns instantly with no
        # candidates, and the loop would otherwise churn through every
        # (domain, rule) pair writing zero-yield request entries that then
        # distort the campaign accounting.
        from categorical_polytope.loop_closure import resolve_backend

        if resolve_backend(args.model, args.base_url, args.preset) is None:
            print("no API key set in this process: export LOOP_API_KEY, "
                  "OPENROUTER_API_KEY, or OPENAI_API_KEY before --api",
                  file=sys.stderr)
            return 2
        os.environ["POLYTOPE_API_MAX_TOKENS"] = str(args.max_tokens)
        os.environ["POLYTOPE_API_CONFIGURED_BATCH_SIZE"] = str(args.batch_size)
        # One key means one quota: every domain paces against the same state.
        os.environ["POLYTOPE_API_RATE_STATE"] = str(ROOT / RATE_STATE)
        transport = Transport(args.model, args.base_url, args.preset, args.retries)

        # Checked here, not only inside the round loop: --calibrate takes a
        # different path and would otherwise sleep through a carried-over
        # throttle instead of stopping.
        pace = _throttle_interval()
        if pace > args.max_pace:
            wait = _throttle_wait()
            print(f"throttled before starting: shared interval is {pace:.0f}s "
                  f"(> --max-pace {args.max_pace:.0f}s) after {_throttle_count()} "
                  f"throttle(s); {wait:.0f}s still to wait.", file=sys.stderr)
            print(f"  Resume later, raise --max-pace, or reset pacing with:",
                  file=sys.stderr)
            print(f"    rm {RATE_STATE}", file=sys.stderr)
            return 3

        generative = [a for a in actives if isinstance(a.domain, Generative)]
        skipped = [a.name for a in actives if a not in generative]
        if skipped:
            print(f"not generative, seed-only: {', '.join(skipped)}", flush=True)

        if args.calibrate:
            return _calibrate(generative, transport, args)

        # Round-robin: interleave (domain, rule) so a campaign cut short leaves
        # every domain advanced rather than one finished and the rest empty.
        # Building this domain-major would drain the first domain's whole rule
        # set before touching the second, which is the behaviour this avoids.
        per_domain = [[(a, rule) for rule in a.rules(args.rules)] for a in generative]
        work = [
            pair
            for group in zip_longest(*per_domain)
            for pair in group
            if pair is not None
        ]
        if not work:
            print("no (domain, rule) pairs selected", file=sys.stderr)
            return 2
        total_requests = len(work) * args.rounds
        print(f"campaign: {len(work)} (domain, rule) pairs x {args.rounds} rounds "
              f"= up to {total_requests} requests", flush=True)
        print(flush=True)
        request_seconds: list[float] = []
        throttled = False
        barren = 0
        barren_capped = 0
        for round_index in range(args.rounds):
            progressed = False
            round_capped = 0
            for active, rule_id in work:
                if (active.retained(rule_id) >= args.per_rule
                        and active.in_scope(rule_id) >= args.in_scope_per_rule):
                    continue
                # A free tier answers exhaustion by doubling the shared
                # interval: 30 -> 60 -> 120 -> 240 -> 480 -> 600. Past a point
                # every request returns nothing and the campaign is just
                # sleeping. Stop and say so rather than burn an hour on it.
                if args.max_spend > 0:
                    spent = _spend(actives)
                    if spent >= args.max_spend:
                        print(flush=True)
                        print(f"budget reached: ${spent:.2f} of "
                              f"${args.max_spend:.2f}. Everything so far is "
                              f"checkpointed.", flush=True)
                        throttled = True
                        break
                pace = _throttle_interval()
                if pace > args.max_pace:
                    print(flush=True)
                    print(f"throttled: shared interval is {pace:.0f}s "
                          f"(> --max-pace {args.max_pace:.0f}s) after "
                          f"{_throttle_count()} throttle(s).", flush=True)
                    print("The provider quota looks exhausted. Everything so far is "
                          "checkpointed; rerun later to resume.", flush=True)
                    throttled = True
                    break
                os.environ["POLYTOPE_API_RAW_LOG"] = str(active.paths["raw_log"])
                focus = active.survivor_focus(rule_id) if args.focus_counterexamples else ""
                # A domain that can screen can also say what it is short of, so
                # the request describes the candidates that would carry evidence
                # instead of asking blind. Only such a domain takes the keyword.
                steering = (isinstance(active.domain, Screenable)
                            and not args.no_steer)
                aimed = {"steer": True} if steering else {}
                started = time.monotonic()
                rows, backend = active.domain.propose(
                    rule_id, args.batch_size, transport, focus=focus, **aimed
                )
                request_seconds.append(time.monotonic() - started)
                active.ledger.state["backend"] = backend
                fresh = active.ledger.admit(active.domain, rows, seen=active.seen)
                # What the batch was worth, read off the rows just
                # adjudicated - no re-measurement, every field is recorded.
                mix = {}
                if isinstance(active.domain, Screenable) and rows:
                    mix = tally([active.domain.screen_row(r) for r in rows])
                    mix = {k: v for k, v in mix.items() if v}
                active.ledger.record_request(
                    rule_id=rule_id, requested=args.batch_size,
                    returned=len(rows), fresh=len(fresh), backend=backend,
                    steered=bool(steering), screened=mix,
                )
                if not args.check:
                    _persist(active)
                counts = active.ledger.counts(active.domain, rule_id)
                print(
                    f"[{active.name}] {rule_id} round {round_index + 1}: "
                    f"returned {len(rows)}/{args.batch_size}, fresh {len(fresh)}, "
                    f"corpus {active.retained(rule_id)}/{args.per_rule}, "
                    f"in-scope {active.in_scope(rule_id)}/{args.in_scope_per_rule}, "
                    f"counterexamples {counts['counterexample']}"
                    + (f", screened {_mix(mix)}" if mix else ""),
                    flush=True,
                )
                if rows:
                    progressed = True
                else:
                    if _hit_the_cap(_last_reply(active.paths["raw_log"]),
                                    args.max_tokens):
                        round_capped += 1
                    for line in _diagnose_empty(
                        active.paths["raw_log"], args.preset, args.max_tokens
                    ):
                        print(line, flush=True)
                # Project from measured requests, not from an assumed rate.
                if len(request_seconds) == 1:
                    mean = request_seconds[0]
                    remaining = (total_requests - 1) * mean
                    print(f"  first request took {mean:.0f}s; {total_requests - 1} "
                          f"remaining implies ~{remaining / 60:.0f} min. "
                          f"Lower --batch-size or --rounds to shorten.",
                          flush=True)
            if throttled:
                break
            if progressed:
                barren = 0
                barren_capped = 0
            else:
                barren_capped += round_capped
                # One empty reply is not a dead backend. With several rules a
                # blank from one is masked by the others, but `--rules` on a
                # single rule made any single empty batch fatal - a targeted run
                # asking for the scarcest shape is exactly where empties are
                # most likely, and where losing the remaining rounds costs most.
                barren += 1
                print(f"round {round_index + 1} yielded nothing "
                      f"({barren} in a row)", flush=True)
                if barren >= 2:
                    if barren_capped:
                        # Do not repeat the sizing advice printed above; say
                        # only what the stop itself would otherwise imply
                        # wrongly - that the rule has no candidates left.
                        print(f"two barren rounds, {barren_capped} of them cut "
                              f"off at the {args.max_tokens:,}-token cap; "
                              "stopping.", flush=True)
                        print("  That is a budget that did not fit, not a rule "
                              "that ran out. Resume with the flags above.",
                              flush=True)
                    else:
                        print("two barren rounds; stopping", flush=True)
                    break

    for active in actives:
        active.ledger.validate()
    _print_totals(actives)

    if args.check:
        print("--check: nothing written")
        return 0

    for active in actives:
        _persist(active)
    # Persist only what this run advanced; report across everything.
    _write_summary(_summary_actives(actives, args.timeout))
    print(f"\nwrote {SUMMARY}")
    return 0


def _calibrate(actives: list[Active], transport: Transport, args) -> int:
    """Spend one batch per domain and report what it bought."""
    print(f"calibrating: 1 batch of {args.batch_size} per domain, "
          f"max_tokens={args.max_tokens}\n")
    for active in actives:
        rule_id = active.rules(args.rules)[0]
        os.environ["POLYTOPE_API_RAW_LOG"] = str(active.paths["raw_log"])
        before = _token_usage(active.paths["raw_log"])
        pace = _throttle_interval()
        if pace > args.max_pace:
            print(f"throttled: shared interval is {pace:.0f}s "
                  f"(> --max-pace {args.max_pace:.0f}s); stopping.", flush=True)
            break
        print(f"--- {active.name} / {rule_id} ---", flush=True)
        print(f"  requesting {args.batch_size} candidates, "
              f"max_tokens={args.max_tokens} (generation is serial; "
              f"this can take a while) ...", flush=True)
        started = time.monotonic()
        aimed = ({"steer": True}
                 if isinstance(active.domain, Screenable) and not args.no_steer
                 else {})
        rows, backend = active.domain.propose(
            rule_id, args.batch_size, transport, **aimed)
        elapsed = time.monotonic() - started
        after = _token_usage(active.paths["raw_log"])
        spent = after["total_tokens"] - before["total_tokens"]
        completion = after["completion_tokens"] - before["completion_tokens"]

        print(f"  backend        {backend}")
        print(f"  returned       {len(rows)}/{args.batch_size} in {elapsed:.1f}s")
        print(f"  tokens         {spent:,} total, {completion:,} completion")
        if not rows:
            print(f"  NO CANDIDATES  ({backend})")
            for line in _diagnose_empty(
                active.paths["raw_log"], args.preset, args.max_tokens
            ):
                print(line)
            print()
            continue
        counts = Counter(r["status"] for r in rows)
        in_scope = counts["verified"] + counts["counterexample"]
        print(f"  adjudicated    {dict(counts)}")
        print(f"  in-scope yield {in_scope}/{len(rows)} "
              f"({100.0 * in_scope / len(rows):.0f}%)")
        # In-scope yield says the batch was adjudicable. This says whether it
        # was worth adjudicating - the number that steering is meant to move.
        if isinstance(active.domain, Screenable):
            screenings = [active.domain.screen_row(r) for r in rows]
            print(f"  steered        {'yes' if aimed else 'no'}")
            print(f"  screening      {summarise(screenings)}")
        if completion:
            per_record = completion / len(rows)
            rate = completion / elapsed if elapsed > 0 else 0.0
            print(f"  ~{per_record:.0f} completion tokens/record -> "
                  f"~{int(args.max_tokens / per_record)} would fill {args.max_tokens:,}")
            if rate:
                print(f"  {rate:.0f} tokens/sec -> a {args.max_tokens:,}-token cap "
                      f"costs ~{args.max_tokens / rate:.0f}s per request")
            if len(rows) < args.batch_size * 0.6:
                print(f"  SUGGEST: only {len(rows)} of {args.batch_size} survived; "
                      f"try --batch-size {max(8, len(rows))}")
            elif completion < args.max_tokens * 0.5:
                print(f"  SUGGEST: budget underused; try --batch-size "
                      f"{int(args.batch_size * 1.8)}")
        print()
    print("calibration only: nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
