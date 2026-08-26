"""
Feasible hypersurface H as a box: separate monotonicity in (b, k), quasiconvex r in (λ, σ).

Under these assumptions the composite objective attains its global maximum at
θ_max in ext(H). For independent interval constraints, θ_max is the corner
(λ_max, σ_min, k_max, B_max).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isclose
from typing import Iterator


@dataclass(frozen=True)
class BoxBounds:
    """Independent interval constraints: H = [λ_lo,λ_hi] x [σ_lo,σ_hi] x [b_lo,b_hi] x [k_lo,k_hi]."""

    lam: tuple[float, float]
    sigma: tuple[float, float]
    b: tuple[float, float]
    k: tuple[float, float]

    def __post_init__(self) -> None:
        for name, pair in (
            ("lam", self.lam),
            ("sigma", self.sigma),
            ("b", self.b),
            ("k", self.k),
        ):
            lo, hi = pair
            if lo > hi:
                raise ValueError(f"{name}: lo > hi ({lo} > {hi})")

    @property
    def lam_max(self) -> float:
        return self.lam[1]

    @property
    def lam_min(self) -> float:
        return self.lam[0]

    @property
    def sigma_min(self) -> float:
        return self.sigma[0]

    @property
    def sigma_max(self) -> float:
        return self.sigma[1]

    @property
    def b_max(self) -> float:
        return self.b[1]

    @property
    def k_max(self) -> float:
        return self.k[1]

    def is_compact(self) -> bool:
        return True  # closed bounded box in R^4


@dataclass(frozen=True)
class Theta:
    """Point θ = (λ, σ, b, k) in H. B denotes the b-coordinate at its maximum (B_max)."""

    lam: float
    sigma: float
    b: float
    k: float

    def in_box(self, bounds: BoxBounds, *, tol: float = 1e-9) -> bool:
        def inside(v: float, interval: tuple[float, float]) -> bool:
            lo, hi = interval
            return lo - tol <= v <= hi + tol

        return (
            inside(self.lam, bounds.lam)
            and inside(self.sigma, bounds.sigma)
            and inside(self.b, bounds.b)
            and inside(self.k, bounds.k)
        )

    def project_bk_max(self, bounds: BoxBounds) -> Theta:
        """
        Projection onto (b, k) at highest feasible values in H.
        C(θ) is dominated by C at this projection when C is separately increasing in b, k.
        """
        return Theta(self.lam, self.sigma, bounds.b_max, bounds.k_max)

    def corner_maximizer(self, bounds: BoxBounds) -> Theta:
        """
        Box vertex for global maximum under the lecture hypotheses:
        (λ_max, σ_min, k_max, B_max).
        """
        return Theta(bounds.lam_max, bounds.sigma_min, bounds.b_max, bounds.k_max)

    def as_corner_tuple(self) -> tuple[float, float, float, float]:
        return (self.lam, self.sigma, self.b, self.k)


def _quasiconvex_decreasing_sigma(sigma: float, bounds: BoxBounds) -> float:
    """r contribution: quasiconvex-decreasing along σ (minimize σ)."""
    span = bounds.sigma_max - bounds.sigma_min
    if span <= 0:
        return 1.0
    t = (sigma - bounds.sigma_min) / span
    return 1.0 - t * t


def _quasiconvex_increasing_lambda(lam: float, bounds: BoxBounds) -> float:
    """r contribution: quasiconvex-increasing along λ (maximize λ)."""
    span = bounds.lam_max - bounds.lam_min
    if span <= 0:
        return 1.0
    t = (lam - bounds.lam_min) / span
    return 1.0 - (1.0 - t) ** 2


@dataclass
class CompositeObjective:
    """
    Composite = C(b, k) + r(λ, σ).

    - C separately (monotonically) increasing in b and k
    - r quasiconvex-decreasing in σ, quasiconvex-increasing in λ
    """

    weight_b: float = 1.0
    weight_k: float = 1.0
    weight_r: float = 1.0

    def C(self, theta: Theta) -> float:
        return self.weight_b * theta.b + self.weight_k * theta.k

    def r(self, theta: Theta, bounds: BoxBounds) -> float:
        return self.weight_r * (
            _quasiconvex_increasing_lambda(theta.lam, bounds)
            + _quasiconvex_decreasing_sigma(theta.sigma, bounds)
        )

    def composite(self, theta: Theta, bounds: BoxBounds) -> float:
        return self.C(theta) + self.r(theta, bounds)

    def C_dominated_by_bk_projection(
        self, theta: Theta, bounds: BoxBounds, *, tol: float = 1e-9
    ) -> bool:
        """C(θ) <= C(project onto (b_max, k_max)) when C is separately increasing in b, k."""
        proj = theta.project_bk_max(bounds)
        return self.C(theta) <= self.C(proj) + tol

    def C_at_bk_projection(self, theta: Theta, bounds: BoxBounds) -> float:
        return self.C(theta.project_bk_max(bounds))


@dataclass(frozen=True)
class MaximizerResult:
    theta_max: Theta
    value: float
    is_vertex: bool
    matches_box_corner: bool
    searched_vertices: int


class HypersurfaceBox:
    """Compact feasible set H (box) and Weierstrass-style maximization on ext(H)."""

    def __init__(self, bounds: BoxBounds, objective: CompositeObjective | None = None) -> None:
        self.bounds = bounds
        self.objective = objective or CompositeObjective()

    def ext_H(self) -> list[Theta]:
        """Vertices of box H: all 2^4 corners."""
        corners: list[Theta] = []
        for lam, sigma, b, k in product(
            self.bounds.lam,
            self.bounds.sigma,
            self.bounds.b,
            self.bounds.k,
        ):
            corners.append(Theta(lam, sigma, b, k))
        return corners

    def enumerate_box_grid(self, steps: int = 5) -> Iterator[Theta]:
        """Interior + boundary samples for dominance checks (not exhaustive)."""
        if steps < 2:
            steps = 2

        def lerp(lo: float, hi: float, i: int) -> float:
            return lo + (hi - lo) * i / (steps - 1)

        for i in range(steps):
            for j in range(steps):
                for m in range(steps):
                    for n in range(steps):
                        yield Theta(
                            lerp(*self.bounds.lam, i),
                            lerp(*self.bounds.sigma, j),
                            lerp(*self.bounds.b, m),
                            lerp(*self.bounds.k, n),
                        )

    def maximize_on_ext_H(self) -> MaximizerResult:
        """
        Global maximizer θ_max in ext(H) by exhaustive vertex search.
        Continuous objective on compact H attains a maximum (Weierstrass);
        under separate monotonicity in b,k and quasiconvex r in λ,σ it lies at a vertex.
        """
        best = self.bounds.lam[0], self.bounds.sigma[0], self.bounds.b[0], self.bounds.k[0]
        best_theta = Theta(*best)
        best_val = self.objective.composite(best_theta, self.bounds)
        for theta in self.ext_H():
            val = self.objective.composite(theta, self.bounds)
            if val > best_val:
                best_val, best_theta = val, theta

        corner = best_theta.corner_maximizer(self.bounds)
        return MaximizerResult(
            theta_max=best_theta,
            value=best_val,
            is_vertex=True,
            matches_box_corner=all(
                isclose(a, b, rel_tol=0, abs_tol=1e-9)
                for a, b in zip(
                    best_theta.as_corner_tuple(),
                    corner.as_corner_tuple(),
                    strict=True,
                )
            ),
            searched_vertices=len(self.ext_H()),
        )

    def verify_corner_formula(self) -> bool:
        """θ_max should equal (λ_max, σ_min, k_max, B_max) for box H."""
        result = self.maximize_on_ext_H()
        corner = result.theta_max.corner_maximizer(self.bounds)
        return result.matches_box_corner and result.theta_max.as_corner_tuple() == corner.as_corner_tuple()

    def verify_C_dominance_on_grid(self, steps: int = 4) -> bool:
        """Every sampled θ has C(θ) <= C(θ with b,k at max feasible)."""
        obj = self.objective
        for theta in self.enumerate_box_grid(steps):
            if not obj.C_dominated_by_bk_projection(theta, self.bounds):
                return False
        return True


def box_theorem_summary() -> str:
    return (
        "Box H theorem codified:\n"
        "  - C increasing separately in b, k => dominated by (b_max, k_max) projection.\n"
        "  - r quasiconvex in lambda (up), sigma (down) => marginal extrema at axis ends.\n"
        "  - Composite maximum on compact H => theta_max in ext(H) (Weierstrass + vertices).\n"
        "  - Independent intervals => corner (lambda_max, sigma_min, k_max, B_max).\n"
    )


def demonstrate_box(
    *,
    lam: tuple[float, float] = (0.0, 1.0),
    sigma: tuple[float, float] = (0.0, 1.0),
    b: tuple[float, float] = (0.0, 2.0),
    k: tuple[float, float] = (0.0, 3.0),
) -> list[str]:
    bounds = BoxBounds(lam=lam, sigma=sigma, b=b, k=k)
    hs = HypersurfaceBox(bounds)
    theta = Theta(0.3, 0.7, 1.0, 1.5)
    obj = hs.objective
    result = hs.maximize_on_ext_H()

    lines = [
        f"Sample theta: (lam,sigma,b,k)={theta.as_corner_tuple()}",
        f"  C(theta)={obj.C(theta):.3f}  C at (b_max,k_max) proj={obj.C_at_bk_projection(theta, bounds):.3f}",
        f"  dominated: {obj.C_dominated_by_bk_projection(theta, bounds)}",
        f"theta_max: {result.theta_max.as_corner_tuple()}  value={result.value:.3f}",
        f"  matches (lam_max, sigma_min, k_max, B_max): {result.matches_box_corner}",
        f"  vertices searched: {result.searched_vertices}",
        f"  corner formula OK: {hs.verify_corner_formula()}",
        f"  C dominance on grid: {hs.verify_C_dominance_on_grid()}",
    ]
    return lines
