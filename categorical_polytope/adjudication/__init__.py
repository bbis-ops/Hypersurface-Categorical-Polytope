"""
Domain-independent adjudication harness.

A `Domain` says what a proposal is and how to decide it; a `Ledger` stores the
decisions, re-adjudicates them when the verifier changes, and retains every
reversal. The five-value `Status` vocabulary is the contract between them, and
is what keeps a pass rate honest: only `verified` passes, and nothing the
adjudicator could not decide leaves the denominator.

Adding a domain means implementing `Domain`. The one hard constraint is that
its adjudicator must be ground truth for the rule - an interpreter, a solver, a
policy engine - never a model's opinion.
"""

from .domain import Domain, Screenable, UnsafeProposal, Verdict
from .ledger import Ledger, LedgerIntegrityError, ReadjudicationReport
from .screening import (
    CONFIRMING,
    DECISIVE,
    REFUSED,
    SELECTIVE,
    UNLICENSED,
    VALUE_ORDER,
    Layer,
    Screening,
    rank,
    summarise,
    tally,
)
from .status import ALL, IN_SCOPE, NOT_PASSING, Status

__all__ = [
    "ALL",
    "CONFIRMING",
    "DECISIVE",
    "Domain",
    "Layer",
    "REFUSED",
    "SELECTIVE",
    "Screenable",
    "Screening",
    "UNLICENSED",
    "VALUE_ORDER",
    "IN_SCOPE",
    "Ledger",
    "LedgerIntegrityError",
    "NOT_PASSING",
    "ReadjudicationReport",
    "Status",
    "UnsafeProposal",
    "Verdict",
    "rank",
    "summarise",
    "tally",
]
