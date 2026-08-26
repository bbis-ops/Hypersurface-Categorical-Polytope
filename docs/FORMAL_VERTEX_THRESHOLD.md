# The Vertex-Localization Threshold Is Zero

**Formal Results V.1–V.14** · 2026-08-26

## Abstract

The default composite objective has a vertex maximizer at zero interaction
strength, but that maximizer is first-order degenerate along the
$(\lambda,\sigma)$ face. The `face_bowl` interaction introduces a positive inward
derivative along both of these directions. Consequently, every positive
interaction strength, however small, moves the maximizer into the interior of the
face. The true vertex-localization threshold is therefore

$$s^{*}=0.$$

The displacement from the vertex is linear in $s$, while the objective-value gap
is quadratic:

$$\delta(s)=\frac{3}{8}s+O(s^2),
\qquad
\Delta(s)=\frac{9}{32}s^2+O(s^3).$$

Coarse grid searches can miss this failure because the displacement and value gap
become small faster than practical grid resolution can detect them.

---

## Contents

1. [Executive Summary](#1-executive-summary)
2. [Setup](#2-setup)
3. [Reduction to a Symmetric Face](#3-reduction-to-a-symmetric-face)
4. [Strict Concavity](#4-strict-concavity)
5. [Exact Maximizer](#5-exact-maximizer)
6. [The Threshold Is Zero](#6-the-threshold-is-zero)
7. [Displacement and Objective Gap](#7-displacement-and-objective-gap)
8. [Why Grid Searches Missed the Failure](#8-why-grid-searches-missed-the-failure)
9. [A Corrected Local Robustness Criterion](#9-a-corrected-local-robustness-criterion)
10. [Smooth Perturbations on a Quadratically Flat Face](#10-smooth-perturbations-on-a-quadratically-flat-face)
11. [Fractional Perturbations](#11-fractional-perturbations)
12. [Coupled Perturbations and Directional Optimization](#12-coupled-perturbations-and-directional-optimization)
13. [Amplitude Ceiling and Saturation](#13-amplitude-ceiling-and-saturation)
14. [General Flatness Law](#14-general-flatness-law)
15. [Weighted Anisotropic Law](#15-weighted-anisotropic-law)
16. [Base Self-Failure](#16-base-self-failure)
17. [Implementation Implications](#17-implementation-implications)
18. [Final Conclusions](#18-final-conclusions)

---

## 1. Executive Summary

The objective considered in this report is defined on the box

$$H=[0,1]\times[0,1]\times[0,2]\times[0,3],$$

with coordinates $(\lambda,\sigma,b,k)$.

The separable variables $b$ and $k$ are always maximized at their upper bounds.
The remaining optimization is over the $(\lambda,\sigma)$ face.

At $s=0$, the vertex

$$\theta_c=(1,0,2,3)$$

is a maximizer. However, the inward derivatives in the $\lambda$ and $\sigma$
directions are both zero. The vertex is therefore not first-order robust.

The `face_bowl` perturbation gives each of these directions an inward slope of
$3s/4$. Thus, for every $s>0$, an inward move increases the objective. The vertex
immediately ceases to be a local maximizer.

The main conclusions are

$$\boxed{s^{*}=0},$$

$$\boxed{\delta(s)=\frac{3}{8}s+O(s^2)},$$

and

$$\boxed{\Delta(s)=\frac{9}{32}s^2+O(s^3)}.$$

The broader methodological conclusion is that a vertex-only optimization strategy
is reliable only after checking both:

1. that the base objective is globally maximized at the candidate vertex;
2. that the vertex has sufficient inward margin and curvature under the intended
   perturbations.

---

## 2. Setup

Consider the objective

$$\begin{aligned}
C_s(\theta)={}& b+k+\left[1-(1-\lambda)^2\right]+\left[1-\sigma^2\right]\\
&+s\left(1-\left(\lambda-\tfrac12\right)^2\right)\left(1-\left(\sigma-\tfrac12\right)^2\right),
\end{aligned}$$

where $s\geq 0$ and

$$\theta=(\lambda,\sigma,b,k)\in H.$$

The variables $b$ and $k$ occur only in the separable term $b+k$. Therefore,

$$b^{*}=2,\qquad k^{*}=3$$

at every maximizer.

The problem consequently reduces to the $(\lambda,\sigma)$ face.

Introduce centered coordinates

$$u=\lambda-\frac12,
\qquad
w=\frac12-\sigma.$$

Then

$$u,w\in\left[-\frac12,\frac12\right].$$

The sign reversal in the definition of $w$ maps the relevant corner

$$(\lambda,\sigma)=(1,0)$$

to

$$(u,w)=\left(\frac12,\frac12\right).$$

Using

$$1-(1-\lambda)^2=\frac34+u-u^2$$

and

$$1-\sigma^2=\frac34+w-w^2,$$

the reduced objective becomes

$$C_s=\frac{13}{2}+u+w-u^2-w^2+s(1-u^2)(1-w^2).$$

The additive constant $13/2$ does not affect the location of the maximizer.
Define

$$f_s(u,w)=u+w-u^2-w^2+s(1-u^2)(1-w^2).$$

---

## 3. Reduction to a Symmetric Face

> **Lemma 3.1 (Reduction to the symmetric face).**
> The variables $b$ and $k$ attain their upper bounds at every maximizer:
> $$b^{*}=2,\qquad k^{*}=3.$$
> The remaining objective is
> $$f_s(u,w)=u+w-u^2-w^2+s(1-u^2)(1-w^2),$$
> on
> $$\left[-\frac12,\frac12\right]^2.$$
> Moreover, $f_s$ is symmetric under the exchange $u\leftrightarrow w$.

**Proof.** The first claim follows because $b+k$ is strictly increasing in both
$b$ and $k$. The symmetry follows directly from

$$f_s(u,w)=f_s(w,u). \qquad \blacksquare$$

Once uniqueness of the maximizer has been established, this symmetry will imply
that the maximizer lies on the diagonal $u=w$.

---

## 4. Strict Concavity

> **Theorem 4.1 (Strict concavity).**
> For every $s\geq 0$, the reduced objective $f_s$ is strictly concave on
> $$\left[-\frac12,\frac12\right]^2.$$

**Proof.** The Hessian is

$$\nabla^2 f_s(u,w)=
\begin{pmatrix}
-2-2s(1-w^2) & 4suw\\
4suw & -2-2s(1-u^2)
\end{pmatrix}.$$

Therefore,

$$-\nabla^2 f_s(u,w)=
\begin{pmatrix}
2+2s(1-w^2) & -4suw\\
-4suw & 2+2s(1-u^2)
\end{pmatrix}.$$

The diagonal entries are at least $2$. Since

$$|u|,|w|\leq \frac12,$$

we have

$$|4suw|\leq s$$

and

$$1-u^2,\;1-w^2\geq \frac34.$$

Consequently,

$$\begin{aligned}
\det(-\nabla^2 f_s)
&\geq\left(2+\frac{3s}{2}\right)^2-s^2\\
&=4+6s+\frac{5s^2}{4}>0.
\end{aligned}$$

Thus $-\nabla^2 f_s$ is positive definite, so $f_s$ is strictly concave.
$\blacksquare$

> **Corollary 4.2.** The face objective has a unique global maximizer.

> **Remark 4.3.** Strict concavity rules out multiple local optima. Therefore, an
> apparent vertex/interior transition produced by a numerical grid must be
> distinguished from the actual optimizer obtained analytically.

---

## 5. Exact Maximizer

> **Theorem 5.1 (Exact maximizer).**
> The unique maximizer is
> $$u^{*}=w^{*}=t^{*}(s),$$
> where $t^{*}(s)$ is the unique root in $[0,1/2]$ of
> $$2s\,t^3-2(1+s)t+1=0.$$
> At $s=0$,
> $$t^{*}(0)=\frac12.$$
> For every $s>0$,
> $$0<t^{*}(s)<\frac12.$$

**Proof.** The stationarity equations are

$$1-2u-2su(1-w^2)=0$$

and

$$1-2w-2sw(1-u^2)=0.$$

Subtracting the two equations gives

$$(u-w)\bigl[2+2s(1+uw)\bigr]=0.$$

The bracket is strictly positive on the domain, so every stationary point
satisfies

$$u=w=t.$$

Substituting $u=w=t$ into either stationarity equation gives

$$1-2t-2st(1-t^2)=0,$$

or equivalently

$$2s\,t^3-2(1+s)t+1=0.$$

Strict concavity guarantees that the stationary point is the unique global
maximizer. $\blacksquare$

In the original coordinates,

$$\lambda^{*}=\frac12+t^{*}(s),
\qquad
\sigma^{*}=\frac12-t^{*}(s),
\qquad
b^{*}=2,
\qquad
k^{*}=3.$$

Hence, for every $s>0$,

$$\lambda^{*}<1,
\qquad
\sigma^{*}>0.$$

The optimizer immediately leaves the vertex $(1,0,2,3)$.

---

## 6. The Threshold Is Zero

> **Theorem 6.1 (Zero vertex-localization threshold).**
> The vertex
> $$\theta_c=(1,0,2,3)$$
> is optimal at $s=0$, but it ceases to be locally optimal for every $s>0$.
> Therefore,
> $$\boxed{s^{*}=0}.$$

**Proof.** At the face corner $(u,w)=(1/2,1/2)$,

$$\frac{\partial f_s}{\partial u}=1-2u-2su(1-w^2)=-\frac{3s}{4}.$$

The inward direction is decreasing $u$. Therefore the inward directional
derivative is

$$D_u^{\mathrm{in}}f_s=-\frac{\partial f_s}{\partial u}=\frac{3s}{4}.$$

Similarly,

$$D_w^{\mathrm{in}}f_s=\frac{3s}{4}.$$

Both inward derivatives are strictly positive whenever $s>0$. Therefore an inward
move increases the objective, and the corner cannot be a local maximizer for any
positive $s$. $\blacksquare$

At $s=0$, the inward derivatives in the $\lambda$ and $\sigma$ directions vanish.
By contrast, the $b$ and $k$ directions have strictly negative inward
derivatives, so those coordinates remain pinned at their upper bounds.

---

## 7. Displacement and Objective Gap

Define the displacement

$$\delta(s)=\frac12-t^{*}(s).$$

> **Theorem 7.1 (Displacement and gap).**
> As $s\to0^{+}$,
> $$\delta(s)=\frac38s+O(s^2).$$
> Furthermore, if
> $$\Delta(s)=C_s(\theta^{*})-\max_{\theta\in\mathrm{ext}(H)}C_s(\theta),$$
> then
> $$\Delta(s)=\frac{9}{32}s^2+O(s^3).$$

**Proof.** Set

$$t=\frac12-d.$$

Substituting into the stationarity equation gives

$$-\frac{3s}{4}+\left(2+\frac{s}{2}\right)d+3sd^2-2sd^3=0.$$

Since $d=O(s)$,

$$d=\frac38s+O(s^2).$$

Along the inward diagonal path

$$u=w=\frac12-x,$$

the exact objective difference from the corner is

$$\begin{aligned}
&f_s\left(\frac12-x,\frac12-x\right)-f_s\left(\frac12,\frac12\right)\\
&\qquad=\frac{3s}{2}x-\left(2+\frac{s}{2}\right)x^2+sx^3-\frac{s}{2}x^4.
\end{aligned}$$

Maximizing this expression gives

$$\Delta(s)=\frac{9}{32}s^2+O(s^3). \qquad \blacksquare$$

The exact negative Hessian at the corner is

$$A=-\nabla^2 f_s\left(\frac12,\frac12\right)=
\begin{pmatrix}
2+\frac32s & -s\\
-s & 2+\frac32s
\end{pmatrix}.$$

Its eigenvalue in the inward diagonal direction $(1,1)$ is

$$2+\frac12s.$$

Using the inward gradient

$$\gamma=\frac{3s}{4}(1,1),$$

the corresponding quadratic approximation to the gap is

$$\Delta_{\mathrm{quad}}(s)=\frac{9s^2}{8(4+s)}.$$

This is an approximation and should not be confused with the exact gap.

A useful rational approximation for the displacement is

$$\delta_{\mathrm{Pad\acute{e}}}(s)=\frac{3s}{8+2s}.$$

It matches the first-order expansion but is not exact for finite $s$.

---

## 8. Why Grid Searches Missed the Failure

Let $x$ denote the inward distance from the corner along the diagonal. The exact
crossing distance $x_c(s)$ is the positive root of

$$\frac{3s}{2}-\left(2+\frac{s}{2}\right)x+sx^2-\frac{s}{2}x^3=0.$$

An interior grid point beats the corner whenever

$$\frac{1}{n-1}<x_c(s).$$

For small $s$,

$$x_c(s)=\frac34s+O(s^2),$$

so the required resolution behaves as

$$n\approx 1+\frac{4}{3s}.$$

This is an asymptotic estimate, not an exact identity involving $2\delta(s)$.

The numerical difficulty has two sources:

1. the optimizer displacement is only $O(s)$;
2. the objective-value gap is only $O(s^2)$.

Moreover, a four-dimensional grid with $n$ points per axis requires

$$n^4$$

objective evaluations.

For example, at $s=0.05$,

$$\Delta(0.05)\approx 0.000694.$$

A coarse grid can therefore report the corner as the apparent maximizer even
though the exact maximizer is interior.

A classification rule such as

```
localization_at_vertex = (gap < 0.05)
```

is a tolerance-based numerical flag, not a mathematical certificate.

---

## 9. A Corrected Local Robustness Criterion

Let $x_i\geq0$ denote inward slack coordinates from a candidate vertex
$\theta_c$. Suppose the base objective has the local expansion

$$C_0(\theta_c+x)=C_0(\theta_c)-\sum_i a_i x_i-\frac12x^\top Qx+o(\|x\|^2),$$

with $a_i\geq0$.

Suppose also that the perturbation satisfies

$$P(\theta_c+x)=P(\theta_c)+\sum_i p_i x_i+\cdots.$$

The perturbed first-order coefficient in coordinate $i$ is

$$-a_i+sp_i.$$

If $p_i>0$, the first-order stability limit on that axis is

$$s_i=\frac{a_i}{p_i}.$$

If $a_i=0$ and $p_i>0$, then

$$s_i=0.$$

This criterion is local. Before applying it, one must verify that $\theta_c$ is
actually a global maximizer of $C_0$.

> **Remark 9.1.** A strict vertex maximizer need not have a positive first-order
> margin. For example,
> $$C_0(x)=-x^2,\qquad x\geq0,$$
> has a strict maximum at $x=0$, although its inward derivative is zero.
> Therefore, strict maximality and positive first-order robustness are distinct
> properties.

---

## 10. Smooth Perturbations on a Quadratically Flat Face

Suppose the base objective has local quadratic loss

$$C_0(\theta_c+x)=C_0(\theta_c)-\frac12x^\top Qx+o(\|x\|^2),$$

where $Q$ is positive definite.

Let the perturbation have a positive inward linear term

$$P(\theta_c+x)=P(\theta_c)+g^\top x+o(\|x\|).$$

The leading-order optimization problem is

$$\max_{x\geq0}\left\{s\,g^\top x-\frac12x^\top Qx\right\}.$$

Ignoring active-cone constraints, the optimizer is

$$x^{*}=sQ^{-1}g+O(s^2),$$

and the gap is

$$\Delta(s)=\frac12s^2g^\top Q^{-1}g+O(s^3).$$

If $Q$ is diagonal and the perturbation is separable, this becomes

$$\Delta(s)=s^2\sum_i\frac{\gamma_i^2}{2c_i}+O(s^3).$$

For coupled perturbations or coupled base curvature, the full quadratic form must
be retained.

---

## 11. Fractional Perturbations

Let the base loss be quadratic,

$$-Ax^2,$$

and suppose the perturbation behaves locally as

$$P(x)-P(0)\sim\gamma x^\alpha,\qquad 0<\alpha<2.$$

The local objective is

$$-Ax^2+s\gamma x^\alpha.$$

Its optimizer satisfies

$$x^{*}=\left(\frac{\alpha\gamma s}{2A}\right)^{1/(2-\alpha)},$$

and the gap scales as

$$\Delta(s)=\Theta\left(s^{2/(2-\alpha)}\right).$$

The result applies only while the predicted optimizer remains in the region where
the local power-law approximation is valid.

---

## 12. Coupled Perturbations and Directional Optimization

For a coupled perturbation, coordinate-wise contributions can overestimate the
true gap. Let $d$ be an inward direction and write

$$x=Rd.$$

If the base loss is quadratic and $P$ is positively homogeneous of degree one,
then

$$C_0(\theta_c+Rd)+sP(\theta_c+Rd)=C_0(\theta_c)-\frac{R^2}{2}d^\top Qd+sR\,D_dP+\cdots.$$

Optimizing over $R$ gives

$$\Delta(s)=s^2\max_{d\in\mathcal K}\frac{(D_dP)^2}{2d^\top Qd}+o(s^2),$$

where $\mathcal K$ is the inward direction cone.

This formulation allows for multiple maximizing directions. It does not require
the leading-order optimizer to lie on a unique ray.

For isotropic curvature $Q=cI$,

$$\Delta(s)=\frac{s^2}{2c}\max_{\substack{\|d\|=1\\d\in\mathcal K}}(D_dP)^2+o(s^2).$$

---

## 13. Amplitude Ceiling and Saturation

Local derivative laws have a finite validity range. If the perturbation is
bounded, then

$$\Delta(s)\leq s\left(\sup_H P-P(\theta_c)\right).$$

If $P(\theta_c)=0$ and $P\geq0$, this simplifies to

$$\Delta(s)\leq s\sup_H P.$$

Any derivative-based prediction that exceeds this bound is invalid. The
perturbation has saturated before the local asymptotic optimizer is reached.

This issue is relevant for bounded ridge-like or angular interactions. A large
finite-difference slope near a corner does not imply an arbitrarily large
objective gain.

---

## 14. General Flatness Law

Suppose the base loss behaves as

$$C_0(\theta_c)-C_0(\theta_c+x)\sim A x^\beta,$$

and the perturbation behaves as

$$P(\theta_c+x)-P(\theta_c)\sim \gamma x^\alpha,$$

with

$$0<\alpha<\beta.$$

Then

$$\max_x\{-Ax^\beta+s\gamma x^\alpha\}$$

has optimizer

$$x^{*}=\Theta\left(s^{1/(\beta-\alpha)}\right)$$

and gap

$$\boxed{\Delta(s)=\Theta\left(s^{\beta/(\beta-\alpha)}\right).}$$

The quadratic-base result is obtained by setting $\beta=2$:

$$\Delta(s)=\Theta\left(s^{2/(2-\alpha)}\right).$$

A flatter base produces a smaller scaling exponent and therefore a larger gap at
small interaction strength.

---

## 15. Weighted Anisotropic Law

Suppose different coordinates have different base flatness orders:

$$C_0(\theta_c)-C_0(\theta_c+x)\asymp\sum_i A_i x_i^{\beta_i}.$$

Use the base-adapted dilation

$$D_t x=\left(t^{1/\beta_i}x_i\right)_i.$$

Suppose the leading perturbation is weighted-homogeneous:

$$P(D_t x)-P(0)=t^q(P(x)-P(0))+o(t^q),\qquad 0<q<1.$$

Then

$$\boxed{\Delta(s)=\Theta\left(s^{1/(1-q)}\right).}$$

For a monomial

$$P(x)=\gamma\prod_i x_i^{\alpha_i},$$

the weighted degree is

$$q=\sum_i\frac{\alpha_i}{\beta_i}.$$

Thus anisotropic base flatness can change the scaling exponent even when the
ordinary degree of the perturbation remains unchanged.

---

## 16. Base Self-Failure

All preceding perturbation results assume that the candidate corner is the global
maximizer of the base objective $C_0$.

That assumption can fail independently of perturbations. For example,

$$r(\lambda,\sigma)=-\bigl((1-\lambda)-0.25\bigr)^2-(\sigma-0.35)^2$$

has its maximum at

$$(\lambda,\sigma)=(0.75,0.35),$$

which is strictly interior.

A vertex search therefore returns the wrong point for every $s\geq0$. This is not
an $s^{*}=0$ perturbation phenomenon; it is a failure of the base model.

The appropriate diagnostic is global:

$$\texttt{base\_self\_fails}=\left[\max_H C_0>\max_{\theta\in\mathrm{ext}(H)}C_0\right].$$

This test should be performed before any local margin analysis.

---

## 17. Implementation Implications

The following changes should be reflected in the implementation and
documentation.

### 17.1 Formal theorem documentation

The vertex theorem may remain valid under its stated assumptions, but its
conclusion is not automatically robust. Under the default base objective, the
$(\lambda,\sigma)$ directions have zero first-order margin.

### 17.2 `demonstrate_nonlinear`

The claim that "small coupling preserves vertex localization" should be replaced
by:

> Small coupling can produce a small displacement and a small objective gap, but
> it does not preserve the exact vertex maximizer when the base vertex is
> first-order degenerate.

### 17.3 `localization_at_vertex`

This should be documented as a resolution-and-tolerance flag rather than a
mathematical certificate.

The analysis should report:

- the candidate vertex;
- whether the base objective self-fails;
- all inward first-order margins;
- local curvature or flatness order;
- predicted displacement scaling;
- predicted objective-gap scaling;
- numerical grid resolution;
- the perturbation amplitude ceiling.

### 17.4 Recommended regression tests

The test suite should verify:

1. the sign of the inward directional derivative;
2. the negative off-diagonal signs in $-\nabla^2f_s$;
3. interior displacement for every $s>0$;
4. $\dfrac{\delta(s)}{s}\longrightarrow\dfrac38$;
5. $\dfrac{\Delta(s)}{s^2}\longrightarrow\dfrac{9}{32}$;
6. the distinction between the exact grid-crossing distance and $2\delta(s)$;
7. base self-failure before perturbation analysis;
8. coupled directional optimization;
9. saturation against the amplitude bound.

---

## 18. Final Conclusions

For the stated `face_bowl` objective,

$$\boxed{s^{*}=0}.$$

The vertex is the optimizer only at $s=0$. Every positive interaction strength
moves the optimizer into the interior of the $(\lambda,\sigma)$ face.

The small-$s$ behavior is

$$\boxed{\delta(s)=\frac38s+O(s^2)}$$

and

$$\boxed{\Delta(s)=\frac{9}{32}s^2+O(s^3).}$$

The central result is mathematically sound after correcting the derivative sign
convention and the Hessian display. The report should also distinguish carefully
among:

- exact global results;
- local asymptotic laws;
- heuristic approximants;
- numerical grid classifications.

The principal methodological lesson is:

> Vertex localization is trustworthy only after global base validation and local
> robustness analysis. A zero inward first-order margin means that an arbitrarily
> small positive perturbation can move the optimizer away from the vertex.
