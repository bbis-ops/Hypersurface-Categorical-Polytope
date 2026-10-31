"""The calculator's tape: recorded calculations kept under version control.

A desk calculator prints a paper tape; this one commits it. Each file in
``calculations/`` stores an input and the discrete outcome of its receipt.
``verify`` recomputes every entry with the current code and reports any
answer that drifted, so a change to the backend, the certificate, or the
counter-arguments that alters a recorded result cannot pass silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .provenance import ROOT
from .receipt import calculate

SCHEMA = "gitcalculator.tape.v1"
TAPE = ROOT / "calculations"


def _diff(old: Any, new: Any, path: str = "") -> list[str]:
    if isinstance(old, Mapping) and isinstance(new, Mapping):
        lines = []
        for key in sorted(set(old) | set(new), key=str):
            lines += _diff(old.get(key), new.get(key), f"{path}.{key}" if path else str(key))
        return lines
    return [] if old == new else [f"{path}: {json.dumps(old, ensure_ascii=False)} → {json.dumps(new, ensure_ascii=False)}"]


def entry(name: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    provenance = receipt["provenance"]
    return {
        "schema": SCHEMA,
        "name": name,
        "input": receipt["input"],
        "receipt_id": receipt["id"],
        "answer": {k: receipt["answer"][k] for k in ("verdict", "headline", "gamma", "q_star")},
        "signature": receipt["signature"],
        "recorded_with": {"commit": provenance["git"].get("commit"), "code_id": provenance["code_id"],
                          "calculator_id": provenance["calculator_id"]},
    }


def record(name: str, request: Mapping[str, Any], directory: Path = TAPE) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(entry(name, calculate(request)), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def verify(directory: Path = TAPE) -> list[dict[str, Any]]:
    """Recompute every recorded calculation and report drift."""
    report = []
    for path in sorted(directory.glob("*.json")):
        stored = json.loads(path.read_text(encoding="utf-8"))
        receipt = calculate(stored["input"])
        drift = _diff(stored["signature"], receipt["signature"])
        report.append({"name": stored["name"], "file": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                       "unchanged": not drift, "drift": drift,
                       "recorded_receipt": stored["receipt_id"], "current_receipt": receipt["id"]})
    return report
