"""
Non-quadratic objectives beyond the Fisher quadratic proxy.

Uses local empirical Fisher information at the probe and vertex search
when the structural hypotheses still apply; documents failure modes when
interaction is strong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, exp, log, sin, sqrt
from typing import Protocol

from .formal_bounds import (
    TheoremConstants,
    certify_suboptimality,
    theorem_constants_from_fisher,
)
from .fisher_factorization import BlockFisher, BlockLayout, LeakageReport, build_block_fisher
from .hypersurface_box import BoxBounds, CompositeObjective, HypersurfaceBox, Theta


class Objective(Protocol):
    """General objective on box H (maximize)."""

    def __call__(self, theta: Theta) -> float: ...


@dataclass(frozen=True)
class HypersurfacePlusInteraction:
    """
    Non-quadratic extension of hypersurface C:

        C = g(b) + h(k) + r(lam,sigma) + strength * interaction(lam,sigma,b,k)

    interaction modes:
      - 'bilinear': lam*sigma + b*k  (still vertex-friendly on a box)
      - 'triple': lam*b*k
      - 'softplus': log(1+exp(lam))*log(1+exp(b))  (non-quadratic)
      - 'trig': sin(pi*lam)*cos(pi*sigma)*b  (can break pure vertex localization)
      - 'face_bowl': (1-(lam-0.5)^2)*(1-(sigma-0.5)^2)  (interior of face beats corners)
    """

    bounds: BoxBounds
    strength: float = 0.0
    interaction: str = "bilinear"
    weight_b: float = 1.0
    weight_k: float = 1.0
    weight_r: float = 1.0

    def _base(self) -> CompositeObjective:
        return CompositeObjective(
            weight_b=self.weight_b,
            weight_k=self.weight_k,
            weight_r=self.weight_r,
        )

    def _interaction_term(self, theta: Theta) -> float:
        s = self.strength
        if s == 0.0:
            return 0.0
        lam, sigma, b, k = theta.lam, theta.sigma, theta.b, theta.k
        mode = self.interaction
        if mode == "bilinear":
            return s * (lam * sigma + b * k)
        if mode == "triple":
            return s * lam * b * k
        if mode == "softplus":
            return s * log(1.0 + exp(min(lam, 20))) * log(1.0 + exp(min(b, 20)))
        if mode == "trig":
            return s * sin(3.14159 * lam) * cos(3.14159 * sigma) * b
        if mode == "face_bowl":
            return s * (1.0 - (lam - 0.5) ** 2) * (1.0 - (sigma - 0.5) ** 2)
        raise ValueError(f"unknown interaction: {mode!r}")

    def __call__(self, theta: Theta) -> float:
        base = HypersurfaceBox(self.bounds, self._base())
        return base.objective.composite(theta, self.bounds) + self._interaction_term(theta)

def default_nonlinear_bounds() -> BoxBounds:
    return BoxBounds(lam=(0.0, 1.0), sigma=(0.0, 1.0), b=(0.0, 2.0), k=(0.0, 3.0))


def enumerate_ext_vertices(bounds: BoxBounds) -> list[Theta]:
    from itertools import product

    return [
        Theta(lam, sigma, b, k)
        for lam, sigma, b, k in product(bounds.lam, bounds.sigma, bounds.b, bounds.k)
    ]


def _grid_candidates(bounds: BoxBounds, steps: int = 5) -> list[Theta]:
    """Face/interior grid for nonlinear search beyond vertices only."""
    from itertools import product

    def lerp(interval: tuple[float, float], i: int) -> float:
        lo, hi = interval
        return lo if steps <= 1 else lo + (hi - lo) * i / (steps - 1)

    out: list[Theta] = []
    for i in range(steps):
        for j in range(steps):
            for m in range(steps):
                for n in range(steps):
                    out.append(
                        Theta(
                            lerp(bounds.lam, i),
                            lerp(bounds.sigma, j),
                            lerp(bounds.b, m),
                            lerp(bounds.k, n),
                        )
                    )
    return out


def vertex_maximize(
    objective: Objective,
    bounds: BoxBounds,
) -> tuple[Theta, float]:
    """Global max over ext(H) by exhaustive vertex search (Theorem 1 regime)."""
    best = enumerate_ext_vertices(bounds)[0]
    best_val = objective(best)
    for theta in enumerate_ext_vertices(bounds)[1:]:
        val = objective(theta)
        if val > best_val:
            best_val, best = val, theta
    return best, best_val


def grid_maximize(
    objective: Objective,
    bounds: BoxBounds,
    *,
    steps: int = 7,
) -> tuple[Theta, float]:
    """Reference max on a grid (catches non-vertex optima)."""
    best = _grid_candidates(bounds, steps)[0]
    best_val = objective(best)
    for theta in _grid_candidates(bounds, steps)[1:]:
        val = objective(theta)
        if val > best_val:
            best_val, best = val, theta
    return best, best_val


def separable_block_maximize(
    objective: Objective,
    bounds: BoxBounds,
    *,
    passes: int = 3,
) -> tuple[Theta, float]:
    """Block coordinate ascent on box axes (not restricted to vertices only)."""
    theta = Theta(
        bounds.lam[0],
        bounds.sigma[1],
        bounds.b[0],
        bounds.k[0],
    )
    intervals = {
        "lam": bounds.lam,
        "sigma": bounds.sigma,
        "b": bounds.b,
        "k": bounds.k,
    }
    order = ("lam", "sigma", "b", "k")

    for _ in range(passes):
        for name in order:
            lo, hi = intervals[name]
            best_local = objective(theta)
            best_coord = getattr(theta, name)
            steps = [lo, hi] if hi != lo else [lo]
            for t in steps:
                trial = Theta(
                    t if name == "lam" else theta.lam,
                    t if name == "sigma" else theta.sigma,
                    t if name == "b" else theta.b,
                    t if name == "k" else theta.k,
                )
                val = objective(trial)
                if val > best_local:
                    best_local, best_coord = val, t
            theta = Theta(
                best_coord if name == "lam" else theta.lam,
                best_coord if name == "sigma" else theta.sigma,
                best_coord if name == "b" else theta.b,
                best_coord if name == "k" else theta.k,
            )
    return theta, objective(theta)


def empirical_fisher_at(
    objective: Objective,
    theta: Theta,
    bounds: BoxBounds,
    *,
    h: float = 1e-4,
    layout: BlockLayout | None = None,
) -> BlockFisher:
    """
    Empirical Fisher / Hessian proxy at theta via finite differences.

    F_ij ~ -partial^2 C / partial theta_i partial theta_j  (for maximization).
    """
    layout = layout or BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
    n = 4
    coords = [theta.lam, theta.sigma, theta.b, theta.k]
    spans = [
        bounds.lam[1] - bounds.lam[0],
        bounds.sigma[1] - bounds.sigma[0],
        bounds.b[1] - bounds.b[0],
        bounds.k[1] - bounds.k[0],
    ]

    def at_vec(v: list[float]) -> float:
        return objective(Theta(v[0], v[1], v[2], v[3]))

    def step(i: int) -> float:
        return max(h, 1e-6 * spans[i])

    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ei = [0.0] * n
        ei[i] = step(i)
        vpp = coords[:]
        vmm = coords[:]
        vp = coords[:]
        vm = coords[:]
        vpp[i] = min(coords[i] + 2 * step(i), [bounds.lam[1], bounds.sigma[1], bounds.b[1], bounds.k[1]][i])
        vmm[i] = max(coords[i] - 2 * step(i), [bounds.lam[0], bounds.sigma[0], bounds.b[0], bounds.k[0]][i])
        vp[i] = min(coords[i] + step(i), [bounds.lam[1], bounds.sigma[1], bounds.b[1], bounds.k[1]][i])
        vm[i] = max(coords[i] - step(i), [bounds.lam[0], bounds.sigma[0], bounds.b[0], bounds.k[0]][i])
        mat[i][i] = -(at_vec(vpp) - 2 * at_vec(coords) + at_vec(vmm)) / (step(i) ** 2)
        for j in range(i + 1, n):
            ej = [0.0] * n
            ej[j] = step(j)
            vpp_ij = coords[:]
            vpp_ij[i] = vp[i]
            vpp_ij[j] = vp[j]
            vpm_ij = coords[:]
            vpm_ij[i] = vp[i]
            vpm_ij[j] = vm[j]
            vmp_ij = coords[:]
            vmp_ij[i] = vm[i]
            vmp_ij[j] = vp[j]
            vmm_ij = coords[:]
            vmm_ij[i] = vm[i]
            vmm_ij[j] = vm[j]
            off = -(
                at_vec(vpp_ij)
                - at_vec(vpm_ij)
                - at_vec(vmp_ij)
                + at_vec(vmm_ij)
            ) / (4 * step(i) * step(j))
            mat[i][j] = off
            mat[j][i] = off

    for i in range(n):
        if mat[i][i] < 1e-8:
            mat[i][i] = 1.0
    return BlockFisher(layout, tuple(tuple(row) for row in mat))


@dataclass(frozen=True)
class NonlinearAnalysis:
    objective_name: str
    interaction_strength: float
    theta_vertex: Theta
    value_vertex: float
    theta_grid: Theta | None
    value_grid: float | None
    theta_separable: Theta
    value_separable: float
    gap: float
    gap_vs_grid: float | None
    leakage: LeakageReport
    phi_bound: float
    certified: bool
    certify_reason: str
    vertex_equals_separable_corner: bool
    localization_at_vertex: bool


@dataclass
class NonlinearStudy:
    bounds: BoxBounds = field(default_factory=default_nonlinear_bounds)

    def analyze(
        self,
        *,
        strength: float = 0.0,
        interaction: str = "bilinear",
    ) -> NonlinearAnalysis:
        obj: Objective = HypersurfacePlusInteraction(
            self.bounds,
            strength=strength,
            interaction=interaction,
        )
        theta_v, val_v = vertex_maximize(obj, self.bounds)
        theta_g, val_g = grid_maximize(obj, self.bounds) if interaction == "face_bowl" else (None, None)
        theta_s, val_s = separable_block_maximize(obj, self.bounds)
        gap = val_v - val_s
        gap_grid = (val_g - val_v) if theta_g is not None else None

        probe_theta = theta_g if theta_g is not None else theta_v
        fisher = empirical_fisher_at(obj, probe_theta, self.bounds)
        leak = fisher.leakage()
        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(fisher.layout.n)],
            probe_theta.as_corner_tuple(),
        )
        certified, phi, reason = certify_suboptimality(leak.epsilon, gap, const)

        corner = Theta(
            self.bounds.lam_max,
            self.bounds.sigma_min,
            self.bounds.b_max,
            self.bounds.k_max,
        )
        at_corner = all(
            abs(getattr(theta_v, n) - getattr(corner, n)) < 1e-6
            for n in ("lam", "sigma", "b", "k")
        )
        loc_vertex = at_corner and (gap_grid is None or gap_grid < 0.05)

        return NonlinearAnalysis(
            objective_name=f"HypersurfacePlusInteraction({interaction})",
            interaction_strength=strength,
            theta_vertex=theta_v,
            value_vertex=val_v,
            theta_grid=theta_g,
            value_grid=val_g if theta_g else None,
            theta_separable=theta_s,
            value_separable=val_s,
            gap=gap,
            gap_vs_grid=gap_grid,
            leakage=leak,
            phi_bound=phi,
            certified=certified,
            certify_reason=reason,
            vertex_equals_separable_corner=at_corner,
            localization_at_vertex=loc_vertex,
        )


def lipschitz_gap_bound(
    lipschitz_L: float,
    theta_a: Theta,
    theta_b: Theta,
) -> float:
    """Non-quadratic fallback: |C(a)-C(b)| <= L ||a-b||."""
    dist = sqrt(
        (theta_a.lam - theta_b.lam) ** 2
        + (theta_a.sigma - theta_b.sigma) ** 2
        + (theta_a.b - theta_b.b) ** 2
        + (theta_a.k - theta_b.k) ** 2
    )
    return lipschitz_L * dist


def demonstrate_nonlinear() -> list[str]:
    study = NonlinearStudy()
    lines = ["Non-quadratic objectives (empirical Fisher at vertex probe):", ""]
    for strength, mode in [
        (0.0, "bilinear"),
        (0.5, "bilinear"),
        (0.5, "triple"),
        (1.0, "face_bowl"),
        (2.0, "face_bowl"),
    ]:
        a = study.analyze(strength=strength, interaction=mode)
        grid_note = ""
        if a.gap_vs_grid is not None:
            grid_note = f"  grid_beats_vertex={a.gap_vs_grid:.4f}  theta_g={a.theta_grid.as_corner_tuple() if a.theta_grid else None}"
        lines.append(
            f"  {mode} strength={strength:.2f}  gap={a.gap:.4f}  eps={a.leakage.epsilon:.4f}  "
            f"cert={a.certified}  vertex_ok={a.localization_at_vertex}"
        )
        lines.append(f"    theta_v={a.theta_vertex.as_corner_tuple()}{grid_note}")
    lines.append("")
    lines.append(
        "Interpretation: small bilinear coupling preserves vertex localization; "
        "face_bowl breaks vertex localization (grid max > vertex max); use empirical Fisher at the true probe."
    )
    return lines
