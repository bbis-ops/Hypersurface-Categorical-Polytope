# The mixed-sign binomial positivity-witness law

Formal result **V.19** · backend asset `portable-principle.v8` · exact engine:
`categorical_polytope/face_selection.py`.

## Abstract

Qualified face selection requires more than a weighted degree. A face initial
form must be positive somewhere in the relative interior. General mixed-sign
polynomial positivity can be difficult, so previous versions correctly left
such faces unresolved without a supplied witness.

For a mixed-sign binomial, however, positivity is completely constructive.
Distinct monomial signatures have a nonconstant ratio on the positive orthant.
One face coordinate can therefore be chosen so the positive monomial dominates
the negative monomial by a certified factor. This converts an unresolved
existence condition into an explicit backend witness.

---

## Theorem V.19 — constructive binomial positivity

Let $F$ be a positive-dimensional orthant face and let

$$
W_F(x)=a x^\alpha-b x^\beta,
\qquad a,b\gt 0,
$$

where $\alpha\ne\beta$ are nonnegative integer exponent vectors supported on
$F$. Assume the two terms belong to the same weighted initial layer:

$$
\langle w,\alpha\rangle
=\langle w,\beta\rangle=q,
\qquad 0\lt q\lt 1.
$$

Then there exists $z\in\mathrm{relint}(F)$ such that $W_F(z)\gt 0$.
Consequently the face satisfies the positivity qualification required by the
face-selection law.

### Constructive proof

Because $\alpha\ne\beta$, choose a face coordinate $k$ for which

$$
\delta=\alpha_k-\beta_k\ne0.
$$

Set every other coordinate in $F$ to one. The positive-to-negative monomial
ratio becomes

$$
\frac{a z^\alpha}{b z^\beta}
=\frac ab z_k^\delta.
$$

If $\delta\gt 0$, choose

$$
z_k=\left(\frac{4b}{a}\right)^{1/\delta}.
$$

If $\delta\lt 0$, choose

$$
z_k=\left(\frac{4b}{a}\right)^{-1/|\delta|}.
$$

In either case the ratio equals four, so

$$
W_F(z)=a z^\alpha-b z^\beta=3b z^\beta\gt 0.
$$

All face coordinates remain strictly positive, hence
$z\in\mathrm{relint}(F)$. ∎

---

## Qualified-selection consequence

Once the witness is constructed, the binomial face enters qualified selection:

$$
q_\ast=min_{F\text{ qualified}}q_F.
$$

If the localization, uniform-remainder, isolation, and positive-gain
upper-envelope hypotheses are licensed,
the backend may therefore return

$$
\Delta(s)=\Theta \left(s^{1/(1-q_\ast)}\right)
$$

instead of withholding the result because positivity was unresolved.

A binomial witness settles positivity of that layer. It does not by itself
exclude uncontrolled higher layers on other non-positive faces; see
[`MATHEMATICAL_AUDIT.md`](MATHEMATICAL_AUDIT.md).

For the implemented example

$$
W(x,y)=-2x+y^2,qquad
D_0(x,y)=x^2+y^4,
$$

both monomials have $q=1/2$. The constructed full-face witness makes $W\gt 0$,
and the qualified consequence is

$$
\gamma=\frac1{1-1/2}=2.
$$

## Backend certificate

Exact polynomial transport now returns `positivity_certificates`. Each
certificate contains:

- the tangent-cone face;
- witness coordinates;
- `mixed-sign binomial ratio certificate` provenance; and
- the positive value of the initial form at the witness.

This evidence is retained even when a smaller subface carries the same winning
degree, so the backend audit records that all potentially competing symbolic
faces were settled.

## Boundary

V.19 resolves exactly two distinct combined monomial signatures with opposite
signs. It does not claim that an arbitrary mixed-sign polynomial is positive.
Initial forms with three or more signatures remain unresolved unless they have
another certificate or a caller-provided positive relative-interior witness.
Identical signatures are combined before V.19 is considered; if their combined
coefficient is zero, the layer is classified as cancelled.

## Reproduce

```bash
python -m categorical_polytope.adjudication.polyhedra.backend \
  --input experiments/face_selection_binomial_v19_request.json --pretty
python -m pytest -q tests/test_face_selection.py \
  tests/test_face_selection_portable_asset.py
```
