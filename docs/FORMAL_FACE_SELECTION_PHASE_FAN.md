# The face-selection universality phase-fan law

Formal result **V.17** · executable module:
`categorical_polytope/face_selection_phase.py` · backend asset:
`portable-principle.v7` (V.17 phase fan, V.18 qualification, V.19
constructive binomial positivity, V.20 exact ambient transport, and V.21
finite-family discovery).

## Abstract

The face-selection law does more than solve one singular asymptotic problem.
Applied to a parameterized family, it determines the complete phase diagram of
the leading asymptotic mechanism.

Let the finitely many admissible face mechanisms have weighted degrees

$$
q_j(\theta)=a_j+\langle b_j,\theta\rangle .
$$

Then the selected degree is the lower envelope

$$
q_*(\theta)=\min_{j:\,0<q_j(\theta)<1}q_j(\theta),
$$

and every change of winning face lies on one of the affine walls

$$
q_i(\theta)=q_j(\theta),\qquad q_i(\theta)=0,
\qquad q_i(\theta)=1.
$$

Away from those walls, the winning face, active asymptotic mechanism, and
universality class are constant.  The response exponent is determined
throughout each chamber by

$$
\gamma(\theta)=\frac{1}{1-q_*(\theta)}.
$$

Thus a finite Newton–tropical comparison generates a continuum of asymptotic
predictions and all of its possible universality transitions.

---

## Theorem V.17 — universality phase fan

Let $\Omega\subset\mathbb R^m$ be a parameter domain.  Suppose:

1. the localized tangent-cone geometry is fixed on $\Omega$;
2. there are finitely many face mechanisms $j\in J$;
3. their admissibility and positivity status are fixed on $\Omega$;
4. every weighted degree is affine,
   $q_j(\theta)=a_j+\langle b_j,\theta\rangle$; and
5. the analytic hypotheses of the face-selection law hold uniformly on each
   chamber considered.

Form the hyperplane arrangement

$$
\mathcal H=
\{q_i=q_j:i\ne j\}\cup\{q_i=0:i\in J\}\cup\{q_i=1:i\in J\}.
$$

On every connected component $C$ of $\Omega\setminus\mathcal H$:

- the relevance status $0<q_j<1$ of every mechanism is constant;
- the strict ordering of all nonidentical degree laws is constant;
- the winning set $\operatorname*{argmin}_{0<q_j<1}q_j$ is constant;
- $q_*$ is one affine function on $C$; and
- the gap law is
  $\Delta(s;\theta)=\Theta(s^{\gamma(\theta)})$ with
  $\gamma(\theta)=1/(1-q_*(\theta))$.

If several mechanisms have identical affine degree laws, they remain tied on
the entire chamber.  If they agree only on a proper wall, that wall is an exact
transition locus between universality classes whenever the two mechanisms
exchange lower-envelope dominance.

### Proof

For every pair $i,j$, the sign of $q_i-q_j$ can change only on the affine
hyperplane $q_i=q_j$.  Likewise, the truth values of $q_i>0$ and $q_i<1$ can
change only on $q_i=0$ and $q_i=1$.  All these signs are therefore constant on
each connected component of the complement of $\mathcal H$.  The relevant
candidate set and its ordering are constant there, so its argmin is constant.
The selected degree equals the affine law of the winner.  Composing with the
face-selection scaling map $q\mapsto1/(1-q)$ proves the response formula. ∎

---

## Exact one-parameter section

For one control parameter $t\in[L,U]$, all walls are rational whenever the
affine coefficients are rational:

$$
t_{ij}=\frac{a_j-a_i}{b_i-b_j},\qquad
t_{i,0}=\frac{-a_i}{b_i},\qquad
t_{i,1}=\frac{1-a_i}{b_i}.
$$

The implementation sorts these exact values, selects at one rational midpoint
of every open chamber, and separately evaluates every wall.  No numerical grid
is used, so a narrow chamber cannot be skipped.

For $N$ mechanisms, the candidate wall set has size at most

$$
{N\choose2}+2N
$$

before coincidences and out-of-domain walls are removed.

### Worked transition

Take

$$
q_A(t)=\frac14+\frac12t,qquad
q_B(t)=\frac12-\frac12t,qquad 0\le t\le\frac34.
$$

The unique crossing is $t=1/4$, where $q_A=q_B=3/8$.  Therefore

$$
q_*(t)=
\begin{cases}
\frac14+\frac12t,&0<t<\frac14,\\[2mm]
\frac12-\frac12t,&\frac14<t<\frac34,
\end{cases}
$$

with both mechanisms active at the wall.  The exponent law is

$$
\gamma(t)=
\begin{cases}
\displaystyle\frac{1}{3/4-t/2},&0<t<\frac14,\\[3mm]
\displaystyle\frac{1}{1/2+t/2},&\frac14<t<\frac34.
\end{cases}
$$

At the transition itself, $\gamma=8/5$.

---

## Why this is a new level of the principle

V.15 converts one selected degree into a sharp asymptotic response.  V.16
selects the winning degree among competing perturbations.  V.17 parameterizes
that competition and obtains the entire universality phase structure:

$$
\boxed{
\text{affine face degrees}
\longrightarrow
\text{transition fan}
\longrightarrow
\text{piecewise-exact exponent law}
}
$$

The output is not a list of sampled regimes.  It is a certificate that no
other transition can occur between the enumerated walls under the stated
hypotheses.

This enables:

- exact detection of parameter values where the active mechanism changes;
- prediction of universality classes over continuous parameter domains;
- principled experimental design concentrated at transition walls;
- robustness margins measuring distance to a change of mechanism; and
- inverse localization of parameters from an observed exponent transition.

### Newton-weight compiler

For a parameterized monomial

$$
M_j(x;\theta)=\prod_i x_i^{\alpha_{ij}(\theta)},
\qquad
\alpha_{ij}(\theta)=c_{ij}+d_{ij}\theta,
$$

against a base principal part with orders $\beta_i$, its competing affine law
is derived rather than fitted:

$$
q_j(\theta)
=\sum_i\frac{\alpha_{ij}(\theta)}{\beta_i}
=\sum_i\frac{c_{ij}}{\beta_i}
+\theta\sum_i\frac{d_{ij}}{\beta_i}.
$$

The backend performs this compilation with exact rational arithmetic. This
closes the path from parameterized perturbation exponents to the phase fan;
callers do not need to calculate or numerically estimate the degree laws.

### Transition robustness

For a query point $\theta_0$, define the phase robustness margin

$$
\rho(\theta_0)=
\min_{\tau\in\mathcal T}|\theta_0-\tau|,
$$

where $\mathcal T$ is the set of walls at which the selected universality
mechanism actually changes. Then every parameter perturbation
$|\delta|<\rho(\theta_0)$ preserves the winning mechanism. The backend reports
$\rho$ exactly, together with the closest transition on either side. Candidate
walls that do not alter the lower envelope do not falsely reduce this margin.

---

## Scope and stratified extension

The fixed-admissibility hypothesis is essential.  A coefficient crossing zero,
an initial-form cancellation, a loss of positivity, a change of tangent cone,
or failure of uniform isolation can create an additional wall not visible from
degree equality alone.

The correct general extension is stratified:

1. partition parameter space by geometry, cancellation, positivity, and
   analytic-scope walls;
2. apply V.17 inside each fixed-admissibility stratum; and
3. glue the resulting phase fans along their common boundaries.

The backend therefore computes the diagram even when the hypotheses are not
asserted, but labels it `unlicensed`. A theorem-licensed response requires
fixed admissibility, verified affine degrees, and uniform local maximality,
principal-remainder control, and global isolation. V.18 additionally derives
affine coefficient-qualification walls.

---

## Backend operation

```json
{
  "operation": "phase_diagram",
  "parameter": "theta",
  "domain": ["0", "3/4"],
  "mechanisms": [
    {
      "id": "face-a",
      "face": ["x"],
      "degree": {"intercept": "1/4", "slope": "1/2"}
    },
    {
      "id": "face-b",
      "face": ["y"],
      "degree": {"intercept": "1/2", "slope": "-1/2"}
    }
  ],
  "assumptions": {
    "fixed_admissibility": true,
    "affine_degrees_verified": true,
    "uniform_local_base_maximality": true,
    "uniform_principal_remainder": true,
    "uniform_global_isolation": true
  }
}
```

The response contains exact breakpoints, open chambers, wall winners,
transition kinds, weighted-degree laws, response-exponent laws, scope blockers,
and an audit trail.  Rational strings are retained alongside floating-point
values at the JSON boundary.

## Reproduce

```bash
python -m pytest -q tests/test_face_selection_phase.py
python -m categorical_polytope.adjudication.polyhedra.backend \
  --input experiments/face_selection_phase_v17_request.json --pretty
```
