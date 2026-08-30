"""
The set of domains a campaign can run.

Adding a domain to a multi-domain campaign is one entry here plus a class that
satisfies `Domain` (and `Generative`, if it should accept model proposals).
Nothing else in the runner changes.

Each domain keeps its own corpus, report, and raw API log, because a corpus is
tied to a verifier version and those move independently. The *rate* budget is
deliberately not per-domain: one API key means one quota, so the campaign
shares a single rate-state file across every domain it drives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .domain import Domain

#: Shared across every domain in a campaign: one key, one quota.
RATE_STATE = "experiments/campaign_api_rate_state.json"


@dataclass(frozen=True)
class DomainSpec:
    """A registered domain and where its artifacts live, relative to the repo root."""

    name: str
    factory: Callable[..., Domain]
    corpus: str
    report: str
    raw_log: str
    summary: str

    def paths(self, root: Path) -> dict[str, Path]:
        return {
            "corpus": root / self.corpus,
            "report": root / self.report,
            "raw_log": root / self.raw_log,
        }


def _polytope(**kwargs) -> Domain:
    from .polytope import PolytopeDomain

    kwargs.pop("timeout", None)  # not a knob for an arithmetic adjudicator
    return PolytopeDomain(**kwargs)


def _codeprops(**kwargs) -> Domain:
    from .codeprops import CodePropertyDomain

    return CodePropertyDomain(**kwargs)


def _polyhedra(**kwargs) -> Domain:
    from .polyhedra import PolyhedronDomain

    return PolyhedronDomain(**kwargs)


REGISTRY: dict[str, DomainSpec] = {
    "polytope": DomainSpec(
        name="polytope",
        factory=_polytope,
        corpus="experiments/verification_campaign.json",
        report="docs/VERIFICATION_CERTIFICATE.md",
        raw_log="experiments/verification_api_raw.jsonl",
        summary="V.7-V.14 vertex-localization laws; adjudicator is stdlib arithmetic",
    ),
    "codeprops": DomainSpec(
        name="codeprops",
        factory=_codeprops,
        corpus="experiments/code_properties.json",
        report="docs/CODE_PROPERTIES.md",
        raw_log="experiments/code_properties_api_raw.jsonl",
        summary="reference-implementation property violation; adjudicator is CPython",
    ),
    "polyhedra": DomainSpec(
        name="polyhedra",
        factory=_polyhedra,
        corpus="experiments/polyhedra.json",
        report="docs/POLYHEDRA.md",
        raw_log="experiments/polyhedra_api_raw.jsonl",
        summary=("exponent laws on a general polytope, measured in edge vs ambient "
                 "coordinates; adjudicator is stdlib arithmetic"),
    ),
}

DOMAIN_NAMES: tuple[str, ...] = tuple(REGISTRY)


def resolve(names: list[str] | None) -> list[DomainSpec]:
    """Registered specs for the requested names, or every domain by default."""
    if not names:
        return [REGISTRY[name] for name in DOMAIN_NAMES]
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise KeyError(f"unknown domain(s): {unknown}; known: {list(DOMAIN_NAMES)}")
    return [REGISTRY[n] for n in names]
