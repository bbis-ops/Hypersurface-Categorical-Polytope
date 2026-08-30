"""
The V-style exponent laws, restated on a general polyhedron.

The box laws say: at a degenerate vertex where the base drops like sum A_i t_i^b_i
and the perturbation has weighted degree q = sum alpha_i / beta_i, the gap grows
like s^(1/(1-q)). On a box the t_i are the coordinate axes, because at a box
corner the edges *are* the axes.

That coincidence is what domain three is built to remove. At a simple vertex of
any polytope the inward cone is spanned by d edge directions, and any such cone
is affinely equivalent to the positive orthant - so the law should survive when
the degrees are measured along EDGES. There is no corresponding argument for
measuring along ambient axes at a tilted vertex, where an axis is not an edge
and may not even point into the polytope.

So the same geometry is asked twice, and the difference between the two answers
is the finding:

    edge_exponent_law     degrees measured along edge directions
    ambient_exponent_law  degrees measured along coordinate axes

Both are adjudicated by arithmetic. Nothing here consults a model.
"""

from __future__ import annotations

import ast
import itertools
import math
from typing import Any, Callable, Sequence

from .geometry import Polyhedron, Vertex

#: Whitelisted call targets, mirroring domain one's expression sandbox.
_FUNCS: dict[str, Callable[..., float]] = {
    "sin": math.sin, "cos": math.cos, "exp": math.exp, "log": math.log,
    "sqrt": math.sqrt, "abs": abs, "tanh": math.tanh, "atan": math.atan,
}
_CONSTS = {"pi": math.pi, "e": math.e}

_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
)

MAX_EXPR_CHARS = 200
MAX_NODES = 80
MAX_ABS_EXPONENT = 8.0


class UnsafeExpression(ValueError):
    """Rejected before evaluation."""


def compile_expr(expr: str, dim: int) -> Callable[[Sequence[float]], float]:
    """
    Parse an expression in x0..x{dim-1} under an AST whitelist.

    The same contract domain one gives its candidates: `eval` is never called,
    the tree is walked by hand, and anything outside the whitelist can only be
    rejected rather than executed.
    """
    if len(expr) > MAX_EXPR_CHARS:
        raise UnsafeExpression(f"expression exceeds {MAX_EXPR_CHARS} characters")
    variables = {f"x{i}": i for i in range(dim)}
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"parse: {exc}") from exc

    count = 0
    for node in ast.walk(tree):
        count += 1
        if count > MAX_NODES:
            raise UnsafeExpression("expression too large")
        if not isinstance(node, _NODES):
            raise UnsafeExpression(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise UnsafeExpression("only numeric literals allowed")
        if isinstance(node, ast.Name) and node.id not in variables and node.id not in _CONSTS:
            if node.id not in _FUNCS:
                raise UnsafeExpression(f"unknown name: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
                raise UnsafeExpression("only whitelisted functions may be called")
            if node.keywords:
                raise UnsafeExpression("keyword arguments not allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            rhs = node.right
            if not isinstance(rhs, ast.Constant) or not isinstance(rhs.value, (int, float)):
                raise UnsafeExpression("exponent must be a numeric literal")
            if abs(float(rhs.value)) > MAX_ABS_EXPONENT:
                raise UnsafeExpression("exponent too large")

    def walk(node: ast.AST, point: Sequence[float]) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body, point)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in variables:
                return float(point[variables[node.id]])
            return float(_CONSTS[node.id])
        if isinstance(node, ast.UnaryOp):
            value = walk(node.operand, point)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left, point), walk(node.right, point)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            power = left**right
            if isinstance(power, complex):
                # A negative base with a fractional exponent is complex in
                # Python, and a complex value crashed every caller: they guard
                # against ValueError but then hand the result to math.isfinite,
                # which raises TypeError on a complex and took a whole campaign
                # round down with it. The laws are about real objectives, so
                # this is a point where the expression has no value - which is
                # exactly what ValueError already means to every caller.
                raise ValueError("expression is complex at this point")
            return power
        if isinstance(node, ast.Call):
            return float(_FUNCS[node.func.id](*[walk(a, point) for a in node.args]))
        raise UnsafeExpression(f"unsupported node {type(node).__name__}")

    return lambda point: walk(tree, point)


def is_affine_expression(expr: str, dim: int) -> bool:
    """Whether a validated expression is affine in ``x0..x{dim-1}``.

    Constants may be combined arithmetically, but functions and any product,
    quotient, or power that raises the variable degree above one are rejected.
    This is the hypothesis gate for the linear-programming control rule.
    """
    variables = {f"x{i}" for i in range(dim)}
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return False

    def degree(node: ast.AST) -> int | None:
        if isinstance(node, ast.Expression):
            return degree(node.body)
        if isinstance(node, ast.Constant):
            numeric = isinstance(node.value, (int, float)) and not isinstance(
                node.value, bool
            )
            return 0 if numeric else None
        if isinstance(node, ast.Name):
            if node.id in variables:
                return 1
            return 0 if node.id in _CONSTS else None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return degree(node.operand)
        if not isinstance(node, ast.BinOp):
            return None
        left = degree(node.left)
        right = degree(node.right)
        if left is None or right is None:
            return None
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return max(left, right)
        if isinstance(node.op, ast.Mult):
            total = left + right
            return total if total <= 1 else None
        if isinstance(node.op, ast.Div):
            return left if right == 0 else None
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant):
                return None
            exponent = node.right.value
            if isinstance(exponent, bool) or not isinstance(exponent, (int, float)):
                return None
            if exponent == 0:
                return 0
            if exponent == 1:
                return left
            return 0 if left == 0 else None
        return None

    return degree(tree) is not None


# ------------------------------------------------------------ measurement ---

def _step(vertex: Vertex, direction: Sequence[float], t: float) -> tuple[float, ...]:
    return tuple(v + t * d for v, d in zip(vertex.point, direction))


#: Scale pairs tried from coarse to fine. A quartic drop is 2.5e-17 at t=1e-4,
#: below any usable floor, so a single fixed pair silently reports "no signal"
#: for exactly the flat directions these laws are about. The finest pair that
#: still resolves is kept, since that is the most asymptotic one available.
_ORDER_SCALES: tuple[tuple[float, float], ...] = (
    (1e-1, 1e-2), (3e-2, 3e-3), (1e-2, 1e-3), (3e-3, 3e-4), (1e-3, 1e-4),
    (3e-4, 3e-5), (1e-4, 1e-5),
)


def directional_order(
    f: Callable[[Sequence[float]], float],
    vertex: Vertex,
    direction: Sequence[float],
    *,
    rising: bool,
    scales: tuple[tuple[float, float], ...] | None = None,
) -> float:
    """
    Leading exponent of f along `direction`, by log-log slope.

    `rising=False` measures the base's drop f(v) - f(v + t u); `rising=True`
    measures a perturbation's increase f(v + t u) - f(v). Returns 0.0 when no
    scale pair resolves, which callers treat as undecided rather than as a
    degree of zero - and the same when the expression has no real value at the
    vertex itself, which is the one evaluation that used to sit outside a
    guard. `choose_vertex` calls this before `scope` has anything wrapped, so
    an expression that is complex at the vertex propagated all the way out.
    """
    try:
        base_value = f(vertex.point)
    except (ValueError, OverflowError, ZeroDivisionError):
        return 0.0

    def delta(t: float) -> float | None:
        try:
            moved = f(_step(vertex, direction, t))
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        change = (moved - base_value) if rising else (base_value - moved)
        if not math.isfinite(change) or change <= 1e-14:
            return None
        return change

    best = 0.0
    for hi, lo in (scales or _ORDER_SCALES):
        d_hi, d_lo = delta(hi), delta(lo)
        if d_hi is None or d_lo is None:
            continue
        best = math.log(d_hi / d_lo) / math.log(hi / lo)
    return best


def weighted_degree(
    base: Callable[[Sequence[float]], float],
    pert: Callable[[Sequence[float]], float],
    vertex: Vertex,
    directions: Sequence[Sequence[float]],
) -> tuple[float, dict[str, list[float]]]:
    """
    q = sum_i alpha_i / beta_i over the supplied directions.

    Returns (q, detail). q is 0.0 when no direction carries a resolved pair,
    which the caller reports as undecided.
    """
    alphas: list[float] = []
    betas: list[float] = []
    for direction in directions:
        beta = directional_order(base, vertex, direction, rising=False)
        alpha = directional_order(pert, vertex, direction, rising=True)
        if beta > 1e-6 and alpha > 1e-6:
            alphas.append(alpha)
            betas.append(beta)
    detail = {"alphas": alphas, "betas": betas}
    if not betas:
        return 0.0, detail
    return sum(a / b for a, b in zip(alphas, betas)), detail


#: Probe scale and depth for the per-face weighted degree.
_FACE_SCALE = 1e-3
_FACE_RUNGS = 14
_FACE_SETTLED = 1e-3


def base_homogeneity(
    base: Callable[[Sequence[float]], float],
    vertex: Vertex,
    directions: Sequence[Sequence[float]],
    *,
    scale: float = 1e-2,
) -> float | None:
    """
    The order in tau at which the base falls under its own adapted dilation.

    Theorem V.16 is proved on the positive orthant for a base drop that is a
    sum of pure powers, so that Q(D_tau z) = tau Q(z) exactly. Domain three
    imports it through the affine equivalence between a simple vertex's inward
    cone and the orthant, which carries that hypothesis along unstated: in edge
    coordinates a base may hold cross terms, and one of lower weight makes the
    drop Theta(tau^c) with c < 1, at which point the per-edge beta_i no longer
    describe the cone's interior.

    Returns the measured c, or None where it does not resolve. This is recorded
    and never gated on. A row with c != 1 is not wrong - constructed violations
    at c = 0.75 and c = 0.5 both still predict correctly, because a positive
    cross term only steepens the interior and drives the optimum onto a face.
    It is a row whose agreement V.16 does not license, and the corpus should
    say which rows those are rather than let them pass as confirmations.
    """
    betas = [directional_order(base, vertex, u, rising=False) for u in directions]
    if not betas or any(b <= 1e-6 for b in betas):
        return None
    at_vertex = base(vertex.point)

    def drop(tau: float) -> float:
        point = list(vertex.point)
        for i, direction in enumerate(directions):
            coeff = scale * tau ** (1.0 / betas[i])
            for j in range(len(point)):
                point[j] += coeff * direction[j]
        return at_vertex - base(point)

    tau, settled, slope = 1.0, None, None
    for _ in range(12):
        try:
            high, low = drop(tau), drop(tau / 2.0)
        except (ValueError, OverflowError, ZeroDivisionError):
            break
        # As in `face_weighted_degree`: keep a slope already read rather than
        # discard it because a deeper rung ran out of resolution.
        if not (high > 1e-15 and low > 1e-15):
            break
        slope = math.log(high / low) / math.log(2.0)
        if settled is not None and abs(slope - settled) < 1e-4:
            break
        settled, tau = slope, tau / 8.0
    return slope


def face_weighted_degree(
    base: Callable[[Sequence[float]], float],
    pert: Callable[[Sequence[float]], float],
    vertex: Vertex,
    directions: Sequence[Sequence[float]],
) -> tuple[float, dict[str, Any]]:
    """
    q on the smallest admissible face of the tangent cone at `vertex`.

    For each face spanned by a subset S of the directions, dilate by the
    base-adapted scaling restricted to that face - coefficient i moves as
    tau**(1/beta_i) - and read q as the order of the perturbation in tau. On a
    single ray this reproduces alpha_i/beta_i exactly; on a larger face it is
    the weighted degree the box law derives for a monomial, scoped to the one
    face rather than summed across independently measured rays.

    A face is admissible only when the perturbation is POSITIVE at leading
    order on it. Two ways to fail:

      * it vanishes identically - at the tilted simplex vertex (0,1) the
        vertical edge carries no perturbation at all, so the base's quadratic
        decay there cannot set the exponent;
      * it is negative - a feasible face can point where the push lowers the
        objective, which is not a gain branch. On a sheared 3-D vertex with
        orders (2,4,6) the face spanned by rays 0 and 1 reaches x0 < 0, and
        counting it would predict 4/3 against a measured 2.

    q is the MINIMUM over admissible faces. This is Theorem V.16 in
    docs/FORMAL_NEWTON_TROPICAL.md - Newton-tropical selection, winner-take-all
    - restated on the tangent cone: a monomial of the perturbation is supported
    on the variables it involves, which is a face, its q_j is section 15's sum
    scoped to that support, and q* = min_j q_j. The gap grows like
    s**(1/(1-q*)), so as s falls the smallest exponent gives the largest gap;
    every term with q_j > q* contributes strictly higher order and is invisible
    whatever its amplitude.

    The earlier implementation had section 15's sum without V.16's selection,
    which is why it summed across rays and reached q >= 1 on eight corpus rows
    that V.16 puts at q* = 1/2.

    Returns (q, detail). q is 0.0 when no face is admissible, which the caller
    reports as undecided.
    """
    betas = [directional_order(base, vertex, u, rising=False) for u in directions]
    alphas = [directional_order(pert, vertex, u, rising=True) for u in directions]
    at_vertex = pert(vertex.point)

    def q_on(face: Sequence[int]) -> tuple[float | None, bool, str]:
        """
        The face's weighted degree, whether it settled, and why it has none.

        The settled flag matters as much as the value. `gap_exponent` has had
        one since v3, because a slope still drifting at the deepest resolved
        strength is the probe's reach rather than the law's failure. This probe
        never got the same treatment, and a drifting face degree was recorded
        as fact: on one corpus row the degree on the two-ray face read 0.333
        while still climbing through 0.7, 0.78, 0.94, which made it a false
        minimum and turned a correct prediction into a counterexample.
        """
        def pert_at(tau: float) -> float:
            point = list(vertex.point)
            for i in face:
                coeff = _FACE_SCALE * tau ** (1.0 / betas[i])
                for j in range(len(point)):
                    point[j] += coeff * directions[i][j]
            return pert(point) - at_vertex

        tau, settled, q, converged = 1.0, None, None, False
        why = ""
        for _ in range(_FACE_RUNGS):
            try:
                high, low = pert_at(tau), pert_at(tau / 2.0)
            except (ValueError, OverflowError, ZeroDivisionError):
                why = "the perturbation does not evaluate on this face"
                break
            # Zero or a loss direction: not a branch that opens a gap. Only
            # decisive on the FIRST rung - once a q has been read, a deeper
            # rung underflowing is the probe running out of resolution, not
            # the face going quiet. Discarding it there would drop a face
            # from a minimum and bias q* upward.
            if not (high > 1e-15 and low > 1e-15):
                # Which of the two it is only matters while q is still unread;
                # after that the caller keeps the q and the reason is unused.
                why = ("inactive: the perturbation vanishes on this face"
                       if abs(high) <= 1e-15 else
                       "not positive: the perturbation lowers the objective here")
                break
            q = math.log(high / low) / math.log(2.0)
            if settled is not None and abs(q - settled) < _FACE_SETTLED:
                converged = True
                break
            settled, tau = q, tau / 8.0
        # Falling out of the loop, or breaking on lost resolution after a q was
        # read, both leave `converged` False: the number is the best available
        # rather than the limit, and the caller has to be told which.
        return q, converged, why

    faces: list[tuple[list[int], float]] = []
    rejected: list[tuple[list[int], str]] = []
    unsettled: list[list[int]] = []
    best: float | None = None
    best_settled = True
    for size in range(1, len(directions) + 1):
        for face in itertools.combinations(range(len(directions)), size):
            if any(betas[i] <= 1e-6 for i in face):
                rejected.append(([*face], "no base order along an edge of this face"))
                continue
            q, converged, why = q_on(face)
            if q is None:
                rejected.append(([*face], why or "no weighted degree"))
                continue
            if not math.isfinite(q):
                rejected.append(([*face], "the weighted degree did not resolve"))
                continue
            faces.append(([*face], round(q, 6)))
            if not converged:
                unsettled.append([*face])
            if best is None or q < best:
                best, best_settled = q, converged
    # `rejected` is for callers that need to say what was filtered out and why;
    # nothing in the adjudicated path reads it, so no verdict depends on it.
    detail = {"alphas": alphas, "betas": betas, "faces": faces,
              "rejected": rejected, "unsettled": unsettled,
              "settled": best_settled}
    return (0.0 if best is None else best), detail


def _point_at(vertex: Vertex, coeffs: Sequence[float]) -> list[float]:
    """Vertex plus a non-negative combination of its inward edges."""
    point = list(vertex.point)
    for coeff, edge in zip(coeffs, vertex.edges):
        for j in range(len(point)):
            point[j] += coeff * edge[j]
    return point


#: Seed scan for `local_max_near_vertex`: one geometric ladder of edge
#: coefficients per edge, taken independently, so combinations at wildly
#: different magnitudes are reachable. Ratio 4 over 21 rungs spans a 0.25
#: radius down to about 2e-13, which is where gaps stop resolving anyway.
_SEED_RUNGS = 21
_SEED_RATIO = 4.0
#: Ceiling on seed evaluations. The ladder's resolution does NOT depend on the
#: dimension - only whether the cover is exhaustive or sampled does. Trimming
#: rungs instead would quietly cost depth in exactly the higher-dimensional
#: cases the law is meant to cover.
_SEED_BUDGET = 12000



def _seed_ladder(radius: float) -> list[float]:
    """Coefficient values to try along one edge, same in every dimension."""
    return [0.0] + [radius / (_SEED_RATIO**k) for k in range(_SEED_RUNGS)]


def _halton_bases(count: int) -> list[int]:
    """
    The first `count` primes, one Halton base per edge.

    Generated rather than tabulated: a fixed table would run out in high
    dimension and silently drop the cover back to the coordinate axes, which
    is the exact blind spot the seed scan exists to close.
    """
    primes, candidate = [], 2
    while len(primes) < count:
        if all(candidate % prime for prime in primes if prime * prime <= candidate):
            primes.append(candidate)
        candidate += 1
    return primes


def _halton(index: int, base: int) -> float:
    """Matches `base_search._halton`; duplicated to keep this package standalone."""
    value, factor = 0.0, 1.0 / base
    while index:
        index, digit = divmod(index, base)
        value += digit * factor
        factor /= base
    return value


def _seed_points(dim: int, radius: float):
    """
    Coefficient tuples to try: every combination where that is affordable, a
    deterministic low-discrepancy cover of the same lattice where it is not.

    The exhaustive product is rungs**dim, so it stops being payable around
    dim 4. Sampling keeps the cost flat in the dimension, and Halton rather
    than random keeps a verdict from depending on a seed.
    """
    ladder = _seed_ladder(radius)
    if len(ladder) ** dim <= _SEED_BUDGET:
        yield from itertools.product(ladder, repeat=dim)
        return
    bases = _halton_bases(dim)
    top = len(ladder) - 1
    for index in range(1, _SEED_BUDGET + 1):
        yield [ladder[min(top, int(_halton(index, b) * len(ladder)))] for b in bases]


def local_max_near_vertex(
    objective: Callable[[Sequence[float]], float],
    poly: Polyhedron,
    vertex: Vertex,
    *,
    radius: float,
    passes: int = 60,
    accept: Callable[[Sequence[float]], bool] | None = None,
) -> float:
    """
    Best objective value inside the polytope within `radius` of the vertex.

    Coordinate pattern search in edge coordinates, halving the step whenever a
    sweep fails to improve. Searching in edge coordinates keeps every trial in
    the inward cone by construction; feasibility against the remaining
    constraints is still checked.

    The step has to shrink a long way. For the quadratic-base, linear-push case
    the optimum sits at t ~ s/2, which is 0.005 at s=0.01 - far below any fixed
    grid over a 0.25 radius. An earlier fixed-grid version reported no gap at
    all for exactly that reason.

    A pattern search alone is not enough either. It starts at the vertex, and
    for a product perturbation every single-edge step AND the equal-step
    diagonal are strictly downhill: only a lopsided combination gains anything.
    For base -(x0^2 + x1^4) with push s*x0*x1 the optimum sits at
    x0 ~ s^2, x1 ~ s - two edges at completely different magnitudes - and the
    sweep would shrink its step to nothing at the vertex and report no gap
    against a true gap of s^4/64. So the sweep is seeded by a scan over an
    independent geometric ladder per edge, which reaches such combinations.

    The scan never consults the flatness orders. A probe that used the law's
    own exponents to find the optimum would stop being independent evidence
    for the law.

    `accept` is an optional extra feasibility test applied to every trial
    point, for callers that need the search confined to part of the polytope.
    Seeding stays inside `radius`, but the sweep that follows does not - it
    steps from the seed's own scale and can walk a long way - so a caller that
    needs a bounded region has to say so here rather than rely on the radius.
    Left at None the search is exactly what it was before the parameter
    existed, which is what keeps every recorded verdict comparable.
    """
    dim = poly.dim
    if len(vertex.edges) != dim:
        return objective(vertex.point)

    def value_at(coeffs: Sequence[float]) -> float | None:
        point = _point_at(vertex, coeffs)
        if not poly.contains(point, tol=1e-9):
            return None
        if accept is not None and not accept(point):
            return None
        try:
            out = objective(point)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        return out if math.isfinite(out) else None

    best_coeffs = [0.0] * dim
    best = objective(vertex.point)
    for combo in _seed_points(dim, radius):
        out = value_at(combo)
        if out is not None and out > best:
            best, best_coeffs = out, list(combo)
    # Step from the seed's own scale; `radius` is meaningless once the seed
    # sits many decades below it.
    step = max([c for c in best_coeffs if c > 0.0], default=radius)
    for _ in range(passes):
        improved = False
        moves: list[list[float]] = []
        for axis in range(dim):
            for delta in (step, -step, step / 4.0, -step / 4.0):
                trial = list(best_coeffs)
                trial[axis] = max(0.0, trial[axis] + delta)
                moves.append(trial)
        # A diagonal step, so a ridge between two edges is not invisible to a
        # purely coordinate-wise sweep.
        moves.append([max(0.0, c + step) for c in best_coeffs])
        for trial in moves:
            out = value_at(trial)
            if out is not None and out > best:
                best, best_coeffs, improved = out, trial, True
        if not improved:
            step /= 2.0
            if step < 1e-14:
                break
    return best


#: The neighbourhood U in Lemma 1's isolation hypothesis, and how coarse the
#: sweep outside it is. The radius matches the one `gap_exponent`'s own probe
#: works in: what has to be excluded is a rival the gap measurement could
#: reach, and a point nearer than that is inside U by construction.
_RIVAL_RADIUS = 0.25
_RIVAL_INTERIOR_SAMPLES = 512
#: How many corners get the expensive local search. Every corner's own value is
#: always read - that is free, and it is what decides a tie - but the seeded
#: search around one costs thousands of evaluations, and a proposal is free to
#: describe a polytope with a great many corners. Ranking by value first spends
#: the budget where a rival can actually be.
_RIVAL_CORNER_SEARCHES = 12


def rival_margin(
    base: Callable[[Sequence[float]], float],
    poly: Polyhedron,
    vertex: Vertex,
    *,
    radius: float = _RIVAL_RADIUS,
) -> float | None:
    """
    Lemma 1's eta: how far `v` outranks the best rival found OUTSIDE its radius.

    The face-selection law localises before it does anything else. Lemma 1
    needs `v` to be the unperturbed maximiser, isolated by some `eta > 0`
    everywhere outside a neighbourhood U, so that for small `s` the perturbed
    maximiser is still inside U and the global asymptotic is the local one.
    Every face argument then runs inside that neighbourhood. `choose_vertex`
    only ever checked that `v` is a local maximum along its own edges, which is
    strictly weaker: a second vertex can hold a higher value, and then the
    measured gap belongs to a different vertex than the predicted one and the
    agreement is luck.

    Fixing U as the ball of `radius` about `v` makes eta measurable. Returns
    `F(v) - max(F over probed points outside U)`: a local search around every
    other corner, constrained so it cannot step back into U, plus a
    low-discrepancy sweep of convex combinations for maxima that sit on a facet
    away from any corner. Excluding U is what gives the number a magnitude - a
    probe allowed inside it would converge on `F(v)` itself and report a margin
    near zero for every isolated vertex there is.

    A positive value is the margin the probe found. A value at or below zero is
    a genuine rival, and Lemma 1 is not licensed for that row.

    What this does NOT do is certify isolation. The probe is finite; it can
    find a rival, it cannot prove there is none, and no verdict is gated on it
    for exactly that reason. It is recorded so the corpus states which rows
    carry the hypothesis rather than assuming it - the same standing
    `base_homogeneity` has for Hypothesis 2. Returns None when the polytope
    holds no probed point outside U at all.
    """
    at_vertex = base(vertex.point)
    best: float | None = None

    def outside(point: Sequence[float]) -> bool:
        return math.dist(point, vertex.point) >= radius

    def consider(out: float | None) -> None:
        nonlocal best
        if out is not None and math.isfinite(out) and (best is None or out > best):
            best = out

    def value(point: Sequence[float]) -> float | None:
        try:
            out = base(point)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        return out if math.isfinite(out) else None

    corners = poly.vertices()
    ranked: list[tuple[float, Vertex]] = []
    for other in corners:
        if not outside(other.point):
            continue
        # Exact and free, and on a tie between corners it is the whole answer.
        here = value(other.point)
        if here is None:
            continue
        consider(here)
        ranked.append((here, other))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    for _, other in ranked[:_RIVAL_CORNER_SEARCHES]:
        consider(local_max_near_vertex(base, poly, other, radius=radius,
                                       accept=outside))

    # A maximum in the middle of a facet belongs to no corner's neighbourhood.
    # Evaluations only - the rival's exact height is not the question, whether
    # one outranks `v` at all is.
    points = [v.point for v in corners]
    bases = _halton_bases(len(points))
    for index in range(1, _RIVAL_INTERIOR_SAMPLES + 1):
        weights = [_halton(index, prime) for prime in bases]
        total = sum(weights)
        if total <= 0.0:
            continue
        combo = [sum(w * p[j] for w, p in zip(weights, points)) / total
                 for j in range(poly.dim)]
        if not outside(combo):
            continue
        consider(value(combo))

    return None if best is None else at_vertex - best


#: Strength ladder for the gap exponent, each rung a quarter of the one above.
#: Same shape as `adaptive_axis_gap_exponent` in base_search, which solves the
#: same problem on the box.
GAP_STRENGTHS: tuple[float, ...] = tuple(0.01 / (4.0**index) for index in range(9))

#: Consecutive slopes closer than this are taken to be the asymptotic value.
GAP_CONVERGED = 5e-3

#: Below this a measured gap is rounding, not signal, and the ladder stops.
#: With the top rung at 1e-2 this is also what bounds the largest exponent
#: the probe can resolve at all - see `domain.MEASURABLE_EXPONENT`.
GAP_RESOLUTION = 1e-13


def gap_exponent(
    base: Callable[[Sequence[float]], float],
    pert: Callable[[Sequence[float]], float],
    poly: Polyhedron,
    vertex: Vertex,
    *,
    strengths: Sequence[float] | None = None,
) -> tuple[float, tuple[float, float], bool]:
    """
    Measured gap exponent, plus whether it had settled. Returns
    (exponent, the gaps it was read from, converged).

    One fixed strength pair is not enough. The two-point slope is the
    asymptotic exponent only once the strength is small enough for the leading
    term to dominate, and at a 3-D or strongly anisotropic vertex that can take
    several decades. A measured case read 1.125 at s=1e-2 for a law that
    settles at 4/3, drifting 1.82 -> 1.69 -> 1.51 -> 1.43 -> 1.38 -> 1.35 ->
    1.34 on the way down. Judged at the top rung alone that is a
    counterexample; it is only the resolution of the probe.

    So walk down until the gap stops resolving, keep the deepest pair, and say
    whether the last two slopes agree. `converged=False` means the number is
    the best available rather than the limit, and a mismatch against it is the
    verifier's reach, not the law's failure. The caller decides what to do with
    that; this function does not editorialize.
    """
    ladder = list(strengths) if strengths is not None else list(GAP_STRENGTHS)
    at_vertex = base(vertex.point)

    def gap_at(strength: float) -> float:
        def combined(point: Sequence[float]) -> float:
            return base(point) + strength * pert(point)

        best = local_max_near_vertex(combined, poly, vertex, radius=0.25)
        return best - (at_vertex + strength * pert(vertex.point))

    slopes: list[tuple[float, tuple[float, float]]] = []
    previous: tuple[float, float] | None = None
    for strength in ladder:
        gap = gap_at(strength)
        if gap <= GAP_RESOLUTION:
            # Resolution is gone; deeper rungs would only measure rounding.
            break
        if previous is not None:
            s_hi, g_hi = previous
            slopes.append((
                math.log(g_hi / gap) / math.log(s_hi / strength), (g_hi, gap),
            ))
        previous = (strength, gap)

    if not slopes:
        return 0.0, (0.0, 0.0), False
    exponent, gaps = slopes[-1]
    converged = len(slopes) > 1 and abs(exponent - slopes[-2][0]) < GAP_CONVERGED
    return exponent, gaps, converged


def leading_coefficient(
    base: Callable[[Sequence[float]], float],
    pert: Callable[[Sequence[float]], float],
    poly: Polyhedron,
    vertex: Vertex,
    exponent: float,
    *,
    strengths: Sequence[float] | None = None,
) -> tuple[float | None, float, bool]:
    """
    The prefactor `C` in `gap ~ C s**exponent`. Returns (C, strength, settled).

    The exponent is the universal half of the law and the coefficient is the
    model-specific half: it remembers the shape of the winning face, the
    principal form and the initial form, none of which move `gamma`. Reading it
    costs nothing extra once the exponent is known - divide the measured gap by
    `s**exponent` at each rung and see whether the quotient stops moving.

    On the tilted simplex the quotient is 0.472470394 at every rung the probe
    resolves, against the closed form 3/4**(4/3); that agreement to machine
    precision is the sharpest single check the domain has, and it is the
    reason this is worth reading rather than inferring.

    `settled` is whether the two deepest rungs agree to a part in 1e-6. False
    means the quotient was still drifting, so the number is the best available
    rather than the limit - the same standing `gap_exponent` gives its slope.
    Returns None where no rung resolved a gap at all.
    """
    ladder = list(strengths) if strengths is not None else list(GAP_STRENGTHS)
    at_vertex = base(vertex.point)
    readings: list[tuple[float, float]] = []
    for strength in ladder:
        def combined(point: Sequence[float], strength: float = strength) -> float:
            return base(point) + strength * pert(point)

        best = local_max_near_vertex(combined, poly, vertex, radius=0.25)
        gap = best - (at_vertex + strength * pert(vertex.point))
        if gap <= GAP_RESOLUTION:
            break
        readings.append((strength, gap / strength**exponent))
    if not readings:
        return None, 0.0, False
    strength, coefficient = readings[-1]
    settled = (len(readings) > 1
               and abs(coefficient - readings[-2][1]) <= 1e-6 * abs(coefficient))
    return coefficient, strength, settled


def ambient_axis_directions(
    poly: Polyhedron, vertex: Vertex
) -> tuple[list[tuple[float, ...]], list[int]]:
    """
    Coordinate directions for the naive measurement, plus which ones leave the set.

    Orientation matters. A raw +e_i is often infeasible - at the box vertex
    (1,1), +x0 leaves the box - so each axis is oriented inward where an
    orientation is feasible. That is what makes the box a genuine control:
    there the inward axes coincide with the edges, so the edge and ambient
    rules must agree.

    At a tilted vertex an axis can be feasible in *neither* direction: at the
    simplex vertex (0,1) the x0 axis is tangent to `x0 + x1 <= 1`, so any step
    along it leaves the simplex. The direction is kept anyway, and its index
    returned, because the ambient rule exists to model what someone applying
    the box recipe would actually do - measure along the axes without checking
    feasibility. Dropping it instead would silently turn the finding into "out
    of scope" and hide the very effect under test.
    """
    directions: list[tuple[float, ...]] = []
    infeasible: list[int] = []
    probe = 1e-6
    for i in range(poly.dim):
        chosen = None
        for sign in (1.0, -1.0):
            direction = tuple(sign if j == i else 0.0 for j in range(poly.dim))
            if poly.contains(_step(vertex, direction, probe), tol=1e-9):
                chosen = direction
                break
        if chosen is None:
            infeasible.append(i)
            chosen = tuple(1.0 if j == i else 0.0 for j in range(poly.dim))
        directions.append(chosen)
    return directions, infeasible
