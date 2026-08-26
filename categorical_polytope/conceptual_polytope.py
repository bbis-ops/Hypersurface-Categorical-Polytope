"""Conceptual polytope: bounded diagram scores and extremal maximizers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import isclose
class Vertex(Enum):
    """Extreme points ext(P) — limit/colimit / adjunction corners."""

    LIMIT = auto()
    COLIMIT = auto()
    PRODUCT_EXPONENTIAL = auto()  # inhabited in CCC
    COPRODUCT_COEXPONENTIAL = auto()  # empty in Set
    GENERIC_INTERIOR = auto()


class AdjunctionDirection(Enum):
    LEFT = auto()   # quasiconvex-decreasing toward left adjoint
    RIGHT = auto()  # quasiconvex-increasing toward right adjoint


@dataclass(frozen=True)
class DiagramPoint:
    """
    Coordinates in the feasible polytope P ⊂ R^n.

    - product_exp: marginal along (product, exponential) axis [0,1]
    - coproduct_coexp: marginal along (coproduct, coexponential) axis [0,1]
    - composition: arrows of composition (monotone objective)
    - naturality: strength of natural transformations (monotone objective)
    - cross_naturality: off-diagonal coupling between product/coproduct blocks
    """

    product_exp: float
    coproduct_coexp: float
    composition: float
    naturality: float
    cross_naturality: float = 0.0

    def __post_init__(self) -> None:
        for name in ("product_exp", "coproduct_coexp", "composition", "naturality", "cross_naturality"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1], got {v}")

    def project_product_exp(self) -> float:
        """Linear projection onto highest feasible product/exp corner."""
        return self.product_exp

    def project_coproduct_coexp(self) -> float:
        return self.coproduct_coexp


def _quasiconvex_adjunction(t: float, direction: AdjunctionDirection) -> float:
    """Toy quasiconvex profile along adjoint axis t ∈ [0,1]."""
    if direction is AdjunctionDirection.LEFT:
        return t * t  # decreases toward left — bowl from right
    return 1.0 - (1.0 - t) ** 2  # increases toward right


@dataclass
class ConceptualPolytope:
    """
    Compact feasible set (box) with separate monotone objectives.

    Global maximum of composite understanding lies at ext(P) under the
    lecture's assumptions (Weierstrass on compact + quasiconvex margins).
    """

    composition_weight: float = 1.0
    naturality_weight: float = 1.0
    cross_penalty: float = 0.5
    # In Set the coexponential corner is empty — score it as uninhabited shadow.
    coexp_shadow_penalty: float = 2.0

    def depth_lower_bound(self, p: DiagramPoint) -> float:
        """
        Depth at p is dominated by value at projection onto max feasible
        (product/exp) and (coproduct/coexp) coordinates.
        """
        pe = p.project_product_exp()
        cc = p.project_coproduct_coexp()
        return min(
            self.composition_weight * p.composition + self.naturality_weight * p.naturality,
            pe + cc,
        )

    def composition_score(self, p: DiagramPoint) -> float:
        return self.composition_weight * p.composition

    def naturality_score(self, p: DiagramPoint) -> float:
        return self.naturality_weight * p.naturality

    def adjunction_score(self, p: DiagramPoint, direction: AdjunctionDirection) -> float:
        axis = p.product_exp if direction is AdjunctionDirection.RIGHT else p.coproduct_coexp
        return _quasiconvex_adjunction(axis, direction)

    def understanding(self, p: DiagramPoint) -> float:
        """Separately increasing in composition & naturality; penalize cross block."""
        base = self.composition_score(p) + self.naturality_score(p)
        left = self.adjunction_score(p, AdjunctionDirection.LEFT)
        right = self.adjunction_score(p, AdjunctionDirection.RIGHT)
        penalty = self.cross_penalty * p.cross_naturality
        shadow = 0.0
        if self.vertex_of(p) is Vertex.COPRODUCT_COEXPONENTIAL:
            shadow = self.coexp_shadow_penalty
        return base + left + right - penalty - shadow

    def vertex_of(self, p: DiagramPoint) -> Vertex:
        eps = 1e-9
        at_pe = isclose(p.product_exp, 1.0, abs_tol=eps) and isclose(p.coproduct_coexp, 0.0, abs_tol=eps)
        at_cc = isclose(p.coproduct_coexp, 1.0, abs_tol=eps)
        if at_pe:
            return Vertex.PRODUCT_EXPONENTIAL
        if at_cc:
            return Vertex.COPRODUCT_COEXPONENTIAL
        if isclose(p.product_exp, 1.0, abs_tol=eps):
            return Vertex.LIMIT
        if isclose(p.coproduct_coexp, 1.0, abs_tol=eps):
            return Vertex.COLIMIT
        return Vertex.GENERIC_INTERIOR

    def enumerate_vertices(self) -> list[DiagramPoint]:
        """Corners of the box — ext(P) for this toy polytope."""
        corners: list[tuple[float, float, float, float, float]] = [
            (0, 0, 0, 0, 0),
            (1, 0, 1, 1, 0),
            (0, 1, 1, 1, 0),
            (1, 1, 1, 1, 0),
            (1, 0, 1, 1, 0.2),
            (0, 1, 1, 1, 0.2),
        ]
        return [DiagramPoint(*c) for c in corners]

    def global_maximizer(self) -> tuple[DiagramPoint, float, Vertex]:
        best_p = self.enumerate_vertices()[0]
        best_u = self.understanding(best_p)
        best_v = self.vertex_of(best_p)
        for p in self.enumerate_vertices():
            u = self.understanding(p)
            if u > best_u:
                best_u, best_p, best_v = u, p, self.vertex_of(p)
        return best_p, best_u, best_v


@dataclass(frozen=True)
class CoproductBlock:
    """One summand in a disjoint-union decomposition of structured universes."""

    name: str
    points: tuple[DiagramPoint, ...]
    cross_bound: float  # max allowed off-diagonal leakage


def maximize_under_coproduct_blocks(
    polytope: ConceptualPolytope,
    blocks: list[CoproductBlock],
) -> list[tuple[str, DiagramPoint, float, Vertex]]:
    """
    Lemma (i)+(ii): optimize per coproduct factor; worst-case still at a vertex
    when cross-naturality is bounded per block.
    """
    results: list[tuple[str, DiagramPoint, float, Vertex]] = []
    for block in blocks:
        feasible = [
            p
            for p in block.points
            if p.cross_naturality <= block.cross_bound + 1e-9
        ]
        if not feasible:
            feasible = list(block.points)
        best_p = feasible[0]
        best_u = polytope.understanding(best_p)
        for p in feasible:
            u = polytope.understanding(p)
            if u > best_u:
                best_u, best_p = u, p
        results.append((block.name, best_p, best_u, polytope.vertex_of(best_p)))
    return results


def lecture_summary() -> str:
    return (
        "Lecture codified:\n"
        "  - CCC maximizer -> Vertex.PRODUCT_EXPONENTIAL (curry corner).\n"
        "  - Set coexponential corner -> empty (cardinality obstruction).\n"
        "  - Coproduct blocks -> componentwise probe; max still at vertex.\n"
        "  - Duality = reverse arrows; representability need not follow.\n"
    )
