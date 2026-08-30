# Face-selection law at a simple polyhedral vertex

Theorem V.16 (`FORMAL_NEWTON_TROPICAL.md`) selects `q* = min_j q_j` over the
monomials of the perturbation, on the positive orthant. Section 15 of
`FORMAL_VERTEX_THRESHOLD.md` gives the weighted degree of a single monomial.
This note transports both to a simple vertex of a general polyhedron, which is
what domain three adjudicates.

The transport is a change of coordinates, not a new theorem. What is new is
that the hypotheses it needs are stated explicitly — including several the
first draft left implicit — and that one of them is measured per corpus row
rather than assumed.

## 0. Standing assumptions

`P` is a bounded full-dimensional polyhedron; `F` and `G` are continuous on `P`
and real analytic near the vertex under study. Boundedness is not cosmetic: it
is what makes Lemma 1 available, and the domain's proposal prompt already
rejects unbounded systems.

## 1. Setup

Let `v` be a **simple** vertex with inward edge generators `u_1..u_n`, and

    Phi(c) = v + sum_i c_i u_i,    c >= 0.

Simplicity makes the `u_i` linearly independent, so `Phi` is a linear
isomorphism from the nonnegative orthant onto the tangent cone `T_v P`; near
`v` it is a bijection onto a neighbourhood of `v` in `P`. Set

    D(c) = F(v) - F(Phi(c)),    R(c) = G(Phi(c)) - G(v),

and study `M(s) = sup_{x in P} (F(x) + s G(x))` as `s -> 0+`.

## 2. Global isolation

The first draft asserted that `v` is "the relevant unperturbed maximizer" and
then worked locally. That is an assumption and needs to be one, because a
perturbation can move the global optimum to a different vertex entirely.

**Hypothesis 0 (isolation).** `v` is the unique maximizer of `F` on `P`.

**Lemma 1.** Under Hypothesis 0, for every neighbourhood `U` of `v` there is
`s_U > 0` such that for all `0 < s < s_U` the supremum defining `M(s)` is
attained in `U`.

*Proof.* `P \ U` is compact and `F` is continuous with a unique maximum at `v`,
so `eta := F(v) - max_{P \ U} F > 0`. Let `K = 2 sup_P |G|`, finite by
compactness. For `x` in `P \ U`,

    F(x) + s G(x) <= F(v) - eta + sK/2 < F(v) + s G(v)

as soon as `s K < eta`. The value at `v` already beats everything outside `U`,
so the supremum is attained in `U`. Take `s_U = eta / K`. ∎

Everything below is therefore about the local problem in edge coordinates, and
Lemma 1 is what licenses that reduction. Without Hypothesis 0 — at a tie
between two vertices, say — the conclusion can fail outright, which is part of
what the domain's `linear_max_at_vertex` rule exists to exercise.

## 3. Weights and initial forms

Fix the weight vector `w = (1/beta_1, ..., 1/beta_n)`, the `beta_i` pinned by
Hypothesis 2 below. For a monomial `c**alpha`,

    w-deg(c**alpha) = <w, alpha> = sum_i alpha_i / beta_i.

For a series `H = sum_j gamma_j c**alpha_j` not identically zero, the **initial
form** `in_w(H)` is the sum of the terms of least `w`-degree, and `w-deg(H)` is
that least degree. The anisotropic dilation

    delta_tau(c) = (tau**(1/beta_1) c_1, ..., tau**(1/beta_n) c_n)

sends `c**alpha` to `tau**(w-deg) c**alpha`, so `in_w(H)` is exactly what
survives in `tau**(-w-deg(H)) H(delta_tau c)` as `tau -> 0+`.

`D_0` and `W_S` below are initial forms in this sense, not descriptions of one.

## 4. Hypotheses, with uniform remainders

**Hypothesis 1 (positivity).** `D(c) >= 0` near `c = 0`, with equality only at
`c = 0`.

**Hypothesis 2 (weighted principal part, uniform).** There are `A_i > 0` and
`beta_i > 1` such that, with `D_0(c) = sum_i A_i c_i**beta_i = in_w(D)`,

    D(delta_tau z) = tau ( D_0(z) + e_D(tau, z) ),
    sup_{z in K} |e_D(tau, z)| -> 0  as tau -> 0+,  for every compact K.

**Hypothesis 3 (polynomial perturbation, uniform facewise).** `R` is a finite
sum `sum_j gamma_j c**alpha_j`, and for every face `S` on which `R` does not
vanish identically,

    R|C_S(delta_tau z) = tau**q_S ( W_S(z) + e_R(tau, z) ),
    sup_{z in K} |e_R(tau, z)| -> 0,  for every compact K in C_S,

with `q_S` and `W_S` as defined in section 5.

Uniformity is the point. The first draft wrote `o(tau)` pointwise in `z` and
then took a supremum over `z`, which does not follow: pointwise remainders
permit the error to blow up along a sequence of `z` as `tau -> 0`. With `R` a
finite polynomial and `D` analytic the uniform version holds automatically on
compacta, so nothing is lost — but it has to be said, because the balance in
section 7 exchanges a limit with a supremum.

Hypothesis 2 is the one the transport smuggles in, and the only one not implied
by the setting: an arbitrary `F` in edge coordinates may carry cross terms of
lower weight. `base_homogeneity` in the corpus measures the exponent of
`D(delta_tau z)`; the value 1 means Hypothesis 2 holds for that row.

## 5. Faces, and admissibility defined from the data alone

For nonempty `S` in `{1..n}` let

    C_S = {c >= 0 : c_i = 0 for i not in S},

which `Phi` carries to `v + cone{u_i : i in S}`, the corresponding face of the
tangent cone. Monomial `j` has support `S_j = {i : alpha_ij > 0}`, and
`c**alpha_j` is nonzero on `relint(C_S)` exactly when `S_j` is contained in
`S`. Monomial support and tangent-cone face are the same data in edge
coordinates.

Every `c >= 0` lies in `relint(C_S)` for exactly one `S`, namely `supp(c)`, so
the faces partition the cone and

    sup over the cone = max over S of ( sup over relint(C_S) ).      (*)

Define, for each face `S`, three properties **of the data `(F, G, T_vP)`
alone**:

- `S` is **active** if `R|C_S` is not identically zero, i.e. some `S_j` is
  contained in `S`. For active `S` put `q_S = w-deg(R|C_S)` and
  `W_S = in_w(R|C_S)`; equivalently
  `q_S = min{ q_j : S_j subset S, gamma_j != 0 }` where `q_j = <w, alpha_j>`.
- `S` is **positive** if `W_S(z) > 0` for some `z` in `relint(C_S)`.
- `S` is **subcritical** if `q_S < 1`.

`S` is **admissible** when it is active, positive and subcritical.

None of the three refers to `M(s)`, to `gamma`, or to any conclusion of this
note; all are computable from the exponents, the coefficients and the cone.
That is what makes section 8 non-circular. The first draft folded "the relevant
branch has positive effective perturbation and `q* < 1`" into a hypothesis and
then used admissibility in the conclusion, which is close to assuming what is
to be proved.

**Hypothesis 4 (no leading cancellation).** For each admissible `S`, `W_S` does
not vanish identically on `relint(C_S)`. With `W_S` a nonzero polynomial this
is automatic; it is stated because the initial form of a *sum* over a face can
cancel even when no individual monomial does.

## 6. Inactive and non-positive faces contribute nothing

The first draft excluded such faces by fiat. Under (*) they must be shown
harmless, because the supremum ranges over all of them.

**Lemma 2.** Let `S` be a face that is not admissible. Then `S` yields no
positive improvement for all small `s`, and in particular never determines the
leading order.

*Proof.* Three cases.

*Inactive.* `R|C_S = 0`, so the objective on `C_S` is `-D(c) <= 0` by
Hypothesis 1, with supremum `0` approached only as `c -> 0`. It contributes
nothing positive at all. This is the tilted simplex's vertical edge: feasible,
but perturbatively silent.

*Active, not positive.* `W_S <= 0` throughout `relint(C_S)`. Writing
`c = delta_tau z` with `z` on a compact cross-section, Hypothesis 3 gives
`R|C_S(delta_tau z) = tau**q_S (W_S(z) + e_R)`, which is `<= 0` for small
`tau` by uniformity. The objective is then `<= -tau(D_0(z) + e_D) <= 0`.

*Active, positive, not subcritical.* `q_S >= 1`. The leading balance of section
7 is `-tau A + s tau**q_S B` with `A, B > 0`. For `q_S > 1`, `tau**q_S = o(tau)`
and the expression is negative for all small `tau > 0` once `s` is small. For
`q_S = 1` it is `tau(sB - A)`, negative once `s < A/B`. Either way the face
yields no positive improvement at small `s`. ∎

Lemma 2 turns (*) into a maximum over admissible faces only. It is the step
that makes "inadmissible" mean *contributes nothing* rather than *excluded by
hand*.

## 7. The facewise balance

Fix an admissible `S` and a compact cross-section `Z` of `relint(C_S)` — for
instance `{z in C_S : D_0(z) = 1}`, compact by Hypothesis 1. Write
`c = delta_tau z`. By Hypotheses 2 and 3, uniformly for `z` in `Z`,

    J_s(tau, z) = -D(delta_tau z) + s R(delta_tau z)
                = -tau (D_0(z) + e_D) + s tau**q_S (W_S(z) + e_R).

With `A = D_0(z) > 0`, `B = W_S(z) > 0`, `k = q_S` in `(0,1)`, the leading
expression `-tau A + s tau**k B` is stationary at

    tau_* = ( s k B / A )**(1/(1-k)),

and substituting back gives

    J = A tau_* (1-k)/k  >  0.

Since `tau_*` scales as `s**(1/(1-k))`, so does `J`. Uniformity of `e_D` and
`e_R` on `Z` is what lets the supremum over `z` pass inside the limit, giving
matching upper and lower constants and hence

    sup_{c in relint(C_S)} J_s = Theta( s**(1/(1-q_S)) ),

so the face predicts `gamma_S = 1/(1 - q_S)`.

**Checked against measurement.** For the tilted simplex face `c_2 = 0`
(`D_0 = z**4`, `R = z`, `k = 1/4`) the coefficient is
`3/4 * (1/4)**(1/3) = 0.472470`, and the adjudicator measures
`0.472470 * s**(4/3)` to six decimals at `s = 1e-2, 2.5e-3, 6.25e-4`.

## 8. Selection, qualified

Define

    q* = min { q_S : S admissible }.

By (*) and Lemma 2 the supremum over the cone is the maximum over admissible
faces of `Theta(s**(1/(1-q_S)))`. Since `1/(1-q)` is increasing on `(0,1)` and
`s < 1`, the largest of these is the one with the **smallest** exponent, hence
the smallest `q_S`. With Lemma 1 localising the global problem,

    M(s) - F(v) - s G(v) = Theta( s**(1/(1-q*)) ),    gamma = 1/(1-q*).

**Relation to V.16's monomial minimum.** Because `q_S` is itself a minimum over
the monomials supported in `S`, the minimum of `q_S` over *all* nonempty faces
is attained at the full face and equals `min_j q_j`. Restricting to admissible
faces can only raise it:

    q* >= min_j q_j,

with **equality precisely when some face attaining `min_j q_j` is admissible**.
V.16's statement is therefore recovered under a sufficient condition — for
example all `gamma_j > 0`, whence every active face is positive and no initial
form cancels, together with `min_j q_j < 1` — and *not* in general.

The qualification is not pedantic. `3d_shear_orders_2_4_6` in the corpus has an
inadmissible face carrying `q = 1.3804` alongside admissible ones at `q = 0.5`.
There the inadmissible face is the larger value, so nothing is lost; but that
ordering is not guaranteed, and an implementation taking `min_j q_j` blindly
would in general select a branch that contributes nothing. The adjudicator
computes the face minimum, which is the quantity the theorem is about.

## 9. Worked case: the tilted simplex

`P = {x0 >= 0, x1 >= 0, x0 + x1 <= 1}`, `v = (0,1)`. The active constraints at
`v` are `x0 >= 0` and `x0 + x1 <= 1`, so

    T_v P = { d : d_0 >= 0, d_0 + d_1 <= 0 },

with extreme rays `u_1 = (1,-1)` and `u_2 = (0,-1)`, and `x = (c_1, 1-c_1-c_2)`.
For `F = -((x0+x1-1)**2 + x0**4)` we get `x0+x1-1 = -c_2` and `x0 = c_1`, hence

    D(c) = c_2**2 + c_1**4,    beta = (4, 2),    w = (1/4, 1/2).

With `G = x0`, `R(c) = c_1`, support `{1}`. Face `{1}` is active, positive and
subcritical with `q = 1/4`. Face `{2}` is **inactive**: `R` vanishes on it
identically, so by Lemma 2 its `beta = 2` never enters — the quadratic term is
the leading behaviour of `F` along that edge and is nonetheless irrelevant,
which is the point the first draft got wrong by claiming the quadratic term was
constant on the feasible cone. `q* = 1/4` and `gamma = 4/3`.

The ambient axis `e_0 = (1,0)` has `e_00 + e_01 = 1 > 0`, so it is not in
`T_v P` at all; its quadratic decay is not a branch of the constrained problem.
That is the `ambient_exponent_law` counterexample, stated exactly.

## 10. Scope

Conditional statement: for a **simple** vertex, under Hypotheses 0–4, the
asymptotic exponent is `gamma = 1/(1 - q*)` with `q*` the minimum weighted
degree over **admissible** faces.

Not established here:

- **Hypothesis 2 for arbitrary `F`.** In edge coordinates a base may carry
  cross terms; one of lower weight makes the drop `Theta(tau**c)` with `c < 1`,
  and the per-edge `beta_i` stop describing the cone's interior. Constructed
  violations at `c = 0.75` and `c = 0.5` still predict correctly — a positive
  cross term only steepens the interior and drives the optimum onto a face —
  but agreeing is not being licensed. This is why `base_homogeneity` is
  recorded per row and never gated on.
- **Non-simplicial vertices.** With more than `n` active constraints `Phi` is
  not an isomorphism onto the orthant and the argument fails at section 1. The
  vertex probe returns the vertex value there rather than answering.
- **Hypothesis 0 in the corpus.** Uniqueness of the unperturbed maximizer is
  measured rather than assumed, but only by a finite probe. `rival_margin`
  records per row how far the vertex outranks the best competing maximum found
  outside a ball of radius `0.25`; it can exhibit a rival, it cannot certify
  that none exists, so it is recorded and never gated on, exactly as
  `base_homogeneity` is. The count is not zero — [`POLYHEDRA.md`](POLYHEDRA.md)
  lists the rows that come back at or below zero, and some of them are rows the
  edge law is otherwise counted as confirming. There the maximizer is a whole
  face, Lemma 1 does not hold, and the agreement between predicted and measured
  exponent is not evidence for the law.

None of the three is a gap in the coordinate transport; all three are limits on
where it applies.
