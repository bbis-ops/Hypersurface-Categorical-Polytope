"""
Search over BASE objectives, not perturbations.

Everything in `vertex_threshold` (V.1-V.11) fixes the base r(lam,sigma) and varies
the interaction. But the whole story rests on ONE property of that base: it is
quadratically flat at the corner (stationary, curvature > 0). This module varies
the base and asks what changes.

The answer is the master law V.12: if the base is flat to order beta at its
corner (base ~ -A*x^beta along a slack axis) and the perturbation is homogeneous
of degree alpha < beta, the optimality gap scales as

    Delta(s) = Theta( s^{beta / (beta - alpha)} ).

V.7 (beta=2, alpha=1 -> exponent 2) and V.10 (beta=2, general alpha) are the
beta=2 slice. beta need NOT be even: an order-3 base (|x|^3) gives exponent
3/(3-1)=1.5, confirmed. A flatter base (larger beta) breaks vertex localization
HARDER: the exponent falls toward 1, so the gap grows. A base that is NOT flat at
the corner (a strict maximum) has a positive threshold and does not break for
small s.

V.13 (a distinct, prior failure): the base can fail vertex localization on its
OWN, before any perturbation, when its maximiser is interior or off-corner. The
margin criterion (V.6) assumes the corner is the maximiser and cannot see this;
`screen_base` catches it by comparing the base's grid maximum to its vertex
maximum and flags `base_self_fails`.

Model output is data: base expressions in lam, sigma go through the same AST
whitelist as interaction terms (`compile_expression`). Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Any, Callable

from .hypersurface_box import BoxBounds, Theta
from .interaction_search import Candidate, UnsafeExpression, compile_expression
from .nonlinear_objective import default_nonlinear_bounds, grid_maximize, vertex_maximize
from .vertex_threshold import _AXES, _PUSH_TOL, inward_derivatives


@dataclass(frozen=True)
class CustomBase:
    """Base objective C = b + k + r(lam, sigma) for a compiled r."""

    r: Callable[[Theta], float]

    def __call__(self, theta: Theta) -> float:
        return theta.b + theta.k + self.r(theta)


def _inward(corner: Theta, bounds: BoxBounds, axis: str) -> float:
    lo, hi = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}[axis]
    here = getattr(corner, axis)
    return 1.0 if abs(here - lo) < abs(here - hi) else -1.0


def base_flatness_order(
    base: Callable[[Theta], float],
    corner: Theta,
    bounds: BoxBounds,
    axis: str,
    *,
    h: float | None = None,
) -> float:
    """
    Order 2m of the base's vanishing at the corner along an axis: the log-log
    slope of the DROP base(corner) - base(corner + t) as t -> 0. For base ~ x^p
    this returns p (2 for quadratic, 4 for quartic, ...). Returns 0.0 for a base
    with a first-order slope (a strict, non-flat maximum).

    With no explicit ``h``, use the deepest scale whose two drops remain above
    numerical resolution. This avoids both essential-singularity contamination
    at coarse scale and cancellation for high-order/small-coefficient bases.
    """
    inward = _inward(corner, bounds, axis)
    b0 = base(corner)

    def drop(t: float) -> float:
        moved = Theta(
            *[getattr(corner, a) + (inward * t if a == axis else 0.0) for a in _AXES]
        )
        return b0 - base(moved)

    def slope(scale: float) -> float | None:
        d1, d2 = drop(scale), drop(scale / 4.0)
        if d1 <= 1e-12 or d2 <= 1e-12:
            return None
        return log(d1 / d2) / log(4.0)

    if h is not None:
        measured = slope(h)
        return measured if measured is not None else 0.0
    resolved = [measured for scale in (
        0.2, 0.1, 0.05, 0.025, 0.0125, 0.00625, 0.003125,
        0.0015625, 0.00078125,
    )
                if (measured := slope(scale)) is not None]
    return resolved[-1] if resolved else 0.0


def _adaptive_base_strengths(
    base: Callable[[Theta], float], corner: Theta, bounds: BoxBounds, axis: str
) -> tuple[float, float]:
    """Choose strengths whose stationary points sit at resolved local radii."""
    inward = _inward(corner, bounds, axis)
    b0 = base(corner)

    def drop(t: float) -> float:
        moved = Theta(*[getattr(corner, a) + (inward * t if a == axis else 0.0)
                        for a in _AXES])
        return b0 - base(moved)

    def derivative(t: float) -> float:
        eps = t * 1e-3
        return (drop(t + eps) - drop(t - eps)) / (2.0 * eps)

    chosen = (0.08, 0.04)
    for pair in (
        (0.08, 0.04), (0.04, 0.02), (0.02, 0.01), (0.01, 0.005),
        (0.005, 0.0025), (0.0025, 0.00125),
    ):
        if drop(pair[1]) > 5e-13:
            chosen = pair
    return derivative(chosen[0]), derivative(chosen[1])


def _perturbation_pushes(
    p: Callable[[Theta], float], corner: Theta, bounds: BoxBounds, axis: str, *, h: float = 1e-3
) -> bool:
    """True if the perturbation increases moving inward along `axis`."""
    inward = _inward(corner, bounds, axis)
    moved = Theta(*[getattr(corner, a) + (inward * h if a == axis else 0.0) for a in _AXES])
    return p(moved) - p(corner) > 1e-9


def _linear_inward(corner: Theta, bounds: BoxBounds, axis: str) -> Callable[[Theta], float]:
    """Reference perturbation: the linear inward coordinate on `axis` (alpha=1)."""
    inward = _inward(corner, bounds, axis)
    here = getattr(corner, axis)

    def P(theta: Theta) -> float:
        return inward * (getattr(theta, axis) - here)

    return P


def _measure_axis_gap(
    base: Callable[[Theta], float],
    perturbation: Callable[[Theta], float],
    corner: Theta,
    bounds: BoxBounds,
    axis: str,
    *,
    strength: float,
    samples: int = 4000,
) -> tuple[float, float]:
    """High-resolution 1-D gap and displacement along one inward axis."""
    lo, hi = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}[axis]
    inward = _inward(corner, bounds, axis)
    here = getattr(corner, axis)
    span = (hi - lo)
    p0 = perturbation(corner)
    # CustomBase contains the irrelevant b+k constant. Subtract its r component
    # directly so high-order gaps are not destroyed by cancellation against 5.
    base_shape = getattr(base, "r", None)

    def gain(t: float) -> float:
        v = here + inward * t
        if v < lo - 1e-12 or v > hi + 1e-12:
            return float("-inf")
        theta = Theta(*[v if a == axis else getattr(corner, a) for a in _AXES])
        base_change = (
            base_shape(theta) - base_shape(corner)
            if callable(base_shape) else base(theta) - base(corner)
        )
        return base_change + strength * (perturbation(theta) - p0)

    probe_ts = sorted({
        *(span * i / samples for i in range(samples + 1)),
        *(span * (2.0 ** -power) for power in range(1, 48)),
    })
    values = [gain(t) for t in probe_ts]
    best_i = max(range(len(values)), key=values.__getitem__)
    best_t, best = probe_ts[best_i], max(0.0, values[best_i])
    if 0 < best_i < len(probe_ts) - 1:
        left, right = probe_ts[best_i - 1], probe_ts[best_i + 1]
        # Golden-section refinement removes grid quantization from high-order
        # laws whose optimizer can be much closer to the corner than 1/samples.
        phi = (5.0**0.5 - 1.0) / 2.0
        x1, x2 = right - phi * (right - left), left + phi * (right - left)
        f1, f2 = gain(x1), gain(x2)
        for _ in range(80):
            if f1 < f2:
                left, x1, f1 = x1, x2, f2
                x2 = left + phi * (right - left)
                f2 = gain(x2)
            else:
                right, x2, f2 = x2, x1, f1
                x1 = right - phi * (right - left)
                f1 = gain(x1)
        if max(f1, f2) > best:
            best, best_t = (f1, x1) if f1 >= f2 else (f2, x2)
    return best, best_t


def _measure_gap_exponent(
    base: Callable[[Theta], float],
    perturbation: Callable[[Theta], float],
    corner: Theta,
    bounds: BoxBounds,
    axis: str,
    *,
    s_hi: float = 2e-2,
    s_lo: float = 2e-3,
    samples: int = 4000,
) -> tuple[float, float, float]:
    """1-D gap along `axis` at two strengths; return (exponent, gap_hi, gap_lo)."""
    g_hi, _ = _measure_axis_gap(
        base, perturbation, corner, bounds, axis, strength=s_hi, samples=samples
    )
    g_lo, _ = _measure_axis_gap(
        base, perturbation, corner, bounds, axis, strength=s_lo, samples=samples
    )
    if g_hi <= 0.0 or g_lo <= 0.0:
        return (0.0, g_hi, g_lo)
    return (log(g_hi / g_lo) / log(s_hi / s_lo), g_hi, g_lo)


def adaptive_axis_gap_exponent(
    base: Callable[[Theta], float],
    perturbation: Callable[[Theta], float],
    corner: Theta,
    bounds: BoxBounds,
    axis: str,
) -> tuple[float, float, float, tuple[float, float]]:
    """Choose a resolved local strength window without consulting the predicted exponent."""
    span = ({"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}[axis][1]
            - {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}[axis][0])
    strengths = [0.08 / (4.0**index) for index in range(14)]
    valid: list[tuple[float, float, float, tuple[float, float]]] = []
    measured: list[tuple[float, float, float]] = []
    previous: tuple[float, float, float] | None = None
    for strength in strengths:
        current = (strength, *_measure_axis_gap(
            base, perturbation, corner, bounds, axis, strength=strength
        ))
        measured.append(current)
        if previous is not None:
            s_hi, g_hi, t_hi = previous
            s_lo, g_lo, t_lo = current
            if (min(g_hi, g_lo) > 1e-30
                    and 1e-8 * span <= t_lo < t_hi <= 0.25 * span):
                exponent = log(g_hi / g_lo) / log(s_hi / s_lo)
                valid.append((exponent, g_hi, g_lo, (s_hi, s_lo)))
        previous = current
        if valid and (current[1] <= 1e-30 or current[2] < 1e-8 * span):
            break
    if valid:
        return valid[-1]
    return (0.0, measured[0][1], measured[-1][1], (measured[0][0], measured[-1][0]))


def _halton(index: int, base: int) -> float:
    value, factor = 0.0, 1.0 / base
    while index:
        index, digit = divmod(index, base)
        value += digit * factor
        factor /= base
    return value


def base_global_search(
    base: Callable[[Theta], float], bounds: BoxBounds, *, halton_points: int = 4096
) -> tuple[Theta, float, str, bool]:
    """Adversarial 2-D witness search; absence of a witness is not a proof.

    Coprime grids defeat simple frequency aliasing, while a deterministic Halton
    cover probes narrow peaks between all grids. ``legacy_missed`` records when
    the former 9x9 guard would have returned false assurance.
    """
    corner, vertex_value = vertex_maximize(base, bounds)
    _, legacy_value = grid_maximize(base, bounds, steps=9)
    best, best_value, method = corner, vertex_value, "vertex"

    def consider(lam: float, sigma: float, source: str) -> None:
        nonlocal best, best_value, method
        theta = Theta(lam, sigma, bounds.b[1], bounds.k[1])
        value = base(theta)
        if value > best_value:
            best, best_value, method = theta, value, source

    for steps in (10, 11, 13, 17, 33):
        for i in range(steps):
            lam = bounds.lam[0] + (bounds.lam[1] - bounds.lam[0]) * i / (steps - 1)
            for j in range(steps):
                sigma = bounds.sigma[0] + (bounds.sigma[1] - bounds.sigma[0]) * j / (steps - 1)
                consider(lam, sigma, f"grid-{steps}")
    for index in range(1, halton_points + 1):
        lam = bounds.lam[0] + (bounds.lam[1] - bounds.lam[0]) * _halton(index, 2)
        sigma = bounds.sigma[0] + (bounds.sigma[1] - bounds.sigma[0]) * _halton(index, 3)
        consider(lam, sigma, "halton")
    legacy_missed = legacy_value <= vertex_value + 1e-9 and best_value > vertex_value + 1e-9
    return best, best_value, method, legacy_missed


@dataclass(frozen=True)
class BaseScreenResult:
    candidate: Candidate
    ok: bool
    reason: str = ""
    corner: tuple[float, float, float, float] = ()
    flat_axis: str = ""
    flatness_order: float = 0.0
    predicted_exponent: float = 0.0
    measured_exponent: float = 0.0
    base_self_fails: bool = False   # base maximiser not at a vertex even at s=0
    search_method: str = ""
    legacy_grid_missed: bool = False
    breaks: bool = False

    @property
    def law_holds(self) -> bool:
        if not self.breaks or self.predicted_exponent <= 0.0:
            return False
        return abs(self.measured_exponent - self.predicted_exponent) < 0.05

    def row(self) -> str:
        if not self.ok:
            return f"  {self.candidate.name:<16} REJECTED  {self.reason}"
        if self.base_self_fails:
            return f"  {self.candidate.name:<16} BASE ITSELF FAILS vertex localization at s=0"
        return (
            f"  {self.candidate.name:<16} order={self.flatness_order:>5.2f} on {self.flat_axis:<5} "
            f"pred p={self.predicted_exponent:>6.3f} meas p={self.measured_exponent:>6.3f} "
            f"law={'yes' if self.law_holds else 'no '}"
        )


def screen_base(
    candidate: Candidate,
    bounds: BoxBounds | None = None,
    *,
    alpha: float = 1.0,
) -> BaseScreenResult:
    """
    Screen a candidate base r(lam,sigma): find its corner, measure the flatness
    order beta there, and check the master exponent p = beta/(beta-alpha) against
    a measured linear-perturbation gap (alpha=1 reference).
    """
    bounds = bounds or default_nonlinear_bounds()
    try:
        r = compile_expression(candidate.expr)
    except UnsafeExpression as exc:
        return BaseScreenResult(candidate, ok=False, reason=str(exc))

    base = CustomBase(r)
    try:
        corner, vval = vertex_maximize(base, bounds)
        _, gval, search_method, legacy_missed = base_global_search(base, bounds)
        base(corner)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return BaseScreenResult(candidate, ok=False, reason=f"not evaluable: {exc}")

    if gval > vval + 1e-9:
        return BaseScreenResult(
            candidate, ok=True, base_self_fails=True,
            corner=corner.as_corner_tuple(), search_method=search_method,
            legacy_grid_missed=legacy_missed, breaks=True,
        )

    # flat axes = slack axes where the base is stationary at the corner
    ders = inward_derivatives(base, corner, bounds)
    flat = [a for a in ("lam", "sigma") if abs(ders[a]) <= 1e-5]
    if not flat:
        # strict corner: positive threshold, does not break for small s
        return BaseScreenResult(
            candidate, ok=True, corner=corner.as_corner_tuple(),
            flat_axis="(none)", breaks=False,
        )

    # pick the flattest slack axis
    orders = {a: base_flatness_order(base, corner, bounds, a) for a in flat}
    axis = max(orders, key=lambda a: orders[a])
    m2 = orders[axis]
    if m2 <= alpha:  # perturbation dominates: no interior optimum from this term
        return BaseScreenResult(
            candidate, ok=True, corner=corner.as_corner_tuple(), flat_axis=axis,
            flatness_order=m2, breaks=False,
        )

    P = _linear_inward(corner, bounds, axis)
    s_hi, s_lo = _adaptive_base_strengths(base, corner, bounds, axis)
    exponent, g_hi, _ = _measure_gap_exponent(
        base, P, corner, bounds, axis, s_hi=s_hi, s_lo=s_lo
    )
    return BaseScreenResult(
        candidate,
        ok=True,
        corner=corner.as_corner_tuple(),
        flat_axis=axis,
        flatness_order=m2,
        predicted_exponent=m2 / (m2 - alpha),  # 2m/(2m-alpha), m2 is the order 2m
        measured_exponent=exponent,
        breaks=g_hi > 1e-12,
    )


def screen_bases(
    candidates: list[Candidate] | None = None,
    bounds: BoxBounds | None = None,
    *,
    alpha: float = 1.0,
) -> list[BaseScreenResult]:
    items = list(candidates if candidates is not None else BUILTIN_BASES)
    out = [screen_base(c, bounds, alpha=alpha) for c in items]
    out.sort(key=lambda r: (not r.breaks, r.flatness_order))
    return out


BUILTIN_BASES: tuple[Candidate, ...] = (
    Candidate("quadratic", "-(1-lam)**2 - sigma**2", note="the repo default r shape (2m=2)"),
    Candidate("quartic", "-(1-lam)**4 - sigma**4", note="flatter corner (2m=4)"),
    Candidate("sextic", "-(1-lam)**6 - sigma**6", note="very flat (2m=6)"),
    Candidate("mixed_24", "-(1-lam)**2 - sigma**4", note="anisotropic flatness"),
    Candidate("strict", "lam - sigma", note="strict corner: slope != 0, threshold > 0"),
    Candidate("strict_curved", "-(1-lam)**2 - sigma**2 + 0.3*lam - 0.3*sigma",
              note="quadratic bowl plus a linear tilt: strict corner"),
    # Frontier finds (model-proposed), kept as regression fixtures:
    Candidate("odd_cubic", "-(abs(1-lam))**3 - (abs(sigma))**3", source="model",
              note="V.12 odd order beta=3: even-order assumption not needed, p=1.5"),
    Candidate("interior_max", "-((1-lam)-0.25)**2 - (sigma-0.35)**2", source="model",
              note="V.13 base self-fails: maximiser interior at (0.75,0.35), not a corner"),
)


PROPOSAL_PROMPT = """You are proposing BASE objective shapes r(lam,sigma) for a study
of when corner (vertex) search fails on a box lam in [0,1], sigma in [0,1].

The full objective is C = b + k + r(lam,sigma), maximized. The interesting corner
is (lam,sigma) = (1,0). Write x = 1-lam and y = sigma (both 0 at that corner).

Theory so far: if r is flat to order 2m at the corner (r ~ -x^(2m) - y^(2m), no
linear term), a small perturbation makes the maximizer leave the corner with gap
~ s^(2m/(2m-1)). Flatter (bigger m) breaks HARDER. A base with a genuine linear
slope at the corner (r ~ +x or -y ... i.e. strictly increasing toward the corner)
has a POSITIVE threshold and does not break for small s.

Propose {n} distinct r(lam,sigma). Aim for variety and to stress the theory:
  1. Different EVEN flatness orders at (1,0): quartic, sextic, order 8.
  2. ANISOTROPIC: flat to different orders in x vs y, e.g. -x^2 - y^6.
  3. Bases whose maximizer is NOT at the corner (1,0) at all - put it elsewhere,
     or make a whole edge/face optimal (a tie).
  4. Strict corners (nonzero slope) that should have a positive threshold.
  5. Mixed: a flat term plus a tiny linear tilt.

Use lam and sigma written out. Allowed: + - * / ** and sin cos tan exp log sqrt
abs tanh atan sinh cosh, and pi. Numeric exponents only. No other names.

Reply with JSON only, no prose:
{{"candidates":[{{"name":"slug","expr":"r in lam and sigma","why":"what it tests"}}]}}
"""


def propose_bases(
    n: int = 16,
    *,
    model: str | None = None,
    base_url: str | None = None,
    retries: int = 8,
) -> tuple[list[Candidate], str]:
    """Ask a model for base shapes. Reuses the interaction-search HTTP path."""
    from . import interaction_search as isc

    saved = isc.FRONTIER_PROMPT
    try:
        isc.FRONTIER_PROMPT = PROPOSAL_PROMPT
        return isc.propose_candidates(
            n, model=model, base_url=base_url, frontier=True, retries=retries
        )
    finally:
        isc.FRONTIER_PROMPT = saved


@dataclass(frozen=True)
class CombinedResult:
    """V.14 result, including anisotropic weighted homogeneity."""

    base_name: str
    pert_name: str
    ok: bool
    reason: str = ""
    beta: float = 0.0
    alpha: float = 0.0
    axis: str = ""
    predicted_exponent: float = 0.0
    measured_exponent: float = 0.0
    weighted_degree: float = 0.0
    active_axes: tuple[str, ...] = ()
    base_orders: tuple[tuple[str, float], ...] = ()
    base_self_fails: bool = False
    breaks: bool = False
    measurement_scales: tuple[float, float] = ()

    @property
    def law_holds(self) -> bool:
        if not self.breaks or self.predicted_exponent <= 0.0:
            return False
        return abs(self.measured_exponent - self.predicted_exponent) < 0.08

    def row(self) -> str:
        if not self.ok:
            return f"  {self.base_name:<14}x {self.pert_name:<16} REJECTED {self.reason}"
        if self.base_self_fails:
            return f"  {self.base_name:<14}x {self.pert_name:<16} BASE SELF-FAILS"
        return (
            f"  {self.base_name:<14}x {self.pert_name:<16} beta={self.beta:>5.2f} "
            f"alpha={self.alpha:>5.2f} pred p={self.predicted_exponent:>6.3f} "
            f"q={self.weighted_degree:>5.3f} meas p={self.measured_exponent:>6.3f} "
            f"law={'yes' if self.law_holds else 'no '}"
        )


def _weighted_push_modes(
    p: Callable[[Theta], float],
    corner: Theta,
    bounds: BoxBounds,
    orders: dict[str, float],
) -> list[tuple[float, tuple[str, ...]]]:
    """Estimate positive weighted-homogeneous modes of ``P-P(corner)``.

    The base-adapted dilation is x_i -> t^(1/beta_i) x_i.  A monomial
    product(x_i^alpha_i) then has weighted degree q=sum(alpha_i/beta_i).
    Single-axis and joint rays are both required: a product such as sqrt(x*y)
    vanishes on every coordinate axis but is positive in the interior.
    """
    axes = tuple(orders)
    p0 = p(corner)
    ratio = 64.0
    # The deep weighted scale suppresses higher-weight/rational corrections.
    # At the old t=1e-12, beta=8 still meant a 0.032 displacement, enough for
    # a factor such as 1/(1+y) to bias q by several percent.
    t_hi, t_lo = 1e-20, 1e-20 / ratio
    modes: list[tuple[float, tuple[str, ...]]] = []

    for mask in range(1, 1 << len(axes)):
        active = tuple(axes[i] for i in range(len(axes)) if mask & (1 << i))
        # Unequal rays avoid a false zero caused by cancellation on the diagonal.
        patterns = [tuple(1.0 for _ in active)]
        if len(active) > 1:
            patterns.extend(
                tuple(0.5 if j == i else 1.0 for j in range(len(active)))
                for i in range(len(active))
            )

        ray_degrees: list[float] = []
        for coeffs in patterns:
            weights = dict(zip(active, coeffs))

            def rise(t: float) -> float:
                values = []
                for axis in _AXES:
                    value = getattr(corner, axis)
                    if axis in weights:
                        value += (_inward(corner, bounds, axis) * weights[axis]
                                  * t ** (1.0 / orders[axis]))
                    values.append(value)
                return p(Theta(*values)) - p0

            d_hi, d_lo = rise(t_hi), rise(t_lo)
            if d_hi <= 1e-30 or d_lo <= 1e-30:
                continue
            q = log(d_hi / d_lo) / log(ratio)
            if 0.0 < q < 1.0:
                ray_degrees.append(q)
        if ray_degrees:
            # A crease can vanish on one ray (for example |x-y| on x=y).
            # Roundoff there must not masquerade as a lower weighted degree;
            # the median across diagonal and unequal rays rejects that artifact.
            ray_degrees.sort()
            modes.append((ray_degrees[len(ray_degrees) // 2], active))
    return modes


def combined_screen(
    base_cand: Candidate,
    pert_cand: Candidate,
    bounds: BoxBounds | None = None,
) -> CombinedResult:
    """
    Unified test using base-adapted weighted homogeneity.  If the base drop is
    sum A_i*x_i^beta_i and P has weighted degree q under
    x_i -> t^(1/beta_i)*x_i, the gap exponent is p = 1/(1-q).  For an isotropic
    base this reduces to beta/(beta-alpha).  Joint rays detect coupled terms
    that vanish on every coordinate axis.
    """
    from math import log as _log

    from .interaction_search import _local_max

    bounds = bounds or default_nonlinear_bounds()
    try:
        r = compile_expression(base_cand.expr)
        p = compile_expression(pert_cand.expr)
    except UnsafeExpression as exc:
        return CombinedResult(base_cand.name, pert_cand.name, ok=False, reason=str(exc))

    base = CustomBase(r)
    try:
        corner, vval = vertex_maximize(base, bounds)
        _, gval, _, _ = base_global_search(base, bounds)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return CombinedResult(base_cand.name, pert_cand.name, ok=False, reason=f"eval: {exc}")
    if gval > vval + 1e-9:
        return CombinedResult(base_cand.name, pert_cand.name, ok=True,
                              base_self_fails=True, breaks=True)

    ders = inward_derivatives(base, corner, bounds)
    flat = [a for a in ("lam", "sigma") if abs(ders[a]) <= 1e-5]
    if not flat:
        return CombinedResult(base_cand.name, pert_cand.name, ok=True, breaks=False,
                              reason="strict base corner")

    measured_orders = {a: base_flatness_order(base, corner, bounds, a) for a in flat}
    unpenalized = tuple(a for a, order in measured_orders.items() if order <= 1.0)
    if unpenalized:
        return CombinedResult(
            base_cand.name, pert_cand.name, ok=True, breaks=False,
            reason="base has an unpenalized/non-coercive flat direction",
            active_axes=unpenalized,
            base_orders=tuple(measured_orders.items()),
        )
    orders = measured_orders
    modes = _weighted_push_modes(p, corner, bounds, orders)
    if not modes:
        return CombinedResult(base_cand.name, pert_cand.name, ok=True, breaks=False,
                              reason="no positive weighted mode with 0 < q < 1")
    # Smaller p means a larger asymptotic gap and therefore dominates. Prefer a
    # coordinate ray when predictions tie, so legacy beta/alpha fields remain
    # directly interpretable for separable/isotropic examples.
    predicted_modes = [(1.0 / (1.0 - degree), degree, axes) for degree, axes in modes]
    best_prediction = min(item[0] for item in predicted_modes)
    # Numerically estimated degrees on an axis and on a joint ray can differ in
    # the fourth decimal for the same leading monomial. Treat those as a tie and
    # prefer the lower-dimensional ray; otherwise cancellation artifacts can
    # incorrectly relabel a one-axis optimum as coupled.
    eligible = [item for item in predicted_modes if item[0] <= best_prediction + 0.02]
    _, q, active = min(eligible, key=lambda item: (len(item[2]), item[0]))
    predicted = 1.0 / (1.0 - q)
    axis = "+".join(active)
    if len(active) == 1:
        beta = orders[active[0]]
        alpha = q * beta
    else:
        # Effective weighted coordinates have base degree one and P degree q.
        beta, alpha = 1.0, q

    def gap(s: float) -> float:
        def combined(theta: Theta) -> float:
            return base(theta) + s * p(theta)
        return _local_max(combined, bounds, corner, passes=10, samples=800) - combined(corner)

    try:
        if len(active) == 1:
            exponent, g1, g2, scales = adaptive_axis_gap_exponent(
                base, p, corner, bounds, active[0]
            )
        else:
            # Deep scales expose the asymptotic exponent when a higher-degree
            # term contaminates a genuinely coupled leader.
            scales = (0.0003125, 0.000078125)
            g1, g2 = gap(scales[0]), gap(scales[1])
            if g1 <= 1e-13 or g2 <= 1e-13:
                scales = (0.02, 0.005)
                g1, g2 = gap(scales[0]), gap(scales[1])
            exponent = _log(g1 / g2) / _log(scales[0] / scales[1]) if (g1 > 1e-13 and g2 > 1e-13) else 0.0
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return CombinedResult(base_cand.name, pert_cand.name, ok=False, reason=f"search: {exc}")

    return CombinedResult(
        base_cand.name, pert_cand.name, ok=True, beta=beta, alpha=alpha, axis=axis,
        predicted_exponent=predicted, measured_exponent=exponent,
        weighted_degree=q, active_axes=active,
        base_orders=tuple((a, orders[a]) for a in flat),
        breaks=g1 > (1e-30 if len(active) == 1 else 1e-12),
        measurement_scales=scales,
    )


COMBINED_PROMPT = """You are stress-testing a UNIFIED law about when corner search
fails. Setting: maximize C = b + k + r(lam,sigma) + s*P(lam,sigma,b,k) over
lam,sigma in [0,1], b in [0,2], k in [0,3]. Corner (1,0,2,3). Write x=1-lam, y=sigma.

The corrected law uses ANISOTROPIC WEIGHTED DEGREE. If
r(0)-r(x,y) ~ A*x^beta_x+B*y^beta_y and a positive perturbation monomial is
x^alpha_x*y^alpha_y, set q=alpha_x/beta_x+alpha_y/beta_y. For q<1 the gap is
Delta ~ s^(1/(1-q)). The familiar beta/(beta-alpha) is only the isotropic case.

Propose {n} PAIRS (base r, perturbation P) designed to break this. Vary both:
  - base flatness beta in 2,3,4,6,8 incl. odd and anisotropic (-x^2 - y^6)
  - perturbation degree alpha in (0,1] incl. non-smooth (sqrt), and COUPLED P
  - combine them: flat base AND non-smooth coupled perturbation together
  - attack the corrected weighted law with sums, cancellations, and mixed monomials
  - try bases whose max is off-corner, and P that fights the base curvature

r must have an ISOLATED local maximum at (1,0), with positive-order penalties
in BOTH x and y; never omit either axis. Use lam, sigma, and for P also b, k.
Allowed: + - * / ** and sin cos tan exp log sqrt abs tanh atan sinh
cosh, and pi. Numeric exponents only. No other names.

Each base and pert expression must be at most 150 characters. Return only the
expression text in each field: never prefix it with r(...)=, P(...)=, x=, or y=.

Reply JSON only:
{{"pairs":[{{"name":"slug","base":"r in lam,sigma","pert":"P","why":"what it attacks"}}]}}
"""


def parse_pairs(text: Any) -> list[tuple[Candidate, Candidate]]:
    """Parse model (base, perturbation) pairs; drop any that fail the whitelist."""
    import json
    import re

    if not isinstance(text, str):
        return []
    payload: Any = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                payload = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []
    if not isinstance(payload, dict) or not isinstance(payload.get("pairs"), list):
        return []
    out: list[tuple[Candidate, Candidate]] = []
    for item in payload["pairs"]:
        if not isinstance(item, dict):
            continue
        b_expr, p_expr = str(item.get("base", "")).strip(), str(item.get("pert", "")).strip()
        name = re.sub(r"[^A-Za-z0-9_]", "_", str(item.get("name", "")))[:20] or f"pair{len(out)}"
        if not b_expr or not p_expr:
            continue
        try:
            compile_expression(b_expr)
            compile_expression(p_expr)
        except UnsafeExpression:
            continue
        note = str(item.get("why", ""))[:80]
        out.append((Candidate(name + "_b", b_expr, "model", note),
                    Candidate(name + "_p", p_expr, "model", note)))
    return out


def propose_pairs(
    n: int = 16, *, model: str | None = None, base_url: str | None = None,
    preset: str | None = None, focus: str = "",
) -> tuple[list[tuple[Candidate, Candidate]], str]:
    from . import interaction_search as isc

    return isc.propose_candidates(
        n, model=model, base_url=base_url, preset=preset,
        prompt=COMBINED_PROMPT.format(n=n) + focus, parser=parse_pairs,
    )


def base_report(results: list[BaseScreenResult]) -> list[str]:
    breaks = [r for r in results if r.ok and r.breaks and not r.base_self_fails]
    self_fail = [r for r in results if r.ok and r.base_self_fails]
    strict = [r for r in results if r.ok and not r.breaks]
    rejected = [r for r in results if not r.ok]
    lines = [
        f"Base search: {len(results)} candidate base objectives",
        "",
        f"  {len(breaks)} break under perturbation (flat corner), "
        f"{len(strict)} strict (positive threshold), "
        f"{len(self_fail)} fail on their own, {len(rejected)} rejected",
        "",
        "FLAT CORNERS (master law p = beta/(beta-1), linear perturbation):",
    ]
    lines += [r.row() for r in sorted(breaks, key=lambda r: r.flatness_order)]
    if strict:
        lines += ["", "STRICT CORNERS (localization safe for small s):"]
        lines += [f"  {r.candidate.name:<16} corner={r.corner} flat_axis={r.flat_axis}" for r in strict]
    if self_fail:
        lines += ["", "BASE ITSELF FAILS (max not at a vertex even at s=0):"]
        lines += [r.row() for r in self_fail]
    if rejected:
        lines += ["", "REJECTED:"]
        lines += [r.row() for r in rejected]
    return lines
