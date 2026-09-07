"""Exact worked examples for the corrected categorical note (standard library).

This is a reproduction script for docs/FORMAL_THEOREMS.md, not a replacement
for the legacy backend's certificate API. All decisions below use Fraction.
"""

from fractions import Fraction as R
from itertools import product
import json


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), R(0))


def matvec(matrix, vector):
    return tuple(dot(row, vector) for row in matrix)


def solve(matrix, rhs):
    """Rational Gaussian elimination for these small nonsingular examples."""
    n = len(rhs)
    rows = [[R(x) for x in row] + [R(rhs[i])] for i, row in enumerate(matrix)]
    for i in range(n):
        pivot = next(j for j in range(i, n) if rows[j][i])
        rows[i], rows[pivot] = rows[pivot], rows[i]
        divisor = rows[i][i]
        rows[i] = [x / divisor for x in rows[i]]
        for j in range(n):
            if j != i:
                factor = rows[j][i]
                rows[j] = [a - factor * b for a, b in zip(rows[j], rows[i])]
    return tuple(row[-1] for row in rows)


def objective(matrix, linear, point):
    return dot(linear, point) - dot(point, matvec(matrix, point)) / 2


def residual_certificate(matrix, linear, point, mu):
    """Theorem 2 with a caller-proved positive spectral lower bound mu."""
    assert mu > 0
    residual = tuple(c - fz for c, fz in zip(linear, matvec(matrix, point)))
    return dot(residual, residual) / (2 * mu)


def quadratic_example(scale):
    # Eigenvalues are 3*scale and 5*scale, proving the chosen mu.
    matrix = ((4 * scale, scale), (scale, 4 * scale))
    linear = (4 * scale, 4 * scale)
    joint = solve(matrix, linear)
    coordinate_pass = (R(1), R(3, 4))
    independent = (R(1), R(1))
    optimum = objective(matrix, linear, joint)
    gap = optimum - objective(matrix, linear, coordinate_pass)
    residual = tuple(c - fz for c, fz in zip(linear, matvec(matrix, coordinate_pass)))
    identity = dot(residual, solve(matrix, residual)) / 2
    bound = residual_certificate(matrix, linear, coordinate_pass, 3 * scale)
    rho = R(1, 4)  # Eigenvalues of D^(-1/2) E D^(-1/2) are +/-1/4.
    independent_gap = optimum - objective(matrix, linear, independent)
    separation_bound = rho**2 * dot(linear, independent) / (2 * (1 - rho))

    assert joint == (R(4, 5), R(4, 5))
    assert gap == identity == R(3, 40) * scale
    assert bound == R(3, 32) * scale
    assert 0 <= gap <= bound
    assert independent_gap == R(1, 5) * scale
    assert separation_bound == R(1, 3) * scale
    assert 0 <= independent_gap <= separation_bound
    assert residual_certificate(matrix, linear, joint, 3 * scale) == 0
    return {
        "scale": str(scale),
        "joint": [str(x) for x in joint],
        "coordinate_pass_gap": str(gap),
        "residual_bound": str(bound),
        "independent_gap": str(independent_gap),
        "separation_bound": str(separation_bound),
    }


def run_checks():
    corners = tuple(product((R(0), R(1)), repeat=2))

    # The old monotone-plus-quasiconvex assumptions do not imply Theorem 1.
    old_counterexample = lambda x, y: x - x * x + y
    vertex_value = max(old_counterexample(*v) for v in corners)
    nonvertex_value = old_counterexample(R(1, 2), R(1))
    assert vertex_value == 1 and nonvertex_value == R(5, 4)

    # Full-objective coordinate quasiconvexity gives endpoint domination.
    # C=2x+y+xy is affine on each coordinate slice.
    affine_slices = lambda x, y: 2 * x + y + x * y
    full_value = max(affine_slices(*v) for v in corners)
    for x, y in product((R(i, 10) for i in range(11)), repeat=2):
        assert affine_slices(x, y) <= max(affine_slices(R(0), y), affine_slices(R(1), y))
        assert affine_slices(x, y) <= full_value
    assert full_value == 4

    # Corollary 3.1 with T_A={1}, T_B={0}: delta_A=0, delta_B=1, omega=1.
    candidate = (R(1), R(0))
    candidate_gap = full_value - affine_slices(*candidate)
    candidate_bound = R(0) + R(1) + R(1)
    assert candidate_gap == candidate_bound == 2

    # Coupled constraints can introduce vertices absent from the original box.
    filtered = [v for v in corners if sum(v) <= R(1, 2)]
    assert filtered == [(R(0), R(0))]
    cut_vertex = (R(1, 2), R(0))
    assert sum(cut_vertex) == R(1, 2) > max(map(sum, filtered))

    # Scale invariance of optimizer coordinates, covariance of objective bounds.
    quadratics = [quadratic_example(scale) for scale in (R(1, 4), R(1), R(4), R(16))]
    # At scale 1, the older Phi is sqrt(2)/25. Compare squares exactly.
    assert R(3, 40) ** 2 > R(2, 625)

    # The normalized coupling bound is attained on the negative-eigenvalue mode.
    rho = R(1, 4)
    diagonal = R(4)
    matrix = ((diagonal, diagonal * rho), (diagonal * rho, diagonal))
    linear = (R(4), R(-4))
    independent = (R(1), R(-1))
    joint = solve(matrix, linear)
    gap = objective(matrix, linear, joint) - objective(matrix, linear, independent)
    bound = rho**2 * dot(linear, independent) / (2 * (1 - rho))
    assert gap == bound == R(1, 3)

    return {
        "status": "passed",
        "arithmetic": "exact rational; no fitted exponents or floating-point decisions",
        "localization_counterexample": {"best_vertex": str(vertex_value), "true_maximum": str(nonvertex_value)},
        "quadratic_examples": quadratics,
        "sharp_separation_bound": str(bound),
        "candidate_search": {"gap": str(candidate_gap), "upper_bound": str(candidate_bound)},
        "coupled_constraint_example": {"filtered_corner_maximum": "0", "true_maximum": "1/2"},
    }


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2))
