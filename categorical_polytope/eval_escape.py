"""
Safety-evaluation escape: the V-theorems as conditional statements about how a
safety EVALUATION can be fooled.

HONESTY CONTRACT. Every result here is a theorem about an OPTIMIZATION MODEL of
evaluation: an adversary maximizes a harm score H over an input space, and an
evaluator that uses a particular strategy (per-axis tests, boundary checks, a
finite grid, a tolerance) certifies "safe". The theorems bound the gap between
what the evaluator certifies and the true max. They are PROVEN inside this model.

They are NOT measurements of any deployed LLM, and they do not prove real LLM
safety fails. Each carries an explicit MODEL assumption: "if a real evaluation
has this structure, it inherits this blind spot." Read them as design warnings
for how to build evaluations, not as empirical claims. The mapping to LLMs is the
assumption, not the result.

This is defensive analysis: it says where false assurance can come from, to argue
for denser, coupled, adversary-aware, tolerance-free evaluation.

Stdlib only. Reuses the proven machinery in `vertex_threshold`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, gamma, pi, sqrt

from .hypersurface_box import Theta
from .nonlinear_objective import HypersurfacePlusInteraction, default_nonlinear_bounds
from .vertex_threshold import (
    directional_gap,
    displacement,
    fractional_exponent_law,
    optimality_gap,
    universal_gap,
    vertex_margin,
)


@dataclass(frozen=True)
class Claim:
    """One conditional result: proven inside the model, assumed onto LLMs."""

    mode: str
    model_assumption: str      # what must be true of a real evaluation
    proven: str                # what the theorem establishes inside the model
    quantitative: str          # the number/scaling
    operational: str           # what to do differently in an evaluation
    ethical: str               # what false-assurance it removes

    def render(self) -> list[str]:
        return [
            f"### {self.mode}",
            f"- MODEL assumption : {self.model_assumption}",
            f"- Proven (in model): {self.proven}",
            f"- Quantitative     : {self.quantitative}",
            f"- Operational      : {self.operational}",
            f"- Ethical          : {self.ethical}",
        ]


# --------------------------------------------------------------------------
# The new, fully general result: evaluation coverage (generalises V.5)
# --------------------------------------------------------------------------


def grid_miss_radius(n: int, d: int) -> tuple[float, int]:
    """
    Covering radius of the largest endpoint-including Cartesian grid that fits
    within a budget of n points in [0,1]^d. Returns
    (radius, points_per_axis); the grid actually uses m**d <= n points.

    For m >= 2 the exact L2 covering radius is half the cell diagonal,
    sqrt(d)/(2(m-1)). With one point, placing it at the cube center gives radius
    sqrt(d)/2. Generalises V.5 to arbitrary dimension.
    """
    if n < 1 or d < 1:
        raise ValueError("n and d must be positive")
    m = max(1, int(n ** (1.0 / d)))
    # Correct floating-point rounding at exact integer powers.
    while (m + 1) ** d <= n:
        m += 1
    while m**d > n:
        m -= 1
    if m == 1:
        return 0.5 * sqrt(d), 1
    h = 1.0 / (m - 1)
    return 0.5 * h * sqrt(d), m


def samples_to_catch(delta: float, d: int) -> int:
    """
    Points needed for a uniform grid to guarantee catching every unsafe ball of
    radius >= delta: n >= (1 + sqrt(d)/(2 delta))^d. Exponential in d -- the
    curse of dimensionality for behavioral safety testing.
    """
    if delta <= 0.0 or d < 1:
        raise ValueError("delta and d must be positive")
    m = ceil(1.0 + sqrt(d) / (2.0 * delta))
    return m**d


def unit_ball_volume(d: int) -> float:
    """Lebesgue volume v_d = pi^(d/2)/Gamma(d/2+1) of the unit L2 ball."""
    if d < 1:
        raise ValueError("d must be positive")
    return pi ** (d / 2.0) / gamma(d / 2.0 + 1.0)


def adversarial_miss_radius(n: int, d: int) -> float:
    """
    Volume lower bound on the covering radius for ANY n sample points:

        rho(S) >= (1 / (n*v_d))^(1/d).

    If n radius-r balls cover the unit-volume cube, their total Euclidean volume
    n*v_d*r^d must be at least one. Thus every n-point behavioral test leaves an
    empty metric ball at least this large. This is not restricted to grids.
    """
    if n < 1 or d < 1:
        raise ValueError("n and d must be positive")
    return (1.0 / (n * unit_ball_volume(d))) ** (1.0 / d)


def coverage_claim() -> Claim:
    return Claim(
        mode="Grids miss failures (evaluation coverage)",
        model_assumption="behavioral eval = finite sample of inputs; 'safe' iff all sampled pass",
        proven=(
            "an n-point test cannot rule out a failure supported in an empty ball; "
            "its radius is the test set's covering radius"
        ),
        quantitative=(
            "arbitrary samples: rho >= v_d^(-1/d)*n^(-1/d); Cartesian grid: "
            "rho = 0.5*sqrt(d)/(n^(1/d)-1), so delta=0.05 in d=20 needs "
            "46^20 = 1.80e33 grid samples"
        ),
        operational=(
            "report the metric and covering radius; state any minimum failure-width "
            "or regularity assumption; sample adaptively/adversarially"
        ),
        ethical=(
            "'passed N tests' only excludes failures at tested points unless a "
            "coverage/regularity argument extends those observations"
        ),
    )


# --------------------------------------------------------------------------
# The other five modes, each pulled from a proven V-theorem
# --------------------------------------------------------------------------


def separability_claim(s: float = 0.05) -> Claim:
    bounds = default_nonlinear_bounds()
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    # a coupled harm term vs. its per-axis (separable) reading
    from .interaction_search import compile_expression

    coupled = compile_expression("((1-lam)**2 + sigma**2)**0.5")
    add = universal_gap(base, coupled, bounds, s)
    dirc = directional_gap(base, coupled, bounds, s)
    return Claim(
        mode="Separable reasoning is fragile (coupling)",
        model_assumption="eval scores each risk dimension independently and sums/maxes them",
        proven="per-axis scoring mis-estimates a coupled objective; the true optimum is off every axis",
        quantitative=f"additive reading over/under-shoots directional truth (here {add:.2e} vs {dirc:.2e}); by Cauchy-Schwarz the error factor is up to sqrt(#coupled axes)",
        operational="score jointly over interacting dimensions, not one attribute at a time",
        ethical="'safe on each axis' does not imply 'safe'; independence is an assumption, rarely a fact",
    )


def threshold_zero_claim() -> Claim:
    bounds = default_nonlinear_bounds()
    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    vm = vertex_margin(base, bounds)
    return Claim(
        mode="Vertex-like safety boundaries have zero margin",
        model_assumption="'safe region' is a box; reward is (near-)flat along the safe boundary",
        proven="if the boundary optimum is degenerate (zero inward slope), the safety threshold s* = 0",
        quantitative=f"measured margin at the boundary corner = {vm.margin:.2e} (degenerate); s* = 0",
        operational="require a STRICT margin at the boundary (nonzero inward slope); measure it, don't assume it",
        ethical="a boundary that is merely 'not exceeded' can be exceeded by an arbitrarily small push",
    )


def nonsmooth_claim(s: float = 0.01) -> Claim:
    # smooth (alpha=1) vs non-smooth (alpha=0.5) perturbation gap ratio
    _, g_lin = fractional_exponent_law(1.0, s)
    _, g_sqrt = fractional_exponent_law(0.5, s)
    return Claim(
        mode="Non-smooth prompts enlarge the gap",
        model_assumption="adversarial manipulation can be non-smooth (discrete tokens, discontinuous edits)",
        proven="a degree-alpha<1 perturbation opens a gap with exponent 2/(2-alpha) < 2, unboundedly larger than smooth at small s",
        quantitative=f"at s={s}, sqrt-type gap {g_sqrt:.2e} vs linear {g_lin:.2e} = {g_sqrt/g_lin:.0f}x; ratio -> infinity as s -> 0",
        operational="test discrete/non-smooth attacks explicitly; smooth-perturbation robustness does not transfer",
        ethical="robustness measured against smooth changes overstates safety against real (discrete) attacks",
    )


def base_flatness_claim() -> Claim:
    return Claim(
        mode="Flatter safety objectives break harder",
        model_assumption="the safety reward is flat to order beta at the boundary (not just quadratic)",
        proven="the escape gap scales as s^(beta/(beta-alpha)); larger beta -> exponent -> 1 -> bigger gap",
        quantitative="beta=2 -> s^2; beta=6 -> s^1.2; a very flat reward makes the gap almost linear in attack strength",
        operational="prefer sharply-curved safety objectives; measure the flatness order at the boundary",
        ethical="'the reward barely changes near the boundary' is a vulnerability, not a comfort",
    )


def tolerance_claim(s: float = 0.05, tol: float = 0.05) -> Claim:
    gap = optimality_gap(s)  # true gap for face_bowl at this s
    return Claim(
        mode="Tolerance thresholds hide real failures",
        model_assumption="eval certifies 'safe' when a measured gap/score is below a fixed tolerance",
        proven="the true gap is positive but below tolerance exactly in the small-attack regime the tolerance was meant to allow",
        quantitative=f"at s={s} the true gap is {gap:.2e}; a tol={tol} certifies 'safe' while localization has already failed",
        operational="report the raw gap and its scaling exponent, never a boolean pass/fail against a tolerance",
        ethical="a tolerance converts a real, small, exploitable failure into a green checkmark",
    )


def all_claims() -> list[Claim]:
    return [
        coverage_claim(),
        separability_claim(),
        threshold_zero_claim(),
        nonsmooth_claim(),
        base_flatness_claim(),
        tolerance_claim(),
    ]


def capacity_report() -> list[str]:
    lines = [
        "Safety-evaluation capacity analysis (conditional; see HONESTY CONTRACT)",
        "",
        "Each item: a proven statement about an optimization MODEL of evaluation,",
        "plus the explicit assumption under which it maps to a real LLM eval.",
        "These are design warnings, not measurements of any deployed system.",
        "",
    ]
    for c in all_claims():
        lines += c.render()
        lines.append("")
    return lines
