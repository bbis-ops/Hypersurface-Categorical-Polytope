"""Finite Set as cartesian closed category: product ⊣ exponential (curry)."""

from __future__ import annotations

from typing import Callable, Hashable, TypeVar

T = TypeVar("T", bound=Hashable)


def exponential(a: frozenset[T], y: frozenset[T]) -> frozenset[frozenset[T]]:
    """Y^A in Set: all functions A → Y (as frozensets of graph pairs (a,y))."""
    if not a:
        return frozenset({frozenset()})
    result: list[frozenset[T]] = []
    elems = tuple(y)

    def extend(partial: tuple[T, ...], remaining: tuple[T, ...]) -> None:
        if not remaining:
            result.append(frozenset(zip(a, partial, strict=True)))
            return
        for v in elems:
            extend(partial + (v,), remaining[1:])

    extend((), tuple(a))
    return frozenset(result)


def product(a: frozenset[T], x: frozenset[T]) -> frozenset[tuple[T, T]]:
    return frozenset((i, j) for i in a for j in x)


def eval_morphism(a: frozenset[T], y: frozenset[T]) -> Callable[[tuple[frozenset[T], T]], T]:
    """Evaluation ev: Y^A × A → Y."""

    def ev(pair: tuple[frozenset[T], T]) -> T:
        f_graph, arg = pair
        mapping = dict(f_graph)
        return mapping[arg]

    return ev


def curry(
    a: frozenset[T],
    x: frozenset[T],
    y: frozenset[T],
    f: Callable[[tuple[T, T]], T],
) -> Callable[[T], frozenset[T]]:
    """Transpose f: A×X → Y into f̂: X → Y^A (store as graph frozenset per x)."""

    def curried(x0: T) -> frozenset[T]:
        graph = tuple((a0, f((a0, x0))) for a0 in a)
        return frozenset(graph)

    return curried


def uncurry(
    a: frozenset[T],
    x: frozenset[T],
    y: frozenset[T],
    g: Callable[[T], frozenset[T]],
) -> Callable[[tuple[T, T]], T]:
    """Transpose f̂: X → Y^A back to f: A×X → Y."""

    def uncurried(pair: tuple[T, T]) -> T:
        a0, x0 = pair
        return dict(g(x0))[a0]

    return uncurried


def curry_bijection(
    a: frozenset[T],
    x: frozenset[T],
    y: frozenset[T],
    f: Callable[[tuple[T, T]], T],
) -> tuple[Callable[[T], frozenset[T]], Callable[[tuple[T, T]], T]]:
    """
    Witness Hom(A×X, Y) ≅ Hom(X, Y^A) for finite sets.
    Returns (curried, uncurried) with uncurry(curry(f)) = f on the finite grid.
    """
    g = curry(a, x, y, f)
    back = uncurry(a, x, y, g)
    return g, back


def verify_curry_adjunction(
    a: frozenset[T],
    x: frozenset[T],
    y: frozenset[T],
    f: Callable[[tuple[T, T]], T],
) -> bool:
    """Check round-trip on all (a,x) ∈ A×X."""
    _, back = curry_bijection(a, x, y, f)
    for a0 in a:
        for x0 in x:
            if back((a0, x0)) != f((a0, x0)):
                return False
    return True


def hom_product_exp_cardinality(a: int, x: int, y: int) -> tuple[int, int]:
    """|Hom(A×X,Y)| and |Hom(X,Y^A)| — must agree in Set."""
    left = y ** (a * x)
    right = (y**a) ** x
    return left, right
