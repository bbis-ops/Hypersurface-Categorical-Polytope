"""
Neighboring vertices when the coexponential corner is empty in Set.

Reversing arrows is a strategy, not a guarantee of representability. These
corners carry dual-flavored structure without set-theoretic co-curry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Generic, Hashable, TypeVar

from .set_category import hom_cardinality

T = TypeVar("T", bound=Hashable)
R = TypeVar("R", bound=Hashable)


class NeighborVertex(Enum):
    """Walkable corners adjacent to the empty coexponential vertex in Set."""

    CLOSED_MONOIDAL = auto()  # (x) dashv [-,=] on tensor, not cartesian product
    DIALECTICA_CHU = auto()  # linear / relational duals
    CONTINUATION = auto()  # right adjoint to sum-like types via CPS
    COALGEBRA_COMONAD = auto()  # final coalgebras, not left adjoint to coproduct


@dataclass(frozen=True)
class VertexGuide:
    vertex: NeighborVertex
    adjunction_shape: str
    instead_of_coexponential: str
    inhabited_in_set: bool


NEIGHBOR_GUIDES: tuple[VertexGuide, ...] = (
    VertexGuide(
        NeighborVertex.CLOSED_MONOIDAL,
        "tensor (-) dashv internal hom [-,=]",
        "Internal hom for tensor, not cartesian product",
        True,
    ),
    VertexGuide(
        NeighborVertex.DIALECTICA_CHU,
        "relational dual (Chu) / predicate pairs (Dialectica)",
        "Linear or relational duals, not set-theoretic co-curry",
        True,
    ),
    VertexGuide(
        NeighborVertex.CONTINUATION,
        "CPS: A+B -> R  ~=  (A->R) x (B->R)",
        "Right adjoint to sum-like types encoded differently",
        True,
    ),
    VertexGuide(
        NeighborVertex.COALGEBRA_COMONAD,
        "final coalgebra (observation), comonad duplicate",
        "Universal properties with final coalgebras, not left adjoint to coproduct",
        True,
    ),
)


# --- Closed monoidal (tensor vs cartesian product) ---


def tensor_disjoint(a: int, b: int) -> int:
    """A tensor B in a coproduct-monoidal reading of finite sets: |A|+|B|."""
    return a + b


def internal_hom_cardinality(tensor_a: int, x: int, y: int) -> int:
    """
    |[A,X],Y| for Set-like internal hom over tensor = disjoint union:
    maps (A+X) -> Y  (one copy of each sort, tagged).
    """
    return hom_cardinality(tensor_a + x, y)


def cartesian_curry_cardinality(a: int, x: int, y: int) -> int:
    """|Hom(A x X, Y)| in CCC."""
    return hom_cardinality(a * x, y)


def closed_monoidal_vs_cartesian(a: int, x: int, y: int) -> dict[str, int | str]:
    """
    Same objects, different monoidal structure: tensor adjunction != product adjunction.
    """
    ten = tensor_disjoint(a, x)
    return {
        "a": a,
        "x": x,
        "y": y,
        "|Hom(A x X, Y)| (cartesian)": cartesian_curry_cardinality(a, x, y),
        "|[A,X],Y| (tensor=+)": internal_hom_cardinality(a, x, y),
        "note": "tensor corner uses + ; product corner uses * on cardinalities",
    }


# --- Dialectica / Chu ---


@dataclass(frozen=True)
class ChuSpace(Generic[T, R]):
    """Chu space (X, A, r: X x A -> Sigma) for relational duals."""

    objects: frozenset[T]
    attributes: frozenset[R]
    relation: Callable[[T, R], bool]

    def dual(self) -> ChuSpace[R, T]:
        """Dual Chu space: swap object and attribute sorts."""
        return ChuSpace(
            objects=self.attributes,
            attributes=self.objects,
            relation=lambda attr, obj: self.relation(obj, attr),
        )


@dataclass(frozen=True)
class DialecticaPair(Generic[T]):
    """Dialectica object: predicate on a product (U, V) -> Omega = bool."""

    u: frozenset[T]
    v: frozenset[T]
    predicate: Callable[[T, T], bool]

    def linear_reading(self, u0: T, v0: T) -> bool:
        return self.predicate(u0, v0)


def chu_morphism_exists(
    src: ChuSpace[T, R],
    dst: ChuSpace[T, R],
    f: Callable[[T], T],
    g: Callable[[R], R],
) -> bool:
    """
    Chu morphism (f,g) with f: X -> X', g: A' -> A and r(x,a) => r'(f(x), g(a)).
    Toy check on finite samples.
    """
    for x in src.objects:
        for a in dst.attributes:
            if src.relation(x, g(a)) and not dst.relation(f(x), a):
                return False
    return True


# --- Continuations (sum-like right adjoint) ---


def sum_continuation_rep(
    a: int,
    b: int,
    r: int,
) -> tuple[int, int]:
    """
    CPS reading: maps (A + B) -> R correspond to (A -> R) x (B -> R).
    Cardinality witness on finite sets.
    """
    left = hom_cardinality(a + b, r)
    right = hom_cardinality(a, r) * hom_cardinality(b, r)
    return left, right


def verify_continuation_adjunction(a: int, b: int, r: int) -> bool:
    return sum_continuation_rep(a, b, r)[0] == sum_continuation_rep(a, b, r)[1]


# --- Coalgebra / comonad ---


@dataclass(frozen=True)
class Coalgebra(Generic[T]):
    carrier: frozenset[T]
    observe: Callable[[T], tuple[T, ...]]  # shape F(X) -> X coalgebra


def coalgebra_morphism(
    src: Coalgebra[T],
    dst: Coalgebra[T],
    h: Callable[[T], T],
) -> bool:
    """h: src -> dst commutes with observe (toy finite check)."""
    for x in src.carrier:
        ox = src.observe(x)
        hx = tuple(h(xi) for xi in ox)
        if h(x) not in dst.carrier or dst.observe(h(x)) != hx:
            return False
    return True


def final_coalgebra_nat() -> Coalgebra[int]:
    """
    Final coalgebra flavor: streams as Nat -> A (here A = {0,1} as two states).
    Observation: head/tail on a finite prefix encoded as int list.
    """

    def observe(n: int) -> tuple[int, ...]:
        if n <= 0:
            return (0,)
        return (n % 2, n // 2)

    return Coalgebra(carrier=frozenset(range(8)), observe=observe)


@dataclass(frozen=True)
class ComonadWitness(Generic[T]):
    """Comonad on a type: duplicate (coalgebra) + counit, not coproduct left adjoint."""

    carrier: frozenset[T]
    duplicate: Callable[[T], tuple[T, T]]
    counit: Callable[[T], T]

    def coassociative_on(self, x: T) -> bool:
        a, b = self.duplicate(x)
        aa, ab = self.duplicate(a)
        ba, bb = self.duplicate(b)
        return aa == self.duplicate(a)[0] and self.counit(a) == x


# --- Walk from empty coexponential corner ---


@dataclass(frozen=True)
class PolytopeWalkStep:
    from_corner: str
    to_vertex: NeighborVertex
    lesson: str


def walk_from_empty_coexponential() -> list[PolytopeWalkStep]:
    """
    Suggested path when coexp corner vanishes: visit inhabited neighbors in Set.
    """
    return [
        PolytopeWalkStep(
            "COPRODUCT_COEXPONENTIAL (empty)",
            NeighborVertex.CLOSED_MONOIDAL,
            "tensor dashv internal hom replaces product dashv exponential",
        ),
        PolytopeWalkStep(
            "COPRODUCT_COEXPONENTIAL (empty)",
            NeighborVertex.DIALECTICA_CHU,
            "relational dual lives in Chu/Dialectica, not Hom(-, A+Z)",
        ),
        PolytopeWalkStep(
            "COPRODUCT_COEXPONENTIAL (empty)",
            NeighborVertex.CONTINUATION,
            "sum types dualized via continuation, not coexponential",
        ),
        PolytopeWalkStep(
            "COPRODUCT_COEXPONENTIAL (empty)",
            NeighborVertex.COALGEBRA_COMONAD,
            "observation and duplicate, not left adjoint to coproduct",
        ),
    ]


def duality_strategy_note() -> str:
    return (
        "Shadow of duality: reversing arrows is a strategy, not a guarantee "
        "that a representable functor on the dual side exists. "
        "Walk neighboring vertices instead of forcing coexponential in Set."
    )


def demonstrate_neighbors(a: int = 2, x: int = 1, y: int = 2) -> list[str]:
    """Lines for CLI demo."""
    lines: list[str] = []
    mono = closed_monoidal_vs_cartesian(a, x, y)
    lines.append("Closed monoidal:")
    for k, v in mono.items():
        lines.append(f"  {k}: {v}")

    chu = ChuSpace(
        objects=frozenset({"x1", "x2"}),
        attributes=frozenset({"a1"}),
        relation=lambda x, a: x == "x1",
    )
    dual = chu.dual()
    lines.append("Dialectica/Chu:")
    lines.append(f"  Chu |objects|={len(chu.objects)} |attributes|={len(chu.attributes)}")
    lines.append(f"  dual swap: objects={len(dual.objects)} attributes={len(dual.attributes)}")

    left, right = sum_continuation_rep(2, 2, 2)
    lines.append("Continuation (A+B -> R):")
    lines.append(f"  |Hom(A+B,R)|={left}  (A->R)x(B->R)={right}  equal={left == right}")

    nat = final_coalgebra_nat()
    com = ComonadWitness(
        carrier=frozenset({0, 1}),
        duplicate=lambda n: (n, n),
        counit=lambda n: n,
    )
    lines.append("Coalgebra/comonad:")
    lines.append(f"  final coalgebra carrier size={len(nat.carrier)}")
    lines.append(f"  comonad coassociative on 0: {com.coassociative_on(0)}")

    lines.append("")
    lines.append(duality_strategy_note())
    return lines
