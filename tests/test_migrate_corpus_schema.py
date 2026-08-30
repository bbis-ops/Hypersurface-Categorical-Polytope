import json
import os
import sys
from pathlib import Path

from experiments import migrate_corpus_schema


def _v1_state():
    return {
        "schema_version": 1,
        "records": [{
            "law": "V.7",
            "name": "custom",
            "expr": "sigma",
            "base_expr": "",
            "status": "verified",
            "reason": "kept",
            "metrics": {"evidence": 1},
            "note": "",
        }],
    }


def _paths(label):
    directory = Path(__file__).resolve().parents[1] / "experiments"
    corpus = directory / f"_test_{label}_{os.getpid()}.json"
    return corpus, migrate_corpus_schema._backup_path(corpus)


def test_custom_corpus_gets_its_own_verified_backup(monkeypatch):
    corpus, backup = _paths("custom_migration")
    corpus.unlink(missing_ok=True)
    backup.unlink(missing_ok=True)
    original = _v1_state()
    try:
        corpus.write_text(json.dumps(original), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["migrate", "--corpus", str(corpus)])

        assert migrate_corpus_schema.main() == 0

        assert json.loads(backup.read_text(encoding="utf-8")) == original
        assert json.loads(corpus.read_text(encoding="utf-8"))["schema_version"] == 2
    finally:
        corpus.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)


def test_migration_refuses_unrelated_existing_backup(monkeypatch):
    corpus, backup = _paths("conflicting_migration")
    corpus.unlink(missing_ok=True)
    backup.unlink(missing_ok=True)
    try:
        corpus.write_text(json.dumps(_v1_state()), encoding="utf-8")
        backup.write_text(json.dumps({"different": True}), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["migrate", "--corpus", str(corpus)])

        assert migrate_corpus_schema.main() == 2
        assert json.loads(corpus.read_text(encoding="utf-8"))["schema_version"] == 1
    finally:
        corpus.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)
