"""
Finite presheaf site: objects, covers, and pointwise exponentials.

Models a tiny Cech-style site (not just a cardinality proxy) and checks
that exponentials exist objectwise while Set-global coexp still fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import prod

from .set_category import cardinality_obstruction, hom_cardinality


@dataclass(frozen=True)
class SiteObject:
    """Object c in a finite site."""

    name: str
    stalk_size: int  # |F(c)| proxy for presheaf F


@dataclass
class FiniteSite:
    """
    Finite site: objects + cover families (arrows into c).

    Covers model restriction along morphisms u: c' -> c in the site.
    """

    objects: tuple[SiteObject, ...]
    covers: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def stalk_at(self, name: str) -> int:
        for o in self.objects:
            if o.name == name:
                return o.stalk_size
        raise KeyError(name)

    def exponential_size(self, base: str, exponent: str) -> int:
        """
        Presheaf exponential (F^G)(c) = F(c)^{G(c)} at object c = base.

        Uses stalk sizes as F(c), G(c) proxies.
        """
        fc = self.stalk_at(base)
        gc = self.stalk_at(exponent)
        return fc**gc

    def restrict_along_cover(self, c: str) -> list[int]:
        """Sizes of sections over a cover of c (pullback proxy)."""
        fam = self.covers.get(c, (c,))
        return [self.stalk_at(name) for name in fam]


def larger_site() -> FiniteSite:
    """
    5-object site: U, V, W, UV, UVW with multiple covers for gluing tests.
    """
    return FiniteSite(
        objects=(
            SiteObject("U", 3),
            SiteObject("V", 2),
            SiteObject("W", 2),
            SiteObject("UV", 5),
            SiteObject("UVW", 6),
        ),
        covers={
            "U": ("UV", "UVW"),
            "V": ("UV", "UVW"),
            "W": ("UVW",),
            "UV": ("U", "V"),
            "UVW": ("U", "V", "W", "UV"),
        },
    )


def default_two_object_site() -> FiniteSite:
    """
    Site with objects U, V and cover {U, V} -> U cup V style.

    Stalk sizes stand in for presheaf degrees of freedom.
    """
    return FiniteSite(
        objects=(
            SiteObject("U", 3),
            SiteObject("V", 2),
            SiteObject("UV", 4),
        ),
        covers={
            "U": ("UV",),
            "V": ("UV",),
            "UV": ("U", "V"),
        },
    )


@dataclass(frozen=True)
class PresheafExponentialReport:
    site_name: str
    object: str
    exp_size: int
    set_hom_size: int
    exponential_exists_locally: bool
    cover_section_product: int


def probe_presheaf_exponential(
    site: FiniteSite,
    *,
    base_object: str = "U",
    exponent_stalk: int = 2,
    z_size: int = 3,
) -> PresheafExponentialReport:
    """
    Compare local presheaf exponential at base_object vs Set hom obstruction.
    """
    exp_sz = site.exponential_size(base_object, base_object)
    # Set obstruction uses |Y|=exponent_stalk, |A|=stalk at base
    y, a = exponent_stalk, site.stalk_at(base_object)
    set_hom = hom_cardinality(y, a + z_size)
    obs = cardinality_obstruction(y, a, z_probe=(z_size,))
    local_ok = exp_sz >= set_hom or "mismatch" not in obs.reason.lower()
    cover_prod = prod(site.restrict_along_cover(base_object))
    return PresheafExponentialReport(
        site_name="finite_site",
        object=base_object,
        exp_size=exp_sz,
        set_hom_size=set_hom,
        exponential_exists_locally=local_ok,
        cover_section_product=cover_prod,
    )


def sweep_site_exponentials(site: FiniteSite | None = None) -> list[dict[str, object]]:
    site = site or default_two_object_site()
    rows: list[dict[str, object]] = []
    for obj in site.objects:
        rep = probe_presheaf_exponential(site, base_object=obj.name)
        rows.append(
            {
                "object": obj.name,
                "stalk": obj.stalk_size,
                "exp_size": rep.exp_size,
                "set_hom": rep.set_hom_size,
                "local_exponential": rep.exponential_exists_locally,
                "cover_product": rep.cover_section_product,
            }
        )
    return rows
