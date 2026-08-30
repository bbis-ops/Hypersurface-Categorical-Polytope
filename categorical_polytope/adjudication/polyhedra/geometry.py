"""
Polyhedral geometry for domain three: `Ax <= b`, vertices, and edge directions.

Domain one runs entirely on a box. `BoxBounds` is documented as "independent
interval constraints" and `vertex_maximize` enumerates 2^d corners, so every
V.7-V.14 result is a statement about a *hypercube* - the most special polytope
there is. This module supplies the general object so the same laws can be asked
on a simplex, on an arbitrary bounded polytope, and at degenerate vertices.

The distinction that matters is coordinates. At a simple vertex (exactly d
active constraints) the inward cone is spanned by d edge directions, and any
such cone is affinely equivalent to the positive orthant - so the box laws
should transfer *when stated in edge coordinates*. They have no reason to
transfer when measured along ambient axes, because at a tilted vertex an axis
is not an edge. Domain three tests exactly that difference.

Small dimensions only (d <= 3): vertex enumeration is brute force over d-subsets
of the constraints, which is fine at this size and keeps the whole thing stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

#: Tolerance for calling a constraint active or a point feasible.
TOL = 1e-9

#: Largest dimension the brute-force enumeration will accept.
MAX_DIM = 3

#: Largest constraint count, bounding C(m, d) work.
MAX_ROWS = 12


class GeometryError(ValueError):
    """The supplied system is not a usable bounded polyhedron."""


Matrix = list[list[float]]
Vector = list[float]


def _solve(matrix: Matrix, rhs: Vector) -> Vector | None:
    """Gaussian elimination with partial pivoting. None when singular."""
    n = len(matrix)
    aug = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col] / pivot_value
            if factor:
                for k in range(col, n + 1):
                    aug[row][k] -= factor * aug[col][k]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def _inverse(matrix: Matrix) -> Matrix | None:
    """Inverse of a small square matrix, column by column. None when singular."""
    n = len(matrix)
    columns: Matrix = []
    for i in range(n):
        basis = [1.0 if j == i else 0.0 for j in range(n)]
        solved = _solve(matrix, basis)
        if solved is None:
            return None
        columns.append(solved)
    return [[columns[j][i] for j in range(n)] for i in range(n)]


@dataclass(frozen=True)
class Vertex:
    """A vertex, the constraints active there, and its inward edge directions."""

    point: tuple[float, ...]
    active: tuple[int, ...]
    #: Unit inward edge directions. Empty when the vertex is degenerate.
    edges: tuple[tuple[float, ...], ...]

    @property
    def is_simple(self) -> bool:
        """A simple vertex has exactly d active constraints and d edges."""
        return len(self.active) == len(self.point)

    @property
    def is_axis_aligned(self) -> bool:
        """True when every edge direction is a coordinate direction."""
        for edge in self.edges:
            nonzero = [i for i, value in enumerate(edge) if abs(value) > 1e-6]
            if len(nonzero) != 1:
                return False
        return True


class Polyhedron:
    """A bounded polyhedron `{x : Ax <= b}` in 2 or 3 dimensions."""

    def __init__(self, rows: Sequence[Sequence[float]], rhs: Sequence[float]):
        if not rows:
            raise GeometryError("no constraints")
        dim = len(rows[0])
        if not 2 <= dim <= MAX_DIM:
            raise GeometryError(f"dimension {dim} outside 2..{MAX_DIM}")
        if len(rows) > MAX_ROWS:
            raise GeometryError(f"{len(rows)} constraints exceeds {MAX_ROWS}")
        if len(rhs) != len(rows):
            raise GeometryError("A and b disagree on row count")
        for row in rows:
            if len(row) != dim:
                raise GeometryError("ragged constraint matrix")
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row):
                raise GeometryError("non-numeric entry in A")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in rhs):
            raise GeometryError("non-numeric entry in b")

        self.A: Matrix = [[float(v) for v in row] for row in rows]
        self.b: Vector = [float(v) for v in rhs]
        self.dim = dim

    # -- membership --------------------------------------------------------

    def slack(self, point: Sequence[float]) -> Vector:
        return [self.b[i] - sum(a * x for a, x in zip(self.A[i], point))
                for i in range(len(self.A))]

    def contains(self, point: Sequence[float], tol: float = TOL) -> bool:
        return all(s >= -tol for s in self.slack(point))

    def active_set(self, point: Sequence[float], tol: float = TOL) -> tuple[int, ...]:
        return tuple(i for i, s in enumerate(self.slack(point)) if abs(s) <= tol)

    # -- structure ---------------------------------------------------------

    def vertices(self) -> list[Vertex]:
        """
        Every vertex, by brute force over d-subsets of the constraints.

        A d-subset with an invertible submatrix gives a candidate point; it is a
        vertex when it is feasible. Degenerate vertices are found more than once
        (several subsets yield the same point) and are deduplicated, keeping the
        full active set so the caller can see the degeneracy.
        """
        found: dict[tuple[int, ...], list[float]] = {}
        for subset in combinations(range(len(self.A)), self.dim):
            square = [self.A[i] for i in subset]
            point = _solve(square, [self.b[i] for i in subset])
            if point is None or not self.contains(point):
                continue
            key = tuple(round(v, 9) + 0.0 for v in point)
            found.setdefault(key, point)

        out: list[Vertex] = []
        for key, point in sorted(found.items()):
            active = self.active_set(point)
            out.append(Vertex(tuple(point), active, self._edges(point, active)))
        return out

    def _edges(self, point: Sequence[float], active: tuple[int, ...]) -> tuple[tuple[float, ...], ...]:
        """
        Inward edge directions at a simple vertex.

        With active set S and A_S v = b_S, moving along u keeps every active
        constraint but one tight and relaxes the remaining one: A_S u = -e_i.
        So the edge directions are the negated columns of A_S^{-1}. A degenerate
        vertex has no such basis and returns nothing - by design, since the
        whole affine-equivalence argument needs exactly d independent edges.
        """
        if len(active) != self.dim:
            return ()
        square = [self.A[i] for i in active]
        inverse = _inverse(square)
        if inverse is None:
            return ()
        edges: list[tuple[float, ...]] = []
        for i in range(self.dim):
            direction = [-inverse[r][i] for r in range(self.dim)]
            norm = sum(v * v for v in direction) ** 0.5
            if norm < 1e-12:
                return ()
            edges.append(tuple(v / norm for v in direction))
        return tuple(edges)

    def is_bounded(self, samples: int = 96) -> bool:
        """
        Decide boundedness by exact coverage of normalized recession slices.

        A direction u is recessive when Au <= 0, and the polyhedron is bounded
        iff no such nonzero u exists.  Any nonzero u can be rescaled so one of
        its largest-magnitude coordinates is +1 or -1.  For each of those 2d
        slices, feasibility is a bounded linear system in at most two unknowns;
        enumerating its vertices is complete under this module's d <= 3 limit.

        ``samples`` remains in the signature for compatibility with older
        callers but no longer affects correctness.
        """
        _ = samples
        for fixed_axis in range(self.dim):
            free_axes = [axis for axis in range(self.dim) if axis != fixed_axis]
            for fixed_value in (-1.0, 1.0):
                rows = [[row[axis] for axis in free_axes] for row in self.A]
                rhs = [
                    -row[fixed_axis] * fixed_value
                    for row in self.A
                ]
                # Restrict the other coordinates to [-1, 1].  Every recession
                # direction has a normalized representative in one such slice.
                for index in range(len(free_axes)):
                    rows.append([1.0 if i == index else 0.0 for i in range(len(free_axes))])
                    rhs.append(1.0)
                    rows.append([-1.0 if i == index else 0.0 for i in range(len(free_axes))])
                    rhs.append(1.0)
                if _bounded_system_feasible(rows, rhs):
                    return False
        return True


def _bounded_system_feasible(rows: Matrix, rhs: Vector) -> bool:
    """Feasibility of a bounded Ax <= b system in one or two dimensions."""
    dim = len(rows[0]) if rows else 0
    if dim == 0:
        return all(0.0 <= bound + TOL for bound in rhs)
    for subset in combinations(range(len(rows)), dim):
        point = _solve([rows[index] for index in subset], [rhs[index] for index in subset])
        if point is None:
            continue
        if all(
            sum(value * coordinate for value, coordinate in zip(row, point))
            <= bound + TOL
            for row, bound in zip(rows, rhs)
        ):
            return True
    return False

# ------------------------------------------------------------- families ----


def simplex(dim: int) -> Polyhedron:
    """The standard simplex: x_i >= 0, sum x_i <= 1. Vertices are NOT axis-aligned."""
    rows = [[-1.0 if i == j else 0.0 for j in range(dim)] for i in range(dim)]
    rows.append([1.0] * dim)
    return Polyhedron(rows, [0.0] * dim + [1.0])


def box(dim: int) -> Polyhedron:
    """The unit box, as `Ax <= b`. This is what domain one actually runs on."""
    rows: list[list[float]] = []
    rhs: list[float] = []
    for i in range(dim):
        rows.append([1.0 if j == i else 0.0 for j in range(dim)])
        rhs.append(1.0)
        rows.append([-1.0 if j == i else 0.0 for j in range(dim)])
        rhs.append(0.0)
    return Polyhedron(rows, rhs)
