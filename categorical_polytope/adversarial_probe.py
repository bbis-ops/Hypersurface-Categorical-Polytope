"""
Adversarial parameters under bounded cross-information between blocks.

Given coproduct-style parameter blocks with a cross-information budget, the
worst-case (adversarial) setting localizes to vertices of each block polytope.
A near-optimal probe is built componentwise on each summand, then assembled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Sequence

from .hypersurface_box import (
    BoxBounds,
    CompositeObjective,
    HypersurfaceBox,
    Theta,
)


@dataclass(frozen=True)
class BlockAssignment:
    """One parameter block at a definite setting (typically a vertex)."""

    block_name: str
    values: dict[str, float]

    def get(self, key: str) -> float:
        return self.values[key]


@dataclass(frozen=True)
class ParameterBlockSpec:
    """
    One summand in a disjoint-union (coproduct) decomposition of parameters.

    Feasible set for the block is a box; ext(block) is its 2^n vertices.
    """

    name: str
    variables: tuple[str, ...]
    bounds: dict[str, tuple[float, float]]

    def __post_init__(self) -> None:
        for v in self.variables:
            if v not in self.bounds:
                raise ValueError(f"block {self.name!r} missing bound for {v!r}")

    def vertices(self) -> list[BlockAssignment]:
        intervals = [self.bounds[v] for v in self.variables]
        out: list[BlockAssignment] = []
        for corner in product(*intervals):
            out.append(
                BlockAssignment(
                    block_name=self.name,
                    values=dict(zip(self.variables, corner, strict=True)),
                )
            )
        return out

    def per_block_maxima(self) -> dict[str, float]:
        return {v: self.bounds[v][1] for v in self.variables}

    def per_block_minima(self) -> dict[str, float]:
        return {v: self.bounds[v][0] for v in self.variables}


def _cross_information_with_specs(
    left: BlockAssignment,
    right: BlockAssignment,
    *,
    left_bounds: dict[str, tuple[float, float]],
    right_bounds: dict[str, tuple[float, float]],
    left_vars: tuple[str, ...],
    right_vars: tuple[str, ...],
    scale: float = 1.0,
) -> float:
    def norm_vec(
        assign: BlockAssignment,
        variables: tuple[str, ...],
        bounds: dict[str, tuple[float, float]],
    ) -> list[float]:
        out: list[float] = []
        for v in variables:
            lo, hi = bounds[v]
            span = hi - lo
            val = assign.get(v)
            out.append(0.5 if span <= 0 else (val - lo) / span)
        return out

    u = norm_vec(left, left_vars, left_bounds)
    v = norm_vec(right, right_vars, right_bounds)
    if not u or not v:
        return 0.0
    # Off-diagonal coupling: distance from independence (0.5, 0.5) mean
    du = sum((x - 0.5) ** 2 for x in u) / len(u)
    dv = sum((y - 0.5) ** 2 for y in v) / len(v)
    coupling = (du * dv) ** 0.5
    return min(scale, coupling * scale)


@dataclass
class CoupledProblem:
    """
    Coproduct of parameter blocks with cross-information budget epsilon.

    Objective is evaluated on the assembled full parameter vector.
    """

    blocks: list[ParameterBlockSpec]
    cross_info_bound: float
    objective: Callable[[dict[str, float]], float]
    cross_scale: float = 1.0
    assemble_order: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.blocks) < 2:
            raise ValueError("need at least two blocks for cross-information")
        if self.cross_info_bound < 0:
            raise ValueError("cross_info_bound must be non-negative")
        all_vars = [v for b in self.blocks for v in b.variables]
        if not self.assemble_order:
            object.__setattr__(self, "assemble_order", tuple(all_vars))

    def _spec_by_name(self, name: str) -> ParameterBlockSpec:
        for b in self.blocks:
            if b.name == name:
                return b
        raise KeyError(name)

    def cross_between(self, a: BlockAssignment, b: BlockAssignment) -> float:
        sa, sb = self._spec_by_name(a.block_name), self._spec_by_name(b.block_name)
        return _cross_information_with_specs(
            a,
            b,
            left_bounds=sa.bounds,
            right_bounds=sb.bounds,
            left_vars=sa.variables,
            right_vars=sb.variables,
            scale=self.cross_scale,
        )

    def assemble(self, assignments: Sequence[BlockAssignment]) -> dict[str, float]:
        merged: dict[str, float] = {}
        for assign in assignments:
            merged.update(assign.values)
        return merged

    def evaluate(self, assignments: Sequence[BlockAssignment]) -> float:
        return self.objective(self.assemble(assignments))

    def joint_cross_information(self, assignments: Sequence[BlockAssignment]) -> float:
        """Sum of pairwise cross-information (for 2 blocks, just one pair)."""
        total = 0.0
        for i, ai in enumerate(assignments):
            for aj in assignments[i + 1 :]:
                total += self.cross_between(ai, aj)
        return total

    def feasible(self, assignments: Sequence[BlockAssignment]) -> bool:
        return self.joint_cross_information(assignments) <= self.cross_info_bound + 1e-9

    def _trial_with(
        self,
        chosen: list[BlockAssignment],
        block: ParameterBlockSpec,
        candidate: BlockAssignment,
    ) -> list[BlockAssignment]:
        trial: list[BlockAssignment] = []
        for b in self.blocks:
            if b.name == block.name:
                trial.append(candidate)
            else:
                prior = next((c for c in chosen if c.block_name == b.name), None)
                trial.append(prior if prior is not None else b.vertices()[0])
        return trial

    def localize_worst_case(self) -> WorstCaseResult:
        """
        Global adversarial parameter over feasible couplings.

        Under bounded cross-information, search ext(block_1) x ... x ext(block_k)
        (vertex localization). Returns the attaining probe.
        """
        vertex_lists = [b.vertices() for b in self.blocks]
        best_assignments: list[BlockAssignment] = []
        best_val = float("-inf")
        best_cross = 0.0
        for combo in product(*vertex_lists):
            if not self.feasible(combo):
                continue
            val = self.evaluate(combo)
            cross = self.joint_cross_information(combo)
            if val > best_val:
                best_val = val
                best_assignments = list(combo)
                best_cross = cross

        if not best_assignments:
            # Relax: pick componentwise then report infeasible cross
            comp = self.build_componentwise_probe(relax_cross=True)
            return WorstCaseResult(
                assignments=comp.per_block,
                assembled=comp.assembled,
                objective_value=comp.objective_value,
                cross_information=comp.cross_information,
                localized_at_vertex=True,
                componentwise_matches_global=False,
                note="no feasible vertex under cross bound; probe is componentwise only",
            )

        comp = self.build_componentwise_probe()
        return WorstCaseResult(
            assignments=best_assignments,
            assembled=self.assemble(best_assignments),
            objective_value=best_val,
            cross_information=best_cross,
            localized_at_vertex=True,
            componentwise_matches_global=comp.objective_value >= best_val - 1e-9,
            note="worst case in ext(H) with cross-information bound",
        )

    def build_componentwise_probe(
        self,
        *,
        relax_cross: bool = False,
    ) -> ComponentwiseProbe:
        """
        Explicit componentwise probe (Lemma i): per-block max on ext(block), assemble.

        Blocks are optimized in order; each picks a vertex maximizing the composite
        objective given previously fixed blocks (defaults for later blocks).
        """
        chosen: list[BlockAssignment] = []
        per_block_obj: dict[str, float] = {}

        for block in self.blocks:
            best_a = block.vertices()[0]
            best_local = float("-inf")
            for candidate in block.vertices():
                val = self.evaluate(self._trial_with(chosen, block, candidate))
                if val > best_local:
                    best_local, best_a = val, candidate
            chosen.append(best_a)
            per_block_obj[block.name] = best_local

        cross = self.joint_cross_information(chosen)
        obj = self.evaluate(chosen)

        if not relax_cross and cross > self.cross_info_bound + 1e-9:
            projected = [
                BlockAssignment(b.name, b.per_block_maxima()) for b in self.blocks
            ]
            if self.feasible(projected):
                chosen = projected
                cross = self.joint_cross_information(chosen)
                obj = self.evaluate(chosen)

        return ComponentwiseProbe(
            per_block=tuple(chosen),
            assembled=self.assemble(chosen),
            objective_value=obj,
            cross_information=cross,
            per_block_objective=per_block_obj,
            satisfies_cross_bound=cross <= self.cross_info_bound + 1e-9,
            is_vertex=True,
        )


@dataclass(frozen=True)
class ComponentwiseProbe:
    """Near-optimal adversarial probe built block-by-block."""

    per_block: tuple[BlockAssignment, ...]
    assembled: dict[str, float]
    objective_value: float
    cross_information: float
    per_block_objective: dict[str, float]
    satisfies_cross_bound: bool
    is_vertex: bool

    def to_theta(self) -> Theta:
        a = self.assembled
        return Theta(
            lam=a.get("lam", 0.0),
            sigma=a.get("sigma", 0.0),
            b=a.get("b", 0.0),
            k=a.get("k", 0.0),
        )


@dataclass(frozen=True)
class WorstCaseResult:
    assignments: list[BlockAssignment]
    assembled: dict[str, float]
    objective_value: float
    cross_information: float
    localized_at_vertex: bool
    componentwise_matches_global: bool
    note: str

    def to_theta(self) -> Theta:
        a = self.assembled
        return Theta(
            lam=a.get("lam", 0.0),
            sigma=a.get("sigma", 0.0),
            b=a.get("b", 0.0),
            k=a.get("k", 0.0),
        )


def default_hypersurface_problem(
    *,
    cross_info_bound: float = 0.15,
    bounds: BoxBounds | None = None,
) -> CoupledProblem:
    """
    Standard split: r-block (lam, sigma) + C-block (b, k) on box H.
    """
    bounds = bounds or BoxBounds(
        lam=(0.0, 1.0),
        sigma=(0.0, 1.0),
        b=(0.0, 2.0),
        k=(0.0, 3.0),
    )
    hs = HypersurfaceBox(bounds)

    def objective(params: dict[str, float]) -> float:
        theta = Theta(
            params["lam"],
            params["sigma"],
            params["b"],
            params["k"],
        )
        return hs.objective.composite(theta, bounds)

    return CoupledProblem(
        blocks=[
            ParameterBlockSpec(
                "r_block",
                ("lam", "sigma"),
                {"lam": bounds.lam, "sigma": bounds.sigma},
            ),
            ParameterBlockSpec(
                "C_block",
                ("b", "k"),
                {"b": bounds.b, "k": bounds.k},
            ),
        ],
        cross_info_bound=cross_info_bound,
        objective=objective,
        cross_scale=1.0,
    )


def adversarial_theorem_summary() -> str:
    return (
        "Adversarial localization (bounded cross-information):\n"
        "  (i) Build probe componentwise: per-block max on ext(block), then assemble.\n"
        "  (ii) Worst-case parameter lies at a vertex of each block (vertex localization).\n"
        "  (iii) Search ext(H) with cross bound; componentwise probe attains near-optimum.\n"
    )


def demonstrate_adversarial(
    *,
    cross_info_bound: float = 0.25,
) -> list[str]:
    problem = default_hypersurface_problem(cross_info_bound=cross_info_bound)
    probe = problem.build_componentwise_probe()
    worst = problem.localize_worst_case()
    hs = HypersurfaceBox(
        BoxBounds(lam=(0, 1), sigma=(0, 1), b=(0, 2), k=(0, 3))
    )
    unconstrained = hs.maximize_on_ext_H()

    lines = [
        f"Cross-information bound: {cross_info_bound}",
        "Componentwise probe:",
    ]
    for assign in probe.per_block:
        lines.append(f"  {assign.block_name}: {assign.values}")
    lines.append(f"  assembled theta: {probe.to_theta().as_corner_tuple()}")
    lines.append(f"  objective={probe.objective_value:.3f}  cross={probe.cross_information:.4f}")
    lines.append(f"  satisfies bound: {probe.satisfies_cross_bound}")
    lines.append("Worst-case (vertex search with bound):")
    lines.append(f"  theta: {worst.to_theta().as_corner_tuple()}  objective={worst.objective_value:.3f}")
    lines.append(f"  cross={worst.cross_information:.4f}  at vertex: {worst.localized_at_vertex}")
    lines.append(f"  componentwise = global: {worst.componentwise_matches_global}")
    lines.append(f"  note: {worst.note}")
    lines.append("Unconstrained box corner (reference):")
    lines.append(f"  theta_max: {unconstrained.theta_max.as_corner_tuple()}  value={unconstrained.value:.3f}")
    return lines
