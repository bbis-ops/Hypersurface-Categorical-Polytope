"""
Candidate selection: what a proposal would be evidence for, before spending on it.

The ledger answers "did it pass". These pin the question that comes first and is
nowhere else recorded - would passing have meant anything - and the one rule the
mechanism must never break: screening may reorder and steer, never drop.
"""

from __future__ import annotations

import pytest

from categorical_polytope.adjudication import (
    CONFIRMING,
    DECISIVE,
    REFUSED,
    SELECTIVE,
    UNLICENSED,
    VALUE_ORDER,
    Layer,
    Screenable,
    Screening,
    rank,
    summarise,
    tally,
)
from categorical_polytope.adjudication.domain import Transport
from categorical_polytope.adjudication.polyhedra import PolyhedronDomain
from categorical_polytope.adjudication.polyhedra.domain import (
    MEASURABLE_EXPONENT,
    exponent_tolerance,
    separates,
)
from categorical_polytope.adjudication.polyhedra.predict import RULE
from categorical_polytope.adjudication.polyhedra.screening import (
    DECISIVE_TARGETS,
    focus_for_gap,
    screen,
    screen_row,
)

#: Box vertex at the origin, orders (2, 4), push surviving on both edges: the
#: rays give q = 1/2 and q = 1/4, both below 1. The minimum rule says 4/3 and
#: the maximum rule says 2, so measurement chooses between two real numbers.
#: This is the shape the corpus has none of inside the hypotheses.
DECIDING = ("([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
            "-(x0**2 + x1**4)", "x0 + x1")

#: The note's own worked case. Both its faces read q = 1/4.
SIMPLEX = ("([[-1,0],[0,-1],[1,1]], [0,0,1])",
           "-((x0+x1-1)**2 + x0**4)", "x0")

#: Faces disagree, but the rival is at q = 1.38, where 1/(1-q) is negative.
DIVERGING = ("([[-1,-1,0],[0,-1,0],[0,0,-1],[1,2,1]], [0,0,0,1])",
             "-((x0 + x1)**2 + (x1)**4 + (x2)**6)", "x0")

#: A symmetric double well along x0: the box corners (0,0) and (1,0) are both
#: maxima worth zero, so the unperturbed maximiser is not unique and Lemma 1
#: fails. Every base order still resolves, which is what makes this UNLICENSED
#: rather than out of scope - the row is adjudicated, its agreement just
#: licenses nothing.
TIED = ("([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
        "-(x0**2*(x0-1)**2) - x1**2", "x0 + x1")

#: Different failure, worth keeping apart from the one above. Here a base term
#: of order 8 underflows the order probe and reads as order 0, so the law has
#: no input at all - v11 puts the row out of scope instead of adjudicating it
#: against a prediction that was never the law's.
UNREADABLE_ORDER = ("([[-1,0],[0,-1],[1,1]], [0,0,1])",
                    "-(x0**8 + x1**2)", "x0 + x1")

UNBOUNDED = ("([[-1,0],[0,-1]], [0,0])", "-(x0**2 + x1**2)", "x0")


# ---------------------------------------------------------- classification ---


def test_a_candidate_that_separates_minimum_from_maximum_is_decisive():
    out = screen(*DECIDING)
    assert out.value == DECISIVE
    assert out.informative
    assert all(layer.passed for layer in out.layers)


def test_the_notes_own_worked_case_only_confirms():
    """
    Worth pinning because it is counterintuitive. The tilted simplex is the
    example the whole note is built on, and it does not test the selection
    clause at all: both {0} and {0,1} read q = 1/4, so a maximum rule would
    have returned the same 4/3. It tests the transport and the admissibility
    filter, which is not nothing - but it is not selection.
    """
    out = screen(*SIMPLEX)
    assert out.value == CONFIRMING
    assert not out.informative
    layers = {layer.name: layer for layer in out.layers}
    assert layers["localization"].passed
    assert layers["scaling"].passed
    assert not layers["selection"].passed


def test_a_diverging_rival_is_only_selective():
    """
    Rejecting a divergence is something any rule survives, so a face at
    q >= 1 does not put the minimum rule at risk the way a finite rival does.
    """
    out = screen(*DIVERGING)
    assert out.value == SELECTIVE
    assert out.informative, "it still distinguishes something, just weakly"
    assert "diverges" in out.reason


def test_a_tied_maximiser_is_unlicensed_not_confirming():
    """In scope, adjudicated, and licensing nothing - a class of its own."""
    out = screen(*TIED)
    assert out.value == UNLICENSED
    assert "isolated maximiser" in out.reason
    assert not next(l for l in out.layers if l.name == "localization").passed
    assert next(l for l in out.layers if l.name == "scaling").passed


def test_an_unreadable_base_order_is_refused_not_merely_unlicensed():
    """
    v11. The distinction matters: `unlicensed` says the row was measured and
    the measurement licenses nothing, while this row could not be measured at
    all. Calling the second one unlicensed would put it in the denominator.
    """
    out = screen(*UNREADABLE_ORDER)
    assert out.value == REFUSED
    assert "did not resolve" in out.reason


def test_a_candidate_scope_would_decline_is_refused_with_the_reason():
    out = screen(*UNBOUNDED)
    assert out.value == REFUSED
    assert "unbounded" in out.reason


# ------------------------------------------------------------- ordering ---


def test_ranking_puts_the_scarce_kind_first():
    order = [s.value for s in rank(
        [screen(*case) for case in (UNBOUNDED, SIMPLEX, DECIDING, TIED, DIVERGING)])]
    assert order == [DECISIVE, SELECTIVE, CONFIRMING, UNLICENSED, REFUSED]


def test_within_a_class_a_wider_spread_ranks_higher():
    wide = Screening("d", "r", ("a",), DECISIVE, "wide", margin=0.4)
    narrow = Screening("d", "r", ("b",), DECISIVE, "narrow", margin=0.1)
    assert rank([narrow, wide]) == [wide, narrow]


def test_a_batch_reports_its_own_mix():
    screenings = [screen(*case) for case in (DECIDING, SIMPLEX, UNBOUNDED)]
    counts = tally(screenings)
    assert counts[DECISIVE] == 1 and counts[CONFIRMING] == 1 and counts[REFUSED] == 1
    assert sum(counts.values()) == 3
    line = summarise(screenings)
    assert "3 screened" in line and "33% distinguish" in line


def test_every_value_is_ordered_and_unknown_ones_are_refused():
    assert set(VALUE_ORDER) == {DECISIVE, SELECTIVE, CONFIRMING, UNLICENSED, REFUSED}
    with pytest.raises(ValueError):
        Screening("d", "r", (), "excellent", "not a class")


# --------------------------------------------------------------- contract ---


def test_the_domain_satisfies_the_screenable_protocol():
    assert isinstance(PolyhedronDomain(), Screenable)


def test_screening_through_the_domain_matches_the_module():
    domain = PolyhedronDomain()
    assert domain.screen(RULE, *DECIDING).value == screen(*DECIDING).value


def test_screening_never_touches_the_corpus():
    """
    The one hard rule. Screening orders and steers; if it could drop a received
    proposal the denominator would quietly exclude whatever was hard to fit.
    A screen is a pure function of the candidate and the local adjudicator.
    """
    domain = PolyhedronDomain()
    first = domain.screen(RULE, *DECIDING)
    second = domain.screen(RULE, *DECIDING)
    assert first.value == second.value and first.margin == second.margin
    assert first.payload == DECIDING


def test_the_gap_prompt_asks_for_what_the_corpus_lacks():
    text = focus_for_gap(RULE)
    for expected in ("UNIQUE", "below 1", "strictly above 1", "tilted"):
        assert expected in text, expected


def test_the_gap_prompt_is_empty_for_a_rule_it_does_not_describe():
    assert focus_for_gap("polyhedron/linear_max_at_vertex") == ""


def test_a_layer_carries_its_reason_either_way():
    out = screen(*TIED)
    assert all(isinstance(layer, Layer) and layer.detail for layer in out.layers)


# ------------------------------------------------- the cheap path agrees ---


def test_screening_a_stored_row_matches_screening_the_candidate():
    """
    The equivalence the campaign relies on.

    `screen` measures; `screen_row` reads what the adjudicator already
    recorded. The runner uses the cheap one on every batch it receives, so if
    the two could disagree the reported mix would be fiction.
    """
    domain = PolyhedronDomain()
    for system, base, pert in (DECIDING, SIMPLEX, DIVERGING, TIED, UNBOUNDED):
        row = domain.to_row(RULE, "case", system, base, pert)
        measured, read = screen(system, base, pert), screen_row(row)
        assert read.value == measured.value, (system, base, pert)
        assert read.margin == pytest.approx(measured.margin, abs=1e-9)


def test_a_rule_without_a_screen_confirms_rather_than_claiming_more():
    domain = PolyhedronDomain()
    row = domain.to_row("polyhedron/linear_max_at_vertex", "control",
                        "([[1,0],[-1,0],[0,1],[0,-1]], [1,0,1,0])", "x0", "0")
    out = screen_row(row)
    assert out.value == CONFIRMING
    assert "no domain-specific screen" in out.reason


# ------------------------------------------------------ wiring to propose ---


class _Recorder:
    """Stands in for the model call, capturing the prompt it was handed."""

    def __init__(self, proposals):
        self.proposals, self.prompt = proposals, None

    def __call__(self, n, *, prompt, parser, **kwargs):
        self.prompt = prompt
        return list(self.proposals), "stub-backend"


def _patch_proposer(monkeypatch, proposals):
    import categorical_polytope.interaction_search as search

    recorder = _Recorder(proposals)
    monkeypatch.setattr(search, "propose_candidates", recorder)
    return recorder


def test_propose_steers_the_request_by_default(monkeypatch):
    recorder = _patch_proposer(monkeypatch, [])
    PolyhedronDomain().propose(RULE, 3, Transport())
    assert "decisive" in recorder.prompt
    assert "MORE THAN 0.3" in recorder.prompt, "the exponent-separation spec"


def test_propose_can_be_told_to_ask_blind(monkeypatch):
    recorder = _patch_proposer(monkeypatch, [])
    PolyhedronDomain().propose(RULE, 3, Transport(), steer=False)
    assert "decisive" not in recorder.prompt


def test_steering_is_appended_to_a_counterexample_focus_not_instead_of_it(monkeypatch):
    recorder = _patch_proposer(monkeypatch, [])
    PolyhedronDomain().propose(RULE, 3, Transport(), focus="\n\nMARKER")
    assert "MARKER" in recorder.prompt and "decisive" in recorder.prompt


def test_every_proposal_is_admitted_however_badly_it_screens(monkeypatch):
    """
    The integrity rule. Steering changes what is asked for, never what is kept:
    a corpus that dropped whatever failed to match the ask would have a
    denominator that means nothing.
    """
    proposals = [
        {"name": "good", "system": DECIDING[0], "base": DECIDING[1],
         "pert": DECIDING[2], "why": ""},
        {"name": "unbounded", "system": UNBOUNDED[0], "base": UNBOUNDED[1],
         "pert": UNBOUNDED[2], "why": ""},
        {"name": "tied", "system": TIED[0], "base": TIED[1],
         "pert": TIED[2], "why": ""},
    ]
    _patch_proposer(monkeypatch, proposals)
    rows, backend = PolyhedronDomain().propose(RULE, 3, Transport())
    assert backend == "stub-backend"
    assert len(rows) == 3, "nothing may be filtered out on the way in"
    assert [r["name"] for r in rows] == ["good", "unbounded", "tied"]
    assert {screen_row(r).value for r in rows} == {DECISIVE, REFUSED, UNLICENSED}


# ------------------------------- separation is judged on the exponents ---


def test_separation_is_measured_on_exponents_not_on_degrees():
    """
    v10. `1/(1-q)` is flat for small q, so degrees can differ by plenty while
    the exponents they predict sit inside one another's tolerance. These pairs
    are real: they came out of the first steered campaign round, and the old
    degree test called every one of them decisive.
    """
    # q* against rival -> exponents -> can a 0.15-tolerance measurement choose?
    assert separates(0.25, 0.50)      # 1.333 vs 2.000, gap 0.667
    assert separates(1 / 3, 0.50)     # 1.500 vs 2.000, gap 0.500
    assert not separates(1 / 6, 0.25)  # 1.200 vs 1.333, gap 0.133
    assert not separates(1 / 7, 0.20)  # 1.167 vs 1.250, gap 0.083
    assert not separates(0.25, 1 / 3)  # 1.333 vs 1.500, gap 0.167


def test_the_gap_must_exceed_twice_the_tolerance_so_the_intervals_are_disjoint():
    """The guarantee: no single measurement can sit inside both windows."""
    for low_q, rival in ((0.25, 0.50), (1 / 3, 0.50), (0.20, 0.50)):
        low, high = 1 / (1 - low_q), 1 / (1 - rival)
        assert separates(low_q, rival)
        assert high - low > 2 * exponent_tolerance(low)
        # Disjoint acceptance intervals is exactly what that buys.
        assert low + exponent_tolerance(low) < high - exponent_tolerance(low)


def test_a_rival_too_close_to_exclude_confirms_rather_than_decides():
    """
    Faces disagree, both degrees below 1, and it is still not decisive - the
    measurement would be consistent with either rule. Before v10 this screened
    as `decisive`, which overstated what such a row could establish.
    """
    # Orders (6, 3) at a box corner: q* = 1/6 against a rival at 1/3.
    out = screen("([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
                 "-(x0**3 + x1**6)", "x0 + x1")
    assert out.value == CONFIRMING
    assert "consistent with both rules" in out.reason
    assert not next(l for l in out.layers if l.name == "selection").passed


def test_separation_needs_both_degrees_inside_the_unit_interval():
    assert not separates(0.25, 1.5)   # rival diverges, handled as SELECTIVE
    assert not separates(1.5, 0.25)
    assert not separates(0.0, 0.5)
    assert not separates(0.25, 1.0)


def test_the_gap_prompt_asks_for_exponent_separation_not_degree_spread():
    text = focus_for_gap(RULE)
    assert "MORE THAN 0.3" in text
    assert "1.200 against 1.333" in text, "the near-miss has to be named"
    # And shapes that work: the target table carries them, with the exponent
    # pair each one implies. `test_the_prompt_renders_every_target_with_its_exponents`
    # checks all six; this only pins that the table reached the prompt at all.
    assert "1.333 vs 2.000" in text, "and a shape that works"


def test_an_exponent_the_probe_cannot_reach_is_not_decisive():
    """
    The criterion runs the other way at the top of the range. As q approaches 1
    the exponent diverges while the tolerance only grows proportionally, so any
    degree gap clears 2*tolerance. Three corpus rows sat at a predicted 2872
    against a rival at 4739, screened decisive, and had measured exactly
    nothing - s**2872 is zero at every strength the ladder visits.
    """
    assert MEASURABLE_EXPONENT == pytest.approx(6.5, abs=1e-9)
    assert not separates(1 - 1 / 2872.73, 1 - 1 / 4739.34)
    # Just under the ceiling still works, just over it does not.
    assert separates(1 - 1 / 6.0, 1 - 1 / 20.0)
    assert not separates(1 - 1 / 7.0, 1 - 1 / 20.0)


def test_the_ceiling_is_derived_from_the_probe_not_chosen():
    """If the ladder or the resolution floor moves, the ceiling moves with it."""
    import math

    from categorical_polytope.adjudication.polyhedra import laws

    assert MEASURABLE_EXPONENT == pytest.approx(
        math.log(laws.GAP_RESOLUTION) / math.log(laws.GAP_STRENGTHS[0]))
    # A gap at the ceiling is exactly at the floor at the ladder's top rung.
    assert laws.GAP_STRENGTHS[0] ** MEASURABLE_EXPONENT == pytest.approx(
        laws.GAP_RESOLUTION, rel=1e-9)


# --------------------------------------------- the advertised spread holds ---


def test_every_advertised_target_is_certified():
    """
    The prompt's examples are data, not prose, so they can be checked. If the
    separation criterion moves and one of the advertised pairs stops being
    decisive, this fails rather than the campaign quietly asking for shapes the
    screen would then reject.
    """
    for degree, rival, how in DECISIVE_TARGETS:
        assert separates(float(degree), float(rival)), f"{degree} vs {rival} ({how})"
        assert 1.0 / (1.0 - float(degree)) < MEASURABLE_EXPONENT, how
        assert 0.0 < float(degree) < float(rival) < 1.0, how


def test_the_advertised_targets_actually_spread():
    """
    The whole point of the clause. Six targets that all shared a rival degree
    would reproduce the failure they exist to fix - the first steered round
    returned ten decisive candidates with the rival at 1/2 every time.
    """
    rivals = [rival for _degree, rival, _how in DECISIVE_TARGETS]
    degrees = [degree for degree, _rival, _how in DECISIVE_TARGETS]
    assert len(set(rivals)) == len(rivals), "a repeated rival wastes a slot"
    assert len(set(degrees)) == len(degrees)
    assert float(max(rivals)) - float(min(rivals)) > 0.4, "rivals must span a range"


def test_the_prompt_explains_why_a_linear_push_cannot_spread():
    """
    The mechanism, not just the instruction. q on an edge is alpha/beta, so a
    linear push reaches only 1/beta and tops out at 1/2 - which is why every
    candidate in the first steered round had its rival there. A model told to
    vary the rival without being told that will vary the base orders and land
    in the same place.
    """
    text = focus_for_gap(RULE)
    assert "VARY THE RIVAL DEGREE" in text
    assert "alpha/beta" in text
    assert "1/beta" in text and "largest of" in text
    assert "raise the PUSH degree" in text


def test_the_prompt_renders_every_target_with_its_exponents():
    text = focus_for_gap(RULE)
    for degree, rival, _how in DECISIVE_TARGETS:
        low, high = 1.0 / (1.0 - float(degree)), 1.0 / (1.0 - float(rival))
        assert f"{low:.3f} vs {high:.3f}" in text, (degree, rival)
        assert str(degree) in text and str(rival) in text


def test_the_prompt_states_the_measurability_ceiling():
    assert f"{MEASURABLE_EXPONENT:.1f}" in focus_for_gap(RULE)
