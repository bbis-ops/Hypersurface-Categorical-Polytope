"""An independent, exact certificate for the polyhedral face-selection theorem.

The backend admits a calculation using numerical probes where the analytic
hypotheses cannot be read off its data. For polynomial inputs, most of those
hypotheses are decidable, or at least certifiable by sufficient tests, in exact
rational arithmetic. This module re-derives the local model from the request
alone and checks each link of ``docs/FORMAL_FACE_SELECTION.md`` in order:

    standing assumptions -> simple vertex -> exact transport -> H0 ... H3
    -> faces and qualification -> H5 (upper envelope) -> selection.

Each link records the theorem clause it discharges, the method, and one of the
statuses below. Only a chain of ``exact`` links is reported as a theorem.

``exact``        proved here with rational arithmetic
``probed``       supported only by the backend's finite numerical probe
``failed``       shown false here, exactly
``unresolved``   the sufficient exact test does not decide it
``not_reached``  an earlier link failed, so the premise is missing
"""

from __future__ import annotations

import ast
import random
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations, product
from typing import Any, Mapping, Sequence

from categorical_polytope.ambient_face_compiler import (
    exact_chart_from_active_constraints,
    transport_ambient_polynomial,
)

from . import exact as X

THEOREM = "docs/FORMAL_FACE_SELECTION.md"
LINKS: dict[str, tuple[str, str, str]] = {
    "standing": ("§0 Standing assumptions", f"{THEOREM}#0-standing-assumptions",
                 "P is a bounded full-dimensional polyhedron; F and G are real analytic near v."),
    "vertex": ("§1 Setup", f"{THEOREM}#1-setup",
               "v is a simple vertex; Φ(c) = v + Σ cᵢuᵢ identifies the orthant with the tangent cone."),
    "transport": ("V.20 Feasible-chart transport", "docs/FORMAL_AMBIENT_FACE_TRANSPORT.md#statement",
                  "The Newton data are the exact pullbacks D(c) = F(v) − F(Φ(c)) and R(c) = G(Φ(c)) − G(v)."),
    "H0": ("Hypothesis 0 · global isolation", f"{THEOREM}#2-global-isolation",
           "v is the unique maximizer of F on P, so Lemma 1 localizes every perturbed maximizer."),
    "H1": ("Hypothesis 1 · strict local maximality", f"{THEOREM}#4-hypotheses-with-uniform-remainders",
           "D(c) ≥ 0 near zero, with equality only at zero."),
    "H2": ("Hypothesis 2 · diagonal principal part", f"{THEOREM}#4-hypotheses-with-uniform-remainders",
           "in_w(D) = D₀ = Σ Aᵢcᵢ^βᵢ with Aᵢ > 0, βᵢ > 1, and a uniform weighted remainder."),
    "H3": ("Hypothesis 3 · polynomial perturbation", f"{THEOREM}#4-hypotheses-with-uniform-remainders",
           "R is a finite polynomial with R(0) = 0."),
    "faces": ("§5 Faces and admissibility", f"{THEOREM}#5-faces-and-admissibility-defined-from-the-data-alone",
              "Restrict the combined R to each face; qualify its first nonzero layer if 0 < q_S < 1 and it is positive in the relative interior."),
    "H5": ("Hypothesis 5 · positive-gain envelope", f"{THEOREM}#6-upper-control-on-unqualified-faces",
           "R₊ ≤ K·D₀^q* near zero (with q* = 1 and Lemma 2 when no face qualifies)."),
    "selection": ("§8 Selection, qualified", f"{THEOREM}#8-selection-qualified",
                  "Under Hypotheses 0–5, Δ(s) = Θ(s^γ) with γ = 1/(1 − q*)."),
    "absorption": ("Lemma A · absorption by the loss", "docs/FORMAL_LOSS_ABSORPTION.md#statement",
                   "If every coefficient of D is nonnegative and each positive monomial of R is divisible by a positive "
                   "monomial of D, then s·R ≤ D near zero for small s; with Hypothesis 0, Δ(s) = 0."),
}
GRID_LIMIT = 4096


@dataclass
class LocalModel:
    """The exact local data at the selected vertex, shared with the measurement."""

    rows: list[tuple[Fraction, ...]]
    rhs: list[Fraction]
    base_tree: ast.Expression
    perturbation_tree: ast.Expression
    base: str
    perturbation: str
    vertex: tuple[Fraction, ...]
    active: tuple[int, ...]
    axes: tuple[str, ...]
    generators: dict[str, tuple[Fraction, ...]]
    rho: Fraction
    polynomial: bool
    loss: X.Polynomial = field(default_factory=dict)
    gain: X.Polynomial = field(default_factory=dict)
    base_at_vertex: Fraction | None = None
    perturbation_at_vertex: Fraction | None = None
    weights: tuple[Fraction, ...] | None = None
    principal: dict[str, tuple[int, Fraction]] = field(default_factory=dict)

    @property
    def dimension(self) -> int:
        return len(self.vertex)

    def point(self, c: Sequence[Fraction]) -> tuple[Fraction, ...]:
        return tuple(
            v + sum((ci * self.generators[axis][k] for ci, axis in zip(c, self.axes)), Fraction(0))
            for k, v in enumerate(self.vertex)
        )

    def contains(self, x: Sequence[Fraction]) -> bool:
        return all(X.dot(row, x) <= b for row, b in zip(self.rows, self.rhs))

    def describe(self) -> dict[str, Any]:
        return {
            "vertex": [X.label(v) for v in self.vertex],
            "active_constraints": list(self.active),
            "edge_axes": list(self.axes),
            "generators": {a: [X.label(u) for u in self.generators[a]] for a in self.axes},
            "released_by_axis": {a: self.active[i] for i, a in enumerate(self.axes)},
            "local_box_radius": X.label(self.rho),
            "loss": X.poly_text(self.loss, self.axes) if self.polynomial else None,
            "gain": X.poly_text(self.gain, self.axes) if self.polynomial else None,
            "weights": None if self.weights is None else dict(zip(self.axes, map(X.label, self.weights))),
        }


def parse_system(system: str) -> tuple[list[tuple[Fraction, ...]], list[Fraction]]:
    raw = ast.literal_eval(system) if isinstance(system, str) else system
    rows_raw, rhs_raw = raw
    rows = [tuple(X.to_fraction(a) for a in row) for row in rows_raw]
    rhs = [X.to_fraction(b) for b in rhs_raw]
    if not rows or len(rows) != len(rhs) or len({len(r) for r in rows}) != 1:
        raise ValueError("system must be ([[...] * m], [... m values]) with equal row lengths")
    return rows, rhs


class _Ledger:
    def __init__(self) -> None:
        self.links: list[dict[str, Any]] = []

    def add(self, key: str, status: str, method: str, detail: str, **values: Any) -> dict[str, Any]:
        clause, doc, statement = LINKS[key]
        link = {"id": key, "clause": clause, "doc": doc, "statement": statement,
                "status": status, "method": method, "detail": detail}
        if values:
            link["values"] = values
        self.links.append(link)
        return link

    def status(self, key: str) -> str | None:
        return next((l["status"] for l in self.links if l["id"] == key), None)


def _bounded(rows: Sequence[Sequence[Fraction]]) -> bool | None:
    """Exact recession test: bounded iff no d != 0 with A·d <= 0."""
    n = len(rows[0])
    try:
        for i, sign in product(range(n), (1, -1)):
            unit = [Fraction(0)] * n
            unit[i] = Fraction(-sign)  # -sign*d_i <= -1, i.e. sign*d_i >= 1
            if X.feasible(list(rows) + [tuple(unit)], [Fraction(0)] * len(rows) + [Fraction(-1)]):
                return False
    except X.FeasibilityUndecided:
        return None
    return True


def _box_radius(rows, rhs, vertex, active, generators, axes) -> Fraction:
    """Largest rho <= 1 with Φ([0, rho]^n) inside P (exact)."""
    rho = Fraction(1)
    for j, (row, bound) in enumerate(zip(rows, rhs)):
        if j in active:
            continue
        slack = bound - X.dot(row, vertex)
        growth = sum((max(Fraction(0), X.dot(row, generators[a])) for a in axes), Fraction(0))
        if growth > 0:
            rho = min(rho, slack / growth)
    return rho


def _grid_points(dimension: int, degree: int, seed: str) -> tuple[list[tuple[Fraction, ...]], str]:
    if (degree + 1) ** dimension <= GRID_LIMIT:
        values = [Fraction(k) for k in range(degree + 1)]
        return [tuple(p) for p in product(values, repeat=dimension)], "proof"
    rng = random.Random(seed)
    points = [tuple(Fraction(rng.randint(-10**6, 10**6), rng.randint(1, 10**6)) for _ in range(dimension))
              for _ in range(256)]
    return points, "random"


def _transport(model: LocalModel, expression: str, tree: ast.Expression, degree: int):
    """Pull back through the repository's compiler, then prove the identity here.

    The compiler returns the centered pullback H(Φ(c)) − H(v) (V.20), so the
    value at the vertex is evaluated here, exactly and independently.
    """
    transported = transport_ambient_polynomial(expression, model.vertex, model.generators)
    zero = (0,) * model.dimension
    polynomial = {s: c for s, c in transported.polynomial.items() if c != 0 and s != zero}
    constant = X.evaluate_exact(tree, model.vertex)
    points, kind = _grid_points(model.dimension, degree, expression)
    for c in points:
        if X.evaluate_exact(tree, model.point(c)) != constant + X.poly_evaluate(polynomial, c):
            return constant, polynomial, False, kind, len(points)
    return constant, polynomial, True, kind, len(points)


def _initial_layer(polynomial: Mapping[X.Signature, Fraction], weights: Sequence[Fraction]):
    degrees = {s: X.weighted_degree(s, weights) for s in polynomial}
    q = min(degrees.values())
    return q, {s: c for s, c in polynomial.items() if degrees[s] == q}


def _witness(initial: Mapping[X.Signature, Fraction], face: Sequence[int], n: int, extra=()) -> tuple | None:
    """A rational relative-interior point where the initial form is positive."""
    candidates = [tuple(Fraction(1) if i in face else Fraction(0) for i in range(n))]
    grid = [Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)]
    if len(face) <= 4:
        for values in product(grid, repeat=len(face)):
            point = [Fraction(0)] * n
            for i, v in zip(face, values):
                point[i] = v
            candidates.append(tuple(point))
    candidates.extend(extra)
    for point in candidates:
        if all(point[i] > 0 for i in face) and X.poly_evaluate(initial, point) > 0:
            return point
    return None


def _backend_witnesses(response: Mapping[str, Any], axes: Sequence[str]) -> dict[tuple[int, ...], list[tuple]]:
    found: dict[tuple[int, ...], list[tuple]] = {}
    for item in (response.get("exact_refinement") or {}).get("positivity_certificates") or []:
        try:
            point = tuple(X.to_fraction(item["coordinates"].get(a, 0.0)) for a in axes)
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
        found.setdefault(tuple(item.get("face") or ()), []).append(point)
    return found


def _faces(model: LocalModel, response: Mapping[str, Any]):
    n, weights = model.dimension, model.weights
    backend_points = _backend_witnesses(response, model.axes)
    table = []
    for size in range(1, n + 1):
        for face in combinations(range(n), size):
            restricted = {s: c for s, c in model.gain.items()
                          if all(s[i] == 0 for i in range(n) if i not in face)}
            entry: dict[str, Any] = {"face": [model.axes[i] for i in face], "edges": list(face)}
            if not restricted:
                entry.update(status="inactive", reason="the perturbation vanishes on this face")
                table.append(entry)
                continue
            q, initial = _initial_layer(restricted, weights)
            entry.update(degree=X.label(q), initial_form=X.poly_text(initial, model.axes))
            signs = {c > 0 for c in initial.values()}
            if q >= 1:
                entry.update(status="critical" if q == 1 else "subleading",
                             reason="q_S = 1 needs a different balance" if q == 1 else "q_S > 1: dominated by the base")
            elif signs == {False}:
                entry.update(status="non_positive", reason="every initial coefficient is negative")
            else:
                point = _witness(initial, face, n, backend_points.get(face, ()))
                if point is None:
                    entry.update(status="unresolved", reason="mixed signs and no rational witness found")
                else:
                    entry.update(status="qualified", witness=[X.label(p) for p in point],
                                 witness_value=X.label(X.poly_evaluate(initial, point)),
                                 reason="0 < q_S < 1 with an exact positive relative-interior witness")
            entry["_q"] = q
            table.append(entry)
    qualified = [e for e in table if e["status"] == "qualified"]
    q_star = min((e["_q"] for e in qualified), default=None)
    for e in table:
        e["winning"] = q_star is not None and e["status"] == "qualified" and e["_q"] == q_star
    return table, q_star


def _envelope(model: LocalModel, cutoff: Fraction) -> tuple[bool, list[str], list[str]]:
    """Sufficient exact test for R₊ ≤ K·D₀^cutoff near the vertex.

    A positive monomial of weighted degree >= cutoff is bounded by the base on
    its compact normalized section. One below the cutoff is absorbed when a
    negative monomial divides it componentwise: -b·N + a·N·m = -N(b - a·m) <= 0
    near zero because m has positive degree.
    """
    negatives = [s for s, c in model.gain.items() if c < 0]
    uncontrolled, absorbed = [], []
    for signature, coefficient in sorted(model.gain.items()):
        if coefficient <= 0 or X.weighted_degree(signature, model.weights) >= cutoff:
            continue
        divisor = next((n for n in negatives if X.divides(n, signature)), None)
        text = X.monomial_text(signature, model.axes)
        degree = X.label(X.weighted_degree(signature, model.weights))
        if divisor is None:
            uncontrolled.append(f"{text} (degree {degree})")
        else:
            absorbed.append(f"{text} by −{X.monomial_text(divisor, model.axes)}")
    return not uncontrolled, uncontrolled, absorbed


def _backend_selection(response: Mapping[str, Any]) -> dict[str, Any]:
    """The backend's own selection, read through its exact labels where it has them."""
    refinement = response.get("exact_refinement") or {}
    label = (response.get("universality_class") or {}).get("weighted_degree_label")
    if label:
        return {"q_star": Fraction(label), "source": "universality class (exact label)",
                "faces": refinement.get("supporting_faces") if refinement.get("status") == "applied"
                else (response.get("selection") or {}).get("winning_faces")}
    if refinement.get("weighted_degree") is not None:
        value = Fraction(repr(float(refinement["weighted_degree"]))).limit_denominator(10**6)
        return {"q_star": value, "source": f"exact layer, not applied ({refinement.get('status')})",
                "faces": refinement.get("supporting_faces")}
    return {"q_star": None, "source": "no backend selection", "faces": None}


def _minimal(faces: list[list[int]]) -> list[list[int]]:
    return sorted(f for f in faces if not any(set(g) < set(f) for g in faces))


def _absorption(model: LocalModel) -> tuple[bool, list[str], Fraction | None]:
    """Lemma A: can the loss absorb every positive term of the gain?

    Needs every coefficient of D nonnegative and, for each positive monomial c^α
    of R, a positive monomial c^β of D with β ≤ α. On [0, min(ρ, 1)]ⁿ then
    c^α ≤ c^β, so s·R ≤ D once s ≤ s₀ = min over β of d_β / (the coefficients
    of R assigned to β). Returns the assignments and s₀ (None when R has no
    positive monomial, where any s > 0 works).
    """
    if not model.polynomial or not model.loss or any(c < 0 for c in model.loss.values()):
        return False, [], None
    divisors = sorted((beta, d) for beta, d in model.loss.items() if d > 0)
    demand: dict[tuple[int, ...], Fraction] = {}
    pairs = []
    for alpha, r in sorted(model.gain.items()):
        if r <= 0:
            continue
        options = [(beta, d) for beta, d in divisors if all(b <= a for b, a in zip(beta, alpha))]
        if not options:
            return False, [], None
        beta, _ = max(options, key=lambda o: (o[1], tuple(-x for x in o[0])))  # largest coefficient, then least exponent
        demand[beta] = demand.get(beta, Fraction(0)) + r
        pairs.append(f"{X.monomial_text(alpha, model.axes)} by {X.monomial_text(beta, model.axes)}")
    if not demand:
        return True, [], None
    weight = dict(divisors)
    return True, pairs, min(weight[beta] / total for beta, total in demand.items())


def certify(request: Mapping[str, Any], response: Mapping[str, Any]) -> tuple[dict[str, Any], LocalModel | None]:
    """Return the certificate and, when a simple vertex was found, its local model."""
    ledger = _Ledger()
    result: dict[str, Any] = {"status": "not_applicable", "conclusion": None, "links": ledger.links}
    try:
        rows, rhs = parse_system(request["system"])
        n = len(rows[0])
        base_tree = X.parse(request["base"], n)
        pert_tree = X.parse(request.get("perturbation", request.get("pert")), n)
    except (KeyError, ValueError, SyntaxError, TypeError, X.UnsafeExpression) as exc:
        result["reason"] = f"input is outside the exact checker: {exc}"
        return result, None

    base_degree, pert_degree = X.total_degree(base_tree), X.total_degree(pert_tree)
    polynomial = base_degree is not None and pert_degree is not None
    bounded = _bounded(rows)
    corners = X.vertices(rows, rhs)
    if bounded is False:
        ledger.add("standing", "failed", "exact Fourier–Motzkin recession test",
                   "P is unbounded: some direction d ≠ 0 has A·d ≤ 0.")
        result["status"] = "incomplete"
        return result, None
    if not corners:
        ledger.add("standing", "failed" if corners == [] else "unresolved", "exact vertex enumeration",
                   "P has no vertices." if corners == [] else "too many constraints to enumerate vertices exactly.")
        result["status"] = "incomplete"
        return result, None

    # Choose the base maximizer among the vertices: exactly when F is rational.
    try:
        values = [X.evaluate_exact(base_tree, corner) for corner in corners]
        exact_values = True
    except (X.NotExact, ZeroDivisionError):
        values = [X.evaluate_float(base_tree, [float(x) for x in corner]) for corner in corners]
        exact_values = False
    best = max(values)
    best_corners = [corner for corner, value in zip(corners, values) if value == best]
    backend_vertex = (response.get("localization") or {}).get("vertex") or []
    vertex = best_corners[0]
    if len(best_corners) > 1 and backend_vertex:
        vertex = min(best_corners, key=lambda c: sum((float(a) - b) ** 2 for a, b in zip(c, backend_vertex)))
    active = tuple(j for j, (row, b) in enumerate(zip(rows, rhs)) if X.dot(row, vertex) == b)

    if len(active) != n:
        ledger.add("standing", "exact" if bounded else "unresolved", "exact recession test and vertex enumeration",
                   f"P is bounded with {len(corners)} vertices.")
        ledger.add("vertex", "failed", "exact active-set count",
                   f"The best vertex {[X.label(v) for v in vertex]} has {len(active)} active constraints in dimension {n}: "
                   "its tangent cone is not simplicial, which the theorem excludes.", active=list(active))
        result["status"] = "incomplete"
        return result, None

    vertex_exact, generators = exact_chart_from_active_constraints(rows, rhs, active)
    axes = tuple(generators)
    active_matrix = [rows[j] for j in active]
    chart_ok = tuple(vertex_exact) == tuple(vertex) and all(
        X.dot(active_matrix[r], generators[a]) == (-1 if r == k else 0)
        for k, a in enumerate(axes) for r in range(n)
    )
    rho = _box_radius(rows, rhs, vertex, active, generators, axes)
    interior = tuple(v + (rho / 2) * sum((generators[a][k] for a in axes), Fraction(0)) for k, v in enumerate(vertex))
    full_dimensional = all(X.dot(row, interior) < b for row, b in zip(rows, rhs))
    model = LocalModel(rows, rhs, base_tree, pert_tree, request["base"],
                       request.get("perturbation", request.get("pert")), tuple(vertex), active, axes,
                       {a: tuple(generators[a]) for a in axes}, rho, polynomial)
    result["model"] = model.describe()

    standing_ok = bool(bounded) and full_dimensional and polynomial
    ledger.add(
        "standing", "exact" if standing_ok else ("failed" if not full_dimensional else "unresolved"),
        "exact recession test, interior point, polynomial degree",
        ("P is bounded and full-dimensional; F and G are polynomials (degrees "
         f"{base_degree} and {pert_degree}), hence analytic.") if standing_ok else
        ("P has empty interior." if not full_dimensional else
         "F or G is not a polynomial, so analyticity and exact transport are not checked here."),
        vertices=len(corners), interior_point=[X.label(x) for x in interior],
    )
    ledger.add("vertex", "exact" if chart_ok else "failed", "exact active-constraint solve A_S·v = b_S, A_S·uᵢ = −eᵢ",
               f"v = ({', '.join(X.label(x) for x in vertex)}) with active constraints {list(active)}; "
               f"Φ([0, {X.label(rho)}]ⁿ) ⊂ P." if chart_ok else "The repository chart does not solve the active system.",
               vertex=[X.label(x) for x in vertex], active=list(active))
    if backend_vertex and any(abs(float(a) - b) > 1e-9 for a, b in zip(vertex, backend_vertex)):
        result["vertex_disagreement"] = {"exact": [X.label(x) for x in vertex], "backend": backend_vertex}

    if not polynomial:
        for key in ("transport", "H0", "H1", "H2", "H3", "faces", "H5", "selection"):
            ledger.add(key, "not_reached", "—", "Exact checks need polynomial F and G.")
        result["status"] = "incomplete"
        return result, model

    # Exact transport, proved by agreement on a (degree + 1)^n grid.
    fv, loss_raw, base_ok, kind_b, count_b = _transport(model, model.base, base_tree, base_degree)
    gv, gain, pert_ok, kind_p, count_p = _transport(model, model.perturbation, pert_tree, pert_degree)
    model.base_at_vertex, model.perturbation_at_vertex = fv, gv
    model.loss = {s: -c for s, c in loss_raw.items()}
    model.gain = gain
    proof = kind_b == kind_p == "proof"
    ledger.add("transport", "exact" if base_ok and pert_ok and proof else ("failed" if not (base_ok and pert_ok) else "unresolved"),
               "repository compiler, re-verified by exact evaluation on a product grid",
               f"D(c) = {X.poly_text(model.loss, axes)}, R(c) = {X.poly_text(gain, axes)}; identity checked at "
               f"{count_b} and {count_p} grid points" + (" (a polynomial proof)." if proof else " (random points only)."),
               loss=X.poly_text(model.loss, axes), gain=X.poly_text(gain, axes))

    # H2 first: its exact form also discharges H1.
    orders, coefficients, h2_problem, h1_problem = {}, {}, None, None
    for i, axis in enumerate(axes):
        pure = [(s[i], c) for s, c in model.loss.items() if s[i] and sum(s) == s[i]]
        if not pure:
            h1_problem = f"D has no pure term along {axis}: F is constant on that edge to every order."
            break
        beta, coefficient = min(pure)
        orders[axis], coefficients[axis] = beta, coefficient
        if coefficient < 0:
            h1_problem = f"F increases along {axis} (leading coefficient {X.label(-coefficient)} > 0 in F)."
            break
        if beta == 1:
            h2_problem = f"β = 1 along {axis}: the base decays linearly, but the theorem needs βᵢ > 1."
    if h1_problem is None:
        model.principal = {a: (orders[a], coefficients[a]) for a in axes}
    if h1_problem is None and h2_problem is None:
        weights = tuple(Fraction(1, orders[a]) for a in axes)
        model.weights = weights
        principal = {tuple(orders[a] if j == i else 0 for j in range(n)) for i, a in enumerate(axes)}
        low = [s for s in model.loss if s not in principal and X.weighted_degree(s, weights) <= 1]
        if low:
            texts = ", ".join(f"{X.monomial_text(s, axes)} (weight {X.label(X.weighted_degree(s, weights))})" for s in low)
            h2_problem = f"in_w(D) is not diagonal: {texts} sits at or below the principal weight 1."
    if h1_problem:
        ledger.add("H2", "not_reached", "exact Newton data of D", h1_problem)
        ledger.add("H1", "failed", "exact Newton data of D", h1_problem)
    else:
        d0 = " + ".join(f"{X.label(coefficients[a]) + '·' if coefficients[a] != 1 else ''}{a}^{orders[a]}" for a in axes)
        ledger.add("H2", "failed" if h2_problem else "exact", "exact weighted Newton polygon of D",
                   h2_problem or f"D₀ = {d0}; every other monomial of D has weighted degree > 1, so the "
                   "remainder is uniform on compact sets.", orders=orders)
        ledger.add("H1", "exact" if not h2_problem else "unresolved", "implied by the exact H2",
                   "D ≥ a·D₀ > 0 near zero on the cone, by compactness of the section D₀ = 1."
                   if not h2_problem else "Not implied without H2; the backend probe is the only evidence.")

    # H0: two exact routes, else the backend's probe.
    tie = len(best_corners) > 1
    positive_loss = (not h1_problem) and all(c >= 0 for c in model.loss.values())
    shape = X.curvature(base_tree)
    if tie:
        ledger.add("H0", "failed", "exact vertex comparison",
                   f"F attains its maximum {X.label(best) if exact_values else best} at {len(best_corners)} vertices.")
    elif positive_loss:
        ledger.add("H0", "exact", "global positivity of the base loss",
                   "Every coefficient of D is nonnegative and each edge carries a positive pure term, so D > 0 on the "
                   "whole cone minus 0; since P ⊂ v + T_vP, F(x) < F(v) for every x ∈ P other than v.")
    elif shape in {"concave", "affine"} and ledger.status("H1") == "exact":
        ledger.add("H0", "exact", "concavity certificate plus strict local maximality",
                   f"F is {shape} by structural rules; a strict local maximum of a concave function on a convex set is "
                   "its unique global maximum.")
    else:
        hypotheses = (response.get("scope") or {}).get("hypotheses") or {}
        isolated = hypotheses.get("isolated_maximizer")
        ledger.add("H0", "probed" if isolated else "unresolved", "backend isolation probe (numerical)",
                   f"No exact certificate; the backend probe reports isolated_maximizer={isolated} with margin "
                   f"{hypotheses.get('isolation_margin')}. A finite probe cannot prove uniqueness.")

    ledger.add("H3", "exact", "exact pullback",
               f"R(c) = {X.poly_text(gain, axes)} is a finite polynomial with R(0) = 0." if gain else
               "R ≡ 0 near v: the perturbation is constant there, so Δ(s) = 0.")

    def conclude_by_absorption() -> bool:
        """Lemma A decides zero response where the face law cannot (Hypothesis 2 may fail)."""
        if any(ledger.status(key) != "exact" for key in ("standing", "vertex", "transport", "H0", "H3")):
            return False
        ok, pairs, s0 = _absorption(model)
        if not ok:
            return False
        ledger.add("absorption", "exact", "monomial division by a nonnegative loss",
                   (f"Every positive monomial of R is divisible by a positive monomial of D ({'; '.join(pairs)}), "
                    if pairs else "R has no positive monomial, ") +
                   "and every coefficient of D is nonnegative, so s·R ≤ D on [0, min(ρ, 1)]ⁿ" +
                   (f" for 0 < s ≤ {X.label(s0)}" if s0 is not None else " for every s > 0") +
                   "; with Hypothesis 0, Δ(s) = 0 for all sufficiently small s > 0.",
                   pairs=pairs, s0=X.label(s0))
        result.pop("open_links", None)
        result.update(status="zero_response", conclusion="Δ(s) = 0 for all sufficiently small s > 0", q_star=None, gamma=None)
        return True

    if model.weights is None:
        for key in ("faces", "H5", "selection"):
            ledger.add(key, "not_reached", "—", "Face weights need the exact principal part (H1/H2).")
        result["status"] = "incomplete"
        conclude_by_absorption()
        return result, model

    if not gain:
        ledger.add("faces", "exact", "exact face restriction", "Every face is inactive.")
        ledger.add("H5", "exact", "trivial", "R ≡ 0.")
        ledger.add("selection", "exact", "trivial", "Δ(s) = 0 for every s ≥ 0.")
        result.update(status="zero_response", conclusion="Δ(s) = 0 for every s ≥ 0", q_star=None, gamma=None)
        return result, model

    table, q_star = _faces(model, response)
    public_table = [{k: v for k, v in e.items() if k != "_q"} for e in table]
    counts: dict[str, int] = {}
    for e in table:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    unresolved_faces = [e for e in table if e["status"] == "unresolved"]
    ledger.add("faces", "unresolved" if unresolved_faces else "exact", "exact face restriction and rational witnesses",
               (f"q* = {X.label(q_star)} on {sum(e['winning'] for e in table)} face(s); " if q_star is not None
                else "No face qualifies; ") + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) + ".",
               faces=public_table)

    cutoff = q_star if q_star is not None else Fraction(1)
    envelope_ok, uncontrolled, absorbed = _envelope(model, cutoff)
    ledger.add("H5", "exact" if envelope_ok else "unresolved", "monomial domination and absorption (sufficient test)",
               (f"Every positive monomial has weighted degree ≥ {X.label(cutoff)}" +
                (f" or is absorbed ({'; '.join(absorbed)})" if absorbed else "") + ".") if envelope_ok else
               f"Positive terms below {X.label(cutoff)} are not controlled: {', '.join(uncontrolled)}. A curved approach "
               "can open a channel that no coordinate face sees.", uncontrolled=uncontrolled, absorbed=absorbed)

    backend = _backend_selection(response)
    ours = _minimal([e["edges"] for e in table if e["winning"]])
    agreement: dict[str, Any] = {
        "backend_q_star": X.label(backend["q_star"]), "backend_source": backend["source"],
        "exact_q_star": X.label(q_star),
        "backend_winning_faces": backend["faces"], "exact_minimal_winning_faces": ours,
    }
    # Only a licensed backend answer is a selection; otherwise its degree is a diagnostic.
    if response.get("status") == "licensed":
        agreement["q_star"] = backend["q_star"] == q_star
        if backend["faces"] and q_star is not None:
            agreement["winning_faces"] = sorted(map(list, backend["faces"])) == ours
    result["agreement"] = agreement

    required = ("standing", "vertex", "transport", "H0", "H1", "H2", "H3", "faces", "H5")
    open_links = [key for key in required if ledger.status(key) != "exact"]
    if q_star is not None and not open_links:
        gamma = 1 / (1 - q_star)
        ledger.add("selection", "exact", "Hypotheses 0–5 discharged exactly",
                   f"q* = {X.label(q_star)}, so Δ(s) = Θ(s^{X.label(gamma)}).", q_star=X.label(q_star), gamma=X.label(gamma))
        result.update(status="theorem", conclusion=f"Δ(s) = Θ(s^{X.label(gamma)})", q_star=X.label(q_star), gamma=X.label(gamma))
    elif q_star is None and not open_links:
        ledger.add("selection", "exact", "Lemma 2 with R₊ ≤ K·D₀",
                   "No face qualifies and the positive part is dominated by the base: Δ(s) = 0 for all small s > 0.")
        result.update(status="zero_response", conclusion="Δ(s) = 0 for all sufficiently small s > 0", q_star=None, gamma=None)
    else:
        ledger.add("selection", "unresolved" if q_star is not None else "not_reached",
                   "conditional on the open links",
                   (f"The exact face data give q* = {X.label(q_star)} and γ = {X.label(1 / (1 - q_star))}, but "
                    if q_star is not None else "No qualified face; ") + f"open links: {', '.join(open_links)}.",
                   open_links=open_links)
        result.update(status="incomplete", conclusion=None, open_links=open_links,
                      q_star=X.label(q_star), gamma=X.label(1 / (1 - q_star)) if q_star is not None else None)
        conclude_by_absorption()
    return result, model
