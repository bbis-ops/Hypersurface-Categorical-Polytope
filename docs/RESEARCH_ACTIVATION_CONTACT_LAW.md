# Activation contact law beyond the leading Newton–tropical crossover

This note proves a further result for the signed cancellation family underlying
[V.22](FORMAL_CURVED_REDUCTION.md). It determines the true activation boundary,
including the effect of the base cost discarded in the leading crossover, and
classifies response rates by contact with that boundary. It is a mathematical
extension developed here, not a claim of literature priority. The current
backend does not implement this joint-parameter classification.

## 1. The family and the result

On $P=[0,1]^2$, let

$$
D=x^6+y^6,\qquad
R_\varepsilon=-(x-y^2/2)^2+\varepsilon y^4+y^5,
$$

and define $\Delta(s,\varepsilon)=\max_P(-D+sR_\varepsilon)$ for $s\gt 0$.
Set $\varepsilon=s\lambda$.

**Activation contact theorem.** There is a real-analytic function
$\lambda_c(s)$ near $s=0$, with $\lambda_c(0)=-1/4$, such that, for all
sufficiently small positive $s$,

$$
\Delta(s,s\lambda)=0\quad\Longleftrightarrow\quad\lambda\le\lambda_c(s).
$$

There is also a positive real-analytic function $B(s,\delta)$ near $(0,0)$,
with $B(0,0)=1/16$, for which the following identity holds for small positive
$s$ and sufficiently small $|\delta|$:

$$
\boxed{
\Delta\bigl(s,s[\lambda_c(s)+\delta]\bigr)
=s^6\max\lbrace \delta,0\rbrace B(s,\delta).
}
$$

In particular, uniformly as $(s,\delta)\to(0,0)$ with $s\gt 0$,

$$
\Delta\bigl(s,s[\lambda_c(s)+\delta]\bigr)
=s^6\delta_+\left[\frac1{16}+O(s^6+|\delta|)\right].
$$

The critical curve has expansion

$$
\boxed{
\lambda_c(s)=-\frac14+\frac{s^6}{2^{14}}
-\frac{s^{12}}{2^{22}}-\frac{9s^{13}}{2^{26}}+O(s^{18}).
}
$$

Equivalently, the physical coefficient threshold is

$$
\varepsilon_c(s)=-\frac{s}{4}+\frac{s^7}{2^{14}}
-\frac{s^{13}}{2^{22}}-\frac{9s^{14}}{2^{26}}+O(s^{19}).
$$

Thus the outer crossover's boundary $\lambda=-1/4$ is the limiting boundary;
the full finite-$s$ problem activates on a displaced analytic curve.

This is a boundary for **positive response**, not a boundary for the accuracy
of a leading asymptotic formula. For example, $\varepsilon=s\gt 0$ is above the
activation curve, yet the ratio to the fixed-coefficient prediction
$(4/27)\varepsilon^3s^3$ tends to $320/27$, not 1. Accuracy at a supplied
positive $s$ is separately assessed by the
[finite-scale certificate](CURVED_FINITE_SCALE.md). In particular, the condition
$\varepsilon\gt \varepsilon_c(s)$ cannot replace a relative-error bound.

## 2. Exact elimination and global localization of activation

Write $y=sv$, $x=s^2u$. The full scaled objective is

$$
F_s(u,v;\lambda)
=-v^6+v^5+\lambda v^4-s^6u^6
-\frac1s\left(u-\frac{v^2}{2}\right)^2.
$$

For every $v\gt 0$, minimization of the two discarded costs is strictly convex
in $u\ge0$. Its unique minimizer $u_s(v)$ satisfies

$$
u_s(v)+3s^7u_s(v)^5=\frac{v^2}{2}.
$$

It obeys $0\lt u_s(v)\lt v^2/2$. Consequently, for $0\lt v\le1/s$, the corresponding
$x=s^2u_s(v)$ lies below $y^2/2\le1/2$ and is feasible in the square.
Using the stationary equation, the exact minimized cost is

$$
C_s(v)=s^6u_s(v)^6+9s^{13}u_s(v)^{10}.
$$

Define, for $v\gt 0$,

$$
T_s(v)=v^2-v+\frac{C_s(v)}{v^4}.
$$

The exact reduced objective is

$$
f_s(v;\lambda)=v^4[\lambda-T_s(v)],
$$

and hence

$$
\lambda_c(s)=\min_{0\lt v\le1/s}T_s(v).
$$

This minimum exists for small $s$. Indeed, $T_s(v)\ge v^2-v$, while
evaluation at $v=1/2$ gives $T_s(1/2)=-1/4+O(s^6)\lt 0$.
Also $T_s(v)\to0$ as $v\downarrow0$. The minimum is therefore attained
away from zero. Every minimizing point satisfies

$$
\left(v-\frac12\right)^2\le O(s^6),
$$

so all global minimizers approach $1/2$. This argument excludes a competing
activation threshold elsewhere in the square; it is not just a local
stationary-point calculation.

Near $v=1/2$, the implicit equation for $u_s(v)$ defines a real-analytic
function of $(s,v)$, including $s=0$. Thus $T_s$ is analytic there and
$T_s''(v)=2+O(s^6)$ uniformly on a fixed sufficiently small neighborhood.
It follows that the global minimizer $v_c(s)$ is unique and analytic for
small $s$. So is $\lambda_c(s)=T_s(v_c(s))$.

For $\lambda\lt \lambda_c(s)$, every nonzero feasible point has negative gain,
and the origin is the unique maximizer. At equality there are exactly two
maximizers: the origin and the minimizing-cost point with
$y=sv_c(s)$, $x=s^2u_s(v_c(s))$. Above the boundary, that point already gives
strictly positive gain. This proves the exact activation criterion.

## 3. Why the contact formula is uniform

At $s=0$ and $\lambda=-1/4$,

$$
f_0(v;-1/4)=-v^4(v-1/2)^2,
\qquad f_0''(1/2;-1/4)=-\frac18.
$$

The implicit-function theorem therefore gives a unique analytic positive
critical branch $v_\ast(s,\lambda)$ near $1/2$.
Moreover, if a point has positive gain then, by dropping the nonnegative cost,

$$
0\lt f_s(v;\lambda)
\le v^4\left[\lambda+\frac14-(v-1/2)^2\right].
$$

For $\lambda$ sufficiently close to $-1/4$, every positive-gain maximizer is
therefore in the neighborhood of this branch. Strict concavity there makes
it the unique nonzero global maximizer whenever the optimal gain is positive.

Let $V(s,\lambda)=f_s(v_\ast(s,\lambda);\lambda)$. This is analytic, vanishes
at $\lambda=\lambda_c(s)$, and the envelope derivative is exactly

$$
\frac{\partial V}{\partial\lambda}(s,\lambda)=v_\ast(s,\lambda)^4.
$$

Consequently,

$$
V(s,\lambda_c(s)+\delta)
=\delta\int_0^1v_\ast(s,\lambda_c(s)+t\delta)^4 dt.
$$

The integral is the analytic positive factor $B(s,\delta)$. Taking the
maximum with the origin proves the theorem. In particular, there is no
additive error term that can overwhelm an exceptionally small positive
$\delta$: the error is relative to the distance from the true boundary.

Since $v_c(s)=1/2+O(s^6)$ and $v_\ast(s,\lambda_c(s)+\delta)-v_c(s)=O(|\delta|)$,
the stated uniform expansion of $B$ follows.

## 4. Calculation of the critical curve

Put $c=v^2/2$. The exact inner stationarity equation gives, uniformly with
derivatives near $v=1/2$,

$$
u_s(v)=c-3s^7c^5+45s^{14}c^9+O(s^{21}).
$$

Substitution into the minimized cost yields

$$
C_s(v)=\frac{s^6v^{12}}{64}
-\frac{9s^{13}v^{20}}{1024}+O(s^{20}).
$$

The second term records relaxation away from the square center. Therefore

$$
T_s(v)=v^2-v+s^6f(v)+s^{13}g(v)+O(s^{20}),
$$

where $f(v)=v^8/64$ and $g(v)=-9v^{16}/1024$. Minimizing near $v_0=1/2$ gives

$$
v_c(s)=\frac12-\frac{s^6}{2048}+O(s^{12}),
$$

and

$$
\lambda_c(s)=-\frac14+s^6f(v_0)
-\frac{s^{12}}4 f'(v_0)^2+s^{13}g(v_0)+O(s^{18}).
$$

Here $f(v_0)=2^{-14}$, $f'(v_0)=2^{-10}$, and
$g(v_0)=-9\cdot2^{-26}$, giving the displayed critical curve.

There is also an exact polynomial characterization of the coexistence point:

$$
u_c+3s^7u_c^5=\frac{v_c^2}{2},\qquad
v_c^5(2v_c-1)+8s^6u_c^6=0,
$$

with $(u_c(0),v_c(0))=(1/8,1/2)$, followed by

$$
\lambda_c(s)=\frac{6v_c^2-5v_c}{4}
+\frac32\frac{s^6u_c^5}{v_c^2}.
$$

The Jacobian of the first two equations in $(u_c,v_c)$ at $s=0$ has
determinant $1/16$. These equations permit exact recursive calculation of
arbitrarily many Taylor coefficients. The independent rational check script
below verifies the equations through degree 20, including

$$
\lambda_c(s)=-\frac14+\frac{s^6}{2^{14}}-\frac{s^{12}}{2^{22}}
-\frac{9s^{13}}{2^{26}}+\frac{7s^{18}}{2^{32}}
+\frac{9s^{19}}{2^{32}}+\frac{135s^{20}}{2^{38}}+O(s^{21}).
$$

The gaps in these Taylor powers have an analytic explanation. Treat
$a=s^6$ and $b=s^7$ as independent small parameters. The inner equation becomes
$u+3bu^5=v^2/2$, and the threshold functional is

$$
T(v;a,b)=v^2-v+a\frac{u(v,b)^6+9b u(v,b)^{10}}{v^4}.
$$

Its minimizing branch near $v=1/2$ is analytic in $(a,b)$. At $a=0$ its
minimum is exactly $-1/4$ for every sufficiently small $b$. Analytic divisibility
therefore gives an analytic function $G$ such that

$$
\boxed{\lambda_c(s)=-\frac14+s^6G(s^6,s^7).}
$$

Only powers $6+6i+7j$, with integers $i,j\ge0$, can occur in its nonconstant
Taylor series. Grouping by $N=i+j+1$ gives the allowed sets
$\lbrace 6N,6N+1,\ldots,7N-1\rbrace$: initially $\lbrace 6\rbrace$, $\lbrace 12,13\rbrace$,
$\lbrace 18,19,20\rbrace$, and $\lbrace 24,25,26,27\rbrace$. These are allowed powers;
the argument does not require every allowed coefficient to be nonzero, and
the sets eventually overlap. In particular, the remainder after the displayed
degree-20 expansion can be sharpened to $O(s^{24})$. Multiplication by $s$
gives a remainder $O(s^{25})$ for the corresponding physical threshold.

## 5. Nested response laws

The critical curve immediately resolves narrower parameter windows.
Here all limits are as $s\downarrow0$ and all named path coefficients are fixed.

For $\varepsilon=-s/4+\mu s^7$,

$$
\boxed{
\frac{\Delta(s,\varepsilon)}{s^{12}}
\longrightarrow\frac1{16}\left(\mu-2^{-14}\right)_+.
}
$$

At $\mu=2^{-14}$, this limit is zero, but the full response is positive and
has the finer law

$$
\boxed{
\Delta\left(s,-\frac{s}{4}+\frac{s^7}{2^{14}}\right)
\sim\frac{s^{18}}{2^{26}}.
}
$$

More generally, for $\varepsilon=-s/4+s^7/2^{14}+\nu s^{13}$,

$$
\frac{\Delta(s,\varepsilon)}{s^{18}}
\longrightarrow\frac1{16}\left(\nu+2^{-22}\right)_+.
$$

Tuning $\nu=-2^{-22}$ exposes the transverse relaxation term:

$$
\boxed{
\Delta\left(s,-\frac{s}{4}+\frac{s^7}{2^{14}}-\frac{s^{13}}{2^{22}}\right)
\sim\frac{9s^{19}}{2^{30}}.
}
$$

These are coefficient paths through the same spatial polynomial family.
They are not different exponents of a single fixed-coefficient perturbation.
The paths displayed here are themselves polynomials in $s$.

The exact analytic factorization gives a general contact-order rule. If

$$
\lambda(s)-\lambda_c(s)=a s^m+o(s^m),\qquad a\gt 0,\quad m\gt 0,
$$

then

$$
\boxed{\Delta(s,s\lambda(s))\sim\frac{a}{16}s^{6+m}.}
$$

For $a\lt 0$ the gap is eventually exactly zero. For every positive integer $m$,
a polynomial path $\lambda(s)$ can be chosen by matching the Taylor series of
$\lambda_c$ below degree $m$ and choosing a larger coefficient at degree $m$.
Thus fixed degree in the spatial variables does not bound response exponents
along parameter paths of arbitrarily high contact order. The required degree
and tuning of the parameter path increase with $m$.

The possibility of arbitrarily high contact orders is generic once a
transversally vanishing analytic branch has been proved; it is not by itself
a special novelty of this polynomial. The family-specific content is the
global activation proof, the critical-curve coefficients, the factor $s^6$
and limiting contact coefficient $1/16$, the displacement scales, and their
transport under the stated exact full-normal-form hypotheses. A perturbation
of a tuned path can change its response order or move it to the inactive side.

## 6. Optimizer geometry and portability

At activation the nonzero maximizing point satisfies

$$
y_c(s)=\frac{s}{2}-\frac{s^7}{2048}+O(s^{13}),
\qquad x_c(s)=\frac{s^2}{8}+O(s^8).
$$

Along every positive contact path above, $y_\ast(s)\sim s/2$ and
$x_\ast(s)\sim s^2/8$, even when the gain is of order $s^{18}$, $s^{19}$, or
higher. The value can become extremely flat while the maximizing point keeps
the same leading displacement scales.

At each sufficiently small fixed $s$, the origin and the nonzero point coexist
on the critical curve. Crossing that curve changes the maximizing displacement
by order $s$ in $y$. This finite-$s$ displacement change tends to zero as
$s\to0$; it is not a macroscopic jump persisting in the original coordinates.

Now let $P$ be any bounded full-dimensional polyhedron with a simple vertex
whose **exact full** inward-coordinate polynomials are the displayed $D$ and
$R_\varepsilon$. All feasible coordinates are nonnegative, and a sufficiently
small nonnegative coordinate box is feasible. The global upper inequalities
above hold throughout $P$. Every positive maximizing branch near activation
has $y=O(s)$ and $x=O(s^2)$, and is therefore in that small feasible box for
sufficiently small $s$, uniformly in a sufficiently small parameter neighborhood.
The unconstrained orthant upper bound is attained in $P$.

Consequently the same critical curve, contact factorization, response laws,
and chart-coordinate displacement laws hold at all such polyhedral vertices.
The ambient displacement is obtained by applying the exact inward generators.
The numerical constants above refer to this full normalized polynomial model;
arbitrary base remainders require their own uniform analysis.

This extends the portable principle to the geometry of the activation boundary
and contact with it. The first signed initial form identifies a zero set; the
terms suppressed at that stage then determine the boundary and its subsequent
response laws.

## 7. Verification and relation to existing mathematics

Run the exact, standard-library-only coefficient verification with:

```bash
python experiments/activation_contact_check.py
```

The analytic and global arguments above prove the activation/contact theorem.
The script verifies its algebraic expansion independently; formal coefficients
alone would not prove global maximization. Additional 150-digit checks of the
full stationary equations at $s=0.1,0.03,0.01$ agree with the three response
laws. For the $s^{18}$ path, the ratios to its limiting coefficient are
approximately $1.05625$, $1.016875$, and $1.005625$ respectively.

Recursive extraction of tropical critical points is established research;
for example, [Judd and Rietsch](https://arxiv.org/abs/1911.04463) give a finite
recursive construction for complete Laurent polynomials with positive
generalized-Puiseux leading coefficients. That theorem has different hypotheses
from this signed, constrained activation problem. The implicit-function and
envelope arguments used here are standard tools. The specific result established
in this note is the global activation/contact law for the repository's family
and its exact polyhedral transport; a literature-priority assessment would
require a separate, broader comparison.
