# Finite-scale certificates for quadratic curved channels

The `curved_reduction` operation can certify the accuracy of its leading power
law at a specified positive perturbation scale. This extends the exact
[V.22 reduction](FORMAL_CURVED_REDUCTION.md) through the same feasible
polyhedral chart. The implementation is
[`curved_finite_scale.py`](../categorical_polytope/curved_finite_scale.py).

The asymptotic result holds as $s\to0^+$ with all polynomial coefficients and
the polyhedron fixed. It does not automatically supply a uniform approximation
when a coefficient also approaches cancellation. The optional finite-scale
assessment retains the full reduced polynomial and certifies objective-value
bounds at the requested $s$.

## Request

```json
{
  "operation": "curved_reduction",
  "system": "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
  "base": "-(x0**6+x1**6)",
  "perturbation": "-x0**2+x0*x1**2-x1**4/4+x1**4/1000000000+x1**5",
  "finite_scale": {
    "s": "1e-12",
    "relative_tolerance": "1/10",
    "max_subdivisions": 512
  }
}
```

| `finite_scale` field | Required | Meaning |
| --- | --- | --- |
| `s` | yes | Positive scale, supplied as a number, decimal string, or rational string |
| `relative_tolerance` | no | Allowed error relative to $L s^\gamma$; defaults to `1/10`, must lie in $[0,1)$ |
| `max_subdivisions` | no | Integer work budget from 0 through 1024; defaults to 512 |

Strings preserve exact tiny scales without JSON floating-point underflow.
Numeric inputs are interpreted through their decimal spelling. Boolean values,
nonfinite numbers, zero denominators, unknown fields, and invalid budgets are
rejected as `invalid_request`. Scalar spellings are limited to 256 characters
and decimal exponents to absolute value 1000.

Both operation names (`curved_reduction` and `polyhedral_curved_reduction`),
Python calls, JSON batches, and the CLI support this option. A reproducible
two-scale batch is provided in
[`curved_finite_scale_requests.json`](../experiments/curved_finite_scale_requests.json).

## Response and interpretation

The existing `curved-reduction.backend.v1` response receives additive fields.
`scaling.limit` states the fixed-coefficient limit and
`scaling.uniform_in_coefficients` is `false`. The exponent, sharp coefficient,
and asymptotic license retain their meanings.

The separate `finite_scale` block contains:

| Field | Meaning |
| --- | --- |
| `status` | Accuracy decision listed below |
| `bounds_certified` | Whether a rigorous gap interval is supplied |
| `gap_interval` | Rational lower and upper bounds for the actual gap |
| `prediction_interval` | Rational enclosure of $L s^\gamma$, including irrational values |
| `gap_to_prediction_ratio` | Rational enclosure of the true gap divided by $L s^\gamma$ |
| `relative_error_bound` | Certified upper bound on that ratio's distance from 1 |
| `witness` | Feasible rational edge coordinates, constraint slacks, full objective gain, and charged costs |
| `envelope` | Full reduced objective, retained-coordinate projection, maximum enclosure, and subdivision count |
| `reason`, `limits`, `proof` | Termination reason, resource limits, and proof method when bounds are available |

Every numeric bound has an authoritative `exact` rational string and a display
`value`. A display value is `null` on overflow or nonzero underflow. Display
values never decide feasibility, sign, or accuracy.

For certified ratio interval $[r_-,r_+]$ and tolerance $\delta$:

- `within_tolerance`: the entire interval lies in $[1-\delta,1+\delta]$.
- `outside_tolerance`: the entire interval lies strictly above or strictly
  below that band.
- `not_resolved`: the available bounds do not decide accuracy, or a resource
  guard prevented their construction. Inspect `bounds_certified` and `reason`.

`not_requested` is returned when the option is absent. `not_available` is
returned when the quadratic asymptotic reduction is outside its supported
scope. The CLI's successful exit code and top-level `licensed` status continue
to describe the asymptotic analysis; clients requesting finite accuracy must
also inspect `finite_scale.status`.

The algorithm may stop as soon as the tolerance decision is proved. Its gap
interval can therefore be wider than an independently computed sharp bound.
`outside_tolerance` is useful information about a specified approximation at a
specified scale; it does not revoke the fixed-coefficient theorem.

## Mathematical guarantee

Let the exact full transported loss and perturbation satisfy V.22:

$$
D(x,y)=A x^p+B y^q,\qquad
R(x,y)=S(y)-a\left(x-\frac{H(y)}{2a}\right)^2,
$$

with $A,B,a\gt 0$. All feasible edge coordinates are nonnegative. Write

$$
\Delta(s)=\max_P\lbrace-D+sR\rbrace,\qquad
E_s(y)=-B y^q+sS(y).
$$

Exact elimination of the $x$ inequalities gives the retained-coordinate
projection $[0,Y]$. Define $U(s)=\max_{0\le y\le Y}E_s(y)$. Dropping the
two nonpositive costs gives

$$
\Delta(s)\le U(s).
$$

Every verified feasible witness $(x_w,y_w)$ gives

$$
\max\lbrace 0,E_s(y_w)-A x_w^p
-sa\left(x_w-\frac{H(y_w)}{2a}\right)^2\rbrace
\le\Delta(s).
$$

The origin supplies the zero lower bound. These are finite-scale inequalities;
they do not use an asymptotic remainder estimate. If an exact envelope maximizer
$\widehat y$ has feasible center $\widehat x=H(\widehat y)/(2a)$, they specialize to

$$
\max\lbrace 0,U(s)-A\widehat x^p\rbrace \le\Delta(s)\le U(s).
$$

The implementation uses rational sample points and a certified enclosure of
$U(s)$. Its interval includes uncertainty in the envelope maximum as well as
the omitted base and square costs. It makes no claim that its witness is the
exact optimizer.

At a retained sample coordinate, the remaining inequalities give an exact
feasible interval for $x$. The center $H(y)/(2a)$ is clipped to that interval
when necessary, and the resulting square penalty is charged explicitly.
Nonnegative coordinates and every original transported constraint are checked.

## Certified envelope computation

On an interval $[\ell,r]$, express the polynomial in the Bernstein basis,
with $t=(y-\ell)/(r-\ell)$:

$$
E_s(y)=\sum_{i=0}^n b_i\binom ni t^i(1-t)^{n-i}.
$$

The basis functions are nonnegative and sum to one, so

$$
\min_i b_i\le E_s(y)\le\max_i b_i.
$$

The initial coefficients and all midpoint subdivisions use exact rational
arithmetic. The algorithm refines the interval with largest upper bound.
Intervals whose upper bounds are already below a feasible full-objective
lower bound can be discarded. The maximum remaining bound, together with
the best feasible witness value, encloses the global gap. This argument
covers the entire retained projection, including endpoints and multiple
competing maxima; it does not rely on a grid finding every critical point.

The leading prediction is positive throughout the licensed V.22 scope. Its
rational-power expression is enclosed by 96 steps of rational bisection from
a power-of-two bracket, allowing scales far below floating-point resolution.
For $0\lt b_-\le Ls^\gamma\le b_+$ and $0\le\ell\le\Delta\le u$:

$$
\frac{\ell}{b_+}\le\frac{\Delta}{Ls^\gamma}\le\frac{u}{b_-}.
$$

Thus the tolerance decisions also use rational inequalities. No additional
scientific-computing dependency is required.

The finite assessment currently caps the base, driver, and reduced degrees
at 32 and guards stored rational bound/coefficient sizes at 4096 bits.
`degree_limit` or an initial `rational_size_limit` returns `not_resolved`
without a gap interval. A later size limit or exhausted subdivision budget
preserves the bounds already proved. When the envelope maximum is enclosed
within $2^{-40}b_-$ but the gap interval still overlaps the tolerance boundary,
`envelope_relaxation_gap` returns `not_resolved`: further refinement of that
envelope cannot remove the omitted-cost uncertainty by itself. These are
finite-assessment limits, separate from the asymptotic license.

The certificate applies to the supplied full polynomial. It does not cover
measurement uncertainty in input coefficients or an unverified base remainder.

## Cancellation crossover

On $[0,1]^2$, take

$$
D=x^6+y^6,\qquad
R_\varepsilon=-(x-y^2/2)^2+\varepsilon y^4+y^5.
$$

Every fixed $\varepsilon\gt 0$ has the V.22 law
$\Delta\sim(4/27)\varepsilon^3s^3$. At $\varepsilon=0$, the exponent is 6.
For $\varepsilon=\lambda s$, $\lambda\gt-1/4$, put

$$
v_\lambda=\frac{5+\sqrt{25+96\lambda}}{12},\qquad
K(\lambda)=\frac{v_\lambda^5(2v_\lambda-1)}4.
$$

Maximizing $-v^6+v^5+\lambda v^4$ on $v\ge0$ gives $K(\lambda)$.
The full objective at $y=sv_\lambda$, $x=s^2v_\lambda^2/2$ therefore proves

$$
s^6K(\lambda)-\frac{s^{12}v_\lambda^{12}}{64}
\le\Delta(s,\lambda s)\le s^6K(\lambda)
$$

whenever this witness is feasible. At $\lambda=1$, the response relative to
the fixed-coefficient prediction obeys

$$
\frac{320}{27}-\frac{65536}{19683}s^6
\le\frac{\Delta(s,s)}{(4/27)s^6}\le\frac{320}{27}.
$$

Thus at $\varepsilon=s=10^{-9}$, the response is approximately 11.85 times
the fixed-coefficient leading prediction. The backend certifies
`outside_tolerance` at tolerance `1/10`. Keeping $\varepsilon=10^{-9}$ and
using $s=10^{-12}$ instead gives `within_tolerance`, with the true ratio
approximately 1.08067. Both requests retain the exponent-3 asymptotic license.
The implementation obtains these decisions from the general polynomial
envelope, without a special-case crossover formula.

## Reproduce

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/curved_finite_scale_requests.json --pretty
python -m pytest -q -p no:cacheprovider tests/test_curved_finite_scale.py tests/test_curved_reduction.py tests/test_curved_reduction_backend.py
```
