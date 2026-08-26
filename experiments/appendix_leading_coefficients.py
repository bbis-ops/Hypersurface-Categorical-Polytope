r"""
Appendix: numerical reproduction of the leading gap coefficients.

Self-contained -- depends only on numpy and the standard library. Reproduces the
leading coefficients of Theorem 5.1 (face_bowl, quadratic law), Theorem 9.1
(directional / coupled law), and Theorem 10.1 (fractional-exponent law).

Cancellation safety (the point of this rewrite)
-----------------------------------------------
The naive route -- maximize C_s(x) over the box, then subtract the corner value
C_s(corner) -- subtracts two quantities that are both O(1) while their difference
is Theta(s^p). In float64 that difference is lost once s <~ 1e-5, and returns
exactly 0.0 by s ~ 1e-8.

Every function here instead works in the INWARD coordinate x = (distance from the
corner), with the objective written so that f(0) = 0 identically. The gap is then

        Delta(s) = max_{x >= 0} f(x)

read off directly -- no subtraction of large numbers -- so it stays accurate to
full precision down to s ~ 1e-9 and below. Each closed-form coefficient is
cross-checked against (a) this cancellation-free numerical maximization and, where
a polynomial stationarity condition exists, (b) the exact root via numpy.roots.
"""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------
# numpy-only unimodal maximizer (golden section)
# --------------------------------------------------------------------------


def golden_max(f, a, b, iters=400):
    """Maximize a unimodal f on [a, b]. Returns (x_star, f_star)."""
    r = (np.sqrt(5.0) - 1.0) / 2.0  # 1/phi = 0.6180339887...
    c, d = b - r * (b - a), a + r * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(iters):
        if fc > fd:            # maximum lies in [a, d]
            b, d, fd = d, c, fc
            c = b - r * (b - a)
            fc = f(c)
        else:                  # maximum lies in [c, b]
            a, c, fc = c, d, fd
            d = a + r * (b - a)
            fd = f(d)
    x = 0.5 * (a + b)
    return x, f(x)


def _smallest_positive_real_root(coeffs):
    """Smallest strictly positive real root of a polynomial (numpy.roots)."""
    roots = np.roots(coeffs)
    real = [z.real for z in roots if abs(z.imag) < 1e-9 and z.real > 1e-15]
    return min(real) if real else float("nan")


# ==========================================================================
# Theorem 5.1 -- face_bowl quadratic law:  Delta ~ (9/32) s^2,  delta ~ (3/8) s
# ==========================================================================
#
# Diagonal reduction (Lemma V.0): on u = w = t the objective is
#   g(t) = 2t - 2t^2 + s (1 - t^2)^2,  corner at t = 1/2.
# Inward coordinate x = 1/2 - t. Expanding g(1/2 - x) - g(1/2) EXACTLY gives a
# polynomial with no constant/linear O(1) piece -- the cancellation is done by
# hand, once, symbolically:
#
#   h(x) = -2 x^2 + s [ (3/2)(x - x^2) + (x - x^2)^2 ],   x in [0, 1/2],  h(0)=0.


def face_bowl_gap(s):
    """(Delta, delta) for face_bowl, cancellation-free. delta = argmax = 1/2 - t*."""
    def h(x):
        y = x - x * x
        return -2.0 * x * x + s * (1.5 * y + y * y)

    x_star, gap = golden_max(h, 0.0, 0.5)
    return gap, x_star


def face_bowl_gap_exact(s):
    """Same gap from the exact stationarity cubic h'(x) = 0:
        4 s x^3 - 6 s x^2 - (4 + s) x + 3 s / 2 = 0,
    solved by numpy.roots (the small positive root is delta)."""
    x = _smallest_positive_real_root([4.0 * s, -6.0 * s, -(4.0 + s), 1.5 * s])
    y = x - x * x
    return (-2.0 * x * x + s * (1.5 * y + y * y)), x


# ==========================================================================
# Theorem 9.1 -- directional / coupled law:
#   Delta(s) = s^2 * max_d  (D_d P)^2 / (2 * sum_i c_i d_i^2)     (c_i = 2 here)
# Coupled P: the maximizer sits on ONE inward ray; the separable/additive law
# (Theorem 5.1 summed over axes) strictly over-predicts by Cauchy-Schwarz.
# ==========================================================================
#
# Inward coordinates x, y >= 0, base drop x^2 + y^2 (c = 2 per axis). On a ray
# (x, y) = R (d0, d1), |d| = 1, a degree-1 P gives
#   f(R) = -R^2 + s R * P(d),   R* = s P(d)/2,   f(R*) = s^2 P(d)^2 / 4.
# The honest global maximum scans the inward half-disk of directions and takes the
# exact radial max on each -- no assumption about where the optimum lands.


def directional_gap(P, s, *, n_dirs=20001):
    """Cancellation-free 2-D gap for a degree-1-homogeneous coupled P(x, y)."""
    thetas = np.linspace(0.0, np.pi / 2.0, n_dirs)         # inward quadrant
    d0, d1 = np.cos(thetas), np.sin(thetas)
    Pd = P(d0, d1)                                          # D_d P for |d| = 1
    best = np.max(Pd * Pd) / 4.0                            # max_d P(d)^2 / (2*2)
    return s * s * best


def additive_gap(P, s):
    """The separable (Theorem 5.1-summed) prediction, which over-predicts for
    coupled P: sum of per-axis pushes gamma_i = P along each axis, gap = s^2 * sum
    gamma_i^2 / 4."""
    gx = P(np.array([1.0]), np.array([0.0]))[0]
    gy = P(np.array([0.0]), np.array([1.0]))[0]
    return s * s * (gx * gx + gy * gy) / 4.0


# ==========================================================================
# Theorem 10.1 -- fractional-exponent law:  P = gamma x^alpha, 0 < alpha < 2
#   x* = (alpha gamma s / c)^{1/(2-alpha)},
#   Delta(s) = c (2-alpha)/(2 alpha) (alpha gamma s / c)^{2/(2-alpha)} = Theta(s^p),
#   p = 2/(2-alpha).
# ==========================================================================
#
# Inward coordinate x >= 0, base drop (c/2) x^2, so f(x) = -(c/2) x^2 + s gamma x^a,
# f(0) = 0 -- the gap is max f directly.


def fractional_coefficient(alpha, gamma=1.0, c=2.0):
    """Leading coefficient and exponent (p, C) with Delta ~ C s^p."""
    p = 2.0 / (2.0 - alpha)
    C = c * (2.0 - alpha) / (2.0 * alpha) * (alpha * gamma / c) ** (2.0 / (2.0 - alpha))
    return p, C


def fractional_gap(alpha, s, gamma=1.0, c=2.0):
    """Cancellation-free numerical gap for P = gamma x^alpha."""
    p, _ = fractional_coefficient(alpha, gamma, c)
    x_hat = (alpha * gamma * s / c) ** (1.0 / (2.0 - alpha))   # scale of the optimum
    hi = max(10.0 * x_hat, 1e-300)
    f = lambda x: -(c / 2.0) * x * x + s * gamma * x ** alpha
    _, gap = golden_max(f, 0.0, hi)
    return gap


# ==========================================================================
# Report
# ==========================================================================


def main():
    print("Theorem 5.1  face_bowl:  Delta/s^2 -> 9/32 =", 9 / 32,
          "   delta/s -> 3/8 =", 3 / 8)
    print(f"  {'s':>7} {'Delta/s^2 (num)':>16} {'Delta/s^2 (exact)':>18} "
          f"{'delta/s (num)':>14} {'delta/s (exact)':>16}")
    for s in [1e-1, 1e-3, 1e-5, 1e-7, 1e-9]:
        Dn, dn = face_bowl_gap(s)
        De, de = face_bowl_gap_exact(s)
        print(f"  {s:>7.0e} {Dn / s**2:>16.6f} {De / s**2:>18.6f} "
              f"{dn / s:>14.6f} {de / s:>16.6f}")

    print("\nTheorem 9.1  directional (coupled):  isotropic c=2, expect Delta/s^2 = 1/4;")
    print("             the separable/additive law over-predicts (1/2 for the cone).")
    cone = lambda x, y: np.sqrt(x * x + y * y)     # D_d P = 1 in every direction
    crease = lambda x, y: np.abs(x - y)            # coupled crease
    print(f"  {'P':>18} {'Delta/s^2 (dir)':>16} {'additive/s^2':>14} {'over-pred x':>12}")
    for name, P in [("cone sqrt(x^2+y^2)", cone), ("crease |x-y|", crease)]:
        s = 1e-4
        dg = directional_gap(P, s) / s**2
        ag = additive_gap(P, s) / s**2
        print(f"  {name:>18} {dg:>16.6f} {ag:>14.6f} {ag / dg:>12.4f}")
    # stability of the coupled gap across s (must stay 0.25):
    print("  cone Delta/s^2 across s:",
          "  ".join(f"{directional_gap(cone, s) / s**2:.6f}"
                    for s in [1e-2, 1e-5, 1e-8]))

    print("\nTheorem 10.1  fractional P = x^alpha (c=2):  Delta/s^p -> C, p = 2/(2-alpha)")
    print(f"  {'alpha':>6} {'p':>7} {'C (closed)':>12} {'C (num @1e-6)':>14} "
          f"{'C (num @1e-9)':>14}")
    for alpha in [0.5, 1.0, 1.5]:
        p, C = fractional_coefficient(alpha)
        c6 = fractional_gap(alpha, 1e-6) / (1e-6) ** p
        c9 = fractional_gap(alpha, 1e-9) / (1e-9) ** p
        print(f"  {alpha:>6} {p:>7.4f} {C:>12.6f} {c6:>14.6f} {c9:>14.6f}")


if __name__ == "__main__":
    main()
