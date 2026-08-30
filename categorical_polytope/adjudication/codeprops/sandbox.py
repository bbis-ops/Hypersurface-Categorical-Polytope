"""
Process isolation for running a property against an untrusted input.

Domain one could parse a candidate with an AST whitelist and evaluate it in
process, because a candidate there was an arithmetic expression. Here a
candidate is an *input* to real code, and real code can hang, recurse, or
allocate without bound. None of that is safe to run in the campaign's own
interpreter, so each check gets its own.

What this does guarantee:

  * a wall-clock timeout, enforced by killing the child
  * a crash, recursion blowup, or non-zero exit is reported, not propagated
  * one runaway candidate costs one process

What it does not: `resource.setrlimit` is POSIX-only, so there is no hard
memory cap on Windows. `MemoryError` inside the child is reported as
`exhausted` and adjudicated `inconclusive` - an admission that the box ran out,
never a claim about the code. Nor is this a security boundary: the code under
test is repo-local and the input is a literal, so the threat model is resource
exhaustion, not hostile execution. A domain that ran model-authored *code*
would need a real jail, not this.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

WORKER = Path(__file__).resolve().parent / "_worker.py"

#: Wall-clock budget per candidate. Anything slower is undecided, not passing.
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class RunResult:
    """What the sandbox observed. Deliberately not a verdict."""

    #: held | failed | raised | exhausted | timeout | crashed | harness_error
    outcome: str
    detail: str = ""
    seconds: float = 0.0

    @property
    def decided(self) -> bool:
        return self.outcome in ("held", "failed", "raised")


def run_property(
    rule_id: str,
    args: Sequence[Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> RunResult:
    """Run one property check in a child interpreter and report what happened."""
    request = json.dumps({"rule_id": rule_id, "args": list(args)})
    try:
        completed = subprocess.run(
            [sys.executable, str(WORKER)],
            input=request,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RunResult("timeout", f"exceeded {timeout}s", timeout)
    except OSError as exc:  # pragma: no cover - spawn failure is environmental
        return RunResult("harness_error", f"spawn failed: {exc}")

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        return RunResult("crashed", f"exit {completed.returncode}: {detail[-1] if detail else ''}")

    line = (completed.stdout or "").strip().splitlines()
    if not line:
        return RunResult("crashed", "child produced no output")
    try:
        payload = json.loads(line[-1])
    except json.JSONDecodeError:
        return RunResult("crashed", f"unparseable child output: {line[-1][:120]}")

    return RunResult(str(payload.get("outcome", "harness_error")), str(payload.get("detail", "")))
