"""
Lawvere damping overlaid on face_bowl learner — interior onset shift probe.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fisher_factorization import BlockLayout, build_block_fisher
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .hypersurface_box import BoxBounds
from .lawvere_metric import LawvereMetric
from .learner_diagram import SearchMode, recommend_search_mode
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    empirical_fisher_at,
    grid_maximize,
    vertex_maximize,
)


@dataclass(frozen=True)
class LawvereFaceBowlReading:
    strength: float
    block_distance: float
    epsilon_plain: float
    epsilon_lawvere: float
    gap_vertex_grid: float
    mode_plain: str
    mode_lawvere: str


def reading_at_strength(
    strength: float,
    block_distance: float,
    *,
    bounds: BoxBounds | None = None,
    interior_tol: float = 0.01,
) -> LawvereFaceBowlReading:
    bounds = bounds or default_nonlinear_bounds()
    obj = HypersurfacePlusInteraction(
        bounds=bounds, strength=strength, interaction="face_bowl"
    )
    from .hypersurface_box import Theta

    t = Theta(1.0, 0.0, 2.0, 3.0)
    # Empirical Fisher at a corner is often ~0 for face_bowl; use coupling proxy for
    # epsilon branch so Lawvere damping is visible (gap branch stays geometric).
    layout = BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
    fisher = build_block_fisher(layout, off_diag_coupling=strength * 0.4)
    leak = fisher.leakage()
    met = LawvereMetric.two_blocks(block_distance)
    eps_l = met.epsilon_metric(fisher)
    th_v, v_v = vertex_maximize(obj, bounds)
    th_g, v_g = grid_maximize(obj, bounds, steps=9)
    gap = v_g - v_v
    const = theorem_constants_from_fisher(
        leak,
        [fisher.matrix[i][i] for i in range(4)],
        theta_joint=(th_g.lam, th_g.sigma, th_g.b, th_g.k),
    )
    cert_p, _, _ = certify_suboptimality(leak.epsilon, 0.0, const)
    cert_l, _, _ = certify_suboptimality(eps_l, 0.0, const)
    mode_p, _ = recommend_search_mode(
        leak.epsilon,
        gap_vertex_grid=gap,
        certified_separable=cert_p,
        epsilon_0=const.epsilon_0,
        interior_tol=interior_tol,
    )
    mode_l, _ = recommend_search_mode(
        eps_l,
        gap_vertex_grid=gap,
        certified_separable=cert_l,
        epsilon_0=const.epsilon_0,
        interior_tol=interior_tol,
    )
    return LawvereFaceBowlReading(
        strength=strength,
        block_distance=block_distance,
        epsilon_plain=leak.epsilon,
        epsilon_lawvere=eps_l,
        gap_vertex_grid=gap,
        mode_plain=mode_p.name,
        mode_lawvere=mode_l.name,
    )


def _bisect_onset(
    predicate,
    lo: float = 0.0,
    hi: float = 1.0,
    *,
    tol: float = 0.02,
) -> float | None:
    if not predicate(lo) and not predicate(hi):
        return None
    if predicate(lo):
        return lo
    a, b = lo, hi
    for _ in range(40):
        if b - a <= tol:
            return b
        mid = 0.5 * (a + b)
        if predicate(mid):
            b = mid
        else:
            a = mid
    return b


def probe_lawvere_face_bowl_onset(
    distances: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0),
) -> dict[str, object]:
    """
    Critical strength for interior search: plain vs Lawvere-damped epsilon branch.

    gap_vertex_grid is unchanged by Lawvere; interior from gap is identical.
    Non-corner modes (BLOCK_COORDINATE) may shift — we track both interior-only
    and any-non-corner onsets.
    """
    strengths = [i * 0.025 for i in range(41)]
    rows: list[dict[str, object]] = []
    onsets: dict[str, dict[str, float | None]] = {}

    for d in distances:
        def interior_plain(s: float, dist: float = d) -> bool:
            r = reading_at_strength(s, dist)
            return r.mode_plain == SearchMode.INTERIOR_SEARCH.name

        def interior_lawvere(s: float, dist: float = d) -> bool:
            r = reading_at_strength(s, dist)
            return r.mode_lawvere == SearchMode.INTERIOR_SEARCH.name

        def noncorner_lawvere(s: float, dist: float = d) -> bool:
            r = reading_at_strength(s, dist)
            return r.mode_lawvere != SearchMode.CORNER_HUNTING.name

        def block_only_lawvere(s: float, dist: float = d) -> bool:
            r = reading_at_strength(s, dist)
            return r.mode_lawvere == SearchMode.BLOCK_COORDINATE.name

        onsets[str(d)] = {
            "interior_plain": _bisect_onset(interior_plain),
            "interior_lawvere": _bisect_onset(interior_lawvere),
            "noncorner_lawvere": _bisect_onset(noncorner_lawvere),
            "block_only_lawvere": _bisect_onset(block_only_lawvere),
        }

    def eps_cross_plain(s: float) -> bool:
        r = reading_at_strength(s, 0.0)
        layout = BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
        fisher = build_block_fisher(layout, off_diag_coupling=s * 0.4)
        const = theorem_constants_from_fisher(
            fisher.leakage(),
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=(1.0, 0.5, 2.0, 3.0),
        )
        return r.epsilon_plain > const.epsilon_0

    def eps_cross_lawvere(s: float, dist: float = 2.0) -> bool:
        r = reading_at_strength(s, dist)
        layout = BlockLayout(names=("r_block", "C_block"), sizes=(2, 2))
        fisher = build_block_fisher(layout, off_diag_coupling=s * 0.4)
        const = theorem_constants_from_fisher(
            fisher.leakage(),
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=(1.0, 0.5, 2.0, 3.0),
        )
        return r.epsilon_lawvere > const.epsilon_0

    eps0_cross_plain = _bisect_onset(eps_cross_plain, lo=0.0, hi=0.9)
    eps0_cross_lawvere = _bisect_onset(
        lambda s: eps_cross_lawvere(s, 2.0), lo=0.0, hi=0.9
    )

    d0 = 0.0
    d2 = 2.0
    for s in strengths:
        if s in (0.0, 0.1, 0.2, 0.35, 0.5):
            rows.append(
                {
                    "strength": s,
                    "d0": reading_at_strength(s, d0).__dict__,
                    "d2": reading_at_strength(s, d2).__dict__,
                }
            )

    ip = onsets["0.0"]["interior_plain"]
    bo0 = onsets["0.0"].get("block_only_lawvere")
    bo2 = onsets["2.0"].get("block_only_lawvere")

    prediction_holds = eps0_cross_plain is not None and (
        eps0_cross_lawvere is None
        or eps0_cross_lawvere > eps0_cross_plain + 0.02
    )

    return {
        "onsets_by_distance": onsets,
        "sample_rows": rows,
        "prediction": (
            "Lawvere damping lowers effective epsilon -> delays epsilon_0 crossing; "
            "interior onset from gap is unchanged at fixed strength."
        ),
        "prediction_epsilon_delayed": prediction_holds,
        "epsilon_cross_plain": eps0_cross_plain,
        "epsilon_cross_lawvere_d2": eps0_cross_lawvere,
        "interior_onset_plain_d0": ip,
        "block_onset_d0": bo0,
        "block_onset_d2": bo2,
    }
