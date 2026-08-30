"""
The multi-domain campaign.

What matters here is that the runner is not secretly shaped like either domain:
it resolves them from a registry, drives both through the same ledger, paces
them against one shared rate budget, and interleaves their rules so a campaign
cut short leaves every domain advanced rather than one finished and the rest
untouched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from categorical_polytope.adjudication import Ledger, Status
from categorical_polytope.adjudication.codeprops import CodePropertyDomain
from categorical_polytope.adjudication.domain import Domain, Generative, Transport
from categorical_polytope.adjudication.polytope import PolytopeDomain
from categorical_polytope.adjudication.registry import (
    DOMAIN_NAMES,
    RATE_STATE,
    REGISTRY,
    resolve,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def runner():
    path = ROOT / "experiments" / "run_campaign.py"
    spec = importlib.util.spec_from_file_location("run_campaign", path)
    module = importlib.util.module_from_spec(spec)
    # `Active` is a dataclass under `from __future__ import annotations`, so
    # dataclasses resolves its string annotations through sys.modules. Register
    # before exec, or the class body raises while building the field types.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- registry ---


def test_every_registered_domain_satisfies_both_protocols():
    for name in DOMAIN_NAMES:
        domain = REGISTRY[name].factory(timeout=2.0)
        assert isinstance(domain, Domain), name
        assert isinstance(domain, Generative), name


def test_registry_resolves_all_by_default_and_subsets_on_request():
    assert [s.name for s in resolve(None)] == list(DOMAIN_NAMES)
    assert [s.name for s in resolve(["codeprops"])] == ["codeprops"]


def test_unknown_domain_is_refused():
    with pytest.raises(KeyError):
        resolve(["not_a_domain"])


def test_each_domain_owns_a_distinct_corpus_and_log():
    corpora = [s.corpus for s in REGISTRY.values()]
    logs = [s.raw_log for s in REGISTRY.values()]
    assert len(set(corpora)) == len(corpora)
    assert len(set(logs)) == len(logs)


def test_the_rate_budget_is_shared_not_per_domain():
    # One API key means one quota. A per-domain rate file would let two domains
    # race each other into the provider's limit.
    assert isinstance(RATE_STATE, str) and RATE_STATE
    assert all(RATE_STATE != s.raw_log for s in REGISTRY.values())


def test_domain_rule_ids_do_not_collide_across_domains():
    seen: dict[str, str] = {}
    for name in DOMAIN_NAMES:
        for rule in REGISTRY[name].factory(timeout=2.0).rule_ids:
            assert rule not in seen, f"{rule} claimed by {seen.get(rule)} and {name}"
            seen[rule] = name


# ------------------------------------------------------------------ report ---


def test_summary_totals_every_domain(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "SUMMARY", tmp_path / "CAMPAIGN.md")
    actives = []
    for name in DOMAIN_NAMES:
        spec = REGISTRY[name]
        domain = spec.factory(timeout=2.0)
        ledger = Ledger.load(ROOT / spec.corpus)
        actives.append(runner.Active(spec, domain, ledger, spec.paths(ROOT), set()))
    runner._write_summary(actives)

    text = (tmp_path / "CAMPAIGN.md").read_text(encoding="utf-8")
    for name in DOMAIN_NAMES:
        assert f"`{name}`" in text
    assert "**total**" in text
    # The honesty line must survive into the cross-domain page.
    assert "Only `verified` is a pass" in text


# ------------------------------------------------------------- round robin ---


def _stub_rows(rule_id: str, tag: str, payload_key: str) -> list[dict]:
    """Rows in the shape the given domain's `identity` expects."""
    def payload(i: int) -> dict:
        if payload_key == "expr":
            return {"expr": f"sigma*{tag}{i}", "base_expr": ""}
        return {"args": f"('{tag}{i}',)"}

    return [{
        "rule_id": rule_id, "name": f"{tag}_{i}", "payload": payload(i),
        "status": "verified", "reason": "stub", "metrics": {}, "note": "",
    } for i in range(2)]


def test_campaign_interleaves_domains_instead_of_draining_one(
    runner, tmp_path, monkeypatch
):
    """Round-robin: every domain advances in round one, before any is finished."""
    for sub in ("experiments", "docs"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY", tmp_path / "docs" / "CAMPAIGN.md")

    order: list[str] = []

    def make_stub(domain_name, payload_key):
        def propose(self, rule_id, n, transport, *, focus=""):
            order.append(domain_name)
            tag = f"{domain_name}_{len(order)}"
            return _stub_rows(rule_id, tag, payload_key), "stub@test"
        return propose

    monkeypatch.setattr(PolytopeDomain, "propose", make_stub("polytope", "expr"))
    monkeypatch.setattr(CodePropertyDomain, "propose", make_stub("codeprops", "args"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-used")
    monkeypatch.setattr(
        sys, "argv",
        ["run_campaign.py", "--api", "--check", "--rounds", "1",
         "--batch-size", "4", "--per-rule", "999", "--in-scope-per-rule", "999",
         "--timeout", "2"],
    )
    assert runner.main() == 0

    # Both domains must appear in the single round, not one after the other.
    assert set(order) == {"polytope", "codeprops"}
    first_codeprops = order.index("codeprops")
    last_polytope = len(order) - 1 - order[::-1].index("polytope")
    assert first_codeprops < last_polytope, "domains were drained sequentially"


def test_campaign_shares_one_rate_state_across_domains(runner, tmp_path, monkeypatch):
    for sub in ("experiments", "docs"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY", tmp_path / "docs" / "CAMPAIGN.md")

    rate_paths: set[str] = set()
    log_paths: set[str] = set()

    def propose(self, rule_id, n, transport, *, focus=""):
        rate_paths.add(os.environ.get("POLYTOPE_API_RATE_STATE", ""))
        log_paths.add(os.environ.get("POLYTOPE_API_RAW_LOG", ""))
        return [], "stub@test"

    monkeypatch.setattr(PolytopeDomain, "propose", propose)
    monkeypatch.setattr(CodePropertyDomain, "propose", propose)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-used")
    monkeypatch.setattr(
        sys, "argv",
        ["run_campaign.py", "--api", "--check", "--rounds", "1", "--batch-size", "2",
         "--per-rule", "999", "--in-scope-per-rule", "999", "--timeout", "2"],
    )
    assert runner.main() == 0
    assert len(rate_paths) == 1, "every domain must pace against one quota"
    assert len(log_paths) > 1, "each domain keeps its own provenance log"


def test_check_mode_writes_nothing(runner, tmp_path, monkeypatch):
    summary = tmp_path / "CAMPAIGN.md"
    monkeypatch.setattr(runner, "SUMMARY", summary)
    monkeypatch.setattr(sys, "argv", ["run_campaign.py", "--check", "--timeout", "2"])
    assert runner.main() == 0
    assert not summary.exists()


def test_list_mode_names_every_domain(runner, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_campaign.py", "--list"])
    assert runner.main() == 0
    out = capsys.readouterr().out
    for name in DOMAIN_NAMES:
        assert name in out


# ------------------------------------------------------------- live corpora ---


def test_both_live_corpora_validate_and_keep_an_honest_denominator():
    for name in DOMAIN_NAMES:
        spec = REGISTRY[name]
        domain = spec.factory(timeout=2.0)
        ledger = Ledger.load(ROOT / spec.corpus)
        ledger.validate()
        counts = ledger.counts(domain)
        undecided = counts["outside_scope"] + counts["rejected"] + counts["inconclusive"]
        assert undecided > 0, f"{name}: a corpus with nothing undecided is a red flag"
        assert ledger.in_scope_total(domain) < len(ledger)


def test_the_newer_code_targets_actually_yield_counterexamples():
    """A campaign that can only produce `verified` teaches a fine-tune nothing."""
    domain = CodePropertyDomain(timeout=5.0)
    for rule_id, payload in (
        ("chunk/covers", "([1, 2, 3], 2)"),
        ("binary_search/finds_present", "([1, 2, 3, 4], 4)"),
        ("truncate/respects_limit", "('abcdef', 5)"),
    ):
        assert domain.adjudicate(rule_id, payload).status is Status.COUNTEREXAMPLE


# ------------------------------------------------------ scope of the page ---


def _scoped_to(runner, name: str) -> list:
    spec = REGISTRY[name]
    return [runner.Active(spec, spec.factory(timeout=2.0),
                          Ledger.load(ROOT / spec.corpus), spec.paths(ROOT), set())]


def test_a_scoped_run_still_reports_every_domain(runner, tmp_path, monkeypatch):
    """
    `--domains` scopes what a run advances, never what the page reports.

    A `--domains polyhedra` run once republished the cross-domain summary with
    a single row, printing that domain's corpus as the campaign total and
    dropping the other two entirely.
    """
    monkeypatch.setattr(runner, "SUMMARY", tmp_path / "CAMPAIGN.md")
    scoped = _scoped_to(runner, "polyhedra")

    runner._write_summary(runner._summary_actives(scoped, 2.0))

    text = (tmp_path / "CAMPAIGN.md").read_text(encoding="utf-8")
    for name in DOMAIN_NAMES:
        assert f"`{name}`" in text, f"{name} dropped by a scoped run"


def test_the_summary_reuses_what_the_run_advanced(runner):
    """The advanced ledger is the in-memory one, so the page shows fresh work."""
    scoped = _scoped_to(runner, "polyhedra")
    full = runner._summary_actives(scoped, 2.0)

    assert {a.name for a in full} == set(DOMAIN_NAMES)
    assert next(a for a in full if a.name == "polyhedra") is scoped[0]


# ------------------------------------------------ diagnosing an empty batch ---


def _raw_log(tmp_path: Path, **fields) -> Path:
    entry = {
        "utc": "2026-08-28T08:42:59-04:00", "backend": "test",
        "requested_n": 12, "parsed_items": 0,
        "usage": {"completion_tokens": 10000,
                  "completion_tokens_details": {"reasoning_tokens": 7147}},
    }
    entry.update(fields)
    path = tmp_path / "raw.jsonl"
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return path


def test_a_reply_that_never_opened_the_envelope_is_named_a_budget_overrun(
    runner, tmp_path
):
    """
    The reply that motivated this: 28k characters of reasoning, cut off at the
    cap, no JSON. It is a spent budget, not a model that ignored the format,
    and the operator has to be told which.
    """
    log = _raw_log(
        tmp_path, finish_reason="length",
        response="We need to produce JSON with candidates for the law. " * 500,
    )
    out = " ".join(runner._diagnose_empty(log, "nemotron-super", 10000))

    assert "10,000-token cap" in out
    assert "reasoning" in out
    assert "batch-size" in out, "the operator needs the lever, not just the cause"


def test_a_reply_cut_off_mid_record_is_not_blamed_on_the_model(runner, tmp_path):
    """Truncation after the envelope opened is a cap problem, plainly stated."""
    log = _raw_log(
        tmp_path, finish_reason="length",
        response='{"candidates":[{"name":"a","system":"([[1,0]], [1])","base":"-x0**2',
    )
    out = " ".join(runner._diagnose_empty(log, "nemotron-super", 10000))

    assert "cap" in out and "max-tokens" in out


def test_a_complete_reply_that_parses_to_nothing_is_reported_as_itself(
    runner, tmp_path
):
    """Not every empty batch is truncation; a finished reply must not be called one."""
    log = _raw_log(tmp_path, finish_reason="stop",
                   usage={"completion_tokens": 120},
                   response="Sorry, I cannot help with that.")
    out = " ".join(runner._diagnose_empty(log, "nemotron-super", 10000))

    assert "no parseable candidates" in out
    assert "cap" not in out
