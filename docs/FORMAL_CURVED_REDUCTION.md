# Quadratic elimination of curved asymptotic channels

Formal result **V.22** · backend operation `polyhedral_curved_reduction` ·
response contract `curved-reduction.backend.v1`.

This result resolves a family of signed perturbations that cannot be decided
by the first weighted layer on coordinate faces. It extends the exact
counterexample in [the mathematical audit](MATHEMATICAL_AUDIT.md) to a
constructive theorem and an executable certificate.

Implementation: `categorical_polytope/curved_reduction.py`.
Polyhedral interface: backend operation `curved_reduction`.

## Theorem

Let $P$ be a bounded full-dimensional polyhedron with a simple vertex $v$.
In its exact inward edge coordinates $(x,y)$, suppose the **full** base loss
and centered perturbation are

$$
D(x,y)=A x^p+B y^q,\qquad
R(x,y)=-a x^2+xH(y)+K(y),
$$

where $A,B,a\gt 0$, $p,q\gt 1$ are integers, and $H,K$ are polynomials with
$H(0)=K(0)=0$. Write

$$
H(y)=h_r y^r+O(y^{r+1}),\qquad h_r\gt 0,
$$

and combine the coefficients of the reduced polynomial **exactly**:

$$
S(y)=\frac{H(y)^2}{4a}+K(y)
 =C y^\alpha+O(y^{\alpha+1}).
$$

Assume

$$
C\gt 0,\qquad 0\lt \alpha\lt q,\qquad pr\gt q.
$$

Then, with $M(s)=\max_P(F+sG)$,

$$
\boxed{M(s)-F(v)-sG(v)\sim Ls^\gamma,\qquad
\gamma=\frac{q}{q-\alpha},}
$$

where

$$
\boxed{L=C\frac{q-\alpha}{q}
\left(\frac{\alpha C}{qB}\right)^{\alpha/(q-\alpha)}.}
$$

An asymptotically sharp witness is

$$
y_s=\left(\frac{\alpha C}{qB}s\right)^{1/(q-\alpha)},
\qquad x_s=\frac{H(y_s)}{2a}.
$$

The effective weight $\alpha/q$ is the weight **after elimination**. It
need not be the initial weight on any coordinate face of the original
polynomial.

## Proof

**Global localization.** Every feasible point has nonnegative edge
coordinates, because the active constraints at $v$ are satisfied throughout
$P$. The exact identity $F(v)-F=A x^p+B y^q$ makes $v$ the unique global
maximizer of $F$. Compactness and continuity then force maximizers of $F+sG$
into every fixed neighborhood of $v$ as $s\to0^+$.

**Uniform upper bound.** Completing the square is a polynomial identity:

$$
R=S(y)-a\left(x-\frac{H(y)}{2a}\right)^2.
$$

Consequently, throughout the local feasible region,

$$
-D+sR\le-B y^q+sS(y).
$$

For every $\varepsilon\gt 0$ sufficiently small, after shrinking the
neighborhood, $S(y)\le(C+\varepsilon)y^\alpha$ for $y\ge0$ there.
Maximizing $-B y^q+s(C+\varepsilon)y^\alpha$ on the nonnegative axis
gives $L(C+\varepsilon)s^\gamma$, where $L(\cdot)$ is the displayed
continuous coefficient formula. Localization therefore gives
$\limsup\Delta(s)/s^\gamma\le L$ on letting $\varepsilon\downarrow0$.

**Matching feasible lower bound.** Since $h_r\gt 0$, the square-center curve
$x=H(y)/(2a)$ has positive coordinates for all sufficiently small $y\gt 0$.
At a simple vertex, every sufficiently small nonnegative edge displacement
is feasible. The proposed $(x_s,y_s)$ is therefore eventually in $P$ and
annuls the square exactly. At this point,

$$
-B y_s^q+sS(y_s)=Ls^\gamma+o(s^\gamma),
$$

while

$$
A x_s^p=O\left(s^{pr/(q-\alpha)}\right)=o(s^\gamma)
$$

by $pr\gt q$. This proves the matching lower bound and the asymptotic
equivalence. ∎

## Why the omitted base condition matters

The square-center curve is not generally the exact optimizer at finite $s$.
It is useful because its value asymptotically attains the upper bound.

At $pr=q$, the omitted cost is of the same order as the response, so it can
change the leading coefficient. For example, with $D=x^3+y^6$ and
$R=-x^2+xy^2$, set $x=su$, $y=s^{1/2}v$. The reduced objective at order
$s^3$ is

$$
-u^3-v^6-u^2+uv^2.
$$

The term $-u^3$ survives and cannot be dropped. For $pr\lt q$, it can even
change the dominant balance. The resolver refuses both regimes instead of
reusing a coefficient derived under strict subleading control.

Arbitrary additions to the base also require a new proof. The resolver
checks the full transported polynomial rather than borrowing a certificate
from a diagonal principal part.

## Two exact resolutions

For $D=x^6+y^6$ and $R=-x^2+xy^2$, the reduced polynomial is $S=y^4/4$.
Hence $\alpha=4$, $\gamma=3$, $L=1/432$. The witness is
$y_s=\sqrt{s/6}$, $x_s=s/12$. The sharper identity from the audit proves

$$
\frac{s^3}{432}-\frac{s^6}{12^6}\le\Delta(s)\le\frac{s^3}{432}.
$$

For the same base and

$$
R=-x^2+xy^2-\frac14y^4+y^5,
$$

completion of the square gives $S=y^5$: its fourth-order layer cancels
exactly. Now

$$
\gamma=6,\qquad L=\frac{3125}{46656},\qquad
y_s=\frac56s,\qquad x_s=\frac{25}{72}s^2.
$$

In particular,

$$
\frac{3125}{46656}s^6-\left(\frac{25}{72}\right)^6s^{12}
\le\Delta(s)\le\frac{3125}{46656}s^6
$$

for sufficiently small $s$ that the witness is feasible. This cancellation
is exposed on the curved channel; it is not cancellation of the original
full-cone initial polynomial.

## Exact polyhedral certification

The new backend operation enumerates candidate simple vertices by exact
active-constraint solves. At each it checks:

1. every constraint slack is nonnegative and exactly two constraints are active;
2. the recession cone is trivial;
3. the full base pullback is exactly a positive diagonal loss;
4. the perturbation has the required quadratic form, in either axis orientation;
5. the reduced polynomial has positive subcritical leading degree; and
6. the omitted base exponent is strictly higher than the response exponent.

The two-dimensional recession test is exact. In edge coordinates, any
nonzero recession direction can be normalized to $(t,1-t)$, $0\le t\le1$.
Every constraint becomes an affine inequality in $t$. Boundedness is
equivalent to the resulting rational interval being empty. A single
remaining point still represents an unbounded direction.

The certificate contains the rational chart, slacks, complete reduced
polynomial, square identity, effective weight, response exponent, witness
rates, and coefficient. Nonrational coefficients retain an exact rational
power expression alongside an approximate display value. Exponent selection
does not depend on floating-point approximations or an observed optimizer.

This operation has its own response contract because its effective weight
comes from elimination. The original face-selection operation continues to
report unresolved cases under its own theorem; a curved certificate does
not retroactively make its first-layer face calculation valid.

## Reproduce

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/curved_reduction_request.json --pretty
python -m pytest -q -p no:cacheprovider tests/test_curved_reduction.py tests/test_curved_reduction_backend.py
```

The same operation works in JSON batches and with the Python handler:

```python
from categorical_polytope.adjudication.polyhedra.backend import analyze_face_selection

result = analyze_face_selection({
    "operation": "curved_reduction",
    "system": "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
    "base": "-(x0**6+x1**6)",
    "perturbation": "-x0**2+x0*x1**2",
})
assert result["licensed"]
assert result["scaling"]["response_exponent_exact"] == "3"
assert result["scaling"]["leading_coefficient"]["exact"] == "1/432"
```
