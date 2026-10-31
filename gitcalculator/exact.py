"""Exact arithmetic for the gitcalculator's independent checks.

Everything here is deliberately separate from the backend's own numerics.
Expressions are parsed under the same whitelist as the backend and walked by
hand; ``eval`` is never called. Polynomial arithmetic, linear solves, and
feasibility decisions use ``fractions.Fraction`` throughout, so a check that
passes here is an exact statement about the supplied input.
"""

from __future__ import annotations

import ast
import math
from fractions import Fraction
from itertools import combinations, product
from typing import Iterable, Mapping, Sequence

Signature = tuple[int, ...]
Polynomial = dict[Signature, Fraction]

MAX_EXPRESSION_CHARS = 20_000
FUNCTIONS = {
    "sin": math.sin, "cos": math.cos, "exp": math.exp, "log": math.log,
    "sqrt": math.sqrt, "abs": abs, "tanh": math.tanh, "atan": math.atan,
}
CONSTANTS = {"pi": math.pi, "e": math.e}
_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
)


class UnsafeExpression(ValueError):
    """Rejected before any evaluation."""


class NotExact(ValueError):
    """The expression leaves rational arithmetic (a function, constant, or root)."""


def to_fraction(value: int | float | str | Fraction) -> Fraction:
    """Read a number through its decimal spelling, never through binary floats."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError("booleans are not numbers here")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("numbers must be finite")
        return Fraction(repr(value))
    return Fraction(value)


def label(value: Fraction | None) -> str | None:
    """Canonical exact spelling: ``3`` or ``4/3``."""
    if value is None:
        return None
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def parse(expression: str, dimension: int) -> ast.Expression:
    """Parse ``expression`` in ``x0..x{dimension-1}`` under the backend's whitelist."""
    if not isinstance(expression, str) or not expression.strip():
        raise UnsafeExpression("expression must be a non-empty string")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise UnsafeExpression(f"expression exceeds {MAX_EXPRESSION_CHARS} characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"cannot parse: {exc.msg}") from exc
    variables = {f"x{i}" for i in range(dimension)}
    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise UnsafeExpression(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, (int, float))
        ):
            raise UnsafeExpression("only numeric literals are allowed")
        if isinstance(node, ast.Name) and node.id not in variables | set(CONSTANTS) | set(FUNCTIONS):
            raise UnsafeExpression(f"unknown name {node.id!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
                raise UnsafeExpression("only whitelisted functions may be called")
    return tree


def _int_exponent(node: ast.AST) -> int | None:
    """An integer exponent literal (allowing a unary sign), else ``None``."""
    sign = 1
    while isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        sign = -sign if isinstance(node.op, ast.USub) else sign
        node = node.operand
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = to_fraction(node.value)
        if value.denominator == 1:
            return sign * int(value)
    return None


def evaluate_exact(tree: ast.AST, point: Sequence[Fraction]) -> Fraction:
    """Evaluate exactly at a rational point; raise :class:`NotExact` otherwise."""
    def walk(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return to_fraction(node.value)
        if isinstance(node, ast.Name):
            if node.id in CONSTANTS:
                raise NotExact(f"constant {node.id} is irrational")
            return point[int(node.id[1:])]
        if isinstance(node, ast.UnaryOp):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                power = _int_exponent(node.right)
                if power is None:
                    raise NotExact("non-integer exponent")
                base = walk(node.left)
                if power < 0 and base == 0:
                    raise ZeroDivisionError("zero to a negative power")
                return base ** power
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        if isinstance(node, ast.Call):
            raise NotExact(f"function {node.func.id} is not rational")  # type: ignore[attr-defined]
        raise NotExact(f"unsupported node {type(node).__name__}")
    return walk(tree)


def evaluate_float(tree: ast.AST, point: Sequence[float]) -> float:
    """Floating evaluation, used only to steer searches, never to certify."""
    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in CONSTANTS:
                return CONSTANTS[node.id]
            return float(point[int(node.id[1:])])
        if isinstance(node, ast.UnaryOp):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            value = left ** right
            if isinstance(value, complex):
                raise ValueError("complex value")
            return value
        if isinstance(node, ast.Call):
            return float(FUNCTIONS[node.func.id](*[walk(arg) for arg in node.args]))  # type: ignore[attr-defined]
        raise ValueError(f"unsupported node {type(node).__name__}")
    return walk(tree)


def total_degree(tree: ast.AST) -> int | None:
    """Total polynomial degree, or ``None`` when the expression is not polynomial."""
    def walk(node: ast.AST) -> int | None:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return 0
        if isinstance(node, ast.Name):
            return None if node.id in CONSTANTS else 1
        if isinstance(node, ast.UnaryOp):
            return walk(node.operand)
        if isinstance(node, ast.BinOp):
            left = walk(node.left)
            if left is None:
                return None
            if isinstance(node.op, ast.Pow):
                power = _int_exponent(node.right)
                if power is None or power < 0:
                    return None
                return left * power
            right = walk(node.right)
            if right is None:
                return None
            if isinstance(node.op, (ast.Add, ast.Sub)):
                return max(left, right)
            if isinstance(node.op, ast.Mult):
                return left + right
            return left if right == 0 else None  # division by a constant only
        return None
    return walk(tree)


# --- curvature certificates -------------------------------------------------
#
# A small sound rule system: every rule holds on all of R^n, hence on any
# polyhedron. "unknown" never claims anything.

def _negate(kind: str) -> str:
    return {"convex": "concave", "concave": "convex"}.get(kind, kind)


def curvature(tree: ast.AST) -> str:
    """One of ``constant``, ``affine``, ``convex``, ``concave`` or ``unknown``."""
    def constant_value(node: ast.AST) -> Fraction | None:
        try:
            if total_degree(node) == 0:
                return evaluate_exact(node, ())
        except (NotExact, ZeroDivisionError, IndexError):
            return None
        return None

    def add(left: str, right: str) -> str:
        kinds = {left, right} - {"constant"}
        if not kinds:
            return "constant"
        if "unknown" in kinds or kinds == {"convex", "concave"}:
            return "unknown"
        if kinds == {"affine"}:
            return "affine"
        return (kinds - {"affine"}).pop()

    def scale(kind: str, factor: Fraction) -> str:
        if factor == 0:
            return "constant"
        return kind if factor > 0 else _negate(kind)

    def walk(node: ast.AST) -> str:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if constant_value(node) is not None:
            return "constant"
        if isinstance(node, ast.Name):
            return "affine" if node.id not in CONSTANTS else "constant"
        if isinstance(node, ast.UnaryOp):
            kind = walk(node.operand)
            return _negate(kind) if isinstance(node.op, ast.USub) else kind
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Add):
                return add(walk(node.left), walk(node.right))
            if isinstance(node.op, ast.Sub):
                return add(walk(node.left), _negate(walk(node.right)))
            if isinstance(node.op, ast.Mult):
                for factor_node, other in ((node.left, node.right), (node.right, node.left)):
                    factor = constant_value(factor_node)
                    if factor is not None:
                        return scale(walk(other), factor)
                return "unknown"
            if isinstance(node.op, ast.Div):
                factor = constant_value(node.right)
                if factor:
                    return scale(walk(node.left), 1 / factor)
                return "unknown"
            if isinstance(node.op, ast.Pow):
                power = _int_exponent(node.right)
                base = walk(node.left)
                if power == 1:
                    return base
                if base == "affine" and power is not None and power >= 2 and power % 2 == 0:
                    return "convex"
                return "unknown"
        return "unknown"
    return walk(tree)


# --- polynomials -------------------------------------------------------------

def poly_evaluate(polynomial: Mapping[Signature, Fraction], point: Sequence[Fraction]) -> Fraction:
    total = Fraction(0)
    for signature, coefficient in polynomial.items():
        term = coefficient
        for value, power in zip(point, signature):
            if power:
                term *= value ** power
        total += term
    return total


def poly_float(polynomial: Mapping[Signature, Fraction]) -> list[tuple[float, tuple[int, ...]]]:
    """A float evaluation plan: ``[(coefficient, exponents), ...]``."""
    return [(float(c), s) for s, c in sorted(polynomial.items()) if c]


def poly_float_evaluate(plan: Sequence[tuple[float, tuple[int, ...]]], point: Sequence[float]) -> float:
    total = 0.0
    for coefficient, signature in plan:
        term = coefficient
        for value, power in zip(point, signature):
            if power:
                term *= value ** power
        total += term
    return total


def weighted_degree(signature: Signature, weights: Sequence[Fraction]) -> Fraction:
    return sum((Fraction(p) * w for p, w in zip(signature, weights)), Fraction(0))


def monomial_text(signature: Signature, axes: Sequence[str]) -> str:
    parts = [axis if p == 1 else f"{axis}^{p}" for axis, p in zip(axes, signature) if p]
    return "·".join(parts) or "1"


def poly_text(polynomial: Mapping[Signature, Fraction], axes: Sequence[str], limit: int = 12) -> str:
    """Readable spelling such as ``c0^4 + c1^2`` (lowest total degree first)."""
    items = sorted(((s, c) for s, c in polynomial.items() if c), key=lambda item: (sum(item[0]), item[0]))
    if not items:
        return "0"
    pieces = []
    for index, (signature, coefficient) in enumerate(items[:limit]):
        magnitude = abs(coefficient)
        body = monomial_text(signature, axes)
        if body == "1":
            text = label(magnitude)
        elif magnitude == 1:
            text = body
        else:
            text = f"{label(magnitude)}·{body}"
        sign = "-" if coefficient < 0 else "+"
        pieces.append((("-" if sign == "-" else "") + text) if index == 0 else f" {sign} {text}")
    if len(items) > limit:
        pieces.append(f" + … ({len(items) - limit} more)")
    return "".join(pieces)


def divides(small: Signature, large: Signature) -> bool:
    return small != large and all(a <= b for a, b in zip(small, large))


# --- linear algebra and feasibility ---------------------------------------------

def solve(matrix: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction]) -> list[Fraction] | None:
    """Exact Gaussian elimination for a square system; ``None`` if singular."""
    n = len(matrix)
    rows = [list(map(Fraction, row)) + [Fraction(value)] for row, value in zip(matrix, rhs)]
    for column in range(n):
        pivot = next((r for r in range(column, n) if rows[r][column] != 0), None)
        if pivot is None:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        lead = rows[column][column]
        rows[column] = [value / lead for value in rows[column]]
        for r in range(n):
            if r != column and rows[r][column] != 0:
                factor = rows[r][column]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[column])]
    return [row[n] for row in rows]


class FeasibilityUndecided(RuntimeError):
    """Fourier-Motzkin grew beyond its row budget."""


def _normalize(row: tuple[Fraction, ...], bound: Fraction) -> tuple[tuple[Fraction, ...], Fraction]:
    scale = next((abs(a) for a in row if a != 0), None)
    if scale is None:
        return row, bound
    return tuple(a / scale for a in row), bound / scale


def feasible(rows: Sequence[Sequence[Fraction]], bounds: Sequence[Fraction], *, budget: int = 6000) -> bool:
    """Decide exactly whether ``{x : rows·x <= bounds}`` is nonempty (Fourier-Motzkin)."""
    system = {_normalize(tuple(map(Fraction, row)), Fraction(b)) for row, b in zip(rows, bounds)}
    if not system:
        return True
    dimension = len(next(iter(system))[0])
    for k in reversed(range(dimension)):
        positive = [(r, b) for r, b in system if r[k] > 0]
        negative = [(r, b) for r, b in system if r[k] < 0]
        kept = {(r, b) for r, b in system if r[k] == 0}
        for (p, pb), (q, qb) in product(positive, negative):
            fp, fq = p[k], -q[k]
            row = tuple(a / fp + c / fq for a, c in zip(p, q))
            kept.add(_normalize(row, pb / fp + qb / fq))
            if len(kept) > budget:
                raise FeasibilityUndecided("Fourier-Motzkin row budget exceeded")
        # Drop dominated duplicates: same row, keep the tightest bound.
        tightest: dict[tuple[Fraction, ...], Fraction] = {}
        for r, b in kept:
            tightest[r] = min(b, tightest.get(r, b))
        system = set(tightest.items())
        if any(all(a == 0 for a in r) and b < 0 for r, b in system):
            return False
    return all(b >= 0 for r, b in system if all(a == 0 for a in r))


def vertices(rows: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction], *, limit: int = 6000) -> list[tuple[Fraction, ...]] | None:
    """All vertices of ``{x : rows·x <= rhs}`` exactly, or ``None`` past ``limit`` subsets."""
    m = len(rows)
    n = len(rows[0]) if rows else 0
    if n == 0 or math.comb(m, n) > limit:
        return None
    found: list[tuple[Fraction, ...]] = []
    seen: set[tuple[Fraction, ...]] = set()
    for subset in combinations(range(m), n):
        point = solve([rows[i] for i in subset], [rhs[i] for i in subset])
        if point is None:
            continue
        key = tuple(point)
        if key in seen:
            continue
        if all(sum(a * x for a, x in zip(row, key)) <= b for row, b in zip(rows, rhs)):
            seen.add(key)
            found.append(key)
    return found


def dot(left: Iterable[Fraction], right: Iterable[Fraction]) -> Fraction:
    return sum((a * b for a, b in zip(left, right)), Fraction(0))
