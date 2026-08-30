"""
What a candidate would be evidence FOR, decided before spending on it.

The ledger answers "did this candidate pass". Screening answers the question
that comes first and is nowhere recorded: *would passing have meant anything*.
Those are different, and conflating them is how a corpus grows without its
evidence growing.

Domain three is the worked example. Of its 286 rows, 97 are out of scope and 15
never parsed; among the rest almost every row has admissible faces that all
agree about the weighted degree. Such a row exercises the transport and the
admissibility filter, and it would have looked identical under a minimum rule, a
maximum rule, or "pick any". The rows that separate those rules, inside the
theorem's own hypotheses, number **0**. No amount of further corpus growth
changes that number; only the right candidate does.

The vocabulary here is deliberately domain-independent, because the situation is
not special to polyhedra. Every rule has rivals it ought to be distinguished
from, every domain admits candidates that cannot distinguish them, and every
campaign spends the same budget on both.

    DECISIVE    would separate the rule from a rival that also gives a definite
                answer. The scarce kind.
    SELECTIVE   would separate it from a rival that merely fails or diverges -
                weaker, since any rule at all survives that.
    CONFIRMING  in scope and fully licensed, but consistent with the rivals too.
    UNLICENSED  would be adjudicated, but a hypothesis of the rule is unmet, so
                a pass would license nothing.
    REFUSED     scope would decline it, with the reason.

Screening ranks and steers; it must not drop. A domain that discarded the
proposals it screened badly would have a denominator that quietly excludes
whatever was hard to fit, and that is not a denominator. What screening changes
is which candidates are *asked for* - see `Screenable.focus_for_gap`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

DECISIVE, SELECTIVE, CONFIRMING, UNLICENSED, REFUSED = (
    "decisive", "selective", "confirming", "unlicensed", "refused")

#: Most evidentially valuable first. `rank` sorts by this order.
VALUE_ORDER: tuple[str, ...] = (
    DECISIVE, SELECTIVE, CONFIRMING, UNLICENSED, REFUSED)


@dataclass(frozen=True)
class Layer:
    """
    One stage of a domain's own screen, and whether the candidate clears it.

    Domain three names its three after the law's structure - localization,
    selection, scaling. Another domain will have different ones. What the
    ledger and the campaign need is only the pass and the sentence saying why,
    so that a rejected candidate can be reported rather than merely dropped.
    """

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Screening:
    """One candidate, weighed before adjudication."""

    domain: str
    rule_id: str
    payload: tuple[str, ...]
    value: str
    reason: str
    layers: tuple[Layer, ...] = ()
    #: Within-class tie-break, larger is better. A domain sets whatever
    #: quantity makes one candidate of a class sharper than another.
    margin: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.value not in VALUE_ORDER:
            raise ValueError(f"unknown screening value: {self.value!r}")

    @property
    def rank_key(self) -> tuple[int, float]:
        return (VALUE_ORDER.index(self.value), -self.margin)

    @property
    def informative(self) -> bool:
        """Would this candidate distinguish the rule from a rival at all?"""
        return self.value in (DECISIVE, SELECTIVE)

    def line(self) -> str:
        return f"{self.value:<11} {self.reason}"


def rank(screenings: Iterable[Screening]) -> list[Screening]:
    """Order a batch, most evidentially valuable first."""
    return sorted(screenings, key=lambda s: s.rank_key)


def tally(screenings: Sequence[Screening]) -> dict[str, int]:
    """How a batch broke down, keyed in `VALUE_ORDER`."""
    counts = {name: 0 for name in VALUE_ORDER}
    for screening in screenings:
        counts[screening.value] += 1
    return counts


def summarise(screenings: Sequence[Screening]) -> str:
    """One line: the mix, and how much of it was worth anything."""
    counts = tally(screenings)
    total = len(screenings)
    useful = sum(1 for s in screenings if s.informative)
    mix = "  ".join(f"{name}={counts[name]}" for name in VALUE_ORDER if counts[name])
    share = (100.0 * useful / total) if total else 0.0
    return f"{total} screened  {mix}  ({share:.0f}% distinguish the rule)"
