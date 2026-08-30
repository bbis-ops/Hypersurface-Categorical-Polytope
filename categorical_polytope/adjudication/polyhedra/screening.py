"""
Domain three's screen: the face-selection law's own three layers.

The generic vocabulary lives in `adjudication/screening.py`. This supplies the
domain-specific part - what "would distinguish the rule from a rival" means when
the rule is `q* = min over admissible faces`.

Its rival is the maximum, and separating them takes more than two faces that
disagree. What has to be far apart is the EXPONENTS the two rules predict,
judged against the tolerance the verdict is decided by. `1/(1-q)` is flat for
small `q`, so a degree gap of 0.05 near `q = 0.15` moves the exponent by about
0.07 and a tolerance of 0.15 swallows it whole. The first steered campaign round
produced two rows exactly like that - 1.200 against a rival at 1.333, and 1.167
against 1.250 - which the old degree test called decisive and no measurement
could have settled.

`separates` therefore requires the predicted exponents to differ by more than
twice the tolerance, which makes their acceptance intervals disjoint and
guarantees, before any measuring, that one rule will be excluded. A rival at or
above 1 is a weaker thing again: the maximum rule merely diverges there, and
rejecting a divergence is something any rule survives.

The three layers, read as a specification rather than as a test:

    localization  a simple maximising vertex, isolated (Lemma 1)
    selection     rival exponent more than 2*tolerance from the winning one
    scaling       a winning degree in (0, 1), giving an exponent

Two entry points, same classifier behind both. `screen` weighs a candidate that
has not been adjudicated, and costs one local adjudication. `screen_row` weighs
one already in the corpus and costs a dict lookup, because every field the
classifier needs has been recorded since v8. That is what makes it affordable to
screen a whole batch on the way past, or the whole corpus on demand.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from ..screening import (
    CONFIRMING,
    DECISIVE,
    REFUSED,
    SELECTIVE,
    UNLICENSED,
    Layer,
    Screening,
)
from .domain import (
    MEASURABLE_EXPONENT,
    SELECTION_SPREAD,
    _EXPONENT_RULES,
    exponent_tolerance,
    separates,
)
from .predict import RULE, Hypotheses, hypotheses_from, predict


def _classify(
    rule_id: str,
    payload: tuple[str, ...],
    *,
    hypotheses: Hypotheses | None,
    degrees: list[float],
    exponent: float | None,
    refusal: str,
    winning: tuple[tuple[int, ...], ...] = (),
) -> Screening:
    """The whole decision, from pieces either entry point can supply."""
    isolated = hypotheses.isolated if hypotheses else False
    if hypotheses is None:
        localization_detail = "no isolation check was reached"
    elif isolated:
        localization_detail = (f"simple maximising vertex, isolated by "
                               f"{hypotheses.isolation_margin:.3g}")
    else:
        localization_detail = (f"rival margin {hypotheses.isolation_margin}: the "
                               "maximiser is tied or beaten elsewhere")

    spread = (degrees[-1] - degrees[0]) if len(degrees) > 1 else 0.0
    disagree = spread > SELECTION_SPREAD
    rival = degrees[-1] if degrees else None
    rival_finite = rival is not None and rival < 1.0
    # Whether measurement could CHOOSE, not merely whether the degrees differ:
    # `1/(1-q)` is flat for small q, so faces can disagree while the exponents
    # they predict sit inside one another's tolerance.
    separated = (rival is not None and degrees
                 and separates(degrees[0], rival))
    if not degrees:
        selection_detail = "no admissible face"
    elif not disagree:
        selection_detail = (f"{len(degrees)} admissible face(s), all agreeing "
                            f"about q within {SELECTION_SPREAD}")
    elif not rival_finite:
        selection_detail = (f"faces disagree by {spread:.4f}; rival at "
                            f"q = {rival:.4f} >= 1, diverges")
    elif not separated:
        low, high = 1.0 / (1.0 - degrees[0]), 1.0 / (1.0 - rival)
        selection_detail = (
            f"faces disagree by {spread:.4f}, but the exponents they predict "
            f"({low:.3f} against {high:.3f}) are closer than "
            f"{2 * exponent_tolerance(low):.3f}, so neither rule is excluded")
    else:
        low, high = 1.0 / (1.0 - degrees[0]), 1.0 / (1.0 - rival)
        selection_detail = (f"faces disagree by {spread:.4f}; exponents "
                            f"{low:.3f} against {high:.3f}, disjoint at "
                            f"tolerance {exponent_tolerance(low):.3f}")

    layers = (
        Layer("localization", isolated, localization_detail),
        Layer("selection", bool(separated), selection_detail),
        Layer("scaling", exponent is not None,
              f"gamma = {exponent:.6g}" if exponent is not None else refusal),
    )

    def made(value: str, reason: str) -> Screening:
        return Screening(
            domain="polyhedra", rule_id=rule_id, payload=payload, value=value,
            reason=reason, layers=layers, margin=spread,
            detail={"face_degrees": degrees, "exponent": exponent,
                    "winning_faces": winning})

    if exponent is None:
        return made(REFUSED, refusal or "scope would decline it")
    if hypotheses is None or not hypotheses.licensed:
        unmet = ", ".join(hypotheses.unmet()) if hypotheses else "nothing measured"
        return made(UNLICENSED, f"would be adjudicated, but unmet: {unmet}")
    if separated:
        low, high = 1.0 / (1.0 - degrees[0]), 1.0 / (1.0 - rival)
        return made(DECISIVE,
                    f"the minimum rule predicts {low:.3f} and the maximum rule "
                    f"{high:.3f}, further apart than twice the "
                    f"{exponent_tolerance(low):.3f} tolerance, so a single "
                    "measurement cannot fit both")
    if disagree and not rival_finite:
        return made(SELECTIVE,
                    f"faces disagree by {spread:.4f}, but the rival sits at "
                    f"q = {rival:.4f} >= 1, where the maximum rule only "
                    "diverges rather than competing")
    if disagree:
        # Degrees differ, exponents do not differ enough to choose between.
        low, high = 1.0 / (1.0 - degrees[0]), 1.0 / (1.0 - rival)
        return made(CONFIRMING,
                    f"faces disagree by {spread:.4f}, but the exponents they "
                    f"predict ({low:.3f} against {high:.3f}) are closer than "
                    f"twice the {exponent_tolerance(low):.3f} tolerance, so "
                    "the measurement is consistent with both rules")
    return made(CONFIRMING,
                "admissible and licensed, but every face agrees about q, so a "
                "maximum rule would have returned the same exponent")


def screen(system: str, base: str, pert: str, *, rule_id: str = RULE) -> Screening:
    """Weigh a candidate that is not in the corpus. One local adjudication."""
    prediction = predict(system, base, pert)
    return _classify(
        rule_id, (system, base, pert),
        hypotheses=prediction.hypotheses,
        degrees=sorted(f.degree for f in prediction.faces if f.degree is not None),
        exponent=prediction.exponent,
        refusal=prediction.refusal,
        winning=prediction.winning_faces)


def screen_row(row: Mapping[str, Any]) -> Screening:
    """
    Weigh a row already adjudicated, from what the adjudicator recorded.

    No re-measurement: `admissible_faces`, `betas`, `base_homogeneity` and
    `rival_margin` are all on the record, so this is exact and costs nothing.
    A rule with no domain-specific screen comes back `CONFIRMING`, which is the
    honest default - without a test there is no ground to claim the candidate
    distinguishes anything.
    """
    rule_id = str(row.get("rule_id", ""))
    payload = row.get("payload") or {}
    fields = (str(payload.get("system", "")), str(payload.get("base", "")),
              str(payload.get("pert", "")))
    if rule_id not in _EXPONENT_RULES:
        return Screening(
            domain="polyhedra", rule_id=rule_id, payload=fields, value=CONFIRMING,
            reason="no domain-specific screen for this rule")

    metrics = row.get("metrics") or {}
    exponent = metrics.get("predicted_exponent")
    return _classify(
        rule_id, fields,
        hypotheses=hypotheses_from(metrics),
        degrees=sorted(d for _, d in (metrics.get("admissible_faces") or ())),
        exponent=None if exponent is None else float(exponent),
        refusal=str(row.get("reason", "")))


#: Target (winning degree, rival degree, how to build it) triples for the gap
#: prompt. Data rather than prose so the examples can be checked: every pair
#: here is certified by `separates`, and `test_every_advertised_target_is_certified`
#: fails if one stops being decisive when the criterion moves.
#:
#: The spread over rival degrees is the point. A degree on an edge is
#: alpha/beta - push degree over base order - so a LINEAR push on every edge can
#: only reach degrees of the form 1/beta, the largest of which is 1/2. A batch
#: built that way has every rival at 1/2 and every maximum-rule prediction at
#: exactly 2.000, which is what the first steered round produced: ten decisive
#: candidates all testing the selection rule at one point. Moving the rival
#: means raising the PUSH degree, not the base order.
DECISIVE_TARGETS: tuple[tuple[Fraction, Fraction, str], ...] = (
    (Fraction(1, 4), Fraction(1, 2), "orders (4,2), linear push on both"),
    (Fraction(1, 8), Fraction(1, 3), "orders (8,3), linear push on both"),
    (Fraction(1, 6), Fraction(2, 3), "order 6 linear push; order 3 squared push"),
    (Fraction(2, 5), Fraction(3, 4), "order 5 squared push; order 4 cubed push"),
    (Fraction(1, 2), Fraction(4, 5), "order 2 linear push; order 5 4th-power push"),
    (Fraction(2, 3), Fraction(6, 7), "order 3 squared push; order 7 6th-power push"),
)


def _target_table() -> str:
    """The advertised spread, rendered with the exponents it actually implies."""
    rows = []
    for degree, rival, how in DECISIVE_TARGETS:
        low, high = 1.0 / (1.0 - degree), 1.0 / (1.0 - rival)
        rows.append(f"      q* = {str(degree):>3}, rival {str(rival):>3}  ->  "
                    f"{low:.3f} vs {high:.3f}   {how}")
    return "\n".join(rows)


def focus_for_gap(rule_id: str = RULE) -> str:
    """
    A prompt fragment asking for the candidates the corpus still lacks.

    Written from the screen read backwards: each clause is one of the three
    layers stated as something to build rather than something to check. This is
    where screening pays. Filtering a batch after the fact throws away tokens
    already spent; describing the decisive shape spends the next batch better.
    """
    if rule_id not in _EXPONENT_RULES:
        return ""
    return (
        "\n\nMost rows already in the corpus have admissible faces that all "
        "agree about the weighted degree. Those cannot distinguish selecting "
        "the MINIMUM face degree from selecting the maximum, so they add "
        "nothing to the evidence however many of them there are. Propose "
        "systems that are decisive instead, meaning ALL of:\n"
        "  - a simple vertex, exactly d active constraints, that is the UNIQUE "
        "maximiser of the base - not tied with another vertex, and not sitting "
        "on a whole face of maximisers;\n"
        "  - at least two admissible faces whose weighted degrees are far "
        "enough apart that the exponents 1/(1-q) they predict differ by MORE "
        "THAN 0.3, with both degrees below 1. Close degrees are not enough: "
        "1/(1-q) is flat for small q, so a winning degree of 1/6 against a "
        "rival at 1/4 predicts 1.200 against 1.333, and no measurement can "
        "tell those apart. The winning exponent must also stay below "
        f"{MEASURABLE_EXPONENT:.1f}, or the gap is under floating-point "
        "resolution at every strength and nothing can be measured at all;\n"
        "  - VARY THE RIVAL DEGREE ACROSS THE BATCH. A degree on an edge is "
        "alpha/beta, the push degree over the base order, so a LINEAR push on "
        "every edge can only reach degrees of the form 1/beta, the largest of "
        "which is 1/2. A batch built that way has every rival at 1/2 and every "
        "maximum-rule prediction at exactly 2.000, which tests the selection "
        "rule at a single point. To move the rival, raise the PUSH degree on "
        "an edge rather than the base order. Spread the batch across these, "
        "one or two candidates each:\n"
        + _target_table() + "\n"
        "  - every edge order of the base strictly above 1, and a base that is "
        "a weighted-homogeneous power sum in edge coordinates, with no cross "
        "term of lower weight;\n"
        "  - a polynomial perturbation whose leading form on the winning face "
        "is strictly positive.\n"
        "Prefer a tilted vertex to an axis-aligned one: at an axis-aligned "
        "vertex the edge and ambient measurements coincide and the effect "
        "cannot show."
    )
