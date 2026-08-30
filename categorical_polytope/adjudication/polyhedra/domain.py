"""
Domain three: the exponent laws on a general polyhedron.

Domain one runs on a box, where a corner's edges are the coordinate axes, so
"measure the flatness along each axis" and "measure it along each edge" are the
same instruction. On any other polytope they are different instructions, and
this domain asks both and records which one the law lives in.

    polyhedron/edge_exponent_law     q from the inward edge directions
    polyhedron/ambient_exponent_law  q from the coordinate axes
    polyhedron/linear_max_at_vertex  control: LP's fundamental theorem

The third rule is a correct statement and exists to be a false-positive probe,
the way `merge_intervals` does in domain two. If an adversarial search starts
producing counterexamples there, the harness is broken, not the theorem.

The adjudicator is arithmetic on stdlib floats. No model decides any verdict.
"""

from __future__ import annotations

import ast
import math
from typing import Any, Hashable, Mapping, Sequence

from ..domain import Transport, Verdict
from ..status import Status
from . import laws
from .geometry import GeometryError, Polyhedron, Vertex

#: Bumped whenever adjudicator semantics change.
VERIFIER_VERSION = 11

#: How far below 1 the weighted degree must sit for `1/(1-q)` to mean anything.
#: q = 1 is the excluded boundary, and a geometry whose edge degrees sum to
#: exactly 1 lands one ULP under it after rounding - 0.9999999999999999 passed
#: a bare `q < 1.0`, and the predicted exponent came out as 2**53 with a
#: tolerance of 9e14, against which any honest measurement is a mismatch.
_Q_MARGIN = 1e-9

#: How far two admissible faces must disagree about q before the row is taken
#: to put the selection clause itself at risk. Below this the minimum, the
#: maximum and "pick any" all return the same exponent within tolerance, so the
#: row tests the dilation and the admissibility filter but not the selection.
SELECTION_SPREAD = 0.05

#: The largest exponent the gap probe could resolve, derived rather than picked.
#: The ladder's top rung is 1e-2 and a gap below `GAP_RESOLUTION` is rounding,
#: so a law predicting `s**gamma` is measurable only while `1e-2**gamma` stays
#: above that floor. Past it every strength reads zero and the row can only ever
#: come back inconclusive, whatever its faces say.
MEASURABLE_EXPONENT = (
    math.log(laws.GAP_RESOLUTION) / math.log(laws.GAP_STRENGTHS[0])
)

RULE_IDS: tuple[str, ...] = (
    "polyhedron/edge_exponent_law",
    "polyhedron/ambient_exponent_law",
    "polyhedron/linear_max_at_vertex",
)

_EXPONENT_RULES = {"polyhedron/edge_exponent_law", "polyhedron/ambient_exponent_law"}

REVERIFY_RULES_BY_VERSION: dict[int, set[str]] = {
    # v2 widened the weighted-degree guard to exclude q = 1 by a margin, which
    # only the two exponent laws reach; `linear_max_at_vertex` returns from
    # `scope` before q is computed.
    2: _EXPONENT_RULES,
    # v3 reads the exponent off a strength ladder instead of one fixed pair,
    # and sends an unsettled mismatch to `inconclusive` rather than
    # `counterexample`. Same two rules.
    3: _EXPONENT_RULES,
    # v4 seeds the vertex probe with an independent ladder per edge, so a gain
    # needing very different magnitudes along different edges is reachable.
    # Every rule here measures with that probe - `linear_max_at_vertex` uses it
    # too, at radius 0.9 - so all three are invalidated, not just the two that
    # measure an exponent.
    4: set(RULE_IDS),
    # v5 takes q on the smallest admissible face of the tangent cone instead of
    # summing alpha_i/beta_i across independently measured rays. Only the two
    # exponent laws compute q at all.
    5: _EXPONENT_RULES,
    # v6 records `base_homogeneity` per row. Diagnostic only - no verdict
    # depends on it - but the metric has to exist on every row for the corpus
    # to state where V.16 applies rather than where it merely agreed.
    6: _EXPONENT_RULES,
    # v7 stops discarding a face whose q was already read when a deeper probe
    # rung runs out of resolution. q* is a minimum over faces, so dropping one
    # could only bias it upward.
    7: _EXPONENT_RULES,
    # v8 records the two hypotheses the corpus was silent about. `rival_margin`
    # probes for a competing maximiser elsewhere in the polytope, which is
    # Lemma 1's localisation - previously assumed, never measured, and the one
    # hypothesis whose failure would make an agreement meaningless rather than
    # merely unlicensed. `hypotheses_licensed`, `rival_max_degree` and
    # `selection_discriminates` move the coverage arithmetic off the report
    # generator and onto the row, so a corpus states its own evidential reach.
    # All four are diagnostic; no verdict depends on any of them.
    8: _EXPONENT_RULES,
    # v9 records `rejected_faces`: the faces the selection filtered out and the
    # reason for each. Diagnostic again, and the reason the forward predictor
    # can answer "why was that direction ignored" instead of only "here is the
    # exponent". A refusal for "no face carries the perturbation" is otherwise
    # unreadable once the run is over.
    9: _EXPONENT_RULES,
    # v10 judges `selection_discriminates` on the exponents rather than on the
    # face degrees. The degree test said a spread above 0.05 was enough, but
    # 1/(1-q) is flat for small q, so two rows from the first steered campaign
    # round - 1.200 against a rival at 1.333, and 1.167 against 1.250 - were
    # recorded as separating the minimum rule from the maximum when no
    # measurement could have excluded either. The new test requires the
    # predicted exponents to be more than 2*tolerance apart, which makes their
    # acceptance intervals disjoint. Still diagnostic; no verdict moves.
    10: _EXPONENT_RULES,
    # v11 stops three of the probe's limits from being recorded as findings,
    # which between them produced the first counterexamples the edge law ever
    # had - all three false.
    #   * A face degree now reports whether it settled, the way `gap_exponent`
    #     has since v3, and an unsettled winning degree sends a mismatch to
    #     inconclusive instead of counterexample. One row read q = 0.333 on a
    #     face whose degree was still climbing past 0.9, making a false minimum.
    #   * A base order that did not resolve is undecided, as
    #     `directional_order` documents, and no longer admits the row. Two rows
    #     carried a term of order 8, which underflows the probe's floor and read
    #     as order 0.
    #   * An expression that evaluates to a complex number raises rather than
    #     reaching `math.isfinite`, which raised TypeError and killed a campaign
    #     round outright.
    11: _EXPONENT_RULES,
}

MAX_PAYLOAD_CHARS = 2000


def exponent_tolerance(predicted: float) -> float:
    """Relative, matching the rule domain one settled on at verifier v17."""
    return max(0.15, 0.10 * predicted)


def separates(degree: float, rival: float) -> bool:
    """
    Could a measurement actually tell the minimum rule from the maximum here?

    Not the same question as whether the face degrees differ, and the
    difference is what v10 exists to fix. Separation has to be judged on the
    EXPONENTS, against the tolerance the verdict is decided by, because
    `1/(1-q)` is flat for small `q`: a gap of 0.05 in `q` near `q = 0.15` moves
    the exponent by about 0.07, well inside a tolerance of 0.15, so no
    measurement could exclude either rule.

    Requiring the two exponents to be more than `2 * tolerance` apart makes
    their acceptance intervals disjoint, so a single measurement cannot sit
    inside both. That is a guarantee available before measuring, which is what
    a screen needs. Two rows from the first steered campaign round - predicted
    1.200 against a rival at 1.333, and 1.167 against 1.250 - passed the old
    degree test and could not have excluded anything.

    The separation test alone is not enough, because it runs the other way at
    the top of the range. As `q` approaches 1 the exponent diverges while the
    tolerance grows only proportionally, so any degree gap at all clears
    `2 * tolerance`: three corpus rows sat at a predicted 2872 against a rival
    at 4739 and were called decisive, having measured nothing whatsoever. A gap
    of `s**2872` is zero in floating point at every strength the probe visits.
    So the winning exponent must also be one the probe could resolve - see
    `MEASURABLE_EXPONENT`, which is derived from the ladder rather than picked.
    """
    if not (0.0 < degree < 1.0 and 0.0 < rival < 1.0):
        return False
    low, high = 1.0 / (1.0 - degree), 1.0 / (1.0 - rival)
    if low >= MEASURABLE_EXPONENT:
        return False
    return (high - low) > 2.0 * exponent_tolerance(low)


class PolyhedronDomain:
    """Adapts the polyhedral exponent laws to the `Domain` protocol."""

    name = "polyhedra"

    def __init__(self, verifier_version: int = VERIFIER_VERSION, *, timeout: float = 0.0):
        self.verifier_version = int(verifier_version)
        self.timeout = float(timeout)  # unused: this adjudicator is arithmetic

    @property
    def rule_ids(self) -> Sequence[str]:
        return RULE_IDS

    def rules_invalidated_between(self, prior: int, current: int) -> set[str]:
        if prior == current:
            return set()
        affected: set[str] = set()
        for version in range(prior + 1, current + 1):
            affected |= REVERIFY_RULES_BY_VERSION.get(version, set())
        return affected

    def identity(self, row: Mapping[str, Any]) -> Hashable:
        p = row["payload"]
        return (row["rule_id"], p.get("system", ""), p.get("base", ""), p.get("pert", ""))

    def readjudicate(self, row: Mapping[str, Any]) -> Verdict:
        p = row["payload"]
        return self.adjudicate(str(row["rule_id"]), p.get("system", ""),
                               p.get("base", ""), p.get("pert", ""))

    # -- stage one: admission ----------------------------------------------

    @staticmethod
    def parse_system(system: str) -> Polyhedron:
        """
        Build `Ax <= b` from a literal `([[...]], [...])` pair.

        `literal_eval` is the whitelist, exactly as in domain two: containers
        and numbers only, nothing that can call or import.
        """
        if len(system) > MAX_PAYLOAD_CHARS:
            raise GeometryError(f"system exceeds {MAX_PAYLOAD_CHARS} characters")
        value = ast.literal_eval(system)
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise GeometryError("system must be a 2-tuple (A, b)")
        return Polyhedron(value[0], value[1])

    @staticmethod
    def choose_vertex(poly: Polyhedron, base=None) -> Vertex | None:
        """
        The vertex the law is actually about, preferring a tilted one.

        Two filters, in order. First the vertex must be a local maximum of the
        base along every inward edge, since the law is about the gap *from* a
        maximising vertex - picking any other one makes the whole question
        vacuous. Then, among those, prefer a vertex whose edges are not the
        coordinate axes, because an axis-aligned vertex makes the edge and
        ambient measurements identical and cannot exhibit the effect at all.

        Choosing here rather than making the proposer name an index keeps the
        payload small and stops a candidate from being wasted on a vertex that
        was never a maximum.
        """
        simple = [v for v in poly.vertices() if v.is_simple and v.edges]
        if not simple:
            return None
        if base is not None:
            simple = [
                v for v in simple
                if all(laws.directional_order(base, v, e, rising=True) <= 1e-6
                       for e in v.edges)
            ]
            if not simple:
                return None
        tilted = [v for v in simple if not v.is_axis_aligned]
        return tilted[0] if tilted else simple[0]

    def scope(self, rule_id: str, system: str, base_expr: str, pert_expr: str
              ) -> tuple[bool, str, str, dict[str, Any]]:
        """
        Admissibility, decided before any gap is measured.

        Everything here is a property of the geometry and the two expressions.
        No run result is consulted, so admission cannot be withdrawn once the
        measured exponent turns out to be inconvenient.
        """
        if rule_id not in RULE_IDS:
            return False, "rejected", f"unknown rule: {rule_id}", {}
        try:
            poly = self.parse_system(system)
        except (GeometryError, ValueError, SyntaxError, TypeError) as exc:
            return False, "rejected", f"unusable system: {type(exc).__name__}: {exc}", {}

        metrics: dict[str, Any] = {"dim": poly.dim, "constraints": len(poly.A)}
        if not poly.is_bounded():
            # A recession direction was found. The laws presuppose a maximum,
            # so this is a hypothesis failure, not a refutation.
            return False, "outside_scope", "polyhedron is unbounded", metrics

        try:
            base = laws.compile_expr(base_expr, poly.dim)
            pert = laws.compile_expr(pert_expr, poly.dim)
        except laws.UnsafeExpression as exc:
            return False, "rejected", f"expression rejected: {exc}", metrics

        if (
            rule_id == "polyhedron/linear_max_at_vertex"
            and not laws.is_affine_expression(base_expr, poly.dim)
        ):
            return False, "outside_scope", (
                "linear_max_at_vertex requires an affine base expression"
            ), metrics

        if not [v for v in poly.vertices() if v.is_simple and v.edges]:
            return False, "outside_scope", "no simple vertex with an edge basis", metrics
        vertex = self.choose_vertex(poly, base)
        if vertex is None:
            return False, "outside_scope", "no vertex is a local maximum of the base", metrics
        metrics["vertex"] = [round(c, 9) for c in vertex.point]
        metrics["active_constraints"] = list(vertex.active)
        metrics["axis_aligned"] = vertex.is_axis_aligned
        metrics["edges"] = [[round(c, 6) for c in e] for e in vertex.edges]

        if rule_id == "polyhedron/linear_max_at_vertex":
            return True, "", "", {**metrics, "poly": poly, "vertex_obj": vertex,
                                  "base_fn": base, "pert_fn": pert}

        if rule_id == "polyhedron/edge_exponent_law":
            directions: Sequence[Sequence[float]] = vertex.edges
        else:
            directions, infeasible = laws.ambient_axis_directions(poly, vertex)
            # An axis that leaves the polytope in both orientations is the
            # sharpest form of the effect: the naive recipe is not merely
            # inaccurate there, it is measuring outside the feasible set.
            metrics["infeasible_axes"] = infeasible
        metrics["directions"] = [[round(c, 6) for c in d] for d in directions]
        q, detail = laws.face_weighted_degree(base, pert, vertex, directions)
        metrics["weighted_degree"] = q
        metrics["alphas"] = [round(a, 6) for a in detail["alphas"]]
        metrics["betas"] = [round(b, 6) for b in detail["betas"]]
        metrics["admissible_faces"] = detail["faces"]
        # And what was filtered out, with the reason. A refusal for "no face
        # carries the perturbation" is otherwise unreadable after the fact, and
        # the forward predictor in `predict.py` has nothing to show a caller
        # who asks why a direction was ignored.
        metrics["rejected_faces"] = detail["rejected"]
        metrics["unsettled_faces"] = detail["unsettled"]
        metrics["weighted_degree_settled"] = bool(detail["settled"])
        # `directional_order` documents 0.0 as "no scale pair resolved", which
        # callers are to treat as undecided. Reading a face structure off it
        # treats it as a degree instead, and the row then gets a prediction the
        # law never made: two corpus rows carried a base term of order 8, which
        # underflows the probe's floor and read as 0, and their honest
        # exponents (8/7) were adjudicated against a prediction of 2 and 1.5.
        if any(order <= 1e-6 for order in detail["betas"]):
            unresolved = [i for i, order in enumerate(detail["betas"]) if order <= 1e-6]
            return False, "outside_scope", (
                f"the base order did not resolve along direction(s) {unresolved}; "
                "an undecided order is not an input the law has"
            ), metrics
        # Recorded, never gated on: says whether V.16's transport from the
        # orthant is licensed for this row, or whether it merely agreed.
        homogeneity = laws.base_homogeneity(base, vertex, directions)
        metrics["base_homogeneity"] = (
            None if homogeneity is None else round(homogeneity, 6)
        )
        # Recorded on the same terms. `base_homogeneity` carries hypothesis 2;
        # `rival_margin` carries Lemma 1's localisation, which `choose_vertex`
        # only ever checked along the vertex's own edges - strictly weaker than
        # the hypothesis, since another vertex may hold a higher value and then
        # the measured gap belongs to a different vertex than the predicted one.
        margin = laws.rival_margin(base, poly, vertex)
        metrics["rival_margin"] = None if margin is None else round(margin, 9)
        # What the row is evidence FOR, stored rather than re-derived at report
        # time. `hypotheses_licensed` is the note's hypothesis 2 in full - every
        # edge order above 1 and a homogeneous principal part.
        # `selection_discriminates` is the harder one: the faces have to
        # disagree, and the rival maximum rule has to predict a finite exponent
        # too, so measurement chooses between two numbers instead of merely
        # rejecting a divergence.
        metrics["hypotheses_licensed"] = bool(
            detail["betas"] and all(b > 1.0 for b in detail["betas"])
            and homogeneity is not None and abs(homogeneity - 1.0) < 1e-3
        )
        face_degrees = [degree for _, degree in detail["faces"]]
        rival = max(face_degrees) if face_degrees else None
        metrics["rival_max_degree"] = rival
        # Whether measurement could CHOOSE between the rules, not merely
        # whether the faces disagree - see `separates`.
        metrics["selection_discriminates"] = bool(
            rival is not None and separates(q, rival)
        )
        if not detail["faces"]:
            return False, "outside_scope", (
                "no face of the tangent cone carries the perturbation"
            ), metrics
        if not 0.0 < q < 1.0:
            return False, "outside_scope", f"weighted degree {q:.4f} outside (0, 1)", metrics
        # Kept as defence in depth. Taking the minimum over admissible faces
        # cannot reach q = 1 the way summing across rays did, so this should
        # now be unreachable - but a guard that costs nothing is worth more
        # than the assumption that it is.
        if 1.0 - q < _Q_MARGIN:
            # The law says nothing at q = 1: the exponent it predicts diverges.
            # Report that as unmeasurable rather than letting float slack turn
            # a boundary geometry into a counterexample.
            return False, "outside_scope", (
                f"weighted degree {q:.12f} is 1 to within {_Q_MARGIN:g}; "
                "the predicted exponent diverges"
            ), metrics
        metrics["predicted_exponent"] = 1.0 / (1.0 - q)
        return True, "", "", {**metrics, "poly": poly, "vertex_obj": vertex,
                              "base_fn": base, "pert_fn": pert}

    # -- stage two: verdict ------------------------------------------------

    def _verdict(self, rule_id: str, metrics: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        poly, vertex = metrics.pop("poly"), metrics.pop("vertex_obj")
        base, pert = metrics.pop("base_fn"), metrics.pop("pert_fn")

        if rule_id == "polyhedron/linear_max_at_vertex":
            best_vertex = max(base(v.point) for v in poly.vertices())
            interior = laws.local_max_near_vertex(base, poly, vertex, radius=0.9)
            metrics["best_vertex_value"] = best_vertex
            metrics["best_interior_value"] = interior
            holds = interior <= best_vertex + 1e-7
            return ("verified" if holds else "counterexample",
                    "maximum attained at a vertex" if holds
                    else "an interior point beat every vertex", metrics)

        predicted = float(metrics["predicted_exponent"])
        measured, gaps, converged = laws.gap_exponent(base, pert, poly, vertex)
        metrics["measured_exponent"] = measured
        metrics["gaps"] = [gaps[0], gaps[1]]
        metrics["exponent_converged"] = converged
        if measured <= 0.0:
            # Admitted, but no gap resolved. The verifier's limit, not the law's.
            return "inconclusive", "no resolved gap at any strength", metrics

        tol = exponent_tolerance(predicted)
        metrics["tolerance"] = tol
        if abs(measured - predicted) < tol:
            return "verified", "exponent matched", metrics
        if not converged:
            # The slope was still drifting at the deepest strength that
            # resolved a gap, so the disagreement is the probe's reach, not the
            # law's failure. Claiming a counterexample here is the one error
            # this domain cannot afford: it is the finding, so it has to be
            # earned by a settled measurement.
            return "inconclusive", (
                f"exponent still drifting at the deepest resolved strength "
                f"({measured:.3f} against {predicted:.3f}); not resolved"
            ), metrics
        if not metrics.get("weighted_degree_settled", True):
            # Same rule applied to the other side of the comparison. A measured
            # exponent can be settled while the PREDICTION is not, because the
            # winning face's degree was still moving when its probe stopped.
            # Comparing a settled measurement against an unsettled prediction
            # and calling the difference a counterexample charges the law for
            # the probe's limits.
            return "inconclusive", (
                f"the winning face's weighted degree was still drifting, so the "
                f"predicted {predicted:.3f} is not settled either "
                f"(measured {measured:.3f}); unsettled faces "
                f"{metrics.get('unsettled_faces')}"
            ), metrics
        return ("counterexample",
                f"exponent mismatch (|{measured:.3f} - {predicted:.3f}| >= {tol:.3f})",
                metrics)

    def adjudicate(self, rule_id: str, system: str, base_expr: str, pert_expr: str) -> Verdict:
        try:
            admitted, status, reason, metrics = self.scope(
                rule_id, system, base_expr, pert_expr)
        except (ArithmeticError, ValueError, TypeError) as exc:
            # Admission measures an untrusted expression at points the proposer
            # never considered, so it can fail arithmetically in ways the
            # whitelist cannot predict - a negative base under a fractional
            # power was the one that killed a campaign round. The verdict for
            # such a payload is that the law has no input here, not a
            # traceback. The exception type is named so a genuine bug in this
            # module is still legible rather than absorbed silently.
            return Verdict(Status.OUTSIDE_SCOPE,
                           f"admission failed on this expression: "
                           f"{type(exc).__name__}: {exc}", {})
        if not admitted:
            return Verdict(Status.coerce(status), reason, metrics)
        try:
            outcome = self._verdict(rule_id, metrics)
        except (ValueError, OverflowError, ZeroDivisionError, TypeError) as exc:
            return Verdict(Status.INCONCLUSIVE, f"measurement failed: {exc}",
                           {k: v for k, v in metrics.items() if not callable(v)})
        verdict_status, verdict_reason, out = outcome
        return Verdict(Status.coerce(verdict_status), verdict_reason,
                       {k: v for k, v in out.items() if not callable(v)})

    # -- ledger envelope ---------------------------------------------------

    def to_row(self, rule_id: str, name: str, system: str, base_expr: str,
               pert_expr: str, note: str = "") -> dict[str, Any]:
        verdict = self.adjudicate(rule_id, system, base_expr, pert_expr)
        return {
            "rule_id": rule_id,
            "name": name,
            "payload": {"system": system, "base": base_expr, "pert": pert_expr},
            "status": str(verdict.status),
            "reason": verdict.reason,
            "metrics": verdict.metrics,
            "note": note,
        }

    # -- generation --------------------------------------------------------

    def propose(self, rule_id: str, n: int, transport: Transport, *,
                focus: str = "", steer: bool = True
                ) -> tuple[list[dict[str, Any]], str]:
        """
        Ask for `n` candidates and adjudicate every one that comes back.

        With `steer`, the request carries `focus_for_gap` - a description of the
        candidates the corpus lacks, which is the screen read as a
        specification instead of as a test.

        Steering changes what is ASKED FOR. It changes nothing about what is
        kept: every proposal received is adjudicated and admitted, including the
        ones that screen badly. A corpus that dropped whatever failed to match
        the ask would have a denominator that means nothing, and the honest
        denominator is the whole reason to believe anything the corpus says.
        The campaign runner records that a round was steered, so a later reader
        can tell an aimed round from a blind one.
        """
        from ...interaction_search import propose_candidates
        from .prompts import parse_polyhedron_proposals, proposal_prompt
        from .screening import focus_for_gap

        gap = focus_for_gap(rule_id) if steer else ""
        proposed, backend = propose_candidates(
            n, prompt=proposal_prompt(rule_id, n) + focus + gap,
            parser=parse_polyhedron_proposals(rule_id), **transport.as_kwargs(),
        )
        rows = [self.to_row(rule_id, s["name"], s["system"], s["base"], s["pert"],
                            s.get("why", "")) for s in proposed]
        return rows, backend

    def focus_for(self, row: Mapping[str, Any]) -> str:
        p = row["payload"]
        return (f"\n\nA current counterexample uses system={p['system']}, "
                f"base={p['base']}, pert={p['pert']}. Generate variants of that "
                "geometry and those expressions that stay inside the hypotheses.")

    # -- screening ---------------------------------------------------------

    def screen(self, rule_id: str, *payload: str):
        """
        What a candidate would be evidence for, without adjudicating it.

        Deliberately does not touch the ledger. Screening exists to order work
        and to aim the next proposal round; a candidate that screens badly is
        still admitted and still recorded if it is actually proposed, because a
        denominator that drops what it found inconvenient is not one.
        """
        from .screening import screen as _screen

        system, base, pert = (list(payload) + ["", "", ""])[:3]
        return _screen(system, base, pert, rule_id=rule_id)

    def screen_row(self, row: Mapping[str, Any]):
        """Weigh a stored row from its recorded metrics. No re-measurement."""
        from .screening import screen_row as _screen_row

        return _screen_row(row)

    def focus_for_gap(self, rule_id: str) -> str:
        from .screening import focus_for_gap as _focus

        return _focus(rule_id)
