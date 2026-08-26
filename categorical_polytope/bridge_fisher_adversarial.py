"""Bridge adversarial cross-information proxy to Fisher off-diagonal leakage."""

from __future__ import annotations

from .adversarial_probe import CoupledProblem, default_hypersurface_problem
from .fisher_factorization import (
    BlockFisher,
    BlockLayout,
    FactorizationAnalysis,
    QuadraticJointObjective,
    build_block_fisher,
    coupling_from_cross_proxy,
)


def fisher_from_coupled_problem(
    problem: CoupledProblem,
    *,
    cross_at_probe: float | None = None,
) -> BlockFisher:
    """
    Map bounded cross-information to a block Fisher matrix.

    Two blocks => 2x2 scalar off-block coupling eps on all cross entries.
    """
    if cross_at_probe is None:
        probe = problem.build_componentwise_probe(relax_cross=True)
        cross_at_probe = probe.cross_information

    sizes = tuple(len(b.variables) for b in problem.blocks)
    names = tuple(b.name for b in problem.blocks)
    layout = BlockLayout(names=names, sizes=sizes)
    eps = coupling_from_cross_proxy(cross_at_probe)
    return build_block_fisher(layout, off_diag_coupling=eps)


def factorization_from_hypersurface(
    *,
    cross_info_bound: float = 0.25,
    linear: tuple[float, ...] = (1.0, 0.5, 2.0, 3.0),
) -> tuple[CoupledProblem, FactorizationAnalysis]:
    """End-to-end: coupled problem + Fisher leakage + factorization gap."""
    problem = default_hypersurface_problem(cross_info_bound=cross_info_bound)
    fisher = fisher_from_coupled_problem(problem)
    obj = QuadraticJointObjective(fisher=fisher, linear=linear)
    return problem, obj.factorization_analysis()
