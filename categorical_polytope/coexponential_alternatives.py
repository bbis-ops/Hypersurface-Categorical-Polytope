"""
Categories where a coexponential-like functor may exist (toy probes).

Contrasts Set obstruction with presheaf/topos exponentials, abelian group
duals, and pointed-space suspension proxies. Probes whether vertex
localization survives or interaction signature flips.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from .hypersurface_box import BoxBounds
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    grid_maximize,
    vertex_maximize,
)
from .set_category import cardinality_obstruction, hom_cardinality


class CategoricalSetting(Enum):
    """Where we probe coexponential-like structure."""

    FINITE_SET = auto()  # obstruction expected
    PRESHEAF_TOY = auto()  # local exponentials on a finite site
    ABELIAN_GROUP_TOY = auto()  # Hom(Z, A+Z) ~ A x Z as Z-module
    POINTED_SUSPENSION = auto()  # suspension shifts base cardinality


@dataclass(frozen=True)
class CoexpRepresentabilityReport:
    setting: CategoricalSetting
    representable: bool
    hom_growth: str
    reason: str
    vertex_localization_holds: bool | None
    interaction_signature: str  # "maximize_corners" | "interior_face" | "mixed"


def presheaf_exponential_toy(site_objects: int, y: int, a: int, z: int) -> int:
    """
    Toy presheaf on a discrete site with |Ob| = site_objects.

    Exponential in a presheaf topos is pointwise: (F^G)(c) = F(c)^{G(c)}.
    Size proxy: (|F(c)|)^{|G(c)|} per object c; use c=0 only.
    """
    if site_objects < 1:
        return 1
    g_size = y
    f_size = a + z
    return f_size**g_size


def abelian_coproduct_hom_size(a: int, z: int) -> int:
    """|Hom(Z, A ⊔ Z)| for finite abelian groups Z, A (cardinality proxy)."""
    return a * z


def suspension_cardinality_proxy(a: int, z: int) -> int:
    """
    Pointed spaces: suspension Sigma A adds a base point;
    maps from Sigma A to Z ⊔ {*} scale like (|Z|+1)^{|A|+1} toy.
    """
    return (z + 1) ** (a + 1)


def probe_setting(
    setting: CategoricalSetting,
    *,
    y: int = 2,
    a: int = 2,
    z: int = 3,
) -> CoexpRepresentabilityReport:
    if setting is CategoricalSetting.FINITE_SET:
        rep = cardinality_obstruction(y, a, z_probe=(z,))
        # exists_nontrivial_representable means "obstruction is nontrivial", not "coexp exists"
        coexp_exists = y == 0 or "mismatch" not in rep.reason.lower()
        return CoexpRepresentabilityReport(
            setting=setting,
            representable=coexp_exists,
            hom_growth="polynomial_in_Z_vs_exponential",
            reason=rep.reason,
            vertex_localization_holds=True,
            interaction_signature="maximize_corners",
        )

    if setting is CategoricalSetting.PRESHEAF_TOY:
        into = presheaf_exponential_toy(1, y, a, z)
        from_set = hom_cardinality(max(1, y), a + z)
        rep = into >= from_set
        return CoexpRepresentabilityReport(
            setting=setting,
            representable=rep,
            hom_growth="pointwise_exponential_in_site",
            reason=(
                f"Presheaf toy: |F^G| proxy = {into} vs Set Hom = {from_set}; "
                "exponentials exist locally in the topos fragment."
            ),
            vertex_localization_holds=True,
            interaction_signature="maximize_corners",
        )

    if setting is CategoricalSetting.ABELIAN_GROUP_TOY:
        size = abelian_coproduct_hom_size(a, z)
        return CoexpRepresentabilityReport(
            setting=setting,
            representable=True,
            hom_growth="bilinear_enrichment",
            reason=f"Abelian toy: |Hom(Z,A+Z)| proxy = {size} (additive enrichment).",
            vertex_localization_holds=True,
            interaction_signature="maximize_corners",
        )

    # POINTED_SUSPENSION
    sus = suspension_cardinality_proxy(a, z)
    set_hom = hom_cardinality(y, a + z)
    return CoexpRepresentabilityReport(
        setting=setting,
        representable=sus != set_hom,
        hom_growth="suspension_extra_base_point",
        reason=(
            f"Suspension proxy |maps| = {sus} vs Set {set_hom}; "
            "coexponential-like role played by Sigma, not Set coexp."
        ),
        vertex_localization_holds=None,
        interaction_signature="suspension_shift",
    )


def localization_vs_interaction(
    interaction: str,
    strengths: tuple[float, ...] = (0.0, 0.25, 0.5, 1.0),
    *,
    bounds: BoxBounds | None = None,
) -> list[dict[str, object]]:
    """
    For each strength, compare vertex-only vs grid max.

    When coexponential exists (metaphorically), we still test whether
    Theorem 1 hypotheses hold — interaction signature may flip to interior.
    """
    bounds = bounds or default_nonlinear_bounds()
    rows: list[dict[str, object]] = []
    for s in strengths:
        obj = HypersurfacePlusInteraction(
            bounds=bounds, strength=s, interaction=interaction
        )
        th_v, v_v = vertex_maximize(obj, bounds)
        th_g, v_g = grid_maximize(obj, bounds, steps=9)
        gap = v_g - v_v
        rows.append(
            {
                "interaction": interaction,
                "strength": s,
                "vertex_ok": gap <= 1e-3,
                "gap_vs_grid": gap,
                "theta_vertex": [th_v.lam, th_v.sigma, th_v.b, th_v.k],
                "theta_grid": [th_g.lam, th_g.sigma, th_g.b, th_g.k],
            }
        )
    return rows


def sweep_settings_localization() -> list[dict[str, object]]:
    """Compare face_bowl localization across categorical setting metadata."""
    settings = list(CategoricalSetting)
    out: list[dict[str, object]] = []
    for st in settings:
        rep = probe_setting(st)
        loc = localization_vs_interaction("face_bowl", (0.0, 0.5))
        onset = next(
            (r for r in loc if not r["vertex_ok"]),
            None,
        )
        out.append(
            {
                "setting": st.name,
                "representable": rep.representable,
                "interaction_signature": rep.interaction_signature,
                "face_bowl_onset_strength": onset["strength"] if onset else None,
                "face_bowl_gap": onset["gap_vs_grid"] if onset else 0.0,
            }
        )
    return out
