#!/usr/bin/env python3
"""
Child process that runs one property check and reports the outcome as JSON.

Runs in its own interpreter so that a hang, a crash, or a runaway recursion in
the function under test costs one process rather than the campaign. Reads a
single JSON request on stdin and writes a single JSON line on stdout.

Never invoked directly - see `sandbox.run_property`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"outcome": "harness_error", "detail": f"bad request: {exc}"}))
        return 0

    try:
        from categorical_polytope.adjudication.codeprops.targets import check_property
    except Exception as exc:  # pragma: no cover - import failure is a harness bug
        print(json.dumps({"outcome": "harness_error", "detail": f"import failed: {exc!r}"}))
        return 0

    rule_id = request.get("rule_id")
    args = tuple(request.get("args", []))

    # Recursion in the function under test must not take the interpreter down
    # in a way we cannot report; cap it well below the platform limit.
    sys.setrecursionlimit(2000)

    try:
        held = bool(check_property(rule_id, args))
    except RecursionError as exc:
        print(json.dumps({"outcome": "raised", "detail": f"RecursionError: {exc}"}))
        return 0
    except MemoryError as exc:
        # Not a defect in the function: the box ran out, so nothing was decided.
        print(json.dumps({"outcome": "exhausted", "detail": f"MemoryError: {exc}"}))
        return 0
    except KeyError as exc:
        print(json.dumps({"outcome": "harness_error", "detail": f"unknown rule {exc}"}))
        return 0
    except BaseException as exc:  # noqa: BLE001 - the point is to catch everything
        print(json.dumps({"outcome": "raised", "detail": f"{type(exc).__name__}: {exc}"}))
        return 0

    print(json.dumps({"outcome": "held" if held else "failed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
