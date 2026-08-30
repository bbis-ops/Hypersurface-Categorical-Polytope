#!/usr/bin/env python3
"""
One-time migration of the V.7--V.14 corpus from record schema v1 to v2.

v1 stored domain-one's fields at the top level::

    {"law": "V.10", "expr": "...", "base_expr": "", "status": ...}

v2 stores the generic envelope the ledger shares with every domain::

    {"rule_id": "V.10", "payload": {"expr": "...", "base_expr": ""}, "status": ...}

This moves fields. It never re-adjudicates: statuses, reasons, metrics, and the
full reversal history carry across byte-for-byte, and the script refuses to
write unless it can prove that. Run with --check to verify without writing.
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

from categorical_polytope.adjudication.ledger import SCHEMA_VERSION  # noqa: E402
from categorical_polytope.adjudication.polytope import PolytopeDomain  # noqa: E402

CORPUS = ROOT / "experiments" / "verification_campaign.json"

#: Fields that must survive migration untouched, per record.
PRESERVED = ("status", "reason", "metrics", "note", "adjudication_history", "initial_status")


def _verify(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[str]:
    """Every way this migration could have lost or altered evidence."""
    problems: list[str] = []
    if len(old) != len(new):
        problems.append(f"record count changed: {len(old)} -> {len(new)}")
        return problems

    for index, (before, after) in enumerate(zip(old, new)):
        for key in PRESERVED:
            if before.get(key) != after.get(key):
                problems.append(f"record {index}: {key} changed")
        if after.get("rule_id") != before.get("law"):
            problems.append(f"record {index}: rule_id does not match law")
        if after.get("name") != before.get("name"):
            problems.append(f"record {index}: name changed")
        payload = after.get("payload", {})
        if payload.get("expr") != before.get("expr"):
            problems.append(f"record {index}: payload.expr does not match expr")
        if payload.get("base_expr", "") != before.get("base_expr", ""):
            problems.append(f"record {index}: payload.base_expr does not match base_expr")
        if any(k in after for k in ("law", "expr", "base_expr")):
            problems.append(f"record {index}: legacy field left behind")

    before_counts = Counter(r["status"] for r in old)
    after_counts = Counter(r["status"] for r in new)
    if before_counts != after_counts:
        problems.append(f"status histogram changed: {before_counts} -> {after_counts}")

    before_hist = sum(len(r.get("adjudication_history") or []) for r in old)
    after_hist = sum(len(r.get("adjudication_history") or []) for r in new)
    if before_hist != after_hist:
        problems.append(f"history entries lost: {before_hist} -> {after_hist}")

    return problems


def _backup_path(corpus: Path) -> Path:
    """A schema-v1 backup adjacent to, and uniquely derived from, its corpus."""
    return corpus.with_name(f"{corpus.stem}.v1.backup{corpus.suffix}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the migration without writing anything")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    args = ap.parse_args()

    if not args.corpus.exists():
        print(f"no corpus at {args.corpus}; nothing to migrate")
        return 0

    state = json.loads(args.corpus.read_text(encoding="utf-8"))
    found = int(state.get("schema_version", 1))
    if found == SCHEMA_VERSION:
        print(f"corpus is already schema v{SCHEMA_VERSION}; nothing to do")
        return 0
    if found != 1:
        print(f"unknown schema v{found}; refusing to migrate", file=sys.stderr)
        return 2

    old = state["records"]
    new = [PolytopeDomain.migrate_row(row) for row in old]
    problems = _verify(old, new)
    if problems:
        print(f"MIGRATION REFUSED - {len(problems)} problem(s):", file=sys.stderr)
        for problem in problems[:20]:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    counts = Counter(r["status"] for r in new)
    reversals = sum(1 for r in new if r.get("adjudication_history"))
    print(f"verified {len(new)} records migrate cleanly")
    print(f"  statuses:  {dict(counts)}")
    print(f"  reversals: {reversals} retained")

    if args.check:
        print("--check: nothing written")
        return 0

    backup = _backup_path(args.corpus)
    if not backup.exists():
        backup.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"  backup:    {backup.name}")
    else:
        try:
            backed_up_state = json.loads(backup.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"backup {backup} is unreadable; refusing migration: {exc}", file=sys.stderr)
            return 2
        if backed_up_state != state:
            print(
                f"backup {backup} does not match {args.corpus}; refusing migration",
                file=sys.stderr,
            )
            return 2
        print(f"  backup:    {backup.name} already exists and matches, kept")

    state["records"] = new
    state["schema_version"] = SCHEMA_VERSION
    tmp = args.corpus.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(args.corpus)
    print(f"wrote {args.corpus} at schema v{SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
