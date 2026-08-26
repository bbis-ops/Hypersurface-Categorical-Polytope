# The Newton–tropical master law

Formal results **V.15** (sharp constant) and **V.16** (winner-take-all selection).
Module: `categorical_polytope/newton_tropical.py`.
Tests: `tests/test_newton_tropical.py` (11 tests, each closed form checked against a
direct orthant maximization).

The V.1–V.14 series (`docs/FORMAL_VERTEX_THRESHOLD.md`) settled the **exponent** of
the vertex-localization gap: at a degenerate corner with base drop
`r(0)-r(x) ≍ Σ_i A_i x_i^{β_i}` and a weighted-homogeneous perturbation of weighted
degree `q`, the gap is `Δ(s) = Θ(s^{1/(1-q)})`. Two things were left open, and both
turn out to have clean closed-form answers.

1. **The constant.** Everything was stated to *order* `Θ(·)`. What is the actual
   leading coefficient?
2. **Superposition.** `combined_screen` (V.14) handles a sum of terms by numerically
   probing many rays and taking a min. Is there a *rule*? When two perturbations act
   together, does the gap add, average, or something else?

Throughout, place the degenerate corner at `x = 0` in inward coordinates `x_i ≥ 0`, so

$$f(x) = -\sum_i A_i x_i^{\beta_i} \;+\; s\,P(x),\qquad A_i>0,\ \beta_i>1,\qquad
P(x)=\sum_j \gamma_j \prod_i x_i^{\alpha_{ij}},\ \ \gamma_j>0,$$

and the gap is `Δ(s) = max_{x≥0} f(x)` with `f(0)=0`.

---

## Theorem V.15 (sharp constant — the `Θ` becomes a `∼`)

On a single flat axis with base drop `A x^β` and perturbation `s γ x^α`, `0<α<β`:

$$\boxed{\;\Delta(s) = C\,s^{p} + o(s^{p}),\qquad p=\frac{\beta}{\beta-\alpha},\qquad
C=\gamma\,\frac{\beta-\alpha}{\beta}\left(\frac{\gamma\alpha}{A\beta}\right)^{\!\frac{\alpha}{\beta-\alpha}}.\;}$$

**Proof.** Maximise `φ(x) = -A x^β + s γ x^α` over `x>0`. Stationarity
`A β x^{β-1} = s γ α x^{α-1}` gives `x_* = (sγα/(Aβ))^{1/(β-α)}`. Write
`u = x_*^{β-α} = sγα/(Aβ)`, so `x_*^β = u\,x_*^α` and

$$\varphi(x_*) = x_*^\alpha(-A u + s\gamma) = s\gamma\Big(1-\tfrac{\alpha}{\beta}\Big)x_*^\alpha
= \gamma\frac{\beta-\alpha}{\beta}\Big(\frac{s\gamma\alpha}{A\beta}\Big)^{\!\alpha/(\beta-\alpha)} s.$$

The powers of `s` collect to `α/(β-α)+1 = β/(β-α) = p`; the `s`-free prefactor is `C`.
`φ''(x_*) = -Aβ(β-1)x_*^{β-2} + sγα(α-1)x_*^{α-2} < 0` after substituting the
stationary relation (since `β>α`), so `x_*` is the interior maximum. ∎

**Independent axes add.** When the base is flat on several axes and `P` is separable,
the cross terms are `O(s·)` of higher order, so `C = Σ_i C_i`.

**Sanity checks (all exact in the module and tests).**

| `α` | `β` | `γ` | `A` | `p` | `C` |
|-----|-----|-----|-----|-----|-----|
| 1 | 2 | 3/4 | 1 | 2 | **9/64** (per axis; two axes → **9/32**, matching V.4) |
| 1 | 2 | 1 | 1 | 2 | 1/4 (bilinear `s²/4`, exact) |
| 1/2 | 2 | 1 | 1 | 4/3 | 0.47247… |
| 1 | 3 | 1 | 1 | 3/2 | 0.38490… |

`sharp_single_axis_gap` reproduces a direct maximization to `<3·10⁻³` relative at
`s=10⁻⁴`, and the closed constant matches the exact 1-D root to machine precision.

---

## Theorem V.16 (Newton–tropical selection — winner-take-all)

Let `q_j = Σ_i α_{ij}/β_i` be the **base-weighted degree** of monomial `j`, and

$$q^\star=\min_{j:\,q_j<1} q_j.$$

Then

$$\boxed{\;\Delta(s)=\Theta\!\big(s^{\,1/(1-q^\star)}\big),\;}$$

and the gap is governed **entirely** by the monomials attaining `q^\star` — the lowest
face of `P`'s Newton polytope under the weight vector `(1/β_i)`. Every term with
`q_j>q^\star` contributes only `o(s^{1/(1-q^\star)})`, whatever its amplitude `γ_j`.

**Proof.** Apply the base-adapted dilation `x_i = t^{1/β_i} z_i`, `z_i≥0`, `t→0⁺`. The
base drop becomes `t·Q(z)` with `Q(z)=Σ_i A_i z_i^{β_i}` (order `t`). Monomial `j`
becomes `γ_j t^{q_j}∏_i z_i^{α_{ij}}` (order `t^{q_j}`). Hence

$$f = -t\,Q(z) + s\Big(t^{q^\star}W(z) + \sum_{q_j>q^\star} t^{q_j}(\cdots)\Big),\qquad
W(z)=\!\!\sum_{j:\,q_j=q^\star}\!\!\gamma_j\prod_i z_i^{\alpha_{ij}}.$$

Fix a direction `z` with `W(z)>0` and maximise `-tQ + s t^{q^\star}W` over `t`:
`t_* = (s q^\star W/Q)^{1/(1-q^\star)} = \Theta(s^{1/(1-q^\star)})`. Both retained terms
are `Θ(s^{1/(1-q^\star)})` there, while each discarded term obeys
`t_*^{q_j}/t_*^{q^\star} = t_*^{\,q_j-q^\star}\to 0`, so it is of strictly higher order
in `s`. Maximising over `z` gives the lower bound; the base's uniform two-sided local
bounds give the matching upper bound. ∎

### The mind-bending part: mixing is winner-take-all, not averaging

Amplitudes `γ_j` **never enter the exponent.** The map `P ↦ exponent` factors through
`min_j q_j` — a **min-plus (tropical)** operation, not a sum. Two consequences that
contradict smooth intuition, where independent effects add:

- **A weaker term dominates if it is more singular.** Base `x²`, perturbation
  `100·x + 0.001·√x`. The linear term (`q=1/2`, `p=2`) is `10⁵×` larger in amplitude,
  yet the `√x` term (`q=1/4`, `p=4/3`) sets the gap as `s→0`. Caught in the act —
  the measured log-log slope drifts off the linear value toward `4/3`:

  | `s`-decade | `10⁻²`→`10⁻⁴` | `10⁻⁴`→`10⁻⁶` | `10⁻⁶`→`10⁻⁸` | `10⁻⁸`→`10⁻¹⁰` | `10⁻¹⁰`→`10⁻¹²` |
  |---|---|---|---|---|---|
  | slope | 2.000 | 1.999 | 1.995 | 1.951 | 1.742 |

  The crossover is just slow: `√x` overtakes `100x` in the *gap* only once
  `s ≲ (0.001/100)^{…}`, but overtake it does, and monotonically.

- **Adding a bump can only ever lower the exponent (raise the gap).** `q^\star` is a
  min, so appending a term never increases it. Perturbations form a monoid under `+`
  whose action on the exponent is `min` — idempotent, commutative, absorptive. This is
  the tropical semiring `(ℝ, min, +)` acting on the localization problem.

### It reproduces the whole V-series as "read the lowest Newton face"

- `β=2, α=1` → `q=1/2 → p=2` (V.7).
- `β=2, 0<α<2` → `p=2/(2-α)` (V.8/V.10).
- general `β`, `q=α/β → p=β/(β-α)` (V.12).
- coupled monomial `√(xy)` on `-x²-y⁶`: `q=1/4+1/12=1/3 → p=3/2` — exactly the V.14
  adversarial row, now read straight off the Newton polytope with no ray search.

`newton_tropical_face` returns `q^\star`, the exponent, and the winning face (flagged
`separable` or `coupled`); `tropical_gap_leading` then gives the **sharp** gap — the
closed-form V.15 sum on a separable face, or the reduced projective maximization

$$C=\frac{1-q^\star}{q^\star}\,(q^\star)^{p}\Big[\max_{z\ge 0}\frac{W(z)}{Q(z)^{q^\star}}\Big]^{p}$$

on a coupled face (the ratio `W/Q^{q^\star}` is invariant under the base dilation, so
the maximum is over a projective orthant).

---

## What this changes upstream

- **Every `Θ(s^p)` in `docs/FORMAL_VERTEX_THRESHOLD.md` now has a constant** (V.15).
  `universal_gap`, `fractional_exponent_law`, and the master law are the `Θ` shadows of
  `sharp_gap_constant`.
- **`combined_screen`'s "probe rays and take a min" is a computation of `q^\star`**
  (V.16). The selection is not a numerical convenience — it is the exact tropical rule,
  and it is closed form once the Newton support is known. A ray search is only needed
  to recover the *constant* on a coupled face, never the exponent.
- The design rule sharpens: to predict how badly a mixed perturbation breaks vertex
  localization, you do not weigh its terms — you find its single most singular monomial
  under the base's flatness weights. Everything else is invisible as `s→0`.
