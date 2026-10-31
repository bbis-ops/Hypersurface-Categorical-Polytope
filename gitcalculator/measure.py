"""Independent evidence: certified lower bounds on the response Δ(s).

For each perturbation size s, a floating search in logarithmic edge
coordinates looks for a good point c of the local chart. The point is then
rounded to a short decimal, mapped to x = Φ(c), verified to lie in P, and the
gain F(x) − F(v) + s·(G(x) − G(v)) is evaluated in exact rational arithmetic
directly from the user's expressions. Any feasible point gives a lower bound,
so every reported value is a proved inequality Δ(s) ≥ L(s), rounded down.

The search only steers; it certifies nothing. A weak search can make L small,
never too large, so lower bounds that outgrow a predicted s^γ are genuine
evidence against that prediction at the tested scales, while bounds that fall
short of it are inconclusive.
"""

from __future__ import annotations

import math
from fractions import Fraction
from itertools import combinations
from typing import Any, Callable, Sequence

from . import exact as X
from .certify import LocalModel

BUDGETS = {
    "quick": {"steps": 12, "need": 6, "starts": 2, "iterations": 80},
    "standard": {"steps": 17, "need": 7, "starts": 3, "iterations": 140},
}
DECADES = 16.0
GRID_STEP = {1: 0.25, 2: 0.8, 3: 1.6, 4: 2.67}
MAX_DIMENSION = 4


def floor_decimal(x: Fraction, digits: int = 12) -> str:
    """A short decimal spelling that is never larger than ``x``."""
    if x <= 0:
        return "0"
    e = len(str(x.numerator)) - len(str(x.denominator))
    while Fraction(10) ** e > x:
        e -= 1
    while Fraction(10) ** (e + 1) <= x:
        e += 1
    mantissa = str(math.floor(x * Fraction(10) ** (digits - 1 - e)))
    return f"{mantissa[0]}.{mantissa[1:]}e{e:+d}"


def _log10(decimal: str) -> float:
    mantissa, exponent = decimal.split("e")
    return math.log10(float(mantissa)) + int(exponent)


def _nelder_mead(f: Callable[[list[float]], float], start: Sequence[float], step: float, iterations: int):
    """Minimize ``f`` from ``start`` (standard coefficients 1, 2, 1/2, 1/2)."""
    n = len(start)
    simplex = [list(start)] + [[start[j] + (step if j == i else 0.0) for j in range(n)] for i in range(n)]
    values = [f(p) for p in simplex]
    for _ in range(iterations):
        order = sorted(range(n + 1), key=values.__getitem__)
        simplex, values = [simplex[i] for i in order], [values[i] for i in order]
        if max(abs(a - b) for p in simplex[1:] for a, b in zip(p, simplex[0])) < 1e-7:
            break
        centroid = [sum(p[j] for p in simplex[:-1]) / n for j in range(n)]
        worst = simplex[-1]
        reflected = [c + (c - w) for c, w in zip(centroid, worst)]
        fr = f(reflected)
        if fr < values[0]:
            expanded = [c + 2 * (c - w) for c, w in zip(centroid, worst)]
            fe = f(expanded)
            simplex[-1], values[-1] = (expanded, fe) if fe < fr else (reflected, fr)
        elif fr < values[-2]:
            simplex[-1], values[-1] = reflected, fr
        else:
            towards = worst if fr >= values[-1] else reflected
            contracted = [c + 0.5 * (t - c) for c, t in zip(centroid, towards)]
            fc = f(contracted)
            if fc < min(fr, values[-1]):
                simplex[-1], values[-1] = contracted, fc
            else:
                best = simplex[0]
                simplex = [best] + [[b + 0.5 * (q - b) for b, q in zip(best, p)] for p in simplex[1:]]
                values = [values[0]] + [f(p) for p in simplex[1:]]
    i = min(range(n + 1), key=values.__getitem__)
    return simplex[i], values[i]


class _Search:
    def __init__(self, model: LocalModel, budget: dict[str, int]):
        self.n = model.dimension
        self.rho = float(model.rho)
        self.loss = X.poly_float(model.loss)
        self.gain = X.poly_float(model.gain)
        self.budget = budget
        self.faces = [f for k in range(1, self.n + 1) for f in combinations(range(self.n), k)]
        self.champions: list[tuple[float, list[float]]] = []

    def _point(self, face, u) -> list[float]:
        c = [0.0] * self.n
        for i, ui in zip(face, u):
            c[i] = self.rho * 10.0 ** (-min(DECADES, max(0.0, ui)))
        return c

    def _continuations(self, s: float) -> list[list[float]]:
        """Earlier champions and their geometric extrapolation along the optimizer path.

        Optimal coordinates follow power laws c_i ~ A_i·s^(a_i) for small s, so
        log c_i is affine in log s and two champions predict the next one,
        even along a narrow curved ridge.
        """
        points = [c for _, c in self.champions[-2:]]
        if len(self.champions) >= 2:
            (s1, c1), (s2, c2) = self.champions[-2:]
            r = math.log(s / s2) / math.log(s2 / s1)
            points.append([min(self.rho, b * (b / a) ** r) if a > 0 and b > 0 else 0.0 for a, b in zip(c1, c2)])
        return points

    def best(self, s: float) -> list[float]:
        champion, champion_value = [0.0] * self.n, 0.0
        continuations = self._continuations(s)
        for face in self.faces:
            def objective(u, face=face):
                c = self._point(face, u)
                return X.poly_float_evaluate(self.loss, c) - s * X.poly_float_evaluate(self.gain, c)
            step = GRID_STEP[len(face)]
            axis = [k * step for k in range(int(DECADES / step) + 1)]
            grid = [[a] for a in axis]
            for _ in range(len(face) - 1):
                grid = [g + [a] for g in grid for a in axis]
            scored = sorted((objective(u), u) for u in grid)[: self.budget["starts"]]
            starts = [u for _, u in scored] + [
                [math.log10(self.rho / c[i]) for i in face] for c in continuations
                if all((c[i] > 0) == (i in face) for i in range(self.n))
            ]
            for start in starts:
                u, value = _nelder_mead(objective, start, 1.0, self.budget["iterations"] * len(face))
                if -value > champion_value:
                    champion, champion_value = self._point(face, u), -value
        champion = self._prune(champion, s)
        if champion_value > 0:
            self.champions.append((s, champion))
        return champion

    def _prune(self, c: list[float], s: float) -> list[float]:
        """Zero coordinates whose removal does not lower the gain (numerical dust)."""
        def gain(point):
            return s * X.poly_float_evaluate(self.gain, point) - X.poly_float_evaluate(self.loss, point)
        best = gain(c)
        for i in sorted(range(self.n), key=lambda i: c[i]):
            if c[i] > 0:
                trial = c[:i] + [0.0] + c[i + 1:]
                value = gain(trial)
                if value >= best - 1e-9 * abs(best):
                    c, best = trial, max(best, value)
        return c


def _certify_point(model: LocalModel, c_float: Sequence[float], s: Fraction) -> dict[str, Any]:
    c = [min(model.rho, Fraction(f"{ci:.12e}")) if ci > 0 else Fraction(0) for ci in c_float]
    x = model.point(c)
    feasible = model.contains(x)
    gain = (X.evaluate_exact(model.base_tree, x) - model.base_at_vertex
            + s * (X.evaluate_exact(model.perturbation_tree, x) - model.perturbation_at_vertex))
    chart_gain = -X.poly_evaluate(model.loss, c) + s * X.poly_evaluate(model.gain, c)
    lower = gain if feasible and gain > 0 else Fraction(0)
    return {
        "s": floor_decimal(s, 6) if s.denominator != 1 else str(s),
        "lower_bound": floor_decimal(lower),
        "witness_c": [floor_decimal(v) if v else "0" for v in c],
        "support": [a for a, v in zip(model.axes, c) if v > 0],
        "feasible": feasible,
        "pullback_consistent": gain == chart_gain,
        "interior": max(c) <= model.rho / 4,
    }


def _slopes(series: list[dict[str, Any]]) -> tuple[list[tuple[float, float]], float | None]:
    """log10 points and the median of the last three local log-log slopes."""
    points = [(math.log10(float(p["s_value"])), _log10(p["lower_bound"])) for p in series]
    slopes = [(b2 - b1) / (a2 - a1) for (a1, b1), (a2, b2) in zip(points, points[1:])]
    tail = sorted(slopes[-3:])
    return points, (tail[len(tail) // 2] if tail else None)


def _usable(row: dict[str, Any]) -> bool:
    """Every positive certified bound is evidence, interior or not."""
    return row["lower_bound"] != "0"


def _verdict(series: list[dict[str, Any]], prediction: dict[str, Any]) -> dict[str, Any]:
    gamma = prediction.get("gamma")
    points, measured = _slopes(series)
    out: dict[str, Any] = {"id": prediction["id"], "label": prediction.get("label"),
                           "gamma": X.label(gamma) if isinstance(gamma, Fraction) else gamma}
    if gamma is None or measured is None or len(series) < 3:
        out["verdict"] = "insufficient"
        return out
    g = float(gamma)
    tolerance = max(0.15, 0.1 * g)
    ratios = [b - g * a for a, b in points]  # log10 of L(s)/s^gamma
    tail = ratios[-4:]
    growth = tail[-1] - tail[0]
    rising = all(later > earlier for earlier, later in zip(tail, tail[1:]))
    if measured < g - tolerance and rising and growth >= 0.2:
        verdict = "contradicted"
        detail = (f"certified lower bounds grow like s^{measured:.3g}, faster than s^{out['gamma']}: "
                  f"L(s)/s^γ rises by a factor of 10^{growth:.1f} as s decreases")
    elif abs(measured - g) <= tolerance:
        verdict, detail = "consistent", f"local slopes approach {measured:.3f} (prediction {g:.3f})"
    else:
        verdict = "inconclusive"
        detail = (f"lower bounds decay like s^{measured:.3g}; a lower bound below the predicted order "
                  "may only mean the search missed the optimum") if measured > g else (
                  f"slopes near {measured:.3f} but the ratio to s^γ has not separated yet")
    out.update(verdict=verdict, detail=detail, ratio_growth_decades=round(growth, 3))
    coefficient = prediction.get("coefficient")
    if coefficient:
        out["coefficient_ratio"] = round(10 ** ratios[-1] / float(coefficient), 6)
    return out


def measure(model: LocalModel | None, predictions: Sequence[dict[str, Any]] = (), *, budget: str = "standard") -> dict[str, Any]:
    """Certified lower bounds Δ(s) ≥ L(s) and a verdict for each prediction."""
    if model is None or not model.polynomial or model.base_at_vertex is None:
        return {"status": "not_available", "reason": "certified bounds need a simple vertex and polynomial F and G"}
    if model.dimension > MAX_DIMENSION:
        return {"status": "not_available", "reason": f"the search supports dimension ≤ {MAX_DIMENSION}"}
    if not model.gain:
        return {"status": "complete", "series": [], "verdicts": [], "summary": "R ≡ 0 near v: no gain at any s"}
    settings = BUDGETS[budget]
    search = _Search(model, settings)
    rows: list[dict[str, Any]] = []
    for k in range(settings["steps"]):
        s = Fraction(f"{10 ** (-k / 2):.6e}")
        row = _certify_point(model, search.best(float(s)), s)
        row["s_value"] = str(float(s))
        rows.append(row)
        if len(rows) >= settings["need"] and all(_usable(r) for r in rows[-settings["need"]:]):
            break
    # The asymptotic evidence is the trailing run of interior points with positive bounds.
    series: list[dict[str, Any]] = []
    for row in reversed(rows):
        if not _usable(row):
            if series:
                break
            continue
        series.insert(0, row)
    verdicts = [_verdict(series, p) for p in predictions]
    smallest = series[-1] if series else (rows[-1] if rows else None)
    found = any(r["lower_bound"] != "0" for r in rows)
    measured = _slopes(series)[1] if len(series) >= 2 else None
    if measured is not None:
        measured = round(measured, 4)
    return {
        "status": "complete",
        "method": "log-coordinate face search; witnesses certified by exact rational evaluation in P",
        "budget": budget,
        "rows": rows,
        "series_length": len(series),
        "measured_exponent": measured,
        "positive_gain_found": found,
        "support_at_smallest_s": smallest["support"] if smallest else [],
        "boundary_dominated": bool(smallest) and not smallest["interior"],
        "all_witnesses_feasible": all(r["feasible"] for r in rows),
        "pullback_consistent": all(r["pullback_consistent"] for r in rows),
        "verdicts": verdicts,
    }
