"""
A tamper-evident store for adjudicated proposals.

The ledger is domain-blind. It holds rows, deduplicates them, re-adjudicates
them when a `Domain` reports a new verifier version, and - the part that
matters - retains the history when a verdict reverses. A record that was
`verified` and is later found `outside_scope` keeps both facts, with a
timestamp and a reason.

Two invariants make the denominator non-gameable:

  1. Status changes only through `sync_verifier`, which always appends history.
     There is no path that quietly overwrites a verdict.
  2. Every status is in the five-value vocabulary, and only `verified` passes.
     Rows the adjudicator could not decide stay in the corpus and stay counted.

Stdlib only.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Hashable, Iterable, Mapping

from .domain import Domain, Verdict
from .status import IN_SCOPE, Status

#: On-disk record schema. v1 stored domain-one's fields at the top level
#: (`law`, `expr`, `base_expr`); v2 stores the generic `rule_id` plus a
#: domain-owned `payload`. A corpus is never silently upgraded - see
#: `experiments/migrate_corpus_schema.py`.
SCHEMA_VERSION = 2

#: Fields every record carries, whatever the domain.
REQUIRED_FIELDS = ("rule_id", "name", "payload", "status")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReadjudicationReport:
    """What one `sync_verifier` pass did."""

    prior_version: int
    current_version: int
    affected_rules: set[str] = field(default_factory=set)
    examined: int = 0
    rechecked: int = 0
    reversals: list[dict[str, Any]] = field(default_factory=list)

    @property
    def changed(self) -> int:
        return len(self.reversals)

    def summary(self) -> str:
        if self.prior_version == self.current_version:
            return f"verifier v{self.current_version}: no re-adjudication needed"
        return (
            f"verifier v{self.prior_version} -> v{self.current_version}: "
            f"rechecked {self.rechecked}/{self.examined} rows across "
            f"{len(self.affected_rules)} rules, {self.changed} verdict(s) reversed"
        )


class LedgerIntegrityError(ValueError):
    """A stored row violates an invariant the ledger guarantees."""


class Ledger:
    """Append-mostly corpus of adjudicated proposals."""

    def __init__(self, state: dict[str, Any] | None = None, *, path: Path | None = None):
        self.path = path
        self.state: dict[str, Any] = state if state is not None else self._empty()
        self.state.setdefault("records", [])
        self.state.setdefault("requests", [])

    # -- construction ------------------------------------------------------

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"created_utc": _now(), "schema_version": SCHEMA_VERSION,
                "backend": "", "requests": [], "records": []}

    @classmethod
    def load(cls, path: Path, *, validate: bool = True) -> "Ledger":
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
        else:
            state = cls._empty()
        ledger = cls(state, path=path)
        ledger.require_current_schema()
        if validate:
            ledger.validate()
        return ledger

    def require_current_schema(self) -> None:
        """
        Refuse a corpus written under an older record schema.

        Upgrading in place on load would rewrite data as a side effect of
        reading it. Migration is a deliberate, backed-up, verifiable step.
        """
        found = int(self.state.get("schema_version", 1))
        if found == SCHEMA_VERSION:
            return
        if not self.records and "schema_version" not in self.state:
            self.state["schema_version"] = SCHEMA_VERSION
            return
        raise LedgerIntegrityError(
            f"corpus is schema v{found}, this build expects v{SCHEMA_VERSION}. "
            f"Run: python experiments/migrate_corpus_schema.py"
        )

    def save(self, path: Path | None = None) -> Path:
        """Atomic write: a crash mid-save leaves the previous corpus intact."""
        target = path or self.path
        if target is None:
            raise ValueError("no path bound to this ledger")
        self.state["schema_version"] = SCHEMA_VERSION
        self.state["updated_utc"] = _now()
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        tmp.replace(target)
        return target

    # -- accessors ---------------------------------------------------------

    @property
    def records(self) -> list[dict[str, Any]]:
        return self.state["records"]

    @property
    def requests(self) -> list[dict[str, Any]]:
        return self.state["requests"]

    @property
    def verifier_version(self) -> int | None:
        raw = self.state.get("verifier_version")
        return None if raw is None else int(raw)

    def __len__(self) -> int:
        return len(self.records)

    # -- integrity ---------------------------------------------------------

    @staticmethod
    def rule_id_of(row: Mapping[str, Any]) -> str:
        """The rule a row was adjudicated against. Generic since schema v2."""
        return str(row["rule_id"])

    def validate(self) -> None:
        """Fail closed on any row the ledger's guarantees do not cover."""
        for index, row in enumerate(self.records):
            missing = [f for f in REQUIRED_FIELDS if f not in row]
            if missing:
                raise LedgerIntegrityError(f"record {index}: missing {missing}")
            if not isinstance(row["payload"], dict):
                raise LedgerIntegrityError(
                    f"record {index}: payload must be an object, got "
                    f"{type(row['payload']).__name__}"
                )
            try:
                status = Status.coerce(row.get("status"))
            except ValueError as exc:
                raise LedgerIntegrityError(f"record {index}: {exc}") from exc
            history = row.get("adjudication_history") or []
            if not history:
                if "initial_status" in row:
                    raise LedgerIntegrityError(
                        f"record {index}: initial_status without adjudication_history"
                    )
                continue
            for entry in history:
                missing = {"utc", "from", "to", "reason"} - set(entry)
                if missing:
                    raise LedgerIntegrityError(
                        f"record {index}: history entry missing {sorted(missing)}"
                    )
            for earlier, later in zip(history, history[1:]):
                if earlier["to"] != later["from"]:
                    raise LedgerIntegrityError(
                        f"record {index}: history chain broken at "
                        f"{earlier['to']} -> {later['from']}"
                    )
            if history[-1]["to"] != status:
                raise LedgerIntegrityError(
                    f"record {index}: history ends at {history[-1]['to']} "
                    f"but status is {status}"
                )
            if row.get("initial_status") != history[0]["from"]:
                raise LedgerIntegrityError(
                    f"record {index}: initial_status {row.get('initial_status')!r} "
                    f"does not match first history entry {history[0]['from']!r}"
                )

    # -- the core operation ------------------------------------------------

    def sync_verifier(self, domain: Domain) -> ReadjudicationReport:
        """
        Bring the corpus up to the domain's current verifier version.

        Rows whose rule was not invalidated keep their verdict untouched. Rows
        that were invalidated are re-adjudicated from scratch; when the verdict
        moves, the reversal is appended to the row's history rather than
        replacing what was there.
        """
        current = int(domain.verifier_version)
        prior = self.verifier_version
        prior = current if prior is None else prior
        report = ReadjudicationReport(prior_version=prior, current_version=current)

        if prior != current:
            report.affected_rules = set(domain.rules_invalidated_between(prior, current))
            refreshed: list[dict[str, Any]] = []
            for old in self.records:
                report.examined += 1
                if self.rule_id_of(old) not in report.affected_rules:
                    refreshed.append(old)
                    continue
                report.rechecked += 1
                refreshed.append(self._apply(old, domain.readjudicate(old), report))
            self.state["records"] = refreshed

        self.state["verifier_version"] = current
        return report

    @staticmethod
    def _apply(
        old: Mapping[str, Any], verdict: Verdict, report: ReadjudicationReport
    ) -> dict[str, Any]:
        """Merge a fresh verdict onto a stored row, retaining any reversal."""
        row = dict(old)
        row["status"] = str(verdict.status)
        row["reason"] = verdict.reason
        row["metrics"] = verdict.metrics
        history = list(old.get("adjudication_history") or [])
        was = old.get("status")
        if was != row["status"]:
            entry = {
                "utc": _now(),
                "from": was,
                "to": row["status"],
                "reason": verdict.reason,
            }
            history.append(entry)
            report.reversals.append({"name": old.get("name"), **entry})
        if history:
            row["adjudication_history"] = history
            row["initial_status"] = old.get("initial_status", was)
        return row

    # -- admission ---------------------------------------------------------

    def seen(self, domain: Domain) -> set[Hashable]:
        return {domain.identity(row) for row in self.records}

    def admit(
        self,
        domain: Domain,
        rows: Iterable[Mapping[str, Any]],
        *,
        seen: set[Hashable] | None = None,
    ) -> list[dict[str, Any]]:
        """Append rows whose identity is not already held. Returns what was new."""
        known = self.seen(domain) if seen is None else seen
        fresh: list[dict[str, Any]] = []
        for row in rows:
            key = domain.identity(row)
            if key in known:
                continue
            known.add(key)
            fresh.append(dict(row))
        self.records.extend(fresh)
        return fresh

    def record_request(self, **fields: Any) -> None:
        self.requests.append({"utc": _now(), **fields})

    # -- counting ----------------------------------------------------------

    def counts(self, domain: Domain, rule_id: str | None = None) -> Counter:
        """Status histogram, over one rule or the whole corpus."""
        rows = (
            self.records
            if rule_id is None
            else [r for r in self.records if self.rule_id_of(r) == rule_id]
        )
        return Counter(str(Status.coerce(r["status"])) for r in rows)

    def in_scope_total(self, domain: Domain, rule_id: str | None = None) -> int:
        """Size of the denominator a pass rate may legitimately be taken over."""
        counts = self.counts(domain, rule_id)
        return sum(counts[str(s)] for s in IN_SCOPE)

    def reversals(self) -> list[dict[str, Any]]:
        """Every row whose verdict has ever moved."""
        return [r for r in self.records if r.get("adjudication_history")]
