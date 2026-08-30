# The finite exponent-law discovery principle

Formal result **V.21** · backend asset `portable-principle.v7` · operation:
`polyhedral_face_selection_discovery`.

## Principle

Fix a bounded polyhedron, a simple maximizing vertex, and an admissible base
principal part. For a finite perturbation family

\[
\mathcal R=\{R_1,\ldots,R_N\},
\]

compile every member through V.20:

\[
R_j(x)
\longmapsto
R_j(\Phi(c))-R_j(v)
\longmapsto
\{q_{j,F}:F\text{ qualified}\}
\longmapsto
(q_j^*,\gamma_j).
\]

The family is then partitioned into three finite, auditable structures:

1. **screening strata:** relevant, critical, subleading, inactive, or
   unresolved;
2. **universality classes:** equal selected weight and response exponent;
3. **mechanism subclasses:** equal weights, winning faces, and transported
   polynomial signature.

This partition is complete relative to the supplied finite family and the
compiler's stated scope. It does not establish that the family exhausts all
possible perturbations.

## Exponent-law candidates

For each relevant class with $0<q_*<1$, the engine emits the candidate law

\[
\Delta(s)=\Theta\!\left(s^{\gamma}\right),
\qquad
\gamma=\frac1{1-q_*}.
\]

A class absent from `known_class_ids` is labeled `unregistered`. This means
only that it is absent from the caller-supplied registry. The backend reports
it as a theorem candidate and explicitly does not claim literature novelty.

Adjacent entries in the discrete exponent spectrum report gaps in $q_*$ and
$\gamma$. They are neighboring classes in the screened family, not continuous
phase walls. A genuine phase wall requires the parametric V.17–V.18 engine.

## Diagnostic elevation

The engine elevates mechanisms for follow-up when exact compilation reveals:

- edge-monomial cancellation;
- complete geometric suppression after localization;
- tied qualified winning faces;
- disagreement between an observed exponent and every compiled feasible face;
- a correction from numerical probing to exact transport;
- a critical $q=1$ boundary requiring a different balance law;
- unresolved positivity or unlicensed analytic hypotheses.

High-order and subleading polynomial terms remain visible even when numerical
probing cannot resolve their scale. Non-polynomial candidates retain the safe
numerical fallback and are labeled accordingly.

## Generated families

Besides explicit perturbation lists, the backend can generate an ambient
monomial grid with bounded total degree, selected variables, rational
coefficients, and optional exclusion of mixed terms. Candidate generation is
capped at 256 members per request. The generated family is data for the exact
compiler; it is not itself evidence that the candidate space is scientifically
complete.

## Canonical discovery

For

\[
D_0(x_0,x_1)=x_0^2+x_1^4,
\]

the family $x_1,x_0,x_1^2,x_0x_1,x_0^2$ produces:

| selected weight | exponent | representative mechanisms |
| --- | --- | --- |
| $1/4$ | $4/3$ | $x_1$ |
| $1/2$ | $2$ | $x_0$, $x_1^2$ |
| $3/4$ | $4$ | $x_0x_1$ |

The term $x_0^2$ lies at the critical boundary $q=1$ and is screened from the
fractional-power law. Adding $x_1-x_1+x_0$ leaves the $q=1/2$ class unchanged
while producing an explicit cancellation diagnostic.

The reproducible request is
`experiments/face_selection_discovery_v21_request.json`; the contract tests are
`tests/test_face_selection_discovery.py`.
