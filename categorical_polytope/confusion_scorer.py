"""
Layer-2 confusion scorer: adjudicate learner text against the concept lattice.

Replaces the turn-index ramp in `category_tutor` with a signal derived from
what the learner actually says. Each utterance is matched against a ledger of
propositions whose truth value is decided locally by an existing module, and
the learner's *stance* (assert / deny / question) is extracted with a negation
window. Two orthogonal numbers come out:

  coupling  -> feeds `LearnerDiagramState.interaction_strength` (the geometry)
  error     -> accuracy against ground truth, reported as a diagnostic

These are deliberately not the same construct. `interaction_strength` is how
entangled the learner's diagram is, not how wrong they are: a learner who
correctly perceives that cross-naturality couples their blocks has *high*
coupling and *zero* error. The scripted ramp conflates the two; this does not.

Standard library only. Model text is untrusted data: nothing here executes it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Sequence


class Stance(Enum):
    """The position an utterance takes on a proposition."""

    ABSENT = auto()
    QUESTION = auto()
    ASSERT = auto()
    DENY = auto()


# Tokens that flip an assertion within the clause. Alongside plain negation
# these include the vocabulary this codebase uses for absence: calling the
# coexponential a "shadow", or naming the cardinality "obstruction", asserts
# that it is not there.
NEGATORS: tuple[str, ...] = (
    "not", "no", "never", "isn't", "aren't", "cannot", "can't", "doesn't",
    "don't", "won't", "fails", "fail", "failed", "failing", "wrong",
    "undefined", "empty", "missing", "absent", "lacks", "without", "nowhere",
    "neither", "shadow", "obstruction", "degenerate",
)

# Interrogative openers; a trailing '?' also marks a question.
INTERROGATIVES: tuple[str, ...] = (
    "where", "what", "why", "how", "should", "is there", "are there",
    "does", "do i", "can i",
)

# Clause boundaries. Negation is scoped to the clause it appears in, so that
# "...is interior on the face, not a corner" denies the corner and leaves the
# interior claim standing. A hyphen only splits when spaced, keeping
# "cross-naturality" and "lambda-sigma" intact.
CLAUSE_SPLIT = re.compile(r"[,;.!?]|\s[—–]\s|\s--?\s")


@dataclass(frozen=True)
class Proposition:
    """A claim about the concept lattice, decidable by a local witness."""

    key: str
    topic: str
    claim: str
    truth: bool | None  # None = context-dependent (holds only at low coupling)
    patterns: tuple[str, ...]
    coupling_assert: float
    coupling_deny: float
    witness: str


# Ground truth is what the stdlib modules already decide. `truth=None` marks a
# claim that is true only in the low-coupling regime, so neither stance is an
# error on its own.
LEDGER: tuple[Proposition, ...] = (
    Proposition(
        key="ccc_curry",
        topic="product_exp_corner",
        claim="Hom(A x X, Y) ~= Hom(X, Y^A)",
        truth=True,
        patterns=(r"\bcurry\b", r"\bproduct\b", r"exponential object", r"\bccc\b"),
        coupling_assert=0.0,
        coupling_deny=0.25,
        witness="cartesian_closed.py",
    ),
    Proposition(
        key="coproduct_disjoint",
        topic="coproduct_blocks",
        claim="coproduct is disjoint union in Set",
        truth=True,
        patterns=(r"\bcoproduct\b", r"disjoint union"),
        coupling_assert=0.05,
        coupling_deny=0.30,
        witness="set_category.py",
    ),
    Proposition(
        key="coexp_exists",
        topic="coexp_empty",
        claim="a coexponential left adjoint to coproduct exists in Set",
        truth=False,
        patterns=(r"coexponential", r"co-exponential", r"\bcoexp\b", r"co-curry"),
        coupling_assert=0.50,
        coupling_deny=0.20,
        witness="set_category.py (cardinality obstruction)",
    ),
    Proposition(
        key="cross_natural_couples",
        topic="cross_natural",
        claim="cross-naturality couples the blocks",
        truth=True,
        patterns=(r"cross.?natural", r"\bcoupl\w*", r"mix\w*\s+(my\s+)?blocks"),
        coupling_assert=0.60,
        coupling_deny=-0.10,
        witness="decomposition_stability.py",
    ),
    Proposition(
        key="blocks_factor",
        topic="coproduct_blocks",
        claim="coproduct blocks factor separably",
        truth=True,
        patterns=(
            r"blocks?\s+factor",
            r"\bseparable\b",
            r"factor\w*\s+cleanly",
            r"independent\s+(blocks?|structure)",
        ),
        coupling_assert=-0.25,
        coupling_deny=0.45,
        witness="decomposition_stability.py",
    ),
    Proposition(
        key="max_at_corner",
        topic="naturality_swap",
        claim="the maximum sits at a vertex of the box",
        truth=None,
        patterns=(r"\bcorners?\b", r"\bvert(ex|ices)\b", r"extreme point"),
        coupling_assert=-0.30,
        coupling_deny=0.55,
        witness="hypersurface_box.py",
    ),
    Proposition(
        key="arrow_reversal",
        topic="review_adjunction",
        claim="reversing arrows guarantees a representable dual",
        truth=False,
        patterns=(r"revers\w*\s+(the\s+)?arrows?", r"arrows?\s+revers\w*"),
        coupling_assert=0.30,
        coupling_deny=0.05,
        witness="neighboring_vertices.py (strategy, not guarantee)",
    ),
    Proposition(
        key="interior_search",
        topic="face_bowl",
        claim="the search must leave the corners for the face interior",
        truth=None,
        patterns=(r"\binterior\b", r"inside the face", r"search the face"),
        coupling_assert=0.70,
        coupling_deny=-0.20,
        witness="learner_diagram.recommend_search_mode",
    ),
)

LEDGER_BY_KEY: dict[str, Proposition] = {p.key: p for p in LEDGER}


@dataclass(frozen=True)
class Engagement:
    """One proposition the utterance took a position on."""

    key: str
    stance: str
    erroneous: bool
    coupling: float


@dataclass(frozen=True)
class TurnScore:
    """Layer-2 readout for a single utterance."""

    text: str
    raw_coupling: float
    smoothed_coupling: float
    commitment: float
    accuracy: float
    engagements: tuple[Engagement, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_coupling": self.raw_coupling,
            "smoothed_coupling": self.smoothed_coupling,
            "commitment": self.commitment,
            "accuracy": self.accuracy,
            "engagements": [
                {"key": e.key, "stance": e.stance, "erroneous": e.erroneous}
                for e in self.engagements
            ],
        }


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _is_question(text: str) -> bool:
    low = text.strip().lower()
    if low.endswith("?"):
        return True
    return any(low.startswith(w) for w in INTERROGATIVES)


def _clause_spans(low: str) -> list[tuple[int, int]]:
    """Half-open (start, end) character spans of the utterance's clauses."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in CLAUSE_SPLIT.finditer(low):
        if m.start() > start:
            spans.append((start, m.start()))
        start = m.end()
    if start < len(low):
        spans.append((start, len(low)))
    return spans or [(0, len(low))]


def _negator_positions(low: str) -> list[int]:
    return [
        m.start()
        for m in re.finditer(r"[a-z']+", low)
        if m.group(0) in NEGATORS
    ]


def analyze(text: str) -> dict[str, Stance]:
    """
    Stance for every proposition in one pass over the utterance.

    Propositions are resolved together because negation scope depends on what
    else is in the sentence. Each negator attaches to the *nearest* proposition
    in its own clause, so "Coexp shadow + Fisher epsilon + interior search"
    denies the coexponential without denying the interior search. A negator in
    a clause naming no proposition falls back to the nearest one in the clause
    before it, so "Coexponential in Set? I can't find one" reads as a denial
    rather than a false presupposition.
    """
    low = text.lower()
    spans = _clause_spans(low)

    hits: dict[str, int] = {}
    for prop in LEDGER:
        for pat in prop.patterns:
            m = re.search(pat, low)
            if m:
                hits[prop.key] = m.start()
                break
    if not hits:
        return {}

    def clause_of(pos: int) -> int:
        for i, (lo, hi) in enumerate(spans):
            if lo <= pos < hi:
                return i
        return len(spans) - 1

    by_clause: dict[int, list[str]] = {}
    for key, pos in hits.items():
        by_clause.setdefault(clause_of(pos), []).append(key)

    negated: set[str] = set()
    for npos in _negator_positions(low):
        ci = clause_of(npos)
        candidates = by_clause.get(ci) or by_clause.get(ci - 1) or []
        if candidates:
            negated.add(min(candidates, key=lambda k: abs(hits[k] - npos)))

    question = _is_question(text)
    stances: dict[str, Stance] = {}
    for key in hits:
        if key in negated:
            stances[key] = Stance.DENY
        elif question:
            stances[key] = Stance.QUESTION
        else:
            stances[key] = Stance.ASSERT
    return stances


def detect_stance(text: str, prop: Proposition) -> Stance:
    """Match `prop` in `text` and read off assert / deny / question."""
    return analyze(text).get(prop.key, Stance.ABSENT)


def _erroneous(prop: Proposition, stance: Stance) -> bool:
    """A stance is an error only when the ledger fixes a truth value."""
    if prop.truth is None:
        return False
    if stance is Stance.ASSERT:
        return not prop.truth
    if stance is Stance.DENY:
        return prop.truth
    if stance is Stance.QUESTION:
        # A question presupposing a false claim ("where is the coexponential?")
        # is a misconception, not mere uncertainty.
        return not prop.truth
    return False


# A question is partial engagement: the learner is entertaining the claim
# without committing to it.
QUESTION_DAMPING = 0.5
# A misconception entangles the diagram beyond the stance's own weight.
ERROR_BUMP = 0.10


def score_text(text: str) -> tuple[float, float, float, tuple[Engagement, ...]]:
    """Raw coupling, commitment, accuracy, and per-proposition engagements."""
    engagements: list[Engagement] = []
    raw = 0.0
    committed = 0
    errors = 0
    stances = analyze(text)
    for prop in LEDGER:
        stance = stances.get(prop.key, Stance.ABSENT)
        if stance is Stance.ABSENT:
            continue
        if stance is Stance.ASSERT:
            weight = prop.coupling_assert
        elif stance is Stance.DENY:
            weight = prop.coupling_deny
        else:
            weight = prop.coupling_assert * QUESTION_DAMPING
        bad = _erroneous(prop, stance)
        if bad:
            damp = QUESTION_DAMPING if stance is Stance.QUESTION else 1.0
            weight += ERROR_BUMP * damp
            errors += 1
        if stance in (Stance.ASSERT, Stance.DENY):
            committed += 1
        raw += weight
        engagements.append(
            Engagement(
                key=prop.key,
                stance=stance.name,
                erroneous=bad,
                coupling=weight,
            )
        )

    n = len(engagements)
    commitment = committed / n if n else 0.0
    accuracy = 1.0 - (errors / n) if n else 1.0
    return max(0.0, raw), commitment, accuracy, tuple(engagements)


@dataclass
class ConfusionScorer:
    """
    Stateful Layer-2 scorer: `(utterance, log) -> interaction_strength`.

    Coupling is a property of the learner's diagram, not of a single sentence,
    so per-turn evidence is folded into an exponential moving average. `alpha`
    and `base` are the only calibrated constants; they are fit once against the
    scripted dialogue reference and frozen (see tests/test_confusion_scorer.py).
    """

    alpha: float = 0.15
    base: float = 0.05
    ceiling: float = 0.95
    history: list[TurnScore] = field(default_factory=list)
    _state: float = field(default=-1.0, repr=False)

    def reset(self) -> None:
        self.history.clear()
        self._state = -1.0

    def __call__(self, text: str, log: Any = None) -> float:
        raw, commitment, accuracy, engagements = score_text(text)
        prev = self.base if self._state < 0.0 else self._state
        smoothed = (1.0 - self.alpha) * prev + self.alpha * raw
        smoothed = min(self.ceiling, max(0.0, smoothed))
        self._state = smoothed
        self.history.append(
            TurnScore(
                text=text,
                raw_coupling=raw,
                smoothed_coupling=smoothed,
                commitment=commitment,
                accuracy=accuracy,
                engagements=engagements,
            )
        )
        return smoothed

    def summary(self) -> dict[str, Any]:
        if not self.history:
            return {"n_turns": 0}
        errs = [e for h in self.history for e in h.engagements if e.erroneous]
        n = len(self.history)
        return {
            "n_turns": n,
            "final_coupling": self.history[-1].smoothed_coupling,
            "mean_accuracy": sum(h.accuracy for h in self.history) / n,
            "mean_commitment": sum(h.commitment for h in self.history) / n,
            "misconceptions": sorted({e.key for e in errs}),
            "trajectory": [h.smoothed_coupling for h in self.history],
        }


def score_dialogue(utterances: Sequence[str], **kw: Any) -> ConfusionScorer:
    """Convenience: run a whole dialogue through a fresh scorer."""
    scorer = ConfusionScorer(**kw)
    for u in utterances:
        scorer(u)
    return scorer
