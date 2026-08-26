"""Finite Set: hom sizes and why coexponential ⊣ coproduct does not exist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def hom_cardinality(domain: int, codomain: int) -> int:
    """|Hom(X,Y)| for finite sets X,Y (maps X → Y)."""
    if domain < 0 or codomain < 0:
        raise ValueError("cardinalities must be non-negative")
    if domain == 0:
        return 1
    return codomain**domain


def coproduct_cardinality(a: int, z: int) -> int:
    return a + z


def hom_into_coproduct(y: int, a: int, z: int) -> int:
    """|Hom(Y, A ⊔ Z)| — each y ∈ Y chooses a tag and an element of A or Z."""
    return hom_cardinality(y, coproduct_cardinality(a, z))


def hom_from_candidate(coexp_size: int, z: int) -> int:
    """|Hom(C, Z)| for candidate representable object C of size coexp_size."""
    return hom_cardinality(coexp_size, z)


@dataclass(frozen=True)
class ObstructionReport:
    """Why a fixed C cannot represent Z ↦ Hom(Y, A ⊔ Z) for all Z."""

    y: int
    a: int
    coexp_candidate: int
    z_values: tuple[int, ...]
    hom_into_coproduct: dict[int, int]
    hom_from_candidate: dict[int, int]
    reason: str

    @property
    def exists_nontrivial_representable(self) -> bool:
        return "degenerate" not in self.reason.lower()


def cardinality_obstruction(
    y: int,
    a: int,
    *,
    coexp_candidate: int | None = None,
    z_probe: Iterable[int] = (0, 1, 2, 3, 4, 5),
) -> ObstructionReport:
    """
    A hypothetical coexponential C = coexp(A,Y) would need, for all Z:

        |Hom(C, Z)| ≅ |Hom(Y, A ⊔ Z)|   (natural in Z)

    For finite sets this means equality of cardinalities for every Z.
    Growth in Z is |Y|^{|A|+|Z|} vs |Z|^|C| — incompatible unless degenerate.
    """
    if y < 0 or a < 0:
        raise ValueError("y and a must be non-negative")
    z_list = tuple(z_probe)
    into = {z: hom_into_coproduct(y, a, z) for z in z_list}
    c_size = coexp_candidate if coexp_candidate is not None else max(1, y)
    from_c = {z: hom_from_candidate(c_size, z) for z in z_list}

    if y == 0:
        reason = (
            "degenerate: Y empty => Hom(Y, A+Z) has size 1 for all Z; "
            "many C work — no interesting co-curry."
        )
    elif into != from_c:
        reason = (
            "cardinality mismatch: |Hom(C,Z)| = |Z|^|C| cannot match "
            "|Hom(Y,A+Z)| = (|A|+|Z|)^|Y| for all Z unless trivial constants."
        )
    else:
        reason = "unexpected exact match on probe — check larger Z or parameters."

    return ObstructionReport(
        y=y,
        a=a,
        coexp_candidate=c_size,
        z_values=z_list,
        hom_into_coproduct=into,
        hom_from_candidate=from_c,
        reason=reason,
    )


def left_adjoint_to_coproduct_exists(
    y: int,
    a: int,
    *,
    z_probe: Iterable[int] = range(8),
) -> bool:
    """
    Decide whether some finite C could represent Hom(-, Z) on the probe range.
    Returns True only for degenerate (Y=0) or accidental probe equality.
    """
    report = cardinality_obstruction(y, a, z_probe=z_probe)
    if y == 0:
        return False  # exists but not "genuine" — lecture: corner vanishes
    return report.hom_into_coproduct == {
        z: hom_from_candidate(report.coexp_candidate, z) for z in report.z_values
    }


def demonstrate_growth_contradiction(y: int, a: int, z_max: int = 6) -> str:
    """Human-readable growth comparison for lecture output."""
    lines = [
        f"Fix Y={y}, A={a}. Compare functor sizes on Z:",
        "  F(Z) = |Hom(Y, A + Z)|",
        "  G_C(Z) = |Hom(C, Z)| for candidate |C| = c",
        "",
    ]
    for z in range(z_max + 1):
        f_z = hom_into_coproduct(y, a, z)
        lines.append(f"  Z={z}: F(Z)={f_z}")
    lines.append("")
    lines.append(
        "For non-degenerate Y, F grows as (a+z)^y while G_C grows as z^c - "
        "no fixed c works for all Z. Coexponential left adjoint to coproduct: absent in Set."
    )
    return "\n".join(lines)
