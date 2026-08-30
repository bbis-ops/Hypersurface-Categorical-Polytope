"""
Invariants of the domain-independent adjudication harness.

These pin the properties that make a denominator trustworthy: the status
vocabulary is closed, only `verified` passes, and a verdict can never be
overwritten without leaving a trace. The live V.7--V.14 corpus is checked
against the same rules, so a regression in the harness shows up as a failing
test rather than as a quietly improved pass rate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from categorical_polytope.adjudication import (
    IN_SCOPE,
    Ledger,
    LedgerIntegrityError,
    Status,
    Verdict,
)
from categorical_polytope.adjudication.ledger import SCHEMA_VERSION
from categorical_polytope.adjudication.polytope import PolytopeDomain

CORPUS = Path(__file__).resolve().parents[1] / "experiments" / "verification_campaign.json"


# ---------------------------------------------------------------- status ---


def test_status_vocabulary_is_closed():
    assert {s.value for s in Status} == {
        "rejected",
        "outside_scope",
        "inconclusive",
        "verified",
        "counterexample",
    }


def test_only_verified_is_a_pass():
    passing = [s for s in Status if s.is_pass]
    assert passing == [Status.VERIFIED]


def test_counterexample_is_in_scope_but_not_a_pass():
    # A found failure is evidence the rule was tested, not evidence it held.
    assert Status.COUNTEREXAMPLE in IN_SCOPE
    assert not Status.COUNTEREXAMPLE.is_pass


def test_undecided_statuses_are_not_in_scope():
    for status in (Status.REJECTED, Status.OUTSIDE_SCOPE, Status.INCONCLUSIVE):
        assert status not in IN_SCOPE
        assert not status.is_pass


def test_status_compares_and_serializes_as_its_legacy_string():
    assert Status.VERIFIED == "verified"
    assert json.dumps({"status": Status.OUTSIDE_SCOPE}) == '{"status": "outside_scope"}'


def test_unknown_status_is_rejected_not_coerced():
    with pytest.raises(ValueError):
        Status.coerce("probably_fine")


# ------------------------------------------------------- a minimal domain ---


class FakeDomain:
    """
    Two rules over integer payloads; rule `even` flips at version 2.

    Deliberately nothing like the polytope laws: if the ledger can drive this,
    it is not secretly coupled to domain one.
    """

    name = "fake"

    def __init__(self, verifier_version: int = 1):
        self.verifier_version = verifier_version

    @property
    def rule_ids(self):
        return ("even", "positive")

    def rules_invalidated_between(self, prior, current):
        return {"even"} if prior < 2 <= current else set()

    def identity(self, row):
        return (row["rule_id"], row["payload"]["value"])

    def readjudicate(self, row):
        value = row["payload"]["value"]
        if self.verifier_version >= 2 and value % 2 == 0:
            return Verdict(Status.OUTSIDE_SCOPE, "even values are out of scope", {})
        return Verdict(Status.VERIFIED, "held", {"value": value})


def _row(rule: str, value: int, status: str = "verified") -> dict:
    return {"rule_id": rule, "name": f"{rule}-{value}", "payload": {"value": value},
            "status": status, "reason": "held", "metrics": {}, "note": ""}


# ---------------------------------------------------------------- ledger ---


def test_same_version_sync_is_a_noop():
    ledger = Ledger({"records": [_row("even", 2)], "verifier_version": 1})
    report = ledger.sync_verifier(FakeDomain(1))
    assert (report.rechecked, report.changed) == (0, 0)
    assert ledger.records[0]["status"] == "verified"


def test_version_bump_records_the_reversal_with_a_reason():
    ledger = Ledger({"records": [_row("even", 2)], "verifier_version": 1})
    report = ledger.sync_verifier(FakeDomain(2))

    assert report.changed == 1
    row = ledger.records[0]
    assert row["status"] == "outside_scope"
    assert row["initial_status"] == "verified"
    history = row["adjudication_history"]
    assert len(history) == 1
    assert history[0]["from"] == "verified"
    assert history[0]["to"] == "outside_scope"
    assert history[0]["reason"] == "even values are out of scope"
    assert history[0]["utc"]


def test_unaffected_rules_keep_their_verdict_untouched():
    ledger = Ledger({"records": [_row("positive", 3)], "verifier_version": 1})
    ledger.sync_verifier(FakeDomain(2))
    row = ledger.records[0]
    assert row["status"] == "verified"
    assert "adjudication_history" not in row


def test_a_reversal_never_erases_earlier_history():
    ledger = Ledger({"records": [_row("even", 2)], "verifier_version": 1})
    ledger.sync_verifier(FakeDomain(2))
    first = list(ledger.records[0]["adjudication_history"])

    # Roll back to v1 and forward again: the round trip must accumulate, not reset.
    ledger.state["verifier_version"] = 1
    ledger.records[0]["rule_id"] = "even"
    ledger.sync_verifier(FakeDomain(2))

    history = ledger.records[0]["adjudication_history"]
    assert history[: len(first)] == first
    assert ledger.records[0]["initial_status"] == "verified"


def test_re_adjudication_that_does_not_move_leaves_no_history():
    ledger = Ledger({"records": [_row("even", 3)], "verifier_version": 1})
    ledger.sync_verifier(FakeDomain(2))
    assert ledger.records[0]["status"] == "verified"
    assert "adjudication_history" not in ledger.records[0]


def test_admit_deduplicates_on_domain_identity():
    ledger = Ledger({"records": [], "verifier_version": 1})
    domain = FakeDomain()
    first = ledger.admit(domain, [_row("even", 2), _row("even", 4)])
    second = ledger.admit(domain, [_row("even", 2), _row("even", 6)])
    assert len(first) == 2
    assert [r["payload"]["value"] for r in second] == [6]
    assert len(ledger) == 3


def test_identity_is_scoped_by_rule():
    # The same payload against two rules is two records, not one.
    ledger = Ledger({"records": [], "verifier_version": 1})
    domain = FakeDomain()
    ledger.admit(domain, [_row("even", 2), _row("positive", 2)])
    assert len(ledger) == 2


def test_counts_and_in_scope_denominator():
    domain = FakeDomain()
    ledger = Ledger({"records": [
        _row("even", 2, "verified"),
        _row("even", 4, "outside_scope"),
        _row("even", 6, "counterexample"),
        _row("even", 8, "inconclusive"),
    ], "verifier_version": 1})
    counts = ledger.counts(domain, "even")
    assert counts["verified"] == 1 and counts["outside_scope"] == 1
    # Only verified + counterexample may serve as a denominator.
    assert ledger.in_scope_total(domain, "even") == 2


# ------------------------------------------------------------- integrity ---


def test_validate_rejects_an_unknown_status():
    with pytest.raises(LedgerIntegrityError):
        Ledger({"records": [_row("even", 2, "looks_fine")]}).validate()


def test_validate_rejects_history_that_does_not_end_at_the_status():
    row = _row("even", 2, "verified")
    row["initial_status"] = "verified"
    row["adjudication_history"] = [
        {"utc": "now", "from": "verified", "to": "outside_scope", "reason": "r"}
    ]
    with pytest.raises(LedgerIntegrityError):
        Ledger({"records": [row]}).validate()


def test_validate_rejects_a_broken_history_chain():
    row = _row("even", 2, "rejected")
    row["initial_status"] = "verified"
    row["adjudication_history"] = [
        {"utc": "now", "from": "verified", "to": "outside_scope", "reason": "r"},
        {"utc": "now", "from": "inconclusive", "to": "rejected", "reason": "r"},
    ]
    with pytest.raises(LedgerIntegrityError):
        Ledger({"records": [row]}).validate()


def test_validate_rejects_initial_status_without_history():
    row = _row("even", 2)
    row["initial_status"] = "verified"
    with pytest.raises(LedgerIntegrityError):
        Ledger({"records": [row]}).validate()


# ------------------------------------------------------------ live corpus ---


@pytest.fixture(scope="module")
def corpus() -> Ledger:
    return Ledger.load(CORPUS, validate=False)


def test_live_corpus_satisfies_every_ledger_invariant(corpus):
    corpus.validate()


def test_live_corpus_uses_only_the_five_statuses(corpus):
    seen = {Status.coerce(r["status"]) for r in corpus.records}
    assert seen <= set(Status)


def test_live_corpus_denominator_excludes_undecided_rows(corpus):
    domain = PolytopeDomain()
    counts = corpus.counts(domain)
    undecided = counts["outside_scope"] + counts["rejected"] + counts["inconclusive"]
    # The honest denominator is strictly smaller than the parse-valid corpus.
    assert corpus.in_scope_total(domain) == len(corpus) - undecided
    assert undecided > 0, "a corpus with nothing undecided is a red flag, not a win"


def test_live_corpus_retains_its_reversals(corpus):
    reversals = corpus.reversals()
    assert reversals, "the reversal history is the point; losing it is a regression"
    for row in reversals:
        assert row["initial_status"] == row["adjudication_history"][0]["from"]
        assert row["adjudication_history"][-1]["to"] == row["status"]


def test_polytope_domain_identity_includes_the_law(corpus):
    domain = PolytopeDomain()
    # Deduplication must not collapse distinct records.
    assert len({domain.identity(r) for r in corpus.records}) == len(corpus)


def test_polytope_domain_invalidation_map_is_narrow_but_nonempty(corpus):
    domain = PolytopeDomain()
    assert domain.rules_invalidated_between(15, 15) == set()
    assert domain.rules_invalidated_between(14, 15) == {"V.10"}
    assert domain.rules_invalidated_between(5, 15) <= set(domain.rule_ids)


# ---------------------------------------------------------------- schema ---


def test_legacy_schema_is_refused_rather_than_silently_upgraded(tmp_path):
    # Reading must never rewrite. A v1 corpus points at the migration script.
    legacy = {"records": [{"law": "V.7", "name": "n", "expr": "sigma",
                           "base_expr": "", "status": "verified", "reason": "",
                           "metrics": {}, "note": ""}]}
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(LedgerIntegrityError) as exc:
        Ledger.load(path)
    assert "migrate_corpus_schema" in str(exc.value)
    # and the file on disk is untouched
    assert json.loads(path.read_text(encoding="utf-8")) == legacy


def test_an_empty_corpus_starts_at_the_current_schema(tmp_path):
    ledger = Ledger.load(tmp_path / "new.json")
    assert ledger.state["schema_version"] == SCHEMA_VERSION


def test_saving_stamps_the_schema_version(tmp_path):
    path = tmp_path / "out.json"
    Ledger({"records": [_row("even", 2)]}, path=path).save()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


def test_validate_requires_the_generic_envelope():
    for missing in ("rule_id", "name", "payload", "status"):
        row = _row("even", 2)
        del row[missing]
        with pytest.raises(LedgerIntegrityError):
            Ledger({"records": [row]}).validate()


def test_validate_rejects_a_non_object_payload():
    row = _row("even", 2)
    row["payload"] = "sigma**2"
    with pytest.raises(LedgerIntegrityError):
        Ledger({"records": [row]}).validate()


def test_live_corpus_is_at_the_current_schema(corpus):
    assert corpus.state["schema_version"] == SCHEMA_VERSION


def test_migrate_row_moves_fields_without_re_deciding_anything():
    legacy = {"law": "V.14", "name": "pair", "expr": "sqrt(sigma)",
              "base_expr": "-(1-lam)**4", "status": "counterexample",
              "reason": "mismatch", "metrics": {"beta": 4.0}, "note": "n",
              "initial_status": "verified",
              "adjudication_history": [{"utc": "t", "from": "verified",
                                        "to": "counterexample", "reason": "r"}]}
    row = PolytopeDomain.migrate_row(legacy)
    assert row["rule_id"] == "V.14"
    assert row["payload"] == {"expr": "sqrt(sigma)", "base_expr": "-(1-lam)**4"}
    # Every adjudication field survives untouched - migration moves, never decides.
    assert row["status"] == "counterexample"
    assert row["reason"] == "mismatch"
    assert row["metrics"] == {"beta": 4.0}
    assert row["initial_status"] == "verified"
    assert row["adjudication_history"] == legacy["adjudication_history"]
    assert not {"law", "expr", "base_expr"} & set(row)
