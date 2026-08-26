"""
Exact threshold for vertex localization under interaction.

Theorem 1 gives theta_max in ext(H) for the unperturbed composite objective.
`nonlinear_objective` then observes numerically that the `face_bowl` interaction
"breaks vertex localization" at some strength. This module replaces that
observation with an exact statement, and the answer is not the expected one:

    the critical strength is s* = 0.

Vertex localization for `face_bowl` fails for EVERY s > 0. What is small for
small s is not the chance of failure but its magnitude, which is Theta(s^2) --
quadratic, hence invisible to the coarse grids used to look for it.

The mechanism is a degeneracy: the unperturbed r is stationary exactly at the
corner (lam_max, sigma_min), so the vertex maximum is attained with zero inward
margin. `vertex_margin` measures that margin for any objective and
`perturbation_threshold` turns it into a critical strength, so the criterion
applies beyond `face_bowl`.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, ceil, cos, log, pi, sin, sqrt

from .hypersurface_box import BoxBounds, Theta
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    Objective,
    default_nonlinear_bounds,
    vertex_maximize,
)

_AXES = ("lam", "sigma", "b", "k")

# Inward slopes below this are numerical noise, not a real push off the vertex.
_PUSH_TOL = 1e-9


# --------------------------------------------------------------------------
# Exact solution for the face_bowl family
# --------------------------------------------------------------------------


def face_coordinates(theta: Theta) -> tuple[float, float]:
    """
    Reparametrise the (lam,sigma) face by u = lam - 1/2, w = 1/2 - sigma.

    Both live in [-1/2,1/2] and the objective becomes symmetric in (u,w), which
    is what collapses the 2-D problem onto a diagonal.
    """
    return (theta.lam - 0.5, 0.5 - theta.sigma)


def face_objective(s: float, u: float, w: float) -> float:
    """
    Closed form of the face_bowl objective in (u,w), with b and k at maxima:

        C = (b_max + k_max) + 3/2 + (u + w) - (u^2 + w^2) + s (1-u^2)(1-w^2)

    Symmetric under u <-> w. Checked against HypersurfacePlusInteraction in
    tests/test_vertex_threshold.py.
    """
    return 5.0 + 1.5 + (u + w) - (u * u + w * w) + s * (1.0 - u * u) * (1.0 - w * w)


def is_strictly_concave_on_face(s: float, *, samples: int = 101) -> bool:
    """
    Leading minors of -Hess on [-1/2,1/2]^2, which stay positive for every s >= 0:

        -Hess = [[2 + 2s(1-w^2),      4suw     ],
                 [     4suw     , 2 + 2s(1-u^2)]]

    det >= (2 + 3s/2)^2 - s^2 > 0 because |u|,|w| <= 1/2. Strict concavity makes
    the maximiser unique, so "vertex or interior" is a genuine dichotomy and not
    a question of which local maximum a search happens to land in.
    """
    if s < 0:
        return False
    step = 1.0 / (samples - 1)
    for i in range(samples):
        u = -0.5 + i * step
        for j in range(samples):
            w = -0.5 + j * step
            a = 2.0 + 2.0 * s * (1.0 - w * w)
            d = 2.0 + 2.0 * s * (1.0 - u * u)
            off = 4.0 * s * u * w
            if a <= 0.0 or a * d - off * off <= 0.0:
                return False
    return True


def t_star(s: float) -> float:
    """
    Exact maximiser coordinate on the diagonal u = w = t: the unique root in
    [0,1/2] of

        2s t^3 - 2(1+s) t + 1 = 0

    via the trigonometric form of Cardano. t_star(0) = 1/2 is the corner itself.
    """
    if s <= 0.0:
        return 0.5
    p = -(1.0 + s) / s
    q = 1.0 / (2.0 * s)
    m = 2.0 * sqrt(-p / 3.0)
    phi = acos(3.0 * q / (p * m)) / 3.0
    roots = [m * cos(phi - 2.0 * pi * kk / 3.0) for kk in range(3)]
    inside = [r for r in roots if -0.5 <= r <= 0.5 + 1e-12]
    return min(inside, key=lambda r: abs(r - 0.5))


def displacement(s: float) -> float:
    """delta(s) = 1/2 - t*(s): how far the maximiser moves off the vertex."""
    return 0.5 - t_star(s)


def displacement_asymptote(s: float) -> float:
    """delta(s) ~ 3s/(8+2s) = (3/8)s + O(s^2)."""
    return 3.0 * s / (8.0 + 2.0 * s)


def optimality_gap(s: float) -> float:
    """Delta(s) = C(theta*) - max over ext(H), exactly, from the cubic root."""
    t = t_star(s)
    return face_objective(s, t, t) - face_objective(s, 0.5, 0.5)


def gap_asymptote(s: float) -> float:
    """Delta(s) ~ 9s^2/(8(4+s)) = (9/32)s^2 + O(s^3)."""
    return 9.0 * s * s / (8.0 * (4.0 + s))


def grid_resolution_needed(s: float) -> int:
    """
    Points per axis for a uniform grid to report ANY positive gap.

    The face objective is concave and symmetric about t*(s), so a grid point at
    distance x inside the corner beats the corner exactly when x < 2*delta(s).
    The nearest interior grid point sits at 1/(n-1), giving

        n >= 1 + 1/(2 delta(s)) ~ 1 + 4/(3s).

    In 4-D the cost is that to the fourth power. At s = 0.05 this needs n >= 29,
    i.e. about 700k objective evaluations, which is why steps=7 sees nothing.
    Use `grid_resolution_to_resolve` for the finer grid that also gets the value
    of the gap approximately right.
    """
    d = displacement(s)
    if d <= 0.0:
        return 0
    return int(ceil(1.0 + 1.0 / (2.0 * d)))


def grid_resolution_to_resolve(s: float) -> int:
    """
    Points per axis for a grid point to land within delta(s) of the true
    maximiser, so most of the gap is recovered rather than just detected:

        n >= 1 + 1/delta(s) ~ 1 + 8/(3s).
    """
    d = displacement(s)
    if d <= 0.0:
        return 0
    return int(ceil(1.0 + 1.0 / d))


# --------------------------------------------------------------------------
# The general criterion
# --------------------------------------------------------------------------


def inward_derivatives(
    objective: Objective,
    theta: Theta,
    bounds: BoxBounds,
    *,
    h: float = 1e-4,
) -> dict[str, float]:
    """
    One-sided derivative of `objective` at a box vertex along each axis, taken
    in the direction pointing into H. At a maximiser all four are <= 0.

    Richardson-extrapolated: the plain difference D(h) = f' + f''h/2 + O(h^2)
    returns -h/2 * |f''| rather than 0 at a degenerate vertex, which would read
    as a small but strictly negative margin and hide exactly the degeneracy this
    module is about. 2*D(h/2) - D(h) cancels the f'' term and is exact for the
    quadratic r used here.
    """
    intervals = {
        "lam": bounds.lam,
        "sigma": bounds.sigma,
        "b": bounds.b,
        "k": bounds.k,
    }
    base = objective(theta)
    out: dict[str, float] = {}
    for axis in _AXES:
        lo, hi = intervals[axis]
        if hi - lo <= 0.0:
            out[axis] = 0.0
            continue
        here = getattr(theta, axis)
        inward = 1.0 if abs(here - lo) < abs(here - hi) else -1.0

        def diff(step: float) -> float:
            moved = Theta(
                *[
                    getattr(theta, a) + (inward * step if a == axis else 0.0)
                    for a in _AXES
                ]
            )
            return (objective(moved) - base) / step

        out[axis] = 2.0 * diff(h / 2.0) - diff(h)
    return out


@dataclass(frozen=True)
class VertexMargin:
    """How strictly a vertex maximiser beats its neighbours along each axis."""

    theta: Theta
    derivatives: dict[str, float]
    margin: float
    degenerate: bool

    def describe(self) -> str:
        kind = "DEGENERATE (zero margin)" if self.degenerate else "strict"
        return f"vertex {self.theta.as_corner_tuple()} is {kind}, margin={self.margin:.6g}"


def vertex_margin(
    objective: Objective,
    bounds: BoxBounds,
    *,
    tol: float = 1e-7,
) -> VertexMargin:
    """
    Margin of the best vertex: min over axes of the drop per unit step inward.

    margin > 0  -- the vertex maximum is strict, survives small perturbations,
                   and `perturbation_threshold` returns a positive s*.
    margin == 0 -- knife-edge: some inward direction is flat to first order, so
                   an arbitrarily small perturbation moves the maximiser off the
                   vertex. This is the case for the default r in this repo.
    """
    theta, _ = vertex_maximize(objective, bounds)
    ders = inward_derivatives(objective, theta, bounds)
    margin = max(min(-d for d in ders.values()), 0.0)
    return VertexMargin(theta, ders, margin, degenerate=margin <= tol)


def perturbation_threshold(
    base: Objective,
    perturbation: Objective,
    bounds: BoxBounds,
) -> float:
    """
    Critical strength s* below which base + s*perturbation keeps its maximiser
    at the vertex, from a first-order balance there:

        s* = margin(base) / max_i (inward derivative of perturbation)_i

    Returns 0.0 when the base vertex is degenerate, and inf when the
    perturbation has no inward-increasing direction at that vertex.
    """
    vm = vertex_margin(base, bounds)
    push = max(inward_derivatives(perturbation, vm.theta, bounds).values())
    if push <= _PUSH_TOL:
        return float("inf")
    if vm.degenerate:
        return 0.0
    return vm.margin / push


def fractional_exponent_law(
    alpha: float,
    s: float,
    *,
    gamma: float = 1.0,
    curvature: float = 2.0,
) -> tuple[float, float]:
    """
    Displacement and gap for a homogeneous perturbation P = gamma * x^alpha,
    0 < alpha < 2, at a degenerate vertex with inward curvature c.

    Maximising gamma*s*x^alpha - (c/2)x^2 gives

        x*    = (alpha*gamma*s/c)^(1/(2-alpha))
        Delta = c(2-alpha)/(2 alpha) * (alpha*gamma*s/c)^(2/(2-alpha))

    The exponent 2/(2-alpha) sweeps the whole range as alpha runs over (0,2):

        alpha in (0,1)  unbounded 1st derivative   exponent in (1,2)
        alpha = 1       linear kink (V.7)           exponent 2
        alpha in (1,2)  C^1 but not C^2             exponent in (2, infinity)

    (This is the unified law V.10; the original V.8 covered only alpha <= 1.)
    As alpha -> 2 the exponent diverges: the perturbation becomes quadratic and
    merges into the curvature, leaving no leading-order gap. Since s is small, a
    smaller alpha (smaller exponent) means a LARGER gap.
    """
    if not 0.0 < alpha < 2.0 or s < 0.0 or curvature <= 0.0:
        raise ValueError("need 0 < alpha < 2, s >= 0, curvature > 0")
    if s == 0.0:
        return (0.0, 0.0)
    a = alpha * gamma * s / curvature
    x = a ** (1.0 / (2.0 - alpha))
    gap = curvature * (2.0 - alpha) / (2.0 * alpha) * a ** (2.0 / (2.0 - alpha))
    return (x, gap)


def gap_exponent(alpha: float) -> float:
    """The exponent p in Delta(s) = Theta(s^p): p = 2/(2-alpha)."""
    return 2.0 / (2.0 - alpha)


def estimate_homogeneity(
    perturbation: Objective,
    corner: Theta,
    bounds: BoxBounds,
    axis: str,
    *,
    h: float = 1e-3,
) -> float:
    """
    Leading homogeneity degree alpha of |P| along an inward axis: the log-log
    slope of |P(corner + t)| against t as t -> 0. Recovers alpha for P ~ t^alpha
    (0.5 -> 0.5, 1 -> 1, 1.5 -> 1.5). This is what selects the gap exponent
    2/(2-alpha) uniformly, so a screen need not know in advance whether a term is
    linear, fractional, or C^1-but-not-C^2.
    """
    intervals = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}
    lo, hi = intervals[axis]
    here = getattr(corner, axis)
    inward = 1.0 if abs(here - lo) < abs(here - hi) else -1.0
    p0 = perturbation(corner)

    def val(t: float) -> float:
        moved = Theta(
            *[getattr(corner, a) + (inward * t if a == axis else 0.0) for a in _AXES]
        )
        return abs(perturbation(moved) - p0)

    v1, v2 = val(h), val(h / 4.0)
    if v1 <= 0.0 or v2 <= 0.0:
        return 0.0
    return log(v1 / v2) / log(4.0)


def amplitude_bound(perturbation: Objective, bounds: BoxBounds, s: float, *, steps: int = 11) -> float:
    """
    Grid estimate of the exact ceiling

        Delta(s) <= s * (sup_H P - P(theta_c)).

    This is invariant to adding a constant to P. When P(theta_c)=0 and P>=0,
    it reduces to the familiar s*sup|P| form. Without that normalization the
    general absolute-value statement is Delta <= 2*s*sup|P|.

    Any derivative-based prediction that exceeds this is invalid: the
    perturbation saturates (e.g. a bounded near-singular ridge such as
    atan(y/x)), so the leading-order theory does not apply and the gap is set by
    amplitude, not by the corner derivative.
    """
    from itertools import product

    def lin(iv: tuple[float, float], i: int) -> float:
        return iv[0] + (iv[1] - iv[0]) * i / (steps - 1)

    corner = Theta(bounds.lam[1], bounds.sigma[0], bounds.b[1], bounds.k[1])
    p_corner = perturbation(corner)
    sup_difference = 0.0
    for i, j, m, n in product(range(steps), repeat=4):
        theta = Theta(lin(bounds.lam, i), lin(bounds.sigma, j), lin(bounds.b, m), lin(bounds.k, n))
        sup_difference = max(sup_difference, perturbation(theta) - p_corner)
    return s * sup_difference


@dataclass(frozen=True)
class InteractionOnly:
    """The interaction term alone, with the base composite objective removed."""

    bounds: BoxBounds
    interaction: str

    def __call__(self, theta: Theta) -> float:
        full = HypersurfacePlusInteraction(
            self.bounds, strength=1.0, interaction=self.interaction
        )
        zero = HypersurfacePlusInteraction(
            self.bounds, strength=0.0, interaction=self.interaction
        )
        return full(theta) - zero(theta)


def inward_curvatures(
    objective: Objective,
    theta: Theta,
    bounds: BoxBounds,
    *,
    h: float = 1e-3,
) -> dict[str, float]:
    """
    c_i = -(second derivative into H) along each axis. Positive at a maximum.

    Only meaningful where the first derivative vanishes, which is exactly the
    degenerate case this module targets: there C(x0 + e) - C(x0) = -c e^2/2.
    """
    intervals = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}
    base = objective(theta)
    out: dict[str, float] = {}
    for axis in _AXES:
        lo, hi = intervals[axis]
        if hi - lo <= 0.0:
            out[axis] = 0.0
            continue
        here = getattr(theta, axis)
        inward = 1.0 if abs(here - lo) < abs(here - hi) else -1.0
        moved = Theta(
            *[getattr(theta, a) + (inward * h if a == axis else 0.0) for a in _AXES]
        )
        out[axis] = -2.0 * (objective(moved) - base) / (h * h)
    return out


def universal_gap(
    base: Objective,
    perturbation: Objective,
    bounds: BoxBounds,
    s: float,
) -> float:
    """
    Leading-order optimality gap at a degenerate vertex, for ANY perturbation.

    Along each axis where the base is flat (curvature c_i > 0) and the
    perturbation pushes inward with slope gamma_i per unit strength, the
    maximiser moves gamma_i s / c_i and gains gamma_i^2 s^2 / (2 c_i). Axes are
    independent to leading order, so

        Delta(s) = s^2 * sum_i gamma_i^2 / (2 c_i) + O(s^3).

    Here c_i is the inward curvature in the convention C = C0 - (c/2) e^2; the
    default r gives c = 2 on both lam and sigma.

    With the default r (c = 1 on both lam and sigma) this reproduces every
    interaction mode in `nonlinear_objective`: bilinear s^2/4 (exact, being
    quadratic), trig pi^2 s^2, face_bowl 9 s^2/32.
    """
    vm = vertex_margin(base, bounds)
    corner = vm.theta
    gammas = inward_derivatives(perturbation, corner, bounds)
    curv = inward_curvatures(base, corner, bounds)
    # Only FLAT axes contribute. On a non-flat axis the base has a first-order
    # slope that dominates any perturbation for small s, so there is no gap there
    # - and inward_curvatures returns a meaningless value off a stationary point.
    total = 0.0
    for axis in _flat_axes(base, corner, bounds):
        g, c = gammas[axis], curv[axis]
        if g > _PUSH_TOL and c > 0.0:
            total += g * g / (2.0 * c)
    return total * s * s


def _flat_axes(base: Objective, corner: Theta, bounds: BoxBounds) -> list[str]:
    """Axes where the base is flat to first order but has positive curvature."""
    ders = inward_derivatives(base, corner, bounds)
    curv = inward_curvatures(base, corner, bounds)
    return [a for a in _AXES if abs(ders[a]) <= 1e-6 and curv[a] > 0.0]


def _orthant_directions(m: int, n: int):
    """Unit inward directions over the nonneg orthant of an m-dim flat subspace."""
    if m <= 1:
        yield (1.0,) * max(m, 1)
        return
    if m == 2:
        for k in range(n + 1):
            t = (pi / 2.0) * k / n
            yield (cos(t), sin(t))
        return
    # m >= 3: normalised nonneg grid (coarse; the repo never reaches this).
    from itertools import product

    steps = max(2, int(round(n ** (1.0 / m))))
    for combo in product(range(steps + 1), repeat=m):
        if not any(combo):
            continue
        norm = sqrt(sum(c * c for c in combo))
        yield tuple(c / norm for c in combo)


def directional_gap(
    base: Objective,
    perturbation: Objective,
    bounds: BoxBounds,
    s: float,
    *,
    n_samples: int = 721,
    h: float = 1e-6,
) -> float:
    """
    Correct leading-order gap for a degree-1-homogeneous perturbation, coupled
    or not (Theorem V.9). The maximiser moves along one ray; on the flat
    subspace with curvature diag(c_i),

        Delta(s) = s^2 * max_d  D_d P(0)^2 / (2 * sum_i c_i d_i^2)

    over unit inward directions d. `universal_gap` is the special case where P is
    separable and the maximising direction is the per-axis gradient; for coupled
    P (a cone sqrt(x^2+y^2), a crease |x-y|) the additive sum strictly
    over-predicts, since by Cauchy-Schwarz sum_i gamma_i^2 >= max_d D_d P^2 with
    equality only in the separable case.
    """
    vm = vertex_margin(base, bounds)
    corner = vm.theta
    curv = inward_curvatures(base, corner, bounds)
    flat = _flat_axes(base, corner, bounds)
    if not flat:
        return 0.0
    intervals = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}
    inward = {
        a: (1.0 if abs(getattr(corner, a) - intervals[a][0]) < abs(getattr(corner, a) - intervals[a][1]) else -1.0)
        for a in flat
    }
    p0 = perturbation(corner)
    best = 0.0
    for d in _orthant_directions(len(flat), n_samples):
        moved = Theta(
            *[
                getattr(corner, a) + (inward[a] * d[flat.index(a)] * h if a in flat else 0.0)
                for a in _AXES
            ]
        )
        g = (perturbation(moved) - p0) / h
        if g <= _PUSH_TOL:
            continue
        quad = sum(curv[flat[i]] * d[i] * d[i] for i in range(len(flat)))
        if quad <= 0.0:
            continue
        best = max(best, g * g / (2.0 * quad))
    return best * s * s


def is_coupled(
    base: Objective,
    perturbation: Objective,
    bounds: BoxBounds,
    s: float = 0.01,
    *,
    tol: float = 0.05,
) -> bool:
    """
    True when the additive law over-predicts the directional law, i.e. the
    perturbation couples flat axes. Diagnostic used by the interaction screen.
    """
    add = universal_gap(base, perturbation, bounds, s)
    dirc = directional_gap(base, perturbation, bounds, s)
    if add <= 0.0:
        return False
    return add > dirc * (1.0 + tol)


def screen_interactions(
    bounds: BoxBounds | None = None,
    *,
    s: float = 0.01,
) -> list[tuple[str, float, float, bool]]:
    """
    Apply the criterion to every interaction mode: (mode, s*, predicted gap,
    breaks_localization). This is the reusable screen - it costs 4 derivative
    evaluations per mode and replaces a grid search that cannot see the effect.
    """
    bounds = bounds or default_nonlinear_bounds()
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    rows: list[tuple[str, float, float, bool]] = []
    for mode in ("bilinear", "triple", "softplus", "trig", "face_bowl"):
        pert = InteractionOnly(bounds, mode)
        star = perturbation_threshold(base, pert, bounds)
        gap = universal_gap(base, pert, bounds, s)
        rows.append((mode, star, gap, star == 0.0))
    return rows


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def demonstrate_threshold() -> list[str]:
    bounds = default_nonlinear_bounds()
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    vm = vertex_margin(base, bounds)

    lines = [
        "Vertex-localization threshold for face_bowl",
        "",
        f"  unperturbed maximiser: {vm.describe()}",
        "  inward derivatives: "
        + ", ".join(f"{a}={vm.derivatives[a]:+.4f}" for a in _AXES),
        "",
        "  The lam and sigma derivatives vanish: r is stationary at the corner,",
        "  so Theorem 1 holds there with zero margin. Hence s* = 0, and an",
        "  interior optimum appears for every s > 0.",
        "",
        f"  {'s':>7} {'delta(s)':>10} {'3s/(8+2s)':>11} {'gap(s)':>11} "
        f"{'9s^2/8(4+s)':>12} {'grid n':>7}",
    ]
    for s in (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0):
        lines.append(
            f"  {s:7.2f} {displacement(s):10.6f} {displacement_asymptote(s):11.6f} "
            f"{optimality_gap(s):11.6f} {gap_asymptote(s):12.6f} "
            f"{grid_resolution_needed(s):7d}"
        )
    lines += [
        "",
        "  gap is Theta(s^2) while grid spacing is Theta(1/n): a 4-D uniform grid",
        "  needs about (1 + 4/(3s))^4 evaluations to detect it, which is why",
        "  steps=7 reports a gap of exactly 0 for s <= 0.1.",
        "",
        "  face_bowl is not special. Screening every interaction mode:",
        "",
        f"  {'mode':>10} {'s*':>6} {'gap at s=0.01':>15}  breaks localization",
    ]
    for mode, star, gap, breaks in screen_interactions(bounds, s=0.01):
        star_s = "0" if star == 0.0 else ("inf" if star == float("inf") else f"{star:.3g}")
        lines.append(f"  {mode:>10} {star_s:>6} {gap:15.8f}  {breaks}")
    lines += [
        "",
        "  Three of five break at s* = 0, including bilinear, which",
        "  nonlinear_objective documents as 'still vertex-friendly on a box'.",
    ]
    return lines
