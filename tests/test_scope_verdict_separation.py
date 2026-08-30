"""
Scope and verdict must stay in separate lanes.

A verifier that can retire a candidate as `outside_scope` after seeing that the
law failed on it controls its own denominator. These tests pin the separation
structurally (scope cannot receive a verdict to consult) and behaviourally (an
admitted candidate the verifier cannot resolve is recorded as `inconclusive`,
never pushed back out of scope).
"""

from __future__ import annotations

import inspect

import pytest

from categorical_polytope.base_search import Candidate
from categorical_polytope.verification_campaign import (
    SCOPE_STATUSES,
    VERDICT_STATUSES,
    ScopeDecision,
    _verdict_base,
    _verdict_interaction,
    _verdict_record,
    scope_base,
    scope_combined,
    scope_interaction,
    verify_base,
    verify_combined,
    verify_interaction,
)

# alpha in (1.05, 1.95) puts these in V.10's slice. The predicted exponent is
# 2/(2-alpha), so alpha=1.9 predicts 20 and the gap underflows the optimizer:
# in scope by hypothesis, unresolvable in practice.
UNRESOLVABLE_IN_SLICE = ("sigma**1.9", "sigma**1.8")
RESOLVABLE_IN_SLICE = ("sigma**1.5", "sigma**1.35")


# --------------------------------------------------------------- structure ---


def test_scope_cannot_receive_a_verdict_to_consult():
    # The strongest guarantee available: scope's parameters carry no status, so
    # no future edit can make admission depend on the outcome by accident.
    for fn, expected in (
        (scope_interaction, ["law", "cand"]),
        (scope_base, ["law", "cand"]),
        (scope_combined, ["base", "pert"]),
    ):
        assert list(inspect.signature(fn).parameters) == expected
    for name in ("status", "reason", "verdict", "law_holds"):
        assert name not in inspect.signature(Candidate).parameters


def test_the_two_lanes_overlap_only_on_inconclusive():
    assert VERDICT_STATUSES & SCOPE_STATUSES == {"inconclusive"}
    assert "outside_scope" not in VERDICT_STATUSES
    assert "verified" not in SCOPE_STATUSES
    assert "counterexample" not in SCOPE_STATUSES


def test_scope_may_not_assign_a_verdict_status():
    for status in ("verified", "counterexample"):
        with pytest.raises(ValueError):
            ScopeDecision(False, status, "sneaking a verdict through scope")


def test_verdict_may_not_assign_outside_scope():
    cand = Candidate("f", "sigma")
    with pytest.raises(ValueError):
        _verdict_record("V.10", cand, ("outside_scope", "retired after the fact", {}))
    with pytest.raises(ValueError):
        _verdict_record("V.10", cand, ("rejected", "retired after the fact", {}))


# --------------------------------------------------------------- behaviour ---


@pytest.mark.parametrize("expr", UNRESOLVABLE_IN_SLICE)
def test_unresolvable_in_slice_candidate_is_admitted_then_inconclusive(expr):
    cand = Candidate("high_alpha", expr)
    scope = scope_interaction("V.10", cand)
    assert scope.admitted, "a measured in-slice homogeneity must be admitted"
    assert 1.05 < scope.metrics["theorem_alpha"] < 1.95

    row = verify_interaction("V.10", cand)
    # The regression this guards: these used to be banked as outside_scope,
    # which quietly excused the theorem's hardest cases from the denominator.
    assert row.status == "inconclusive"
    assert row.status != "outside_scope"
    assert row.reason == "no resolved inward fractional gap"


@pytest.mark.parametrize("expr", RESOLVABLE_IN_SLICE)
def test_resolvable_in_slice_candidate_still_verifies(expr):
    row = verify_interaction("V.10", Candidate("resolvable", expr))
    assert row.status == "verified"


def test_admission_does_not_depend_on_whether_the_law_resolves():
    # Same slice, same admission - only the verdict differs.
    admitted = [
        scope_interaction("V.10", Candidate("c", expr)).admitted
        for expr in UNRESOLVABLE_IN_SLICE + RESOLVABLE_IN_SLICE
    ]
    assert all(admitted)


@pytest.mark.parametrize("expr,alpha", [("sigma**0.5", 0.5), ("lam*sigma", 1.0)])
def test_genuinely_out_of_slice_candidate_is_still_outside_scope(expr, alpha):
    # Below V.10's (1.05, 1.95) slice: a real hypothesis failure, and it must
    # stay one. Widening `inconclusive` to swallow these would be the same
    # denominator problem in the opposite direction.
    scope = scope_interaction("V.10", Candidate("out_of_slice", expr))
    assert not scope.admitted
    assert scope.status == "outside_scope"
    assert scope.metrics["theorem_alpha"] == pytest.approx(alpha, abs=0.05)
    assert verify_interaction("V.10", Candidate("out_of_slice", expr)).status == "outside_scope"


def test_scope_is_deterministic():
    cand = Candidate("high_alpha", "sigma**1.9")
    first, second = scope_interaction("V.10", cand), scope_interaction("V.10", cand)
    assert (first.admitted, first.status) == (second.admitted, second.status)


# ------------------------------------------------------------- composition ---


def test_verify_interaction_is_scope_then_verdict():
    for law, expr in (("V.7", "sigma"), ("V.10", "sigma**1.5"), ("V.9", "((1-lam)**2+sigma**2)**0.5")):
        cand = Candidate("f", expr)
        scope = scope_interaction(law, cand)
        assert scope.admitted
        status, reason, _ = _verdict_interaction(law, cand, scope)
        row = verify_interaction(law, cand)
        assert (row.status, row.reason) == (status, reason)


def test_verify_base_is_scope_then_verdict():
    for law, expr in (("V.12", "-(1-lam)**4-sigma**4"), ("V.13", "-((1-lam)-0.25)**2-(sigma-0.35)**2")):
        cand = Candidate("f", expr)
        scope = scope_base(law, cand)
        assert scope.admitted
        status, reason, _ = _verdict_base(law, cand, scope)
        row = verify_base(law, cand)
        assert (row.status, row.reason) == (status, reason)


def test_verify_combined_is_scope_then_verdict():
    base = Candidate("pair_b", "-(1-lam)**4-sigma**4")
    pert = Candidate("pair_p", "sqrt(sigma)")
    assert scope_combined(base, pert).admitted
    assert verify_combined(base, pert).status == "verified"


def test_every_adjudicator_returns_a_status_from_exactly_one_lane():
    rows = [
        verify_interaction("V.10", Candidate("a", "sigma**1.9")),
        verify_interaction("V.10", Candidate("b", "sigma**2")),
        verify_interaction("V.7", Candidate("c", "sigma")),
        verify_base("V.12", Candidate("d", "-(1-lam)**4-sigma**4")),
        verify_combined(Candidate("e_b", "-(1-lam)**4-sigma**4"), Candidate("e_p", "sqrt(sigma)")),
    ]
    for row in rows:
        assert row.status in SCOPE_STATUSES | VERDICT_STATUSES
