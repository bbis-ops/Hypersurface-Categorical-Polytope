"""
Sheaf of certification bounds over a finite site.

Sections: epsilon, Phi(epsilon), delta(epsilon) per object; restriction on covers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from .fisher_factorization import BlockLayout, QuadraticJointObjective, build_block_fisher
from .formal_bounds import TheoremConstants, certify_suboptimality, theorem_constants_from_fisher
from .presheaf_site import FiniteSite, default_two_object_site


@dataclass(frozen=True)
class CertificateSection:
    """Stalk of the certification sheaf at object c."""

    object: str
    epsilon: float
    phi: float
    delta: float
    certified: bool
    gap: float


@dataclass
class CertificateSheaf:
    """
    Toy sheaf of Fisher certification data over a finite site.

    Restriction: pull back section to cover by averaging stalks (toy).
    """

    site: FiniteSite
    sections: dict[str, CertificateSection] = field(default_factory=dict)
    restriction_maps: dict[tuple[str, str], CertificateSection] = field(default_factory=dict)

    def global_epsilon(self) -> float:
        if not self.sections:
            return 0.0
        return max(s.epsilon for s in self.sections.values())

    def global_certified(self) -> bool:
        return all(s.certified for s in self.sections.values())

    def gluing_ok(self, *, rel_tol: float = 0.35) -> bool:
        """
        Sections glue on overlap: epsilon within relative tolerance on cover.

        Toy: presheaf descent for certification stalks (not strict equality).
        """
        if "UV" not in self.sections:
            return True
        uv = self.sections["UV"]
        for name in ("U", "V"):
            if name not in self.sections:
                continue
            loc = self.sections[name]
            if uv.epsilon <= 1e-12:
                continue
            if abs(loc.epsilon - uv.epsilon) / max(uv.epsilon, 1e-12) > rel_tol:
                return False
        return True


def _section_at_object(
    object_name: str,
    *,
    coupling: float,
    stalk_scale: float,
) -> CertificateSection:
    """Fisher block layout scaled by stalk_size at object."""
    layout = BlockLayout(names=(object_name, "rest"), sizes=(2, 2))
    fisher = build_block_fisher(layout, off_diag_coupling=coupling * stalk_scale)
    leak = fisher.leakage()
    try:
        a = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0)).factorization_analysis()
        gap = a.gap
    except ValueError:
        gap = float("inf")
    const = theorem_constants_from_fisher(
        leak,
        [fisher.matrix[i][i] for i in range(4)],
        theta_joint=(1.0, 0.5, 2.0, 3.0),
    )
    eps = leak.epsilon
    phi = const.Phi(eps)
    delta = const.delta(eps)
    cert, _, _ = certify_suboptimality(eps, gap if isfinite(gap) else 1e9, const)
    return CertificateSection(
        object=object_name,
        epsilon=eps,
        phi=phi,
        delta=delta,
        certified=cert,
        gap=gap if isfinite(gap) else -1.0,
    )


def build_certificate_sheaf(
    site: FiniteSite | None = None,
    *,
    coupling: float = 0.1,
) -> CertificateSheaf:
    site = site or default_two_object_site()
    sheaf = CertificateSheaf(site=site)
    for obj in site.objects:
        scale = 1.0 / max(1, obj.stalk_size)
        sheaf.sections[obj.name] = _section_at_object(
            obj.name, coupling=coupling, stalk_scale=scale
        )
    for c, cover in site.covers.items():
        if c not in sheaf.sections:
            continue
        base = sheaf.sections[c]
        for u in cover:
            if u in sheaf.sections:
                sheaf.restriction_maps[(c, u)] = sheaf.sections[u]
    return sheaf


def probe_site_gluing_sweep(
    sites: list[FiniteSite] | None = None,
    *,
    coupling: float = 0.1,
) -> list[dict[str, object]]:
    """Descent success rate per site geometry."""
    from .presheaf_site import default_two_object_site, larger_site

    sites = sites or [default_two_object_site(), larger_site()]
    out: list[dict[str, object]] = []
    for site in sites:
        sh = build_certificate_sheaf(site, coupling=coupling)
        n = len(site.objects)
        out.append(
            {
                "n_objects": n,
                "n_covers": len(site.covers),
                "gluing_ok": sh.gluing_ok(),
                "global_epsilon": sh.global_epsilon(),
                "objects": list(sh.sections.keys()),
            }
        )
    return out


def probe_sheafified_certificate(
    couplings: tuple[float, ...] = (0.0, 0.08, 0.12, 0.2),
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for f in couplings:
        sh = build_certificate_sheaf(coupling=f)
        rows.append(
            {
                "coupling": f,
                "global_epsilon": sh.global_epsilon(),
                "global_certified": sh.global_certified(),
                "gluing_ok": sh.gluing_ok(),
                "sections": {
                    k: {
                        "epsilon": v.epsilon,
                        "phi": v.phi,
                        "delta": v.delta,
                        "certified": v.certified,
                    }
                    for k, v in sh.sections.items()
                },
            }
        )
    return rows


def full_sheaf_report(coupling: float = 0.1) -> dict[str, object]:
    """Certificate sheaf on default + larger site."""
    from .presheaf_site import default_two_object_site, larger_site

    return {
        "coupling": coupling,
        "sites": probe_site_gluing_sweep(
            [default_two_object_site(), larger_site()],
            coupling=coupling,
        ),
        "coupling_sweep": probe_sheafified_certificate((0.0, 0.1, 0.15, 0.2)),
    }
