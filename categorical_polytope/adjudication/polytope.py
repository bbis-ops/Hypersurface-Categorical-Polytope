"""
Domain one: the V.7-V.14 vertex-localization laws.

This is a thin adapter. All adjudication logic still lives in
`verification_campaign.verify_base` / `verify_combined` / `verify_interaction`;
this module only tells the ledger how to read a stored row, how to identify it,
and which rules a verifier bump invalidates.

The adjudicator here is arithmetic: a candidate is compiled through the AST
whitelist and measured with stdlib math. No model decides any verdict. That is
the property a second domain has to preserve.
"""

from __future__ import annotations

from typing import Any, Hashable, Mapping, Sequence

from ..base_search import Candidate
from ..verification_campaign import (
    VerificationRecord,
    verify_base,
    verify_combined,
    verify_interaction,
)
from .domain import Transport, Verdict

#: Bumped whenever adjudicator semantics change.
VERIFIER_VERSION = 17

#: Laws whose adjudicator semantics changed at each version. This prevents a
#: theorem-local repair from needlessly recomputing the entire multi-law corpus.
#: A law omitted here keeps its old verdict across that bump, so err wide.
REVERIFY_LAWS_BY_VERSION: dict[int, set[str]] = {
    6: {"V.14"},
    7: {"V.14"},
    8: {"V.14"},
    9: {"V.9"},
    10: {"V.10", "V.12"},
    11: {"V.10", "V.12", "V.13", "V.14"},
    12: {"V.14"},
    13: {"V.10"},
    14: {"V.10"},
    15: {"V.10"},
    # v16 split scope from verdict. A candidate admitted into the V.8/V.10
    # slice whose gap will not resolve is now `inconclusive` rather than
    # `outside_scope`: scope was already settled on evidence that did not
    # include that measurement, so the failure is the verifier's, not the
    # theorem's. V.9's underflowing polar gap stops being reported as a
    # directional-law mismatch for the same reason.
    16: {"V.8", "V.9", "V.10"},
    # v17 gave V.14 the relative exponent tolerance its sibling laws
    # already used, and routed an unresolved weighted gap to
    # inconclusive instead of counterexample.
    17: {"V.14"},
}

LAWS: tuple[str, ...] = tuple(f"V.{i}" for i in range(7, 15))

#: Per-law proposal prompts. These generate candidates only; nothing a model
#: returns is trusted, and no verdict depends on which model produced it.
PROMPTS: dict[str, str] = {
    "V.7": """Generate {n} distinct perturbations P(lam,sigma,b,k) designed to falsify the V.7 quadratic gap law. Fixed base is -(1-lam)^2-sigma^2 at corner (1,0). Stay IN SCOPE: P must have finite positive inward slope, be locally degree one, and be separable over x=1-lam and y=sigma. Add large smooth higher-order distractions to stress the asymptotic screen. Use lam/sigma, not x/y. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"attack"}}]}}""",
    "V.8": """Generate {n} distinct perturbations designed to falsify V.8: a homogeneous inward term of degree 0<alpha<1 has gap exponent 2/(2-alpha). Choose EXACTLY ONE alpha per expression from 0.15,0.25,0.33,0.5,0.75,0.9. Use sigma**alpha, (1-lam)**alpha, or both with the SAME alpha. Never mix degrees and never add linear/lower-degree terms. Higher-order distractions may have degree >=2 only. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state alpha and attempted failure"}}]}}""",
    "V.9": """Generate {n} distinct degree-one positively homogeneous COUPLED perturbations around (lam,sigma)=(1,0) to break V.9. Every expression must be a nonseparable norm or crease, patterned on sqrt(a*(1-lam)**2+b*sigma**2) or abs(a*(1-lam)-b*sigma), with positive numeric a,b. No linear sums, products of degree 2, b/k variables, smooth distractions, gates, or saturation. Allowed + - * / ** sqrt abs; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"identify coupled ray geometry"}}]}}""",
    "V.10": """Generate {n} distinct perturbations designed to falsify V.10 for 1<alpha<2. Choose EXACTLY ONE alpha per expression from 1.1,1.2,1.35,1.5,1.65,1.8,1.9. Use sigma**alpha, (1-lam)**alpha, or both with the SAME alpha. Never mix degrees and never add constants, linear, or lower-degree terms. Distractions may have degree >=2 only and must be bounded. Allowed + - * / ** sin cos exp log abs tanh atan; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state alpha and attempted failure"}}]}}""",
    "V.11": """Generate {n} bounded finite perturbations P designed to violate the V.11 amplitude ceiling. Require P(1,0,2,3)=0 and a positive inward push. Use tanh, atan, sin, exp narrow gates, angular ridges with positive numeric denominator floors, and coupled bounded peaks. Never use tan, variable denominators without a positive floor, or unbounded singularities. Allowed + - * / ** sin cos exp sqrt abs tanh atan; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"P","why":"state bounded range and attack"}}]}}""",
    "V.12": """Generate {n} base objectives r(lam,sigma) designed to falsify V.12. Stay in scope: global maximum at corner (1,0), flat there with leading order beta>1, then a linear inward perturbation should yield exponent beta/(beta-1). Vary beta 2.2 through 10, odd, anisotropic, mixed leading orders, and smooth distractions. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"r","why":"attack"}}]}}""",
    "V.13": """Generate {n} base objectives r(lam,sigma) whose true maximum is interior, on an edge, or in a very thin off-corner spike. Attack the current deterministic guard: coprime grids of sizes 10,11,13,17,33 plus 4096 Halton points; seek narrow, aliased, oblique, or boundary maxima it misses. Make each finite on [0,1]^2. Allowed + - * / ** sin cos tan exp log sqrt abs tanh atan sinh cosh pi; numeric exponents only. JSON only: {{"candidates":[{{"name":"slug","expr":"r","why":"attack"}}]}}""",
}

COMPACT_RULE = "\nCritical syntax rule: every expr must be at most 150 characters and contain only the expression. The only variable identifiers allowed are lam, sigma, b, k. Write (1-lam) literally; never use shorthand x, y, r, atan2, or assignment prefixes such as P(...)= and r(...)=. Exponentiation is ** and never ^; a caret is rejected. Keep every why to at most 10 words. Output the JSON object and nothing else: no preamble, no plan, no commentary."

#: Laws adjudicated as a base objective rather than a perturbation.
BASE_LAWS: frozenset[str] = frozenset({"V.12", "V.13"})

#: The one law whose candidate is a (base, perturbation) pair.
PAIR_LAW = "V.14"


class PolytopeDomain:
    """Adapts the V.7-V.14 adjudicators to the `Domain` protocol."""

    name = "polytope-laws"

    def __init__(self, verifier_version: int = VERIFIER_VERSION):
        self.verifier_version = int(verifier_version)

    @property
    def rule_ids(self) -> Sequence[str]:
        return LAWS

    def rules_invalidated_between(self, prior: int, current: int) -> set[str]:
        if prior == current:
            return set()
        affected: set[str] = set()
        for version in range(prior + 1, current + 1):
            affected |= REVERIFY_LAWS_BY_VERSION.get(version, set())
        return affected

    #: This domain's payload is a perturbation expression plus, for V.14, the
    #: base objective it is paired with.
    def identity(self, row: Mapping[str, Any]) -> Hashable:
        # Includes the rule: the same expression against two laws is two records.
        payload = row["payload"]
        return (row["rule_id"], payload.get("base_expr", "") or "", payload["expr"])

    def readjudicate(self, row: Mapping[str, Any]) -> Verdict:
        """Re-run the adjudicator over a stored row. Never reads its status."""
        return self.to_verdict(self._adjudicate_row(row))

    # -- adjudication ------------------------------------------------------

    def _adjudicate_row(self, row: Mapping[str, Any]) -> VerificationRecord:
        law = str(row["rule_id"])
        payload = row["payload"]
        name = row.get("name", "")
        note = row.get("note", "")
        if law == PAIR_LAW:
            return verify_combined(
                Candidate(f"{name}_b", payload.get("base_expr", ""), "model", note),
                Candidate(f"{name}_p", payload["expr"], "model", note),
            )
        candidate = Candidate(name, payload["expr"], "model", note)
        if law in BASE_LAWS:
            return verify_base(law, candidate)
        return verify_interaction(law, candidate)

    def adjudicate(self, rule_id: str, candidate: Candidate) -> VerificationRecord:
        """Adjudicate a fresh candidate. Returns the domain's native record."""
        if rule_id in BASE_LAWS:
            return verify_base(rule_id, candidate)
        return verify_interaction(rule_id, candidate)

    def adjudicate_pair(self, base: Candidate, perturbation: Candidate) -> VerificationRecord:
        return verify_combined(base, perturbation)

    # -- proposal generation -----------------------------------------------

    def proposal_prompt(self, rule_id: str, n: int, focus: str = "") -> str:
        """
        Prompt for candidate generation. V.14 proposes pairs through
        `base_search.propose_pairs` and has no single-expression prompt.
        """
        if rule_id not in PROMPTS:
            raise KeyError(f"no single-expression prompt for {rule_id}")
        return PROMPTS[rule_id].format(n=n) + focus + COMPACT_RULE

    @staticmethod
    def to_verdict(record: VerificationRecord) -> Verdict:
        return Verdict(
            status=record.status,
            reason=record.reason,
            metrics=record.metrics or {},
        )

    @staticmethod
    def to_row(record: VerificationRecord) -> dict[str, Any]:
        """Map this domain's native record onto the generic ledger envelope."""
        return {
            "rule_id": record.law,
            "name": record.name,
            "payload": {"expr": record.expr, "base_expr": record.base_expr},
            "status": record.status,
            "reason": record.reason,
            "metrics": record.metrics or {},
            "note": record.note,
        }

    @staticmethod
    def migrate_row(row: Mapping[str, Any]) -> dict[str, Any]:
        """
        Lift one schema-v1 record into the v2 envelope.

        Used only by `experiments/migrate_corpus_schema.py`. Adjudication fields
        (status, reason, metrics) and the full reversal history carry across
        untouched: this moves fields, it never re-decides anything.
        """
        migrated = {
            "rule_id": row["law"],
            "name": row["name"],
            "payload": {"expr": row["expr"], "base_expr": row.get("base_expr", "")},
            "status": row["status"],
            "reason": row.get("reason", ""),
            "metrics": row.get("metrics") or {},
            "note": row.get("note", ""),
        }
        for carried in ("adjudication_history", "initial_status"):
            if carried in row:
                migrated[carried] = row[carried]
        return migrated

    # -- generation (the `Generative` half of the protocol) -----------------

    def propose(
        self,
        rule_id: str,
        n: int,
        transport: "Transport",
        *,
        focus: str = "",
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Request candidates for one law and adjudicate them.

        V.14 is proposed as (base, perturbation) pairs through its own prompt
        and parser; every other law is a single expression. Both paths return
        the same generic rows, so the campaign runner never learns the
        difference.
        """
        from ..base_search import propose_pairs
        from ..interaction_search import propose_candidates

        kwargs = transport.as_kwargs()
        if rule_id == PAIR_LAW:
            retries = kwargs.pop("retries", None)
            proposed, backend = propose_pairs(n, focus=focus, **kwargs)
            records = [self.adjudicate_pair(base, pert) for base, pert in proposed]
        else:
            proposed, backend = propose_candidates(
                n, prompt=self.proposal_prompt(rule_id, n, focus), **kwargs
            )
            records = [self.adjudicate(rule_id, cand) for cand in proposed]
        return [self.to_row(record) for record in records], backend

    def focus_for(self, row: Mapping[str, Any]) -> str:
        """Ask for mutations of a live numerical survivor."""
        payload = row["payload"]
        if str(row["rule_id"]) == PAIR_LAW:
            return (
                f"\nA current numerical survivor uses base {payload['base_expr']} and "
                f"perturbation {payload['expr']}. Generate weighted-homogeneous, "
                "coefficient, cancellation, and scale variants that preserve the "
                "corrected theorem hypotheses and try to reproduce its mismatch."
            )
        return (
            f"\nA current numerical survivor is {payload['expr']}. Generate "
            "coefficient, scale, and functional variants that preserve the theorem "
            "hypotheses and try to reproduce its mismatch."
        )
