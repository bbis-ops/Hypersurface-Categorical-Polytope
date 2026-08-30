# Face-selection codification

This document is the implementation map for the concepts in
`face_selection_noteBrisen15.pdf`. The executable source of record is
`categorical_polytope/face_selection.py`; the formal mathematical statement
remains `FORMAL_FACE_SELECTION.md`.

## The conceptual pipeline

The implementation follows the law in its natural order:

```text
simple vertex and inward edges
    -> edge-coordinate chart Phi
    -> weighted principal part D_0
    -> polynomial perturbation R
    -> restriction to every nonempty tangent-cone face C_S
    -> first non-cancelling initial form W_S and degree q_S
    -> admissibility evidence
    -> q* = min q_S over admissible faces
    -> gamma = 1 / (1 - q*)
```

All nonempty orthant faces are included, including the full cone. This matters
for coupled monomials: a term such as `x*y` can vanish on every proper face and
be active only on the full-dimensional face.

## Concept-to-type map

| Mathematical concept | Code type | Enforced invariant |
| --- | --- | --- |
| Simple vertex and inward edge generators | `EdgeCoordinateChart` | Exactly `n` generators in dimension `n`; full matrix rank |
| Edge map `Phi(c) = v + sum c_i u_i` | `EdgeCoordinateChart.point` | Known axes; finite nonnegative coordinates |
| Term `A_i c_i**beta_i` | `BasePower` | `A_i > 0`, `beta_i > 1` |
| Principal part `D_0` and dilation | `WeightedPrincipalPart` | Same axes as the edge chart; exact rational weights `1/beta_i` |
| Perturbation monomial | `PerturbationMonomial` | Finite coefficient; nonnegative integer powers |
| Polynomial perturbation | `PolynomialPerturbation` | Finite nonempty term sequence; raw terms retained for cancellation analysis |
| Tangent-cone face `C_S` | `Face` (`frozenset[str]`) | Enumerated from chart axes |
| Weighted degree `q_j` | `PerturbationMonomial.weighted_degree` | Exact `Fraction` arithmetic |
| Restricted first layer `W_S` | `InitialForm` | Like terms combined; cancelled layers skipped and recorded |
| Positive relative-interior point | `PositivityWitness` | Strictly positive on `S`, zero off `S`, and positive for both `D_0` and `W_S` |
| Admissibility decision | `FaceAnalysis` / `FaceStatus` | Every inactive, critical, subleading, or unresolved case is explicit |
| Qualified minimum and exponent | `SelectionResult` | Minimum only over `ADMISSIBLE` faces |
| One-parameter balance | `StationaryProfile` | Witnessed `tau`, coefficient, and value for a selected face direction |
| Analytic theorem scope | `LawHypotheses` | Prediction is distinct from theorem licensing |
| Inverse law `q* = 1 - 1/gamma` | `infer_weight_from_exponent` | Requires `gamma > 1` |

## Scope is data, not a comment

Three analytic hypotheses are not recoverable from a finite monomial model:

1. local base maximality;
2. the uniform facewise weighted-principal-part remainder;
3. global isolation of the unperturbed maximizer.

Each is recorded as `VERIFIED`, `ASSUMED`, `UNVERIFIED`, or `VIOLATED`.
`SelectionResult.theorem_licensed` is true only when a face is selected and all
three hypotheses are either verified or deliberately assumed. A value of
`q_star` by itself is therefore an algebraic prediction, not a hidden theorem
claim. The result also remains unlicensed while any face has unresolved
positivity, because such a face could supply a smaller admissible weight.

The structural hypotheses that can be checked locally are enforced during
construction. A linearly dependent edge chart is rejected as nonsimple;
non-polynomial or negative monomial powers are rejected; chart and principal
part axes must agree.

## Face statuses

`FaceStatus` is exhaustive for this mechanism:

| Status | Meaning |
| --- | --- |
| `ADMISSIBLE` | `0 < q_S < 1` and a positive relative-interior witness exists |
| `NO_SURVIVING_MONOMIAL` | `R` restricts identically to zero on the face |
| `CANCELLED_INITIAL_FORM` | Every weighted layer cancels identically |
| `ZERO_WEIGHT` | A constant layer has `q_S = 0`; it cannot drive displacement |
| `NON_POSITIVE` | The initial form is non-positive throughout the positive orthant |
| `POSITIVITY_UNRESOLVED` | A mixed-sign form may be positive, but no valid witness was supplied |
| `CRITICAL` | `q_S = 1`; a different balance is required |
| `SUBLEADING` | `q_S > 1`; inactive for this fractional-power mechanism |

Positive-coefficient initial forms receive the canonical all-ones witness.
Mixed-sign binomials with distinct signatures receive the exact constructive
monomial-ratio certificate of V.19. General mixed-sign forms never receive a
numerical positivity guess: the caller must supply evidence. An invalid witness
raises immediately.

## Cancellation policy

The note says that if a nominal lowest-weight layer cancels identically, the
true face degree must be recomputed. The implementation does this rather than
discarding the entire face:

1. group surviving raw terms by exact weighted degree;
2. combine identical monomials within the lowest layer;
3. if that layer is zero, record its degree in `cancelled_degrees`;
4. continue until the first nonzero layer becomes `W_S`.

If every layer cancels, the face receives `CANCELLED_INITIAL_FORM`.

## Worked example

```python
from categorical_polytope.face_selection import (
    HypothesisStatus,
    LawHypotheses,
    tilted_simplex_problem,
)

hypotheses = LawHypotheses(
    local_base_maximality=HypothesisStatus.VERIFIED,
    uniform_principal_remainder=HypothesisStatus.VERIFIED,
    global_isolation=HypothesisStatus.VERIFIED,
)
problem = tilted_simplex_problem(hypotheses=hypotheses)
result = problem.select()

assert result.q_star.numerator == 1
assert result.q_star.denominator == 4
assert result.response_exponent.numerator == 4
assert result.response_exponent.denominator == 3
assert result.theorem_licensed

active_edge = result.analysis_for({"c1"})
profile = problem.stationary_profile(active_edge, 1e-3)
assert abs(profile.coefficient - 0.4724703937) < 1e-9
```

The face `{c2}` is geometrically feasible but receives
`NO_SURVIVING_MONOMIAL`. Both `{c1}` and `{c1,c2}` inherit degree `1/4`; the
minimal winning channel is `{c1}`. The selected response exponent is exactly
`4/3`.

## Deliberate boundaries

- The module does not infer inward edge rays from an inequality description of
  a polyhedron. It validates a supplied simple chart.
- It does not prove a uniform analytic remainder or global isolation from
  samples. Those facts require external analysis and are represented as
  hypothesis evidence.
- It does not solve positivity of arbitrary multivariate mixed-sign
  polynomials. V.19 settles distinct binomials; larger initial forms still use
  a caller-provided witness for the existential condition the theorem needs.
- `StationaryProfile.coefficient` is the exact leading coefficient along its
  supplied projective direction. Optimizing that coefficient over a
  higher-dimensional winning face is a separate reduced optimization problem.
- Critical terms (`q=1`), nonsimplicial vertices, and principal parts with
  lower-weight cross terms are outside this implementation's theorem slice.

These boundaries keep the codification faithful to the conditional result:
the software automates the finite Newton-face selection without converting
diagnostics or assumptions into stronger mathematical claims.
