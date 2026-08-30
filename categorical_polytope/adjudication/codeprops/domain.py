"""
Domain two: generated-code property violation.

A rule is `target/property`; a candidate is an input claimed to break it. The
adjudicator is CPython running a reference implementation - free, unarguable,
and not a model. That is the only property of this domain that matters
strategically: swap the interpreter for an LLM judge and the denominators stop
meaning anything.

The five statuses land the same way they do for the polytope laws:

  rejected       the payload is not a literal, or names no known rule
  outside_scope  a well-formed input the function never claimed to accept
  inconclusive   in contract, but the run timed out or the box ran out
  verified       the property held
  counterexample the property failed, or the function raised, on valid input

Scope and verdict stay in separate stages. The contract check runs in this
process and never spawns anything; only an admitted candidate is worth the cost
of a subprocess. That ordering is also the honest one - admission is decided
before there is any result to be embarrassed by.
"""

from __future__ import annotations

import ast
from typing import Any, Hashable, Mapping, Sequence

from ..domain import Transport, Verdict
from ..status import Status
from . import targets
from .sandbox import DEFAULT_TIMEOUT_SECONDS, RunResult, run_property

#: Bumped whenever adjudicator semantics change.
VERIFIER_VERSION = 1

#: Rules whose adjudicator changed at each version.
REVERIFY_RULES_BY_VERSION: dict[int, set[str]] = {}

#: Longest literal payload accepted, mirroring domain one's expression cap.
MAX_PAYLOAD_CHARS = 4000

#: Written out to keep the escape legible in the repair path below.
BACKSLASH = chr(92)


class CodePropertyDomain:
    """Adapts reference-implementation property checks to the `Domain` protocol."""

    name = "code-properties"

    def __init__(
        self,
        verifier_version: int = VERIFIER_VERSION,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.verifier_version = int(verifier_version)
        self.timeout = float(timeout)

    @property
    def rule_ids(self) -> Sequence[str]:
        return targets.RULE_IDS

    def rules_invalidated_between(self, prior: int, current: int) -> set[str]:
        if prior == current:
            return set()
        affected: set[str] = set()
        for version in range(prior + 1, current + 1):
            affected |= REVERIFY_RULES_BY_VERSION.get(version, set())
        return affected

    def identity(self, row: Mapping[str, Any]) -> Hashable:
        # Includes the rule: the same input against two properties is two records.
        return (row["rule_id"], row["payload"]["args"])

    def readjudicate(self, row: Mapping[str, Any]) -> Verdict:
        """Re-run the adjudicator over a stored row. Never reads its status."""
        return self.adjudicate(str(row["rule_id"]), row["payload"].get("args", "()"))

    # -- stage one: admission ----------------------------------------------

    def parse(self, rule_id: str, args_literal: str) -> tuple:
        """
        Turn an untrusted payload into a Python value.

        `literal_eval` is this domain's whitelist: it accepts numbers, strings,
        booleans, None, and the container literals, and nothing that can call,
        import, or reach an attribute. A hostile payload can only be rejected.
        """
        if rule_id not in targets.RULES:
            raise ValueError(f"unknown rule: {rule_id}")
        if len(args_literal) > MAX_PAYLOAD_CHARS:
            raise ValueError(f"payload exceeds {MAX_PAYLOAD_CHARS} characters")
        try:
            value = ast.literal_eval(args_literal)
        except (ValueError, SyntaxError):
            # Models sometimes double-escape quotes inside the JSON string, so
            # a valid payload arrives as ([\"a"\,...], 1). Measured
            # 2026-08-26: 4 of 10 rejections in the first real campaign were
            # this, not hostile or malformed input. Retry once with the stray
            # escapes removed. `literal_eval` still governs the result, so a
            # payload that was never safe cannot become safe here.
            repaired = args_literal.replace(BACKSLASH + '"', '"').replace(
                BACKSLASH + "'", "'")
            if repaired == args_literal:
                raise
            value = ast.literal_eval(repaired)
        if not isinstance(value, tuple):
            value = (value,)
        return value

    def scope(self, rule_id: str, args_literal: str) -> tuple[bool, str, str, dict]:
        """
        Decide admissibility: (admitted, status, reason, metrics).

        Consults the payload and the declared contract only. It has no access
        to a run result, so admission cannot be withdrawn once the property
        turns out to fail.
        """
        try:
            args = self.parse(rule_id, args_literal)
        except (ValueError, SyntaxError, MemoryError, RecursionError) as exc:
            return False, "rejected", f"unparseable payload: {type(exc).__name__}: {exc}", {}

        metrics: dict[str, Any] = {"arity": len(args)}
        breach = targets.check_contract(rule_id, args)
        if breach is not None:
            metrics["contract_breach"] = breach
            # Retained and counted. Never a pass, and never quietly dropped:
            # "your test failed on input we never supported" is a real answer,
            # but only when it is decided before the test is run.
            return False, "outside_scope", f"input is out of contract: {breach}", metrics
        return True, "", "", metrics

    # -- stage two: verdict ------------------------------------------------

    @staticmethod
    def _verdict_from(run: RunResult) -> tuple[Status, str]:
        if run.outcome == "held":
            return Status.VERIFIED, "property held on an in-contract input"
        if run.outcome == "failed":
            return Status.COUNTEREXAMPLE, "property failed on an in-contract input"
        if run.outcome == "raised":
            # A crash on input the function advertises is a defect, not a
            # scope question. Routing it to outside_scope would be the exact
            # trapdoor this design exists to close.
            return Status.COUNTEREXAMPLE, f"raised on an in-contract input: {run.detail}"
        if run.outcome == "timeout":
            return Status.INCONCLUSIVE, f"undecided within budget: {run.detail}"
        if run.outcome == "exhausted":
            return Status.INCONCLUSIVE, f"resources exhausted: {run.detail}"
        return Status.INCONCLUSIVE, f"sandbox could not decide: {run.outcome} {run.detail}".strip()

    def adjudicate(self, rule_id: str, args_literal: str) -> Verdict:
        """Full adjudication: admission first, then - only if admitted - a run."""
        admitted, status, reason, metrics = self.scope(rule_id, args_literal)
        if not admitted:
            return Verdict(Status.coerce(status), reason, metrics)

        args = self.parse(rule_id, args_literal)
        run = run_property(rule_id, args, timeout=self.timeout)
        verdict_status, verdict_reason = self._verdict_from(run)
        metrics = {**metrics, "sandbox_outcome": run.outcome, "timeout_seconds": self.timeout}
        if run.detail:
            metrics["sandbox_detail"] = run.detail
        return Verdict(verdict_status, verdict_reason, metrics)

    # -- ledger envelope ---------------------------------------------------

    def to_row(self, rule_id: str, name: str, args_literal: str, note: str = "") -> dict[str, Any]:
        """Adjudicate a candidate and render it as a generic ledger row."""
        verdict = self.adjudicate(rule_id, args_literal)
        return {
            "rule_id": rule_id,
            "name": name,
            "payload": {"args": args_literal},
            "status": str(verdict.status),
            "reason": verdict.reason,
            "metrics": verdict.metrics,
            "note": note,
        }

    # -- generation (the `Generative` half of the protocol) -----------------

    def propose(
        self,
        rule_id: str,
        n: int,
        transport: Transport,
        *,
        focus: str = "",
    ) -> tuple[list[dict[str, Any]], str]:
        """Request candidate inputs for one rule and adjudicate them."""
        from ...interaction_search import propose_candidates
        from .prompts import parse_input_proposals, proposal_prompt

        proposed, backend = propose_candidates(
            n,
            prompt=proposal_prompt(rule_id, n) + focus,
            parser=parse_input_proposals(rule_id),
            **transport.as_kwargs(),
        )
        rows = [self.to_row(s.rule_id, s.name, s.args, s.note) for s in proposed]
        return rows, backend

    def focus_for(self, row: Mapping[str, Any]) -> str:
        from .prompts import focus_prompt

        return focus_prompt(str(row["rule_id"]), row["payload"]["args"])
