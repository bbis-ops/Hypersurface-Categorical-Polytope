"""
The seam between the ledger and whatever is being adjudicated.

The ledger below knows how to store proposals, re-adjudicate them when the
verifier changes, retain the reversal history, and count an honest denominator.
It knows nothing about what a proposal *is*. A `Domain` supplies that: the rule
set, the identity used for deduplication, and the adjudicator itself.

Every stored row carries the same generic envelope::

    {"rule_id": str, "name": str, "payload": {...}, "status": str,
     "reason": str, "metrics": {...}, "note": str}

`payload` is the domain's own object - an expression pair here, a function and
a failing input elsewhere - and the ledger never looks inside it. Only
`identity` and `readjudicate` do.

Implementing this protocol is the whole cost of adding a domain. The one hard
constraint is on `readjudicate`: the verdict must come from a machine that is
ground truth for the rule, not from a model's opinion. A domain whose
adjudicator is itself a language model reintroduces the circularity the harness
exists to remove, and its denominators mean nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable, Mapping, Protocol, Sequence, runtime_checkable

from .screening import Screening
from .status import Status


class UnsafeProposal(ValueError):
    """A proposal rejected at the sandbox boundary, before adjudication."""


@dataclass(frozen=True)
class Verdict:
    """The outcome of adjudicating one candidate against one rule."""

    status: Status
    reason: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", Status.coerce(self.status))


@runtime_checkable
class Domain(Protocol):
    """What a subject area must provide to be adjudicated by the ledger."""

    #: Stable identifier, used to namespace stored corpora.
    name: str

    #: Bumped whenever adjudicator semantics change. Drives re-adjudication.
    verifier_version: int

    @property
    def rule_ids(self) -> Sequence[str]:
        """Every rule this domain can adjudicate against."""

    def rules_invalidated_between(self, prior: int, current: int) -> set[str]:
        """
        Rules whose adjudicator changed while moving from `prior` to `current`.

        Returning a narrow set is an optimization, not a correctness knob: a
        rule omitted here keeps its old verdict even though the verifier moved.
        Return every rule id when in doubt.
        """

    def identity(self, row: Mapping[str, Any]) -> Hashable:
        """
        Deduplication key for a stored row, derived from `row["payload"]`.

        Must include `row["rule_id"]`: the same proposal against two rules is
        two records, not one.
        """

    def readjudicate(self, row: Mapping[str, Any]) -> Verdict:
        """
        Re-run the adjudicator over a stored row and return a fresh verdict.

        Must be a pure function of the row and the current verifier. It must
        not read the row's existing status: a verdict that can see its own
        predecessor is not an independent re-adjudication.
        """


@dataclass(frozen=True)
class Transport:
    """Which endpoint a campaign talks to. Provider-agnostic by construction."""

    model: str | None = None
    base_url: str | None = None
    preset: str | None = None
    retries: int = 8

    def as_kwargs(self) -> dict[str, Any]:
        return {"model": self.model, "base_url": self.base_url,
                "preset": self.preset, "retries": self.retries}


@runtime_checkable
class Generative(Protocol):
    """
    A `Domain` that can also source candidates from a model.

    Adjudication and generation are deliberately separate protocols. A domain
    is useful with only the first half - the seed banks run offline - and the
    campaign runner needs the second only when `--api` is passed.

    `propose` owns its own transport call because the shape of a request is
    domain business: the polytope laws ask for expression pairs on V.14 and
    single expressions elsewhere, while a code-property domain asks for input
    literals. What every domain returns is the same: ledger rows, already
    adjudicated, plus the backend descriptor to stamp into the corpus.
    """

    def propose(
        self,
        rule_id: str,
        n: int,
        transport: Transport,
        *,
        focus: str = "",
    ) -> tuple[list[dict[str, Any]], str]:
        """Request `n` candidates, adjudicate them, return (rows, backend)."""

    def focus_for(self, row: Mapping[str, Any]) -> str:
        """Prompt fragment asking for mutations of one live counterexample."""


@runtime_checkable
class Screenable(Protocol):
    """
    A `Domain` that can say what a candidate would be evidence for.

    Optional, and separate from `Generative` for the same reason `Generative` is
    separate from `Domain`: a domain is useful without it, and the campaign only
    needs it when it is choosing what to ask for. A domain that does not
    implement this is screened as `CONFIRMING` by default - which is honest,
    since without a domain-specific test there is no ground to claim a candidate
    distinguishes anything.

    The contract has one hard rule, and it is the same one the ledger has:
    screening may reorder and it may steer, but it may never cause a received
    proposal to go unrecorded. A corpus that drops what it screened badly has a
    denominator that means nothing.
    """

    def screen(self, rule_id: str, *payload: str) -> "Screening":
        """Weigh one candidate without adjudicating it into the corpus."""

    def screen_row(self, row: Mapping[str, Any]) -> "Screening":
        """
        Weigh a row already adjudicated, from what the adjudicator recorded.

        Separate from `screen` because the costs differ by orders of magnitude.
        `screen` measures; this reads. A campaign runner screens every batch it
        receives and every row it already holds, so it needs the cheap one.
        """

    def focus_for_gap(self, rule_id: str) -> str:
        """
        Prompt fragment describing the candidates the corpus still lacks.

        This is where screening pays for itself. Filtering a batch after the
        fact throws away tokens already spent; describing the shape that would
        be decisive spends the next batch better.
        """
