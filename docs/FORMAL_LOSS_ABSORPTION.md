# Absorption by the loss

Lemma **A** · certificate link `absorption` in
[`gitcalculator/certify.py`](../gitcalculator/certify.py) and the browser engine.

The face-selection law reads the response exponent off weighted faces of the
perturbation, with weights fixed by a diagonal principal part of the base loss
(Hypothesis 2). When the loss has a mixed monomial below those weights, a face
can qualify under them while the loss still absorbs the gain. Then the true
response is zero. This lemma decides that case exactly. It needs no weights, no
faces, and no condition on the principal part. It was found while testing the
conjecture in
[issue #33](https://github.com/bbis-ops/Hypersurface-Categorical-Polytope/issues/33).

## Statement

Let $P$ be a bounded polyhedron, $F$ and $G$ polynomials, and $v$ a simple
vertex of $P$. Let $\Phi(c)=v+\sum_i c_iu_i$ be the inward edge chart, with
$\Phi([0,\rho]^n)\subset P$, and let

$$
D(c)=F(v)-F(\Phi(c)),\qquad R(c)=G(\Phi(c))-G(v).
$$

Suppose that:

1. $v$ is the unique maximizer of $F$ on $P$ (Hypothesis 0);
2. every coefficient of $D$ is nonnegative;
3. every monomial $c^\alpha$ of $R$ with a positive coefficient is divisible by
   a monomial $c^\beta$ of $D$ with a positive coefficient, so that
   $\beta\le\alpha$ componentwise.

Then

$$
\Delta(s)=\max_P\,(F+sG)-F(v)-sG(v)=0
\qquad\text{for all sufficiently small } s\gt0.
$$

If $R$ has no positive monomial, condition 3 holds vacuously.

## Proof

Write $\rho'=\min(\rho,1)$. Assign to each positive term $r_\alpha c^\alpha$ of
$R$ one dividing positive term $d_\beta c^\beta$ of $D$, and let $T_\beta$ be
the sum of the coefficients $r_\alpha$ assigned to $\beta$. On $[0,\rho']^n$
every coordinate is at most one, so $c^\alpha\le c^\beta$ whenever
$\beta\le\alpha$. For

$$
0\lt s\le s_0=\min_\beta \frac{d_\beta}{T_\beta}
$$

this gives

$$
sR(c)\le s\sum_\alpha r_\alpha c^\alpha\le\sum_\beta sT_\beta c^\beta
\le\sum_\beta d_\beta c^\beta\le D(c).
$$

The first inequality drops the nonpositive terms of $R$. The last uses that the
remaining monomials of $D$ have nonnegative coefficients on the orthant. Hence
$F+sG\le F(v)+sG(v)$ on $\Phi([0,\rho']^n)$.

At a simple vertex, every $x\in P$ is $\Phi(c)$ with $c$ the vector of active
slacks. The set $U=\lbrace x\in P:\max_i c_i(x)\lt\rho'\rbrace$ is therefore
a relatively open neighborhood of $v$ in $P$ contained in
$\Phi([0,\rho']^n)$. The set $P\setminus U$ is compact and misses $v$. By
condition 1, $F\le F(v)-\delta$ there for some $\delta\gt0$. Let
$\omega=\max_P G-\min_P G$. Then $s\,(G-G(v))\le s\omega\lt\delta$ for every
$s\gt0$ when $\omega=0$, and for $s\lt\delta/\omega$ otherwise. So
$F+sG\lt F(v)+sG(v)$ on $P\setminus U$ as well.

Together, $\Delta(s)\le0$ for all small enough $s\gt0$: below $s_0$, and below
$\delta/\omega$ when $\omega\gt0$. The point $x=v$ gives $\Delta(s)\ge0$.
$\blacksquare$

## Why it matters

Take the unit square with $F=-(x_0^4+x_1^4+x_0x_1)$ and $G=x_0x_1$ at the
vertex $0$.

- The diagonal weights $(1/4, 1/4)$ come from the pure terms of
  $D=c_0^4+c_1^4+c_0c_1$.
- The face $\lbrace c_0, c_1 \rbrace$ of $R=c_0c_1$ then qualifies with
  $q=1/2$, which suggests $\gamma=2$.
- But $c_0c_1$ also appears in $D$, at weighted degree $1/2$, so Hypothesis 2
  fails.
- Lemma A applies with $s_0=1$: indeed
  $F+sG=-x_0^4-x_1^4-(1-s)x_0x_1\le0$ on the square for $s\le1$.

The counter-argument `loss-absorption` in
[`counter.py`](../gitcalculator/counter.py) keeps this example as an
executable witness.

The lemma is a sufficient test. It does not cover a loss with negative
coefficients, and it does not decide a positive gain monomial that no
monomial of $D$ divides. In the second case, as in `cross-term`, the response
is typically positive.

## Reproduce

```bash
python -m gitcalculator calc --system "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])" --base "-(x0**4+x1**4+x0*x1)" --perturbation "x0*x1"
python -m gitcalculator counter
```
