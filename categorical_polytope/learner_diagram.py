"""
Live epsilon for a learner's internal diagram polytope.

Treats the conceptual/box diagram as H; measures empirical Fisher leakage
along a session and recommends corner vs interior search.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from pathlib import Path
from random import Random
from typing import Any, Sequence

from .decomposition_stability import DecompositionStrategy
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .hypersurface_box import BoxBounds, Theta
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    empirical_fisher_at,
    grid_maximize,
    vertex_maximize,
)


class SearchMode(Enum):
    CORNER_HUNTING = auto()
    INTERIOR_SEARCH = auto()
    BLOCK_COORDINATE = auto()


@dataclass
class LearnerDiagramState:
    """Coordinates in the learner's feasible diagram box."""

    lam: float
    sigma: float
    b: float
    k: float
    interaction_strength: float = 0.0

    def to_theta(self) -> Theta:
        return Theta(self.lam, self.sigma, self.b, self.k)

    @classmethod
    def from_theta(cls, t: Theta, *, strength: float = 0.0) -> LearnerDiagramState:
        return cls(t.lam, t.sigma, t.b, t.k, interaction_strength=strength)


@dataclass(frozen=True)
class LiveEpsilonReading:
    epsilon: float
    gap_vertex_grid: float
    certified_separable: bool
    recommended_mode: SearchMode
    reason: str


@dataclass
class LearnerSession:
    """
    Simulated learner trajectory: strength ramps as "confusion" grows.

    Models when corner-hunting (vertex probe) should switch to interior search.
    """

    bounds: BoxBounds = field(default_factory=default_nonlinear_bounds)
    interaction: str = "face_bowl"
    strength_schedule: tuple[float, ...] = (0.0, 0.1, 0.2, 0.35, 0.5, 0.8)
    seed: int = 42

    def objective(self, strength: float) -> HypersurfacePlusInteraction:
        return HypersurfacePlusInteraction(
            bounds=self.bounds,
            strength=strength,
            interaction=self.interaction,
        )

    def reading_at_strength(self, strength: float) -> LiveEpsilonReading:
        obj = self.objective(strength)
        theta = LearnerDiagramState(1.0, 0.0, 2.0, 3.0, strength).to_theta()
        fisher = empirical_fisher_at(obj, theta, self.bounds)
        leak = fisher.leakage()
        th_v, v_v = vertex_maximize(obj, self.bounds)
        th_g, v_g = grid_maximize(obj, self.bounds, steps=9)
        gap_vg = v_g - v_v
        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=(th_g.lam, th_g.sigma, th_g.b, th_g.k),
        )
        cert, _, cert_reason = certify_suboptimality(
            leak.epsilon, 0.0, const, require_epsilon_threshold=True
        )
        mode, reason = recommend_search_mode(
            leak.epsilon,
            gap_vertex_grid=gap_vg,
            certified_separable=cert,
            epsilon_0=const.epsilon_0,
        )
        return LiveEpsilonReading(
            epsilon=leak.epsilon,
            gap_vertex_grid=gap_vg,
            certified_separable=cert,
            recommended_mode=mode,
            reason=reason,
        )

    def run(self) -> list[dict[str, object]]:
        return [
            {
                "strength": s,
                "epsilon": r.epsilon,
                "gap_vertex_grid": r.gap_vertex_grid,
                "certified": r.certified_separable,
                "mode": r.recommended_mode.name,
                "reason": r.reason,
            }
            for s in self.strength_schedule
            for r in [self.reading_at_strength(s)]
        ]

    def detect_mode_switch(self) -> dict[str, object]:
        """First strength where recommended mode leaves CORNER_HUNTING."""
        prev = SearchMode.CORNER_HUNTING
        switch_at: float | None = None
        readings: list[dict[str, object]] = []
        for s in self.strength_schedule:
            r = self.reading_at_strength(s)
            readings.append(
                {
                    "strength": s,
                    "mode": r.recommended_mode.name,
                    "epsilon": r.epsilon,
                    "gap_vertex_grid": r.gap_vertex_grid,
                }
            )
            if (
                prev is SearchMode.CORNER_HUNTING
                and r.recommended_mode is not SearchMode.CORNER_HUNTING
                and switch_at is None
            ):
                switch_at = s
            prev = r.recommended_mode
        return {
            "interaction": self.interaction,
            "switch_strength": switch_at,
            "readings": readings,
        }


def recommend_search_mode(
    epsilon: float,
    *,
    gap_vertex_grid: float,
    certified_separable: bool,
    epsilon_0: float,
    interior_tol: float = 0.01,
) -> tuple[SearchMode, str]:
    """
    Operational rule: live epsilon + localization gap -> search mode.

    Mirrors decomposition_stability thresholds with an interior trigger.
    """
    if gap_vertex_grid > interior_tol:
        return (
            SearchMode.INTERIOR_SEARCH,
            f"grid beats vertex by {gap_vertex_grid:.4f} — abandon corner-hunting",
        )
    if epsilon > epsilon_0:
        return (
            SearchMode.BLOCK_COORDINATE,
            f"epsilon={epsilon:.4f} > epsilon_0={epsilon_0:.4f}",
        )
    if certified_separable:
        return (
            SearchMode.CORNER_HUNTING,
            "low leakage and vertex localization — separable corner probe OK",
        )
    return (
        SearchMode.BLOCK_COORDINATE,
        "moderate leakage — block passes before trusting corners",
    )


@dataclass(frozen=True)
class TrajectoryStep:
    """One logged observation along a learner session."""

    step: int
    lam: float
    sigma: float
    b: float
    k: float
    interaction_strength: float
    epsilon: float
    gap_vertex_grid: float
    mode: str
    reason: str


@dataclass
class LearnerTrajectoryLog:
    """
    Human- or model-learner session: append states, measure epsilon live.

    Use for in-the-loop logging or replay from JSON.
    """

    interaction: str = "face_bowl"
    bounds: BoxBounds = field(default_factory=default_nonlinear_bounds)
    steps: list[TrajectoryStep] = field(default_factory=list)

    def append_state(
        self,
        state: LearnerDiagramState,
        *,
        step: int | None = None,
    ) -> TrajectoryStep:
        obj = HypersurfacePlusInteraction(
            bounds=self.bounds,
            strength=state.interaction_strength,
            interaction=self.interaction,
        )
        theta = state.to_theta()
        fisher = empirical_fisher_at(obj, theta, self.bounds)
        leak = fisher.leakage()
        th_v, v_v = vertex_maximize(obj, self.bounds)
        th_g, v_g = grid_maximize(obj, self.bounds, steps=9)
        gap_vg = v_g - v_v
        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=(th_g.lam, th_g.sigma, th_g.b, th_g.k),
        )
        cert, _, _ = certify_suboptimality(leak.epsilon, 0.0, const)
        mode, reason = recommend_search_mode(
            leak.epsilon,
            gap_vertex_grid=gap_vg,
            certified_separable=cert,
            epsilon_0=const.epsilon_0,
        )
        rec = TrajectoryStep(
            step=step if step is not None else len(self.steps),
            lam=state.lam,
            sigma=state.sigma,
            b=state.b,
            k=state.k,
            interaction_strength=state.interaction_strength,
            epsilon=leak.epsilon,
            gap_vertex_grid=gap_vg,
            mode=mode.name,
            reason=reason,
        )
        self.steps.append(rec)
        return rec

    def first_interior_step(self) -> TrajectoryStep | None:
        for s in self.steps:
            if s.mode == SearchMode.INTERIOR_SEARCH.name:
                return s
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction": self.interaction,
            "steps": [asdict(s) for s in self.steps],
        }

    def save_json(self, path: Path | str) -> None:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path | str) -> LearnerTrajectoryLog:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        log = cls(interaction=data.get("interaction", "face_bowl"))
        for raw in data.get("steps", []):
            log.steps.append(TrajectoryStep(**raw))
        return log

    @classmethod
    def simulate_random_walk(
        cls,
        n_steps: int = 12,
        *,
        interaction: str = "face_bowl",
        seed: int = 0,
        strength_ramp: bool = True,
    ) -> LearnerTrajectoryLog:
        """Synthetic trajectory: theta drifts, strength may ramp."""
        rng = Random(seed)
        log = cls(interaction=interaction)
        bounds = log.bounds
        state = LearnerDiagramState(1.0, 0.0, 2.0, 3.0, 0.0)
        for t in range(n_steps):
            if strength_ramp:
                state = LearnerDiagramState(
                    state.lam,
                    state.sigma,
                    state.b,
                    state.k,
                    min(0.9, t * 0.08),
                )
            state = LearnerDiagramState(
                min(1.0, max(0.0, state.lam + rng.uniform(-0.08, 0.08))),
                min(1.0, max(0.0, state.sigma + rng.uniform(-0.08, 0.08))),
                min(bounds.b[1], max(bounds.b[0], state.b + rng.uniform(-0.1, 0.1))),
                min(bounds.k[1], max(bounds.k[0], state.k + rng.uniform(-0.15, 0.15))),
                state.interaction_strength,
            )
            log.append_state(state, step=t)
        return log


def simulate_learner_population(
    n: int = 20,
    *,
    seed: int = 0,
) -> dict[str, object]:
    """Many learners with random strength schedules; count interior switches."""
    rng = Random(seed)
    switches = 0
    for i in range(n):
        sched = tuple(rng.uniform(0, 0.15) for _ in range(5)) + (
            rng.uniform(0.2, 0.9),
        )
        sess = LearnerSession(
            interaction="face_bowl",
            strength_schedule=sched,
            seed=seed + i,
        )
        det = sess.detect_mode_switch()
        if det["switch_strength"] is not None:
            switches += 1
    return {
        "n_learners": n,
        "fraction_switching_to_interior": switches / n,
        "interpretation": (
            "When internal interaction (face_bowl) strengthens, "
            "live epsilon and grid gap trigger interior search."
        ),
    }
