"""
The five-status adjudication vocabulary.

This is the domain-independent core of the harness. A proposal that reaches the
ledger lands in exactly one of these states, and the split between them is what
keeps a denominator honest:

    rejected       failed the sandbox boundary; never reached the adjudicator
    outside_scope  well-formed, but does not satisfy the rule's hypotheses
    inconclusive   in scope, but the verifier could not decide
    verified       in scope, rule held
    counterexample in scope, rule failed; requires independent review

Only `verified` is a pass. The other four are retained and counted, which is the
entire point: a harness that may silently drop what it cannot adjudicate can
always reach 100%.

`Status` subclasses `str`, so existing corpora that store plain strings compare
and serialize unchanged.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Status(str, Enum):
    """A terminal adjudication state."""

    REJECTED = "rejected"
    OUTSIDE_SCOPE = "outside_scope"
    INCONCLUSIVE = "inconclusive"
    VERIFIED = "verified"
    COUNTEREXAMPLE = "counterexample"

    def __str__(self) -> str:  # keep f-strings and JSON writing legacy-identical
        return self.value

    @property
    def is_pass(self) -> bool:
        """Exactly one status is a pass. Do not widen this."""
        return self is Status.VERIFIED

    @property
    def is_in_scope(self) -> bool:
        """In-scope means the rule's hypotheses were met and a verdict was reached."""
        return self in IN_SCOPE

    @classmethod
    def coerce(cls, value: Any) -> "Status":
        """Parse a stored string. Raises on anything outside the vocabulary."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown adjudication status: {value!r}") from exc


#: Statuses that count toward an in-scope denominator.
IN_SCOPE: frozenset[Status] = frozenset({Status.VERIFIED, Status.COUNTEREXAMPLE})

#: Statuses that are retained and counted but are never a pass.
NOT_PASSING: frozenset[Status] = frozenset(
    {Status.REJECTED, Status.OUTSIDE_SCOPE, Status.INCONCLUSIVE, Status.COUNTEREXAMPLE}
)

#: Every status. A record outside this set is a bug, not a new category.
ALL: frozenset[Status] = frozenset(Status)
