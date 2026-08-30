"""Candidate generation for domain three: prompts and an untrusted-reply parser."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .domain import RULE_IDS

MAX_NOTE_CHARS = 240
MAX_FIELD_CHARS = 2000

# Substituted into `_TEMPLATE` as a value, never itself formatted, so braces
# here are literal and must NOT be doubled.
_SHARED = """The system is a bounded polyhedron {x : A x <= b} in 2 or 3 dimensions,
given as a Python literal 2-tuple (A, b) where A is a list of rows and b a list of
numbers. At most 12 constraints. It MUST be bounded and have at least one simple
vertex (exactly d active constraints); an unbounded system is recorded out of
scope and wastes the proposal.

`base` and `pert` are expressions in x0, x1 (and x2 in 3D). The chosen vertex must
be a local maximum of `base` along every inward edge, or the proposal is out of
scope. Allowed: + - * / ** and sin cos exp log sqrt abs tanh atan, and pi.
Numeric exponents only, no other names. Each field at most 200 characters.

Prefer TILTED vertices - ones whose edges are not coordinate directions - since an
axis-aligned vertex cannot distinguish the two measurements at all. The standard
simplex ([[-1,0],[0,-1],[1,1]], [0,0,1]) is the simplest such geometry; vary it
with sheared, rotated, and irregular polytopes."""

_GOALS = {
    "polyhedron/edge_exponent_law": (
        "The claim: with degrees measured along the INWARD EDGES, the gap obeys "
        "Delta ~ s^(1/(1-q*)). Let beta_i be the order at which `base` falls along "
        "edge i. Each monomial j of `pert` has weighted degree "
        "q_j = sum_i alpha_ij/beta_i over the edges its variables involve, and q* is "
        "the SMALLEST q_j that is below 1. Selection, not summation: every monomial "
        "above q* is invisible whatever its coefficient, and a monomial at or above 1 "
        "is out of scope. Attack it. The sharpest tests: a perturbation that vanishes "
        "on EVERY single edge and survives only on a 2-D face, such as 'x0*x1'; "
        "several monomials whose weights differ so that two branches compete, such as "
        "'x0 + x1' against a base quadratic along one edge and quartic along another; "
        "a perturbation that is negative on some feasible face; bases whose flatness "
        "order differs sharply between edges; near-degenerate and very anisotropic "
        "vertices. ARITHMETIC THAT DECIDES WHETHER A CASE COUNTS: a bilinear pert "
        "like 'x0*x1' has q = 1/beta_0 + 1/beta_1, so beta = (2,2) lands exactly on "
        "the excluded boundary q = 1 and the proposal is wasted. You need "
        "1/beta_0 + 1/beta_1 < 1, e.g. beta = (2,4) giving 3/4, or (4,4) giving 1/2. "
        "beta is the order along an EDGE, not along an axis, so a high power written "
        "in x0 alone does nothing unless that direction lines up with an edge. The "
        "way to raise an edge's order: take a linear form that is CONSTANT along that "
        "edge and square it, so it contributes nothing there, leaving a higher power "
        "to set the order. Worked example - for ([[-1,0],[0,-1],[1,1]], [0,0,1]) at "
        "vertex (0,1) the edge is (1,-1), along which x0+x1-1 vanishes identically, "
        "so base '-((x0+x1-1)**2 + x0**4)' has beta = 4 on that edge and 2 on the "
        "other. Vary the geometry rather than reusing one polytope. "
        "THE SHAPE THAT MATTERS MOST, and the one you are least likely to "
        "produce by accident: make two branches COMPETE. That needs beta to "
        "DIFFER between two edges AND pert to be nonzero on BOTH of them, so "
        "each edge contributes its own q = alpha_i/beta_i and the law has to "
        "pick the smallest. A pert that vanishes on an edge kills that branch "
        "and tests nothing about the selection - it leaves one q and any rule "
        "would agree. Worked example: at the origin of "
        "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1]) the edges are the axes, so "
        "base '-(x0**2 + x1**4)' has beta = (2,4), and pert 'x0 + x1' is "
        "nonzero along both, giving q = 1/2 on one edge against 1/4 on the "
        "other. Build that same competition at TILTED vertices, where beta "
        "differs because a squared linear form vanishes along one edge and not "
        "the other. Aim for a wide gap between the two q values."
    ),
    "polyhedron/ambient_exponent_law": (
        "The claim: the same selection holds with degrees measured along the "
        "COORDINATE AXES instead of the edges. This is expected to FAIL at tilted "
        "vertices, where an axis is not an edge and may point out of the polytope. "
        "Find the sharpest disagreements: geometry where the axis-measured order "
        "differs most from the edge-measured one."
    ),
    "polyhedron/linear_max_at_vertex": (
        "The claim: a linear objective attains its maximum at a vertex. This is a "
        "theorem, so it should not break - try anyway. Use `base` as the linear "
        "objective (e.g. '2*x0 - 3*x1'); `pert` is ignored but must still parse. Try "
        "flat faces, ties between vertices, and near-degenerate geometry."
    ),
}

_TEMPLATE = """You are a hostile adversarial geometer. Propose {n} distinct test cases
designed to falsify a stated law about polyhedra.

RULE: {rule_id}
{goal}

{shared}

Give each case a short snake_case "name" and a "why" of AT MOST 10 WORDS. Do not
explain your reasoning; a long "why" is truncated and wastes budget.

Output the JSON object and nothing else. No preamble, no plan, no commentary:
{{"candidates":[{{"name":"slug","system":"([[-1,0],[0,-1],[1,1]], [0,0,1])","base":"-((x0+x1-1)**2 + x0**4)","pert":"x0","why":"quartic along one edge"}}]}}
"""


def proposal_prompt(rule_id: str, n: int) -> str:
    if rule_id not in RULE_IDS:
        raise KeyError(f"unknown rule: {rule_id}")
    return _TEMPLATE.format(n=n, rule_id=rule_id, goal=_GOALS[rule_id], shared=_SHARED)


_ITEM = re.compile(r"\{[^{}]*\"system\"[^{}]*\}", re.DOTALL)
_SLUG = re.compile(r"[^A-Za-z0-9_]")


def _items(text: str) -> list[dict[str, Any]]:
    """Pull candidate objects out of a reply, salvaging a truncated one."""
    payload: Any = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return [i for i in payload["candidates"] if isinstance(i, dict)]
    out = []
    for chunk in _ITEM.findall(text):
        try:
            item = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


def parse_polyhedron_proposals(rule_id: str) -> Callable[[Any], list[dict[str, str]]]:
    """
    Build a parser for one rule.

    Does no content filtering: a payload that will not parse as a system reaches
    the adjudicator and is recorded `rejected`, rather than being dropped here
    where it would vanish from the denominator.
    """

    def parse(text: Any) -> list[dict[str, str]]:
        if not isinstance(text, str) or not text.strip():
            return []
        out: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in _items(text):
            system = str(item.get("system", "")).strip()
            base = str(item.get("base", "")).strip()
            pert = str(item.get("pert", "")).strip() or "0"
            if not system or not base:
                continue
            if max(len(system), len(base), len(pert)) > MAX_FIELD_CHARS:
                continue
            key = (system, base, pert)
            if key in seen:
                continue
            seen.add(key)
            name = _SLUG.sub("_", str(item.get("name", "")).strip())[:32]
            out.append({
                "name": name or f"proposed_{len(out)}",
                "system": system, "base": base, "pert": pert,
                "why": str(item.get("why", "")).strip()[:MAX_NOTE_CHARS],
            })
        return out

    return parse
