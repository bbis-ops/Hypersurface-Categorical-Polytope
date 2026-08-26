"""
Enriched coexponential universal property probes (presheaf / pointed).

Tests whether a representing object exists for Z ↦ Hom(Y, A ⊔ Z) in enriched
settings, and whether Fisher certification still tracks vertex localization.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .coexponential_alternatives import CategoricalSetting, suspension_cardinality_proxy
from .fisher_factorization import BlockLayout, QuadraticJointObjective, build_block_fisher
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .hypersurface_box import BoxBounds
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    grid_maximize,
    vertex_maximize,
)
from .presheaf_site import FiniteSite, default_two_object_site
from .set_category import hom_cardinality, hom_into_coproduct


@dataclass(frozen=True)
class EnrichedCoexpUPReport:
    """Universal property probe in an enriched setting."""

    setting: str
    representing_object_exists: bool
    up_holds_on_probe: bool
    reason: str
    z_probe: tuple[int, ...]
    hom_coproduct: dict[int, int]
    hom_representing: dict[int, int]


def _presheaf_representing_sizes(site: FiniteSite, y: int, a: int, z_values: Sequence[int]) -> dict[int, int]:
    """Presheaf C: size at object c is exp at c; global probe uses max over objects."""
    out: dict[int, int] = {}
    for z in z_values:
        sizes = [
            site.exponential_size(obj.name, obj.name)
            for obj in site.objects
        ]
        out[z] = max(sizes) if sizes else 1
    return out


def _pointed_representing_sizes(y: int, a: int, z_values: Sequence[int]) -> dict[int, int]:
    return {z: suspension_cardinality_proxy(a, z) for z in z_values}


def probe_enriched_universal_property(
    setting: CategoricalSetting,
    *,
    y: int = 2,
    a: int = 2,
    z_probe: Sequence[int] = (0, 1, 2, 3, 4),
) -> EnrichedCoexpUPReport:
    z_list = tuple(z_probe)
    into = {z: hom_into_coproduct(y, a, z) for z in z_list}

    if setting is CategoricalSetting.PRESHEAF_TOY:
        site = default_two_object_site()
        from_rep = _presheaf_representing_sizes(site, y, a, z_list)
        name = "PRESHEAF_TOY"
        reason = "Pointwise exponentials on site; C is a presheaf, not a single set."
    elif setting is CategoricalSetting.POINTED_SUSPENSION:
        from_rep = _pointed_representing_sizes(y, a, z_list)
        name = "POINTED_SUSPENSION"
        reason = "Sigma(A) suspension proxy replaces Set coexp cardinality."
    else:
        from_rep = {z: hom_cardinality(max(1, y), z) for z in z_list}
        name = setting.name
        reason = "Fallback: plain hom cardinality."

    up = into == from_rep
    exists = up or all(into[z] <= from_rep[z] for z in z_list)
    return EnrichedCoexpUPReport(
        setting=name,
        representing_object_exists=exists,
        up_holds_on_probe=up,
        reason=reason,
        z_probe=z_list,
        hom_coproduct=into,
        hom_representing=from_rep,
    )


@dataclass(frozen=True)
class LocalizationCertBundle:
    fisher_coupling: float
    epsilon: float
    vertex_ok: bool
    certified_strict: bool
    gap_joint_sep: float
    phi: float


def fisher_cert_vs_vertex_localization(
    *,
    fisher_couplings: Sequence[float] = (0.0, 0.05, 0.1, 0.25),
    interaction: str = "bilinear",
    strengths: Sequence[float] = (0.0, 0.5),
) -> dict[str, object]:
    """
    In enriched setting metadata, Fisher certificate vs vertex localization
    on the same box (geometry unchanged).
    """
    layout = BlockLayout(names=("A", "B"), sizes=(2, 2))
    bounds = default_nonlinear_bounds()
    fisher_rows: list[dict[str, object]] = []
    for f in fisher_couplings:
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        leak = fisher.leakage()
        try:
            a = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0)).factorization_analysis()
            gap = a.gap
        except ValueError:
            gap = float("nan")
        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=(1.0, 0.5, 2.0, 3.0),
        )
        cert, phi, _ = certify_suboptimality(
            leak.epsilon, gap if isfinite(gap) else 1e9, const
        )
        fisher_rows.append(
            {
                "coupling": f,
                "epsilon": leak.epsilon,
                "certified": cert,
                "phi": phi,
                "gap": gap,
            }
        )

    loc_rows: list[dict[str, object]] = []
    for s in strengths:
        obj = HypersurfacePlusInteraction(bounds=bounds, strength=s, interaction=interaction)
        th_v, v_v = vertex_maximize(obj, bounds)
        th_g, v_g = grid_maximize(obj, bounds, steps=9)
        loc_rows.append(
            {
                "strength": s,
                "interaction": interaction,
                "vertex_ok": (v_g - v_v) <= 1e-3,
                "gap_vs_grid": v_g - v_v,
            }
        )

    presheaf_up = probe_enriched_universal_property(CategoricalSetting.PRESHEAF_TOY)
    pointed_up = probe_enriched_universal_property(CategoricalSetting.POINTED_SUSPENSION)

    return {
        "presheaf_up": {
            "exists": presheaf_up.representing_object_exists,
            "exact_up": presheaf_up.up_holds_on_probe,
            "reason": presheaf_up.reason,
        },
        "pointed_up": {
            "exists": pointed_up.representing_object_exists,
            "exact_up": pointed_up.up_holds_on_probe,
            "reason": pointed_up.reason,
        },
        "fisher_vs_localization": fisher_rows,
        "localization": loc_rows,
        "decoupled": (
            "Fisher cert tracks factorization leakage; vertex_ok tracks Theorem 1 "
            "on interaction — independent of enriched coexp representability."
        ),
    }
