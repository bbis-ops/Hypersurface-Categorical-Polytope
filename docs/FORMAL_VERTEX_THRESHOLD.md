# The vertex-localization threshold is zero

Formal results V.1–V.5. Module: `categorical_polytope/vertex_threshold.py`.
Tests: `tests/test_vertex_threshold.py` (17 tests).

Theorem 1 places `theta_max` in `ext(H)`. `nonlinear_objective.demonstrate_nonlinear`
then reports that the `face_bowl` interaction "breaks vertex localization" at some
strength, with `localization_at_vertex` True for small `s` and False for large `s`.
That reported transition is an artifact of grid resolution. The true critical
strength is **zero**.

---

## Setup

Box `H = [0,1] x [0,1] x [0,2] x [0,3]` with the default composite objective and
the `face_bowl` interaction of strength `s >= 0`:

$$C_s(\theta) = b + k + \big[1-(1-\lambda)^2\big] + \big[1-\sigma^2\big]
  + s\big(1-(\lambda-\tfrac12)^2\big)\big(1-(\sigma-\tfrac12)^2\big)$$

### Lemma V.0 (reduction to a symmetric face)

`b` and `k` appear only in the separable term `b + k`, so both sit at their upper
bounds. Substituting

$$u = \lambda - \tfrac12, \qquad w = \tfrac12 - \sigma, \qquad u,w \in [-\tfrac12,\tfrac12]$$

gives

$$C_s = 5 + \tfrac32 + (u+w) - (u^2+w^2) + s(1-u^2)(1-w^2).$$

**The sign flip on `\sigma` is the point.** In these coordinates the objective is
symmetric under `u <-> w`, so the maximiser lies on the diagonal `u = w`.

---

## Theorem V.1 (strict concavity)

For every `s >= 0`, `C_s` is strictly concave on the face `[-1/2,1/2]^2`.

**Proof.** $-\nabla^2 C_s = \begin{pmatrix} 2+2s(1-w^2) & 4suw \\ 4suw & 2+2s(1-u^2)\end{pmatrix}$.
The diagonal entries are `>= 2`. Since `|u|,|w| <= 1/2`,

$$\det \ge \left(2+\tfrac{3s}{2}\right)^2 - s^2 = 4 + 6s + \tfrac{5s^2}{4} > 0. \qquad \blacksquare$$

**Consequence.** The maximiser is unique. "Vertex or interior" is a genuine
dichotomy, not a question of which local optimum a search happens to find.

---

## Theorem V.2 (exact maximiser)

The maximiser is `u = w = t^*(s)`, the unique root in `[0,1/2]` of

$$2s\,t^3 - 2(1+s)\,t + 1 = 0,$$

solvable in closed form by Cardano. `t^*(0) = 1/2`, the corner itself.

**Proof.** Stationarity gives `1 - 2u - 2su(1-w^2) = 0` and its `u <-> w` mirror.
On the diagonal this is the stated cubic. By Theorem V.1 the stationary point is
the unique maximum; symmetry plus uniqueness forces it onto the diagonal. `∎`

---

## Theorem V.3 (the threshold is zero)

$$\frac{\partial C_s}{\partial u}\Big|_{u=w=1/2} = -\frac{3s}{4}.$$

Hence for every `s > 0` the inward derivative at the corner is strictly negative,
the maximiser is interior, and **`s* = 0`**.

**Proof.** Substitute `u = w = 1/2` into `1 - 2u - 2su(1-w^2)`:
`1 - 1 - 2s(1/2)(3/4) = -3s/4`. `∎`

### Why it is knife-edge

At `s = 0` the derivative is exactly `0`. The unperturbed `r` is *stationary* at
the corner `(\lambda_max, \sigma_min)`: it attains its vertex maximum with **zero
inward margin**. Theorem 1's conclusion is true there but not stable. Any
perturbation with an inward-increasing component moves the argmax off the vertex,
however small its strength.

Numerically (`vertex_margin`), the inward derivatives of the unperturbed
objective at `(1, 0, 2, 3)` are

| axis | `lam` | `sigma` | `b` | `k` |
|------|-------|---------|-----|-----|
| inward derivative | `0.0000` | `0.0000` | `-1.0000` | `-1.0000` |

`b` and `k` are strictly monotone and hold firm. The `(lam, sigma)` face is flat
to first order, and that is where localization fails.

---

## Theorem V.4 (displacement and gap)

$$\delta(s) = \tfrac12 - t^*(s) = \tfrac38 s + O(s^2), \qquad
\Delta(s) = C_s(\theta^*) - \max_{\mathrm{ext}(H)} C_s = \tfrac{9}{32}s^2 + O(s^3)$$

with Padé-type approximants `delta ≈ 3s/(8+2s)` and `Delta ≈ 9s^2/(8(4+s))`.

**Proof.** Write `t = 1/2 - d` in the cubic and expand: `-3s/4 + d(2 + s/2) + O(d^2) = 0`,
so `d = 3s/(8+2s) + O(s^2)`. For the gap, the corner gradient is
`gamma = (3s/4)(1,1)` and `-∇^2` acts on `(1,1)` as `(2 + s/2)`, so the concave
gain is `\tfrac12 \gamma^T(-\nabla^2)^{-1}\gamma = \tfrac{9s^2}{8(4+s)}`. `∎`

**Verified** against the exact cubic root:

| `s` | `delta(s)` | `3s/(8+2s)` | `Delta(s)` | `9s^2/(8(4+s))` |
|-----|-----------|-------------|-----------|-----------------|
| 0.01 | 0.003740 | 0.003741 | 0.000028 | 0.000028 |
| 0.05 | 0.018493 | 0.018519 | 0.000694 | 0.000694 |
| 0.10 | 0.036396 | 0.036585 | 0.002734 | 0.002744 |
| 0.25 | 0.085786 | 0.088235 | 0.016229 | 0.016544 |
| 1.00 | 0.241348 | 0.300000 | 0.191676 | 0.225000 |

---

## Theorem V.5 (why the numerics missed it)

A uniform grid of `n` points per axis reports a positive gap iff

$$n \ge 1 + \frac{1}{2\delta(s)} \sim 1 + \frac{4}{3s}.$$

**Proof.** By Theorem V.1 the face objective is concave and symmetric about
`t^*(s)`, so an interior point at distance `x` from the corner beats the corner
exactly when `x < 2\delta(s)`. The nearest interior grid point is at `1/(n-1)`. `∎`

This is exact — measured against `grid_maximize`, the coarsest detecting grid is
`n = 29` at `s = 0.05` (predicted 28.04), `n = 15` at `s = 0.1` (14.74), `n = 7`
at `s = 0.25` (6.83).

**The trap.** `Delta(s) = Theta(s^2)` shrinks quadratically while grid spacing
shrinks only like `1/n`, and in 4-D the cost is `n^4`. At `s = 0.05` detection
needs about 700k evaluations; `nonlinear_objective` uses `steps=7` (2401 points)
and `loop_closure` uses `steps=9`. Both report a gap of **exactly zero** while the
true gap is `0.000694`. The `localization_at_vertex` flag additionally forgives
any gap below `0.05`, so it reports success in a regime where localization has
already failed.

---

## Corollary V.6 (general criterion)

For a base objective `C_0` with vertex maximiser `theta_c` and perturbation `P`:

$$s^* = \frac{\mathrm{margin}(C_0)}{\max_i (\partial_i^{\mathrm{in}} P)(\theta_c)},
\qquad \mathrm{margin}(C_0) = \min_i \left|(\partial_i^{\mathrm{in}} C_0)(\theta_c)\right|$$

where `∂^in` is the one-sided derivative pointing into `H`. **`s* > 0` iff the base
vertex is strict.** A degenerate vertex — any axis flat to first order — gives
`s* = 0`.

This is the reusable result: `vertex_margin` is a cheap, exact diagnostic that
says whether a vertex-search strategy is safe *before* any search is run, and it
does not depend on `face_bowl` or on this particular box.

**Design rule.** Vertex-only search is trustworthy only against a *strict* vertex
maximum. Report the margin alongside `theta_max`; a margin of zero means the
localization claim carries no robustness at all.

---

## Theorem V.7 (universal quadratic law)

Let `theta_c` be a degenerate vertex maximiser of `C_0`, flat along a set `D` of
axes with inward curvature `c_i > 0` (convention `C_0 = C_0(theta_c) - (c_i/2)e^2`).
Let `P` push inward with slope `gamma_i` per unit strength. Then for `C_0 + sP`:

$$\varepsilon_i^* = \frac{\gamma_i s}{c_i} + O(s^2), \qquad
\Delta(s) = s^2 \sum_{i \in D} \frac{\gamma_i^2}{2c_i} + O(s^3).$$

**Proof.** Along axis `i`, `C_0 + sP = \mathrm{const} + \gamma_i s\varepsilon - (c_i/2)\varepsilon^2 + O(\varepsilon^3)`.
Maximising gives `\varepsilon^* = \gamma_i s/c_i` and gain `\gamma_i^2 s^2/(2c_i)`.
Cross terms between axes are `O(s^3)`. `∎`

The default `r` has `c = 2` on both `lam` and `sigma`. Applying this to every
interaction mode in `nonlinear_objective` (`screen_interactions`):

| mode | pushes inward on | `gamma` | `s*` | `Delta(s)` | breaks localization |
|------|------------------|---------|------|-----------|---------------------|
| `bilinear` | `sigma` | `1` | **0** | `s^2/4` (exact) | **yes** |
| `trig` | `lam` | `2π` | **0** | `π^2 s^2` | **yes** |
| `face_bowl` | `lam` and `sigma` | `3/4` each | **0** | `9s^2/32` | **yes** |
| `triple` | — | `0` | `∞` | `0` | no |
| `softplus` | — | `< 0` | `∞` | `0` | no |

Each closed form is reproduced by `universal_gap` to six significant figures;
`bilinear` is exact because that interaction is exactly quadratic.

### This is the stronger result

`face_bowl` is not special. **Three of the five interaction modes break vertex
localization, all at `s* = 0`, all with `Delta(s) = Theta(s^2)`.** In particular
`nonlinear_objective` documents `bilinear` as "still vertex-friendly on a box"
and `trig` as merely something that "can break pure vertex localization". Both
break it immediately, and `trig` is the worst of the three by a factor of
`(2π)^2/(3/4)^2 ≈ 70` in gap.

What separates the two groups is not the shape of the interaction but a single
scalar: whether it has a strictly positive inward derivative at the degenerate
corner. `triple` (`s·λbk`) and `softplus` do not, because both are increasing in
`lam` where `lam` is already at its upper bound, and neither involves `sigma`.

---

## Theorem V.8 (fractional exponent law)

Theorem V.7 assumed the perturbation has a *finite* inward slope. Dropping that
assumption changes the exponent. For `P = gamma * x^alpha` with `0 < alpha <= 1`
at a degenerate vertex with inward curvature `c`:

$$x^* = \left(\frac{\alpha\gamma s}{c}\right)^{\frac{1}{2-\alpha}}, \qquad
\Delta(s) = \frac{c(2-\alpha)}{2\alpha}\left(\frac{\alpha\gamma s}{c}\right)^{\frac{2}{2-\alpha}}
= \Theta\!\left(s^{\frac{2}{2-\alpha}}\right).$$

**Proof.** Maximise `gamma s x^alpha - (c/2)x^2`. Stationarity gives
`alpha gamma s x^(alpha-1) = c x`, hence `x* = (alpha gamma s/c)^(1/(2-alpha))`.
Writing `A = alpha gamma s/c`, both terms carry exponent `2/(2-alpha)` because
`1 + alpha/(2-alpha) = 2/(2-alpha)`, and the difference is the stated constant. `∎`

**The exponent `p = 2/(2-alpha)` falls continuously from 2 to 1** as `alpha` goes
from 1 to 0, recovering Theorem V.7 exactly at `alpha = 1`. Since `s` is small, a
*smaller* exponent means a *larger* gap:

| `alpha` | `p = 2/(2-alpha)` | `Delta(0.01)` predicted | measured | ratio |
|---------|-------------------|------------------------|----------|-------|
| 1 (smooth) | 2 | `2.500000e-05` | `2.500000e-05` | 1.0000 |
| 3/4 | 1.6 | `2.189267e-04` | `2.189267e-04` | 1.0000 |
| 1/2 | 4/3 | `1.017907e-03` | `1.017906e-03` | 1.0000 |
| 1/3 | 1.2 | `2.318401e-03` | `2.318401e-03` | 1.0000 |
| 1/4 | 8/7 | `3.367293e-03` | `3.367293e-03` | 1.0000 |

**Consequence.** A `sqrt(sigma)` interaction at `s = 0.01` opens a gap 40x larger
than `bilinear` at the same strength, and `sigma^(1/3)` 93x larger. Non-smooth
interactions break vertex localization by an unbounded factor more than any
smooth one, and the ratio grows as `s -> 0`. No amount of grid refinement
tolerance calibrated on smooth cases is safe against them.

---

## How V.8 was found

`interaction_search.py` screens candidate interaction expressions with the V.7
criterion — four derivative evaluations each, versus a grid search that provably
cannot see the effect. Running it over a 16-candidate bank classified 13 as
breaking and 3 as safe, confirmed the quadratic law on all 10 smooth breakers to
within 5%, and flagged two candidates whose inward derivative fails to stabilise
under `h -> h/100`. Those two are `sqrt(sigma)` and `sigma^(1/3)`; they head the
ranking by measured gap, and they are what V.8 explains.

The screen deliberately refuses to fit the quadratic law to a non-smooth
candidate (`predicted_gap` is reported as 0 with a `NON-SMOOTH` flag) rather than
returning a plausible wrong number.

---

## Theorem V.9 (directional law; separability was hiding a factor)

Theorems V.7 and V.8 both silently assumed the perturbation is **separable** — a
sum of single-axis terms. When it couples the flat axes, the additive law
over-predicts. The correct statement maximises over inward directions.

At a degenerate corner flat along axes `D` with inward curvatures `c_i`, for a
perturbation `P` positively homogeneous of degree 1, the maximiser moves along a
single ray `e = R·d`:

$$\Delta(s) = s^2 \max_{d}\ \frac{(D_d P)^2}{2\sum_{i\in D} c_i d_i^2}, \qquad d \in \text{unit inward directions.}$$

**Proof.** On ray `e = Rd`, `C_0 + sP = \mathrm{const} - \tfrac{R^2}{2}\sum c_i d_i^2 + sR\,D_dP`.
Maximise over `R`: `R^* = s\,D_dP / \sum c_i d_i^2`, gain `s^2 (D_dP)^2 / (2\sum c_i d_i^2)`.
Then maximise over `d`. `∎`

**Relation to V.7.** For separable `P = \sum_i \gamma_i e_i` the maximising
direction is the gradient itself and `\max_d (D_dP)^2/(2\sum c_i d_i^2) = \sum_i \gamma_i^2/(2c_i)`
— V.7 exactly. By Cauchy–Schwarz the additive sum is always an **upper bound**,
with equality iff `P` is separable. So V.7 is not wrong; it is the separable
special case, and it over-predicts precisely when the axes couple.

**Verified** on the two coupled terms below (isotropic `c = 2`, so both reduce to
`\Delta = s^2\max_d (D_dP)^2/4`):

| `P` | additive (V.7) | directional (V.9) | measured |
|-----|----------------|-------------------|----------|
| `sqrt((1-λ)^2 + σ^2)` (cone) | `5.0e-5` | `2.5e-5` | `2.5e-5` |
| `\|σ − (1−λ)\|` (crease) | `5.0e-5` | `2.5e-5` | `2.5e-5` |
| `σ` (separable) | `2.5e-5` | `2.5e-5` | `2.5e-5` |

The cone has directional derivative 1 in **every** inward direction, so its push
is `1`, not the `\sqrt2` a slope-1-on-both-axes linear term would have. The
additive law reconstructs it as that linear term and doubles the gap.

The continuous campaign later proposed the harder crease
`P=|4(1-λ)-7σ|`. A corner-seeded coordinate ascent became trapped on the
`λ` branch and reported coefficient `4²/4`; the theorem predicts the global
`σ` branch, `7²/4`. An independent 1,441-direction polar search with radial
maximization recovers `7²s²/4` and exponent `2`. This is retained as a numerical
guard failure: non-smooth coupled objectives require a global directional
measurement, even when their scaling law is exact.

### How V.9 was found

The hand-written bank in V.7/V.8 was entirely separable — single-axis terms and
products that vanish off-axis — so the additive law looked exact. Feeding
`interaction_search --api` real model proposals introduced `cone_dist` and
`diag_kink`, coupled terms no human seed contained. They screened as smooth
breakers where `measured = predicted/2`, an anomaly the separable law could not
explain. `directional_gap` and `is_coupled` resolve it, and the screen now labels
such candidates `COUPLED` and scores them by V.9.

---

## Theorem V.10 (unified exponent law, 0 < α < 2)

V.8 was stated only for `0 < α ≤ 1` (unbounded first derivative). The same
derivation holds for the whole open interval `0 < α < 2`, and the exponent
`p = 2/(2-α)` sweeps its entire range:

| `α` range | regularity of `P = γ x^α` | exponent `p = 2/(2-α)` |
|-----------|---------------------------|------------------------|
| `0 < α < 1` | unbounded 1st derivative | `1 < p < 2` |
| `α = 1` | linear kink (V.7) | `2` |
| `1 < α < 2` | `C^1` but not `C^2` (unbounded 2nd derivative) | `2 < p < ∞` |

As `α → 2` the exponent diverges: the perturbation becomes quadratic and folds
into the curvature, leaving no leading-order gap. As `α → 0` it tends to 1: the
perturbation becomes a step and the gap becomes linear in `s`.

**Verified exactly** (ratio of the closed-form gap to `s^p`, constant across two
decades of `s`, so the exponent is exact):

| `α` | `p` | gap `/ s^p` at `s=0.02` | at `s=0.002` |
|-----|-----|-------------------------|--------------|
| 0.50 | 1.333 | 0.47247 | 0.47247 |
| 1.00 | 2.000 | 0.25000 | 0.25000 |
| 1.25 | 2.667 | 0.17133 | 0.17133 |
| 1.50 | 4.000 | 0.10547 | 0.10547 |
| 1.75 | 8.000 | 0.04909 | 0.04909 |

### How V.10 was found

The `--frontier` prompt asked the model to escape V.7–V.9. It proposed
`sigma**1.5` — flagged "C¹ but not C²" — which the old screen mis-filed as an
anomaly (smooth breaker the quadratic law missed). It is not an anomaly: it is
the `1 < α < 2` half of the fractional law, which V.8 had simply never claimed.
The screen now estimates the homogeneity `α` of every breaker
(`estimate_homogeneity`) and files it by regime, so the fractional law is applied
uniformly for all `α ≠ 1`.

---

## Caveat V.11 (amplitude ceiling; saturating ridges)

Every result above is a *leading-order* statement, valid only while the
maximiser stays in the region where the corner expansion of `P` holds. A trivial
but sharp guard bounds when it does not:

$$\Delta(s) \le s\bigl(\sup_H P-P(\theta_c)\bigr)
\le 2s\sup_H|P|.$$

Under the normalization `P(theta_c)=0` with `P>=0`, this reduces to
`Delta(s) <= s sup_H |P|`.

If a corner-derivative law predicts more than this, it is **invalid** — the
perturbation saturates before the maximiser reaches the predicted point.

The model's `atan(σ / ((1-λ) + 0.002))` is the witness: an angular ridge whose
value depends on the *approach direction* to the corner (no gradient there). Its
finite-difference slope is ~500, so the additive law predicts `Δ ≈ 6.25`, but
`P` is bounded by `π/2`, so `Δ ≤ s·π/2 ≈ 0.0157`. Measured gap: `0.0143`. The gap
is set by amplitude, not curvature, and scales like `s`, not `s²`. `amplitude_bound`
computes the ceiling and the screen flags such candidates `SATURATING` rather
than reporting the meaningless derivative prediction.

---

## Theorem V.12 (master exponent law; the base flatness order)

Everything up to V.11 fixes the base `r` and varies the perturbation. But the
whole degeneracy rests on one property of `r`: it is *quadratically* flat at the
corner. Let the base vanish to order `β` along a slack axis (`r ~ -A x^β`) and the
perturbation be homogeneous of degree `α < β`. Then

$$\Delta(s) = \Theta\!\left(s^{\,\beta/(\beta-\alpha)}\right).$$

**Proof.** Maximise `-A x^β + sγ x^α`: `x* = (αγs/(Aβ))^{1/(β-α)}`, and both terms
scale as `x*^β ∝ s^{β/(β-α)}`. `∎`

This subsumes the whole series: `β=2` is the quadratic base, giving `2/(2-α)`
(V.7 at `α=1`, V.10 for general `α`). **`β` need not be even** — the assumption
was never used. Verified against measured gap exponents across a range of bases
the model proposed:

| base `r` | order `β` | pred `p = β/(β-1)` | measured |
|----------|-----------|--------------------|----------|
| `-(1-λ)^2 - σ^2` | 2 | 2.000 | 2.000 |
| `-|1-λ|^2.5 - |σ|^2.5` | 2.5 | 1.667 | 1.667 |
| `-|1-λ|^3 - |σ|^3` | 3 | 1.500 | 1.500 |
| `-(1-λ)^4 - σ^4` | 4 | 1.333 | 1.333 |
| `-(1-λ)^6 - σ^6` | 6 | 1.200 | 1.200 |
| `-(1-λ)^8 - σ^8` | 8 | 1.143 | 1.143 |

**A flatter base breaks localization harder.** As `β → ∞` the exponent → 1
(gap linear in `s`); as `β → α⁺` it diverges. The quadratic base is the *mildest*
degeneracy, not a typical one. Anisotropic bases (`-(1-λ)^2 - σ^6`) follow the
law on whichever slack axis is flatter.

---

## Theorem V.13 (base self-failure — a prior, distinct mode)

All of V.1–V.12 assume the corner is the base's maximiser and ask when a
perturbation dislodges it. A base can fail *before* any perturbation: its
maximiser may be interior or on a non-corner face at `s = 0`.

The model's `r = -((1-λ)-0.25)^2 - (σ-0.35)^2` has its maximum at
`(λ,σ) = (0.75, 0.35)`, strictly interior. Vertex search returns the wrong point
for **every** `s ≥ 0`. This is not the `s* = 0` story — there is no threshold at
all, because localization was never valid.

The margin criterion V.6 cannot detect this: it evaluates the corner and reports
its margin, but here the corner is not the maximiser. The correct guard is
global: compare the base's grid maximum to its vertex maximum
(`base_self_fails`). This is the one failure the cheap local criterion misses,
and it must be checked first.

### How V.12 and V.13 were found

The `base_search` frontier prompt asked the model for base *shapes* rather than
perturbations. It returned flatness orders 2 through 8 (including the odd order 3
that killed the even-`β` assumption), anisotropic mixes, edge/face ties, and —
crucially — `interior_max`, a base whose maximiser is not a corner at all. The
master law fit every flat-corner case exactly; `interior_max` is what forced
V.13.

---

## Theorem V.14 (weighted unified law — corrected)

Let `x_i ≥ 0` be inward coordinates at a maximizing corner and suppose, locally,

$$r(0)-r(x) \asymp \sum_i A_i x_i^{\beta_i},\qquad A_i>0,\ \beta_i>1.$$

Use the base-adapted dilation `D_t x = (t^{1/β_i}x_i)_i`. If the leading
positive perturbation is weighted-homogeneous,
`P(D_t x)-P(0) = t^q(P(x)-P(0))+o(t^q)`, with `0<q<1`, then

$$\boxed{\Delta(s)=\Theta\!\left(s^{1/(1-q)}\right)}.$$

For a monomial `P(x)=γ∏x_i^{α_i}`, its weighted degree is

$$q=\sum_i\frac{\alpha_i}{\beta_i}.$$

**Proof.** Under `x=D_t z`, the base drop has order `t`, while the perturbation
gain has order `s t^q`. Maximizing `-A(z)t+sB(z)t^q` over a direction with
`B(z)>0` gives `t* = Θ(s^{1/(1-q)})`; both terms at `t*` have that order. Uniform
two-sided local bounds on `A` and a positive maximizing direction give matching
upper and lower bounds. `∎`

The earlier formula is the isotropic corollary: if every active `β_i=β` and the
ordinary total degree is `α=Σα_i`, then `q=α/β` and
`1/(1-q)=β/(β-α)`. Coupling changes only the coefficient **when it preserves the
weighted degree**—in particular on isotropic bases. It can change the exponent
on anisotropic bases.

`combined_screen` estimates every axis order `β_i`, probes both coordinate and
joint base-adapted rays, selects the smallest accessible weighted exponent, and
checks it against a full local optimization. Verified regression cases include:

| base orders | perturbation | weighted `q` | predicted `p` |
|-------------|--------------|--------------|---------------|
| 2 | 1 (linear) | 1/2 | 2.000 |
| 2 | 0.5 (√) | 1/4 | 1.333 |
| 4 | 1 | 1/4 | 1.333 |
| 4 | 0.5 (√) | 1/8 | 1.143 |
| 4 | 1 (cone, coupled) | 1/4 | 1.333 |
| 6 | 1/3 (∛) | 1/18 | 1.059 |
| 2·λ / 6·σ (aniso) | 0.5 on σ | 1/12 | 1.091 |
| 2·λ / 6·σ | `√(x y)` | 1/3 | 3/2 |

The last row is the adversarial correction. For
`r=-x²-y⁶`, `P=2√(xy)+3x`, the old axis rule predicted `p=2`. Stationarity gives
`x=Θ(s^{3/4})`, `y=Θ(s^{1/4})`, and hence `Δ=Θ(s^{3/2})`, exactly as the weighted
law predicts. The API-generated candidate therefore falsified the old wording
and strengthened V.14 rather than being discarded. Saturation (V.11) remains a
validity ceiling, while V.13 remains the case where the base corner already
fails at `s=0`.

### How V.14 was found

`experiments/run_combined_law.py` asks the model for `(base, perturbation)` pairs
that vary both parameters at once — flat bases with non-smooth coupled
perturbations, anisotropic mixes — and screens each against the single formula.

---

## What this changes upstream

- `docs/FORMAL_THEOREMS.md` Theorem 1 stands, but its conclusion is non-generic:
  under the default `r` it holds with zero margin.
- `nonlinear_objective.demonstrate_nonlinear`'s "small coupling preserves vertex
  localization" is false as stated. Small coupling makes the failure *small*, not
  absent.
- `NonlinearAnalysis.localization_at_vertex` is a resolution-and-tolerance flag,
  not a mathematical certificate. `vertex_margin` is the certificate.
