"""
Domain two: generated-code property violation.

The point of this file is not that `merge_intervals` works. It is that the
harness built for the polytope laws drives a domain with nothing in common with
them - different payloads, a different adjudicator, a different failure mode -
without special-casing, and that the properties which make a denominator
trustworthy survive the move.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
from pathlib import Path

import pytest

from categorical_polytope.adjudication import Ledger, Status
from categorical_polytope.adjudication.codeprops import CodePropertyDomain, run_property
from categorical_polytope.adjudication.codeprops.seeds import SEEDS
from categorical_polytope.adjudication.codeprops.targets import RULE_IDS, rle_encode, rle_decode

CORPUS = Path(__file__).resolve().parents[1] / "experiments" / "code_properties.json"


@pytest.fixture(scope="module")
def domain() -> CodePropertyDomain:
    return CodePropertyDomain(timeout=5.0)


# ------------------------------------------------------- protocol conformance ---


def test_domain_implements_exactly_the_six_member_protocol(domain):
    for attribute in ("name", "verifier_version", "rule_ids"):
        assert hasattr(domain, attribute)
    for method in ("rules_invalidated_between", "identity", "readjudicate"):
        assert callable(getattr(domain, method))


def test_readjudicate_cannot_consult_a_prior_verdict(domain):
    # Same structural guarantee as domain one: nothing in the call path takes a
    # status, so admission and verdict cannot be influenced by the old answer.
    assert list(inspect.signature(domain.scope).parameters) == ["rule_id", "args_literal"]
    row = {"rule_id": "rle/roundtrip", "payload": {"args": "('a3',)"}, "status": "verified"}
    assert str(domain.readjudicate(row).status) == "counterexample"


def test_identity_is_scoped_by_rule(domain):
    same_input = "([[1, 2]],)"
    first = domain.identity({"rule_id": RULE_IDS[0], "payload": {"args": same_input}})
    second = domain.identity({"rule_id": RULE_IDS[1], "payload": {"args": same_input}})
    assert first != second


# ------------------------------------------------------------ sandbox boundary ---


def test_hostile_payload_is_rejected(domain):
    verdict = domain.adjudicate("rle/roundtrip", "__import__('os').system('echo pwned')")
    assert verdict.status is Status.REJECTED


def test_hostile_payload_is_never_executed(domain, tmp_path):
    # Rejection is not enough on its own: prove the side effect did not happen.
    marker = tmp_path / "pwned.txt"
    payload = f"__import__('pathlib').Path({str(marker)!r}).write_text('pwned')"
    verdict = domain.adjudicate("rle/roundtrip", payload)
    assert verdict.status is Status.REJECTED
    assert not marker.exists(), "literal_eval must not have executed the payload"


def test_names_and_calls_are_not_literals(domain):
    for payload in ("(undefined_name,)", "(list(range(3)),)", "(lambda: 1,)"):
        assert domain.adjudicate("rle/roundtrip", payload).status is Status.REJECTED


def test_unknown_rule_is_rejected(domain):
    assert domain.adjudicate("no/such_rule", "('a',)").status is Status.REJECTED


def test_oversized_payload_is_rejected(domain):
    assert domain.adjudicate("rle/roundtrip", f"('{'a' * 5000}',)").status is Status.REJECTED


def test_sandbox_reports_a_timeout_rather_than_hanging():
    result = run_property("nth_prime/matches_sieve", (400000,), timeout=0.5)
    assert result.outcome == "timeout"
    assert not result.decided


# --------------------------------------------------------- scope before verdict ---


def test_out_of_contract_input_is_excused_without_being_run(domain, monkeypatch):
    # The strongest form of the guarantee: no run happens at all, so no result
    # can have informed the decision to excuse it.
    import categorical_polytope.adjudication.codeprops.domain as mod

    def _explode(*args, **kwargs):
        raise AssertionError("out-of-contract input must not reach the sandbox")

    monkeypatch.setattr(mod, "run_property", _explode)
    verdict = domain.adjudicate("merge_intervals/disjoint_and_ordered", "([[5, 1]],)")
    assert verdict.status is Status.OUTSIDE_SCOPE
    assert "start must not exceed end" in verdict.reason


def test_scope_admits_on_the_contract_alone(domain):
    # A candidate that will fail and one that will pass are both admitted.
    failing, _, _, _ = domain.scope("rle/roundtrip", "('a3',)")
    passing, _, _, _ = domain.scope("rle/roundtrip", "('aaa',)")
    assert failing and passing


def test_a_raise_on_valid_input_is_a_counterexample_not_a_scope_question(domain):
    from categorical_polytope.adjudication.codeprops.sandbox import RunResult

    status, reason = domain._verdict_from(RunResult("raised", "TypeError: boom"))
    assert status is Status.COUNTEREXAMPLE
    assert status is not Status.OUTSIDE_SCOPE


def test_resource_exhaustion_is_an_admission_not_a_verdict(domain):
    from categorical_polytope.adjudication.codeprops.sandbox import RunResult

    for outcome in ("timeout", "exhausted", "crashed", "harness_error"):
        status, _ = domain._verdict_from(RunResult(outcome, ""))
        assert status is Status.INCONCLUSIVE


# ------------------------------------------------------------- real adjudication ---


def test_the_seeded_encoder_defect_is_found(domain):
    # Not a contrived failure: the decoder reads a greedy digit run, so a digit
    # adjacent to another run is absorbed into the count.
    assert rle_decode(rle_encode("a3")) != "a3"
    assert domain.adjudicate("rle/roundtrip", "('a3',)").status is Status.COUNTEREXAMPLE


def test_a_digit_alone_does_not_break_the_round_trip(domain):
    # "11" is a single run encoding to "12"; the defect needs an adjacent run.
    # Bounding it matters: a fix judged by digit-presence alone would be wrong.
    assert rle_decode(rle_encode("11")) == "11"
    assert domain.adjudicate("rle/roundtrip", "('11',)").status is Status.VERIFIED


def test_correct_implementation_verifies(domain):
    for payload in ("([[1, 3], [2, 6], [8, 10]],)", "([],)", "([[1, 2], [5, 6]],)"):
        assert domain.adjudicate(
            "merge_intervals/disjoint_and_ordered", payload
        ).status is Status.VERIFIED


# ------------------------------------------------------------- ledger integration ---


def _seed_rows(domain: CodePropertyDomain, limit: int | None = None):
    seeds = SEEDS[:limit] if limit else SEEDS
    return [domain.to_row(s.rule_id, s.name, s.args, s.note) for s in seeds]


def test_the_shared_ledger_drives_this_domain(domain):
    ledger = Ledger({"records": [], "verifier_version": domain.verifier_version})
    fresh = ledger.admit(domain, _seed_rows(domain, 6))
    ledger.validate()
    assert len(fresh) == 6
    assert len(ledger) == 6


def test_admit_deduplicates_seeds(domain):
    ledger = Ledger({"records": [], "verifier_version": domain.verifier_version})
    rows = _seed_rows(domain, 4)
    assert len(ledger.admit(domain, rows)) == 4
    assert len(ledger.admit(domain, rows)) == 0


def test_a_verifier_bump_reverses_a_verdict_and_retains_the_history():
    """A bigger time budget turns an undecided candidate into a decided one."""

    class Budgeted(CodePropertyDomain):
        def rules_invalidated_between(self, prior, current):
            return {"nth_prime/matches_sieve"} if prior != current else set()

    stingy = Budgeted(verifier_version=1, timeout=0.01)
    row = stingy.to_row("nth_prime/matches_sieve", "small", "(50,)")
    assert row["status"] == "inconclusive"

    ledger = Ledger({"records": [row], "verifier_version": 1})
    report = ledger.sync_verifier(Budgeted(verifier_version=2, timeout=15.0))

    assert report.changed == 1
    stored = ledger.records[0]
    assert stored["status"] == "verified"
    assert stored["initial_status"] == "inconclusive"
    assert stored["adjudication_history"][-1]["from"] == "inconclusive"
    assert stored["adjudication_history"][-1]["to"] == "verified"
    ledger.validate()


# ------------------------------------------------------------------ live corpus ---


@pytest.fixture(scope="module")
def corpus() -> Ledger:
    if not CORPUS.exists():
        pytest.skip("run experiments/run_code_properties.py first")
    return Ledger.load(CORPUS)


def test_the_seed_bank_exercises_every_status(corpus, domain):
    counts = corpus.counts(domain)
    missing = [str(s) for s in Status if not counts[str(s)]]
    assert not missing, f"seed bank never produced: {missing}"


def test_the_denominator_is_smaller_than_the_corpus(corpus, domain):
    # If everything were in scope and passing, the contract guard would be doing
    # no work and the number would mean nothing.
    assert 0 < corpus.in_scope_total(domain) < len(corpus)


def test_out_of_contract_seeds_are_not_counted_as_passes(corpus):
    excused = [r for r in corpus.records if r["status"] == "outside_scope"]
    assert excused
    for row in excused:
        assert "contract_breach" in row["metrics"]


# ------------------------------------------------------------------ campaign ---


def _load_runner():
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "experiments" / "run_code_properties.py"
    spec = importlib.util.spec_from_file_location("run_code_properties", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_campaign_loop_adjudicates_and_checkpoints_stubbed_proposals(tmp_path, monkeypatch):
    """The --api loop, driven by a canned reply instead of a provider."""
    import categorical_polytope.interaction_search as transport
    from categorical_polytope.adjudication.codeprops.prompts import parse_input_proposals

    runner = _load_runner()
    monkeypatch.setattr(runner, "STATE", tmp_path / "corpus.json")
    monkeypatch.setattr(runner, "REPORT", tmp_path / "report.md")
    monkeypatch.setattr(runner, "RAW_API_LOG", tmp_path / "raw.jsonl")
    monkeypatch.setattr(runner, "RATE_STATE", tmp_path / "rate.json")

    reply = json.dumps({"candidates": [
        {"name": "digit_adj", "args": "('a3',)", "why": "digit beside a run"},
        {"name": "clean", "args": "('aaa',)", "why": "control"},
        {"name": "wrong_type", "args": "(123,)", "why": "out of contract"},
        {"name": "injection", "args": "__import__('os').system('x')", "why": "hostile"},
    ]})
    calls = []

    def fake_propose(n, *, prompt=None, parser=None, **kwargs):
        calls.append(prompt)
        return parser(reply), "stub/nemotron@test"

    monkeypatch.setattr(transport, "propose_candidates", fake_propose)
    monkeypatch.setattr(
        sys, "argv",
        ["run_code_properties.py", "--api", "--no-seeds", "--rules", "rle/roundtrip",
         "--per-rule", "4", "--in-scope-per-rule", "2", "--batch-size", "8",
         "--max-attempts-per-rule", "3", "--timeout", "5"],
    )
    assert runner.main() == 0

    ledger = Ledger.load(tmp_path / "corpus.json")
    domain = CodePropertyDomain()
    by_status = {r["name"]: r["status"] for r in ledger.records}
    assert by_status["digit_adj"] == "counterexample"
    assert by_status["clean"] == "verified"
    assert by_status["wrong_type"] == "outside_scope"
    assert by_status["injection"] == "rejected"

    # The batch repeats, so the second attempt must add nothing.
    assert len(ledger) == 4
    assert ledger.state["backend"] == "stub/nemotron@test"
    assert (tmp_path / "report.md").exists()
    ledger.validate()

    # The prompt actually sent must carry the contract.
    assert calls and "OUT OF CONTRACT" in calls[0]


def test_campaign_loop_sets_the_token_budget_from_flags(tmp_path, monkeypatch):
    import categorical_polytope.interaction_search as transport

    runner = _load_runner()
    monkeypatch.setattr(runner, "STATE", tmp_path / "corpus.json")
    monkeypatch.setattr(runner, "REPORT", tmp_path / "report.md")
    monkeypatch.setattr(runner, "RAW_API_LOG", tmp_path / "raw.jsonl")
    monkeypatch.setattr(runner, "RATE_STATE", tmp_path / "rate.json")
    monkeypatch.delenv("POLYTOPE_API_MAX_TOKENS", raising=False)

    seen = {}

    def fake_propose(n, *, prompt=None, parser=None, **kwargs):
        seen["max_tokens"] = os.environ.get("POLYTOPE_API_MAX_TOKENS")
        seen["raw_log"] = os.environ.get("POLYTOPE_API_RAW_LOG")
        seen["rate_state"] = os.environ.get("POLYTOPE_API_RATE_STATE")
        seen["n"] = n
        return [], "stub"

    monkeypatch.setattr(transport, "propose_candidates", fake_propose)
    monkeypatch.setattr(
        sys, "argv",
        ["run_code_properties.py", "--api", "--no-seeds", "--rules", "rle/roundtrip",
         "--max-tokens", "20000", "--batch-size", "128", "--max-attempts-per-rule", "1"],
    )
    assert runner.main() == 0
    assert seen["max_tokens"] == "20000"
    assert seen["n"] == 128
    assert seen["raw_log"] == str(tmp_path / "raw.jsonl")
    assert seen["rate_state"] == str(tmp_path / "rate.json")
