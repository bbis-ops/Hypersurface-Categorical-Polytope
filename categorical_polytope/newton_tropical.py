"""
Newton-tropical master law: sharp constants and winner-take-all selection.

This module extends the vertex-localization threshold series (V.1-V.14 in
`vertex_threshold.py` and docs/FORMAL_VERTEX_THRESHOLD.md) in two ways that the
existing screens do not provide:

  * V.15 upgrades every `Theta(s^p)` order statement to a sharp asymptotic
    `Delta(s) ~ C s^p` with C in closed form. The old `universal_gap` /
    `fractional_exponent_law` give the exponent and, for a couple of hand cases,
    the constant; here the constant is uniform for all (alpha, beta, gamma, A).

  * V.16 replaces the "screen candidate rays and take the min" procedure of
    `combined_screen` with a closed-form rule: the leading gap of a *sum* of
    monomial perturbations is set by the single monomial of least base-weighted
    degree -- the lowest face of the perturbation's Newton polytope under the
    base's dilation weights (1/beta_i). Mixing perturbations is winner-take-all,
    not averaging: a term 10^5x weaker in amplitude still dominates the gap once
    it is more singular, as s -> 0.

Setup. Near a degenerate maximizing corner (put it at x = 0 in inward
coordinates x_i >= 0), the objective is

    f(x) = -sum_i A_i x_i^{beta_i}  +  s * P(x),      A_i > 0, beta_i > 1,

with base flatness orders beta_i (the base drop `r(0) - r(x)`) and a positive
perturbation P that is a sum of monomials  gamma_j * prod_i x_i^{alpha_ij}.
The gap Delta(s) = max_{x>=0} f(x) (with f(0) = 0) is how much the perturbation
buys by moving the argmax inward off the corner.

Every formula here is checked against a direct orthant maximization in
`tests/test_newton_tropical.py`. Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass


# --------------------------------------------------------------------------
# V.15 -- sharp leading constant (single flat axis, single monomial)
# --------------------------------------------------------------------------


def gap_exponent(alpha: float, beta: float = 2.0) -> float:
    """The exponent p in Delta(s) = Theta(s^p) for base order beta, perturbation
    homogeneity alpha < beta: p = beta / (beta - alpha). (V.12 master exponent.)"""
    if not 0.0 < alpha < beta:
        raise ValueError("need 0 < alpha < beta")
    return beta / (beta - alpha)


def sharp_gap_constant(alpha: float, beta: float, gamma: float, A: float = 1.0) -> tuple[float, float]:
    """
    Theorem V.15 (sharp constant). For a single flat axis with base drop
    A x^beta and perturbation s*gamma*x^alpha, 0 < alpha < beta, gamma, A > 0:

        Delta(s) = C s^p + o(s^p),
        p = beta / (beta - alpha),
        C = gamma * (beta - alpha)/beta * (gamma*alpha/(A*beta))^(alpha/(beta-alpha)).

    Returns (p, C).

    Proof. Maximise phi(x) = -A x^beta + s gamma x^alpha over x > 0. Stationarity
    A beta x^{beta-1} = s gamma alpha x^{alpha-1} gives
        x* = (s gamma alpha / (A beta))^{1/(beta-alpha)}.
    Write u = x*^{beta-alpha} = s gamma alpha/(A beta). Then x*^beta = u x*^alpha,
    so phi(x*) = x*^alpha(-A u + s gamma) = s gamma (1 - alpha/beta) x*^alpha
               = gamma (beta-alpha)/beta * (s gamma alpha/(A beta))^{alpha/(beta-alpha)} * s.
    Collecting the powers of s: alpha/(beta-alpha) + 1 = beta/(beta-alpha) = p, and
    the s-independent prefactor is the stated C. The second derivative is negative
    at x* (concave interior max), so this is the global orthant maximum. QED.
    """
    if not 0.0 < alpha < beta:
        raise ValueError("need 0 < alpha < beta")
    if gamma <= 0.0 or A <= 0.0:
        raise ValueError("need gamma > 0 and A > 0")
    p = beta / (beta - alpha)
    C = gamma * (beta - alpha) / beta * (gamma * alpha / (A * beta)) ** (alpha / (beta - alpha))
    return p, C


def sharp_single_axis_gap(alpha: float, beta: float, gamma: float, A: float, s: float) -> float:
    """Leading gap C s^p on one flat axis (V.15). Exact for the pure monomial."""
    if s <= 0.0:
        return 0.0
    p, C = sharp_gap_constant(alpha, beta, gamma, A)
    return C * s ** p


# --------------------------------------------------------------------------
# V.16 -- Newton-tropical selection for a sum of monomials
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Monomial:
    """gamma * prod_axis x_axis^power. `powers` omits zero exponents."""

    coeff: float
    powers: dict[str, float]

    def weighted_degree(self, base_orders: dict[str, float]) -> float:
        """q = sum_i alpha_i / beta_i -- the base-adapted (dilation) degree."""
        return sum(a / base_orders[ax] for ax, a in self.powers.items())

    def is_single_axis(self) -> bool:
        return len([a for a in self.powers.values() if a > 0.0]) == 1


@dataclass(frozen=True)
class NewtonFace:
    """The lowest face of P's Newton polytope under the base weights 1/beta_i."""

    q_star: float                 # minimal base-weighted degree over the support
    exponent: float               # p = 1/(1 - q_star)
    winners: tuple[Monomial, ...] # monomials attaining q_star (the dominant face)
    separable: bool               # every winner is a single-axis monomial on a distinct axis

    def describe(self) -> str:
        terms = " + ".join(
            f"{m.coeff:g}*" + "*".join(f"{ax}^{p:g}" for ax, p in m.powers.items())
            for m in self.winners
        )
        kind = "separable" if self.separable else "coupled"
        return f"q*={self.q_star:.6g}, p={self.exponent:.6g}, {kind} face: {terms}"


def newton_tropical_face(monomials: list[Monomial], base_orders: dict[str, float], *, tol: float = 1e-9) -> NewtonFace:
    """
    Theorem V.16 (Newton-tropical selection). With base drop sum A_i x_i^{beta_i}
    and P = sum_j gamma_j prod_i x_i^{alpha_ij} (gamma_j > 0), let
    q_j = sum_i alpha_ij / beta_i and q* = min_j q_j over the terms with q_j < 1.
    Then

        Delta(s) = Theta( s^{1/(1-q*)} ),

    and the gap is governed entirely by the monomials attaining q* -- the lowest
    face of P's Newton polytope under the weight vector (1/beta_i). Every term
    with q_j > q* contributes only o(s^{1/(1-q*)}).

    Proof. Apply the base-adapted dilation x_i = t^{1/beta_i} z_i, z_i >= 0, t -> 0+.
    The base drop becomes t * sum A_i z_i^{beta_i} = t Q(z), order t. Monomial j
    becomes gamma_j t^{q_j} prod z_i^{alpha_ij}, order t^{q_j}. Hence
        f = -t Q(z) + s ( t^{q*} W(z) + sum_{q_j > q*} t^{q_j}(...) ),
    where W collects the q* terms. For any fixed direction z with W(z) > 0,
    maximising -t Q + s t^{q*} W over t gives t* = (s q* W / Q)^{1/(1-q*)} = Theta(s^{1/(1-q*)}),
    at which both retained terms are Theta(s^{1/(1-q*)}) and each discarded term is
    s t*^{q_j} = Theta(s^{(1-q_j... )}) of strictly higher power of s because q_j > q*
    forces t*^{q_j} / t*^{q*} = t*^{q_j-q*} -> 0. Taking the best such z gives the
    matching lower bound; the base's uniform two-sided local bounds give the upper
    bound. So the exponent is 1/(1-q*) and the dominant face is the q* terms. QED.

    Consequence (winner-take-all). Amplitudes gamma_j never enter the exponent.
    A term that is more singular (smaller q) beats any number of larger-amplitude
    but less singular terms as s -> 0. This is a min-plus / tropical law: the map
    P |-> exponent factors through min_j q_j, not through any sum over j.
    """
    if not monomials:
        raise ValueError("need at least one monomial")
    active = [(m, m.weighted_degree(base_orders)) for m in monomials]
    below = [(m, q) for (m, q) in active if q < 1.0 - tol and m.coeff > 0.0]
    if not below:
        # No inward-increasing singular term below the base order: no leading gap.
        raise ValueError("no monomial with positive coeff and weighted degree < 1")
    q_star = min(q for _, q in below)
    winners = tuple(m for (m, q) in below if abs(q - q_star) <= tol)
    exponent = 1.0 / (1.0 - q_star)
    axes = [next(ax for ax, p in w.powers.items() if p > 0.0) for w in winners if w.is_single_axis()]
    separable = all(w.is_single_axis() for w in winners) and len(set(axes)) == len(axes)
    return NewtonFace(q_star, exponent, winners, separable)


def tropical_exponent(monomials: list[Monomial], base_orders: dict[str, float]) -> float:
    """Just the leading gap exponent p = 1/(1 - q*) (V.16)."""
    return newton_tropical_face(monomials, base_orders).exponent


def tropical_gap_leading(
    monomials: list[Monomial],
    base_orders: dict[str, float],
    s: float,
) -> tuple[float, bool]:
    """
    Leading gap C s^p (V.15 + V.16). Returns (gap, exact) where `exact` is True
    when the dominant Newton face is separable, so the constant is the closed-form
    sum of per-axis V.15 constants:

        C = sum_{winners on axis i} constant(alpha_i, beta_i, gamma, A_i=1).

    For a coupled dominant face the exponent is still exact; the constant then
    requires a direction optimisation on the face (see `_coupled_face_constant`),
    and `exact` is returned False to flag that it was obtained numerically.
    """
    if s <= 0.0:
        return 0.0, True
    face = newton_tropical_face(monomials, base_orders)
    if face.separable:
        total = 0.0
        for w in face.winners:
            (ax, alpha) = next((a, p) for a, p in w.powers.items() if p > 0.0)
            _, C = sharp_gap_constant(alpha, base_orders[ax], w.coeff, 1.0)
            total += C
        return total * s ** face.exponent, True
    C = _coupled_face_constant(face, base_orders)
    return C * s ** face.exponent, False


def _coupled_face_constant(face: NewtonFace, base_orders: dict[str, float]) -> float:
    """
    Constant for a coupled dominant face, from the reduced maximisation

        C = (1-q*)/q* * q*^p * [ max_{z>=0} W(z) / Q(z)^{q*} ]^p,   p = 1/(1-q*),

    where Q(z) = sum_i z_i^{beta_i} (A_i absorbed as 1) and W(z) = sum_{winners}
    gamma prod z_i^{alpha_i}. The ratio W/Q^{q*} is invariant under the base
    dilation, so the max is over a projective orthant; a coordinate climb suffices.
    """
    axes = sorted({ax for w in face.winners for ax in w.powers})
    q = face.q_star
    p = face.exponent

    def Q(z: dict[str, float]) -> float:
        return sum(z[ax] ** base_orders[ax] for ax in axes)

    def W(z: dict[str, float]) -> float:
        return sum(w.coeff * _prod(z[ax] ** w.powers.get(ax, 0.0) for ax in axes) for w in face.winners)

    def ratio(z: dict[str, float]) -> float:
        qz = Q(z)
        return 0.0 if qz <= 0.0 else W(z) / qz ** q

    best = 0.0
    import itertools

    grid = [0.25, 0.5, 1.0, 2.0, 4.0]
    for start in itertools.product(grid, repeat=len(axes)):
        z = {ax: start[i] for i, ax in enumerate(axes)}
        val = ratio(z)
        step = 0.5
        for _ in range(400):
            improved = False
            for ax in axes:
                for sgn in (1.0, -1.0):
                    cand = dict(z)
                    cand[ax] = max(1e-9, cand[ax] * (1.0 + sgn * step))
                    v = ratio(cand)
                    if v > val:
                        z, val, improved = cand, v, True
            if not improved:
                step *= 0.5
                if step < 1e-12:
                    break
        best = max(best, val)
    return (1.0 - q) / q * q ** p * best ** p


def _prod(xs) -> float:
    out = 1.0
    for x in xs:
        out *= x
    return out


# --------------------------------------------------------------------------
# Numerical ground truth (used by the tests and for coupled constants)
# --------------------------------------------------------------------------


def orthant_gap(
    base_orders: dict[str, float],
    monomials: list[Monomial],
    s: float,
    *,
    A: dict[str, float] | None = None,
    restarts: int = 16,
    iters: int = 800,
    scale: float = 1.0,
    rays: int = 8,
) -> float:
    """
    Direct max over the nonneg orthant of

        f(x) = -sum_i A_i x_i^{beta_i} + s * sum_j gamma_j prod_i x_i^{alpha_ij},

    with f(0) = 0. A shrinking-step climb from several small starts that proposes
    both axis-aligned moves AND random inward directions. The random directions
    matter for coupled perturbations (a cone sqrt(x y), a crease |x - y|): their
    maximiser sits on an interior ridge that coordinate-only ascent walks off,
    landing on an axis where the coupled term vanishes -- exactly the trap flagged
    in V.9. This is the ground truth the closed forms are checked against.
    """
    import random
    from math import sqrt

    axes = sorted(base_orders)
    Ai = {ax: (A or {}).get(ax, 1.0) for ax in axes}
    rng = random.Random(20260824)

    def f(x: dict[str, float]) -> float:
        drop = sum(Ai[ax] * x[ax] ** base_orders[ax] for ax in axes)
        pert = 0.0
        for m in monomials:
            term = m.coeff
            ok = True
            for ax, a in m.powers.items():
                xv = x.get(ax, 0.0)
                if xv <= 0.0 and a > 0.0:
                    ok = False
                    break
                term *= xv ** a
            if ok:
                pert += term
        return -drop + s * pert

    def moves(step: float):
        for ax in axes:
            for sgn in (1.0, -1.0):
                yield {ax: sgn * step}
        # diagonal (equal inward push -- the natural coupled-ridge direction)
        yield {ax: step for ax in axes}
        yield {ax: -step for ax in axes}
        for _ in range(rays):
            d = {ax: rng.gauss(0.0, 1.0) for ax in axes}
            norm = sqrt(sum(v * v for v in d.values())) or 1.0
            yield {ax: step * d[ax] / norm for ax in axes}

    best = 0.0
    for r in range(restarts):
        # mix broad starts with starts already near the origin (tiny optima)
        mag = scale if r % 2 == 0 else scale * 1e-3
        x = {ax: mag * (0.05 + 0.9 * rng.random()) for ax in axes}
        val = f(x)
        step = scale
        for _ in range(iters):
            improved = False
            for delta in moves(step):
                cand = {ax: max(0.0, x[ax] + delta.get(ax, 0.0)) for ax in axes}
                v = f(cand)
                if v > val:
                    x, val, improved = cand, v, True
            if not improved:
                step *= 0.5
                if step < 1e-16:
                    break
        best = max(best, val)
    return best


def measured_exponent(
    base_orders: dict[str, float],
    monomials: list[Monomial],
    *,
    s_hi: float = 1e-4,
    s_lo: float = 1e-6,
) -> float:
    """log-log slope of `orthant_gap` between two small strengths -- the
    empirical p that the tests compare against `tropical_exponent`."""
    from math import log

    ghi = orthant_gap(base_orders, monomials, s_hi)
    glo = orthant_gap(base_orders, monomials, s_lo)
    return log(ghi / glo) / log(s_hi / s_lo)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def demonstrate_newton_tropical() -> list[str]:
    lines = [
        "Newton-tropical master law (V.15 sharp constant, V.16 selection)",
        "",
        "  V.15  Delta(s) ~ C s^p,  p = beta/(beta-alpha),",
        "        C = gamma (beta-alpha)/beta (gamma alpha/(A beta))^{alpha/(beta-alpha)}",
        "",
        f"  {'alpha':>6} {'beta':>5} {'gamma':>6} {'A':>4} {'p':>7} {'C':>12}",
    ]
    for alpha, beta, gamma, A in [(1.0, 2.0, 0.75, 1.0), (0.5, 2.0, 1.0, 1.0),
                                  (1.0, 3.0, 1.0, 1.0), (1.5, 4.0, 0.9, 2.0)]:
        p, C = sharp_gap_constant(alpha, beta, gamma, A)
        lines.append(f"  {alpha:>6} {beta:>5} {gamma:>6} {A:>4} {p:>7.4f} {C:>12.6g}")
    lines += [
        "",
        "  face_bowl per-axis C = 0.140625; two axes add to 9/32 = 0.28125 (V.4).",
        "",
        "  V.16  a SUM of perturbations is winner-take-all: the least base-weighted",
        "        degree q* = min_j sum_i alpha_ij/beta_i sets p = 1/(1-q*).",
        "",
    ]
    base = {"x": 2.0, "y": 6.0}
    P = [
        Monomial(1.0, {"x": 0.5, "y": 0.5}),  # sqrt(xy), q = 1/3
        Monomial(1.0, {"x": 1.0}),            # x,        q = 1/2
        Monomial(1.0, {"y": 1.0}),            # y,        q = 1/6  <- winner
    ]
    face = newton_tropical_face(P, base)
    lines.append(f"  base x^2 + y^6, P = sqrt(xy) + x + y:")
    for m in P:
        lines.append(f"     {list(m.powers.items())}: q = {m.weighted_degree(base):.4f}")
    lines.append(f"  -> {face.describe()}")
    lines.append(f"     measured exponent = {measured_exponent(base, P):.4f}")
    lines += [
        "",
        "  A term 10^5x weaker still wins if it is more singular:",
    ]
    P2 = [Monomial(100.0, {"x": 1.0}), Monomial(0.001, {"x": 0.5})]
    face2 = newton_tropical_face(P2, {"x": 2.0})
    lines.append(f"     100*x [q=1/2, p=2] + 0.001*sqrt(x) [q=1/4, p=4/3]: p* = {face2.exponent:.4f}")
    return lines


if __name__ == "__main__":
    print("\n".join(demonstrate_newton_tropical()))
