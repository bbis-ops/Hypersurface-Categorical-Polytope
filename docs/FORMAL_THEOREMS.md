# Formal theorems — corrected categorical note

**Corrected edition · 7 September 2026**

This is the proof source for [SHORT_NOTE.md](SHORT_NOTE.md) and the
[Overview](../categorical_polytope/Overview.md). The revision replaces the
three older sketches; their counterexamples and implementation mismatches
are recorded in [ORIGINAL_NOTE_REVIEW.md](ORIGINAL_NOTE_REVIEW.md).

The results below combine standard facts about adjunctions, quasiconvexity,
positive-definite quadratics, and upper-bound certificates. The contribution
of this note is their operational organization and reproducible examples.
The repository's separate [Newton–tropical selection principle](../README.md)
has its own theorems and hypotheses.

## 0. The categorical obstruction and the analogy

For fixed nonempty sets $A,Y$, there is no set $L$ with natural bijections

$$
\operatorname{Hom}(L,Z)\cong\operatorname{Hom}(Y,A\sqcup Z)
$$

for every set $Z$. Take $Z=1$, a singleton. There is exactly one map $L\to1$,
whereas there are at least two maps $Y\to A\sqcup1$, namely constant maps
to an element of $A$ and to the other summand. This is a contradiction.
Consequently $A\sqcup-$ has no left adjoint for nonempty $A$. For $A=\varnothing$
it is the identity functor; for the individual case $Y=\varnothing$ the
displayed functor is represented by $L=\varnothing$.

By contrast, $A\times-$ has the exponential right adjoint $(-)^A$ in
`Set`. These categorical facts motivate an optimization analogy.
A parameter block product $H_A\times H_B$ is a Cartesian product of feasible
sets; it is not thereby a categorical coproduct. Likewise a geometric vertex
is not a categorical limit or colimit. “Operational substitute” means a
procedure for selecting and evaluating candidates, with the guarantees below;
it does not construct the missing adjoint.

## Theorem 1 — Vertex localization

Let $H=\prod_{i=1}^n[a_i,b_i]$ be a nonempty compact box and let
$C:H\to\mathbb R$ be continuous and **separately quasiconvex**: for every
coordinate, with all others fixed, the resulting one-dimensional function
$f$ satisfies

$$
f((1-t)u+tv)\le\max\{f(u),f(v)\},\qquad 0\le t\le1.
$$

Then

$$
\boxed{\max_{\theta\in H}C(\theta)
      =\max_{v\in\operatorname{ext}(H)}C(v).}
$$

In particular, **at least one** global maximizer is a vertex.

**Proof.** Compactness and continuity give a maximizer. On each nondegenerate
coordinate interval, the displayed inequality bounds the value at the current
coordinate by the larger endpoint value. Replace that coordinate by such an
endpoint. Repeating for all coordinates never lowers the value and finishes
at a vertex. Degenerate intervals already have their only endpoint. The reverse
inequality follows from $\operatorname{ext}(H)\subset H$. ∎

**Scope.** The hypothesis concerns the full objective $C$, not merely an
interaction term in a decomposition $C=g+h+r$. A constant objective shows why
“every maximizer is a vertex” would be false. The example
$C(x,y)=x-x^2+y$ shows why monotonicity of $g,h$ and separate quasiconvexity
of $r$ alone are insufficient.

For the default `HypersurfaceBox` objective with its default positive weights,
coordinate monotonicity proves the corner
$(\lambda_{\max},\sigma_{\min},b_{\max},k_{\max})$ directly.
For a box intersected with additional constraints, the new feasible set may
have vertices that are not box corners. Filtering the old corners therefore
does not extend this theorem to the intersection.

## Theorem 2 — Quadratic residual and separation bounds

This result has its own hypotheses; it does not assume Theorem 1.

Let $F=F^\top\succ0$ and

$$
Q(\theta)=c^\top\theta-\frac12\theta^\top F\theta,\qquad
\theta^\star=F^{-1}c.
$$

For any candidate $z\in\mathbb R^n$, write $r_z=c-Fz$. Then

$$
\boxed{\begin{aligned}
Q(\theta^\star)-Q(z)
&=\frac12(z-\theta^\star)^\top F(z-\theta^\star)\\
&=\frac12r_z^\top F^{-1}r_z.
\end{aligned}}
$$

If $0\lt \mu\le\lambda_{\min}(F)$ is established independently, this gives

$$
\boxed{Q(\theta^\star)-Q(z)\le\frac{\|r_z\|_2^2}{2\mu}.}
$$

**Proof.** Expanding $Q$ around $\theta^\star$ cancels the linear term because
$F\theta^\star=c$. Also $r_z=-F(z-\theta^\star)$. Substitution gives both
identities. The spectral inequality $F^{-1}\preceq\mu^{-1}I$ gives the bound. ∎

If $z$ lies in a nonempty compact feasible set $P$, the same expression is an
upper bound on $\max_P Q-Q(z)$, even when $\theta^\star$ is infeasible.
The identity itself is for the unconstrained maximum. A coordinate pass,
a pruned candidate, or any other construction may supply $z$; its residual
must be evaluated for the same objective.

### Corollary 2.1 — A bound for independent block solves

Let $D$ be the block-diagonal part of $F$, let $E=F-D$, and put

$$
K=D^{-1/2}ED^{-1/2},\qquad
\rho=\|K\|_2\lt 1,\qquad z_0=D^{-1}c.
$$

Then

$$
\boxed{
Q(\theta^\star)-Q(z_0)
\le \frac{\rho^2}{2(1-\rho)}\,c^\top D^{-1}c.}
$$

**Proof.** Write $v=D^{1/2}z_0$. Since $F=D^{1/2}(I+K)D^{1/2}$
and $r_{z_0}=-D^{1/2}Kv$, Theorem 2 gives the exact gap
$\tfrac12v^\top K(I+K)^{-1}Kv$. Every eigenvalue $t$ of the symmetric matrix
$K$ belongs to $[-\rho,\rho]$, so
$t^2/(1+t)\le\rho^2/(1-\rho)$. Finally
$\|v\|^2=c^\top D^{-1}c$. ∎

This corollary is for the **independent block solve** $z_0$. The legacy
`separable_block_optimization` routine instead makes sequential coordinate
updates; Theorem 2's residual bound applies to its actual returned point.

### Corollary 2.2 — A sufficient Frobenius-norm condition

Define leakage using the **entire** off-diagonal matrix:

$$
\varepsilon=\frac{\|E\|_F}{\|D\|_F},\qquad
\eta=\varepsilon\|D\|_F=\|E\|_F,\qquad d=\lambda_{\min}(D).
$$

If $\eta\lt d$, then $F\succeq(d-\eta)I$ and

$$
\boxed{
Q(\theta^\star)-Q(z_0)
\le
\frac{\varepsilon^2\|D\|_F^2}{2(d-\varepsilon\|D\|_F)}
\|z_0\|_2^2.}
$$

Indeed $\|E\|_2\le\eta$, and $r_{z_0}=-Ez_0$, so Theorem 2 applies with
$\mu=d-\eta$. For two symmetric blocks,
$\|E\|_F=\sqrt2\|F_{AB}\|_F$; the two leakage conventions must not be mixed.

These bounds have the correct scaling: replacing $(F,c)$ by $(aF,ac)$,
$a\gt 0$, multiplies both the true gap and the bounds by $a$. A numerical
cutoff such as $\varepsilon\le0.10$ alone does not establish a chosen
objective-error tolerance.

### Exact example

Take $F=\begin{pmatrix}4&1\\1&4\end{pmatrix}$ and $c=(4,4)^\top$.
Then $\theta^\star=(4/5,4/5)$ and $\lambda_{\min}(F)=3$.

| Candidate | Exact gap | Valid upper bound |
| --- | --- | --- |
| One coordinate pass $z=(1,3/4)$ | $3/40$ | Residual bound $3/32$ |
| Independent block solve $z_0=(1,1)$ | $1/5$ | Corollary 2.1, with $\rho=1/4$: $1/3$ |

### Non-quadratic objectives

Let $Q,F,\mu$ satisfy Theorem 2's hypotheses. If $C=Q+R$ is continuous on
a nonempty compact feasible set $P$ and a **uniform** remainder bound
$\sup_P R-\inf_P R\le\omega$ has been proved, then for feasible $z$,

$$
\max_P C-C(z)\le\frac{\|c-Fz\|_2^2}{2\mu}+\omega.
$$

This follows by bounding $Q(x)-Q(z)$ by the unconstrained quadratic gap and
$R(x)-R(z)$ by $\omega$. A finite-difference Hessian at one point does not
establish such a uniform bound or global concavity.

## Theorem 3 — A certified finite candidate search

Let $P$ be a nonempty compact feasible set, $C:P\to\mathbb R$ continuous,
and $T\subset P$ a finite nonempty candidate set. Let

$$
p\in\operatorname{argmax}_{t\in T}C(t).
$$

If $U$ is a proved upper bound on $\max_P C$, then

$$
\boxed{0\le\max_P C-C(p)\le U-C(p).}
$$

**Proof.** Feasibility gives the left inequality; subtracting $C(p)$ from
$\max_P C\le U$ gives the right one. ∎

Under Theorem 1, a valid choice is
$U=\max_{v\in\operatorname{ext}(H)}C(v)$, obtained by full vertex enumeration.
For the quadratic model, Theorem 2 supplies
$U=Q(p)+\|c-Fp\|_2^2/(2\mu)$. The certificate and the candidate score must
refer to the same objective and feasible set.

### Corollary 3.1 — Marginal pruning with controlled interaction

In Theorem 1's box setting, write $H=H_A\times H_B$ and
$C(a,b)=g(a)+h(b)+r(a,b)$. Let $V_A,V_B$ be the block vertex sets and
choose nonempty $T_A\subset V_A$, $T_B\subset V_B$. Define

$$
\delta_A=\max_{V_A}g-\max_{T_A}g,\qquad
\delta_B=\max_{V_B}h-\max_{T_B}h,
$$

and let $\omega$ bound the oscillation of $r$ on $V_A\times V_B$. For the
best full-objective candidate $p$ in $T_A\times T_B$,

$$
\boxed{\max_H C-C(p)\le\delta_A+\delta_B+\omega.}
$$

**Proof.** Theorem 1 reduces the maximum to the full vertex product, where
$C\le\max_{V_A}g+\max_{V_B}h+\max r$. Pair a maximizer of $g$ on $T_A$
with a maximizer of $h$ on $T_B$; its score is at least
$\max_{T_A}g+\max_{T_B}h+\min r$. The selected $p$ does at least as well.
Subtract the two estimates. ∎

When each retained set contains a marginal maximizer, both $\delta$ terms
vanish. Small interaction oscillation then certifies the marginal candidate
construction. Fisher leakage supplies such control only through a proved
model-specific argument; the quantities are not interchangeable.

**Cost.** With at most $k$ candidates per block, the two-block candidate
evaluation takes at most $k^2$ objective evaluations after marginal scoring.
Computing a full-vertex reference still costs
$|V_A||V_B|$ evaluations. The reference cost is part of certification.

## Implementation boundary and reproducibility

[`note_publication_check.py`](../experiments/note_publication_check.py)
verifies the displayed examples with rational arithmetic and asserts the
correct scaling behavior. Run from the repository root:

```bash
python experiments/note_publication_check.py
```

The existing `formal_bounds.Phi` and `fisher_factorization.leakage_gap_bound`
retain the older expression analyzed in the revision record. Their names
do not imply that they implement Theorem 2 of this corrected edition.
Likewise `FisherPrunedVertexSearch.certified` checks an auxiliary quadratic
comparison; `probe_gap` is a separate finite-reference diagnostic.
The corrected statements above specify what a valid certificate must prove.

## References

The proofs above are self-contained. Background and standard terminology:

1. Emily Riehl, *Category Theory in Context*, Dover, 2016, Chapter 4:
   adjunctions and preservation of limits.
   [Author's book page](https://math.jhu.edu/~eriehl/context/).
2. Stephen Boyd and Lieven Vandenberghe, *Convex Optimization*, Cambridge
   University Press, 2004: quasiconvex functions, quadratic optimization,
   and bounds on optimal values.
   [Authors' book page](https://web.stanford.edu/~boyd/cvxbook/).
