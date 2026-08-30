# Face-selection backend asset

The face-selection law is available as a stable backend capability, not only as
a mathematical helper. Its public boundary is
`categorical_polytope.adjudication.polyhedra.backend`.

The backend accepts a bounded polyhedral system, an unperturbed base objective,
and a perturbation. It executes the law through the exact ambient hierarchy
and presents it in three visible stages:

1. **Localization** - select a simple maximizing vertex and replace the global
   polyhedron by its tangent cone and active constraints.
2. **Selection** - restrict the perturbation to tangent-cone faces, classify
   each face, and select the smallest admissible weighted degree `q_star`.
3. **Scaling** - return `gamma = 1 / (1 - q_star)` and the measured leading
   coefficient when it has stabilized.

Every response carries the analytic warrant for the answer. A computed
exponent is never silently promoted to a licensed theorem conclusion.

## Python integration

```python
from categorical_polytope import analyze_face_selection

response = analyze_face_selection({
    "request_id": "tilted-simplex",
    "system": "([[-1,0],[0,-1],[1,1]], [0,0,1])",
    "base": "-((x0+x1-1)**2 + x0**4)",
    "perturbation": "x0",
    "observed_exponent": 4 / 3,
})

assert response["status"] == "licensed"
assert response["selection"]["weighted_degree"] == 0.25
assert abs(response["scaling"]["response_exponent"] - 4 / 3) < 1e-9
assert response["active_constraints"]["released"] == [0]
assert response["active_constraints"]["binding"] == [2]
assert response["inverse"]["minimal_consistent_faces"] == [[0]]
```

For a long-running process, retain one backend instance so its domain object
can be reused:

```python
from categorical_polytope.adjudication.polyhedra.backend import FaceSelectionBackend

backend = FaceSelectionBackend()
first = backend.handle(first_payload)
batch = backend.handle_many([second_payload, third_payload])
```

`handle` is total at the request boundary. Malformed requests return an
`invalid_request` envelope; one malformed batch item never aborts its siblings.

## JSON process interface

One request or an array of requests can be sent over standard input:

```powershell
@'
{
  "request_id": "tilted-simplex",
  "system": "([[-1,0],[0,-1],[1,1]], [0,0,1])",
  "base": "-((x0+x1-1)**2 + x0**4)",
  "perturbation": "x0"
}
'@ | python -m categorical_polytope.adjudication.polyhedra.backend --pretty
```

The process exits with zero when every item produced either a licensed or an
explicitly unlicensed prediction. Refusals and invalid requests return nonzero.
After installing the package, the same interface is available as
`categorical-face-selection`.

## Request contract

The wire schema remains `face-selection.backend.v1`; the additive portable-law
extension is identified by `asset_version = portable-principle.v7`. Existing
v1 consumers can ignore the new fields without changing behavior.

| Field | Required | Meaning |
| --- | --- | --- |
| `system` | yes | Literal `([[...]], [...])` representation of `Ax <= b` |
| `base` | yes | Safely parsed arithmetic expression in `x0`, `x1`, ... |
| `perturbation` | yes | Safely parsed perturbation expression; `pert` is accepted as an alias |
| `request_id` | no | Caller correlation identifier, at most 128 characters |
| `observed_exponent` | no | Activates the inverse law `q_star = 1 - 1/gamma` |
| `observation_tolerance` | no | Face-matching tolerance; defaults to `0.05` |

Expressions are capped at 20,000 characters and pass through the existing
whitelisted arithmetic parser. Python calls, imports, attribute access, and
other executable syntax are not evaluated.

## Response contract

Every successful analysis contains these top-level fields:

| Field | Backend use |
| --- | --- |
| `status` | `licensed`, `unlicensed`, or `refused` |
| `answered` | Whether a response exponent was produced |
| `licensed` | Whether every measured theorem hypothesis currently holds |
| `capabilities` | Stable names for the asset's supported reasoning functions |
| `principles` | Machine-readable localization, selection, and scaling definitions |
| `localization` | Vertex, tangent-cone face count, binding and released constraints |
| `selection` | `q_star`, winning faces, every examined face and relevance classes |
| `scaling` | Response exponent, power-law form, coefficient and convergence status |
| `active_constraints` | Geometric interpretation of the selected asymptotic channel |
| `mechanism` | Complete ambient-to-face-to-weight-to-exponent causal trace |
| `ambient_hierarchy` | Exact base and perturbation pullbacks, term lineage, face suppressions, weights, selection and exponent consequence |
| `perturbation_analysis` | Per-term relevance, dominance, cancellation and supporting faces |
| `universality_class` | Stable class identifier derived from `q_star` and `gamma` |
| `exact_refinement` | Polynomial edge-transport correction with measured values retained for audit |
| `scope` | Hypothesis measurements, blockers, and refusal reason |
| `inverse` | Optional observed-exponent calibration and consistent faces |
| `audit` | Rule identifier, engine and backend contract version |

The four relevance classes are `relevant`, `critical`, `subleading`, and
`inactive`. Every filtered face includes its reason. This is how the backend
filters irrelevant directions without erasing the evidence that they were
considered.

Polynomial inputs are transported with exact rational arithmetic after the
feasible chart has been reconstructed from the active constraints. Every
top-level perturbation term retains its lineage; cancellations and per-face
geometric suppressions are reported separately. Non-polynomial inputs use the
safe numerical fallback. See [V.20](FORMAL_AMBIENT_FACE_TRANSPORT.md).

## Discovery operation

`operation = "discover"` promotes the compiler into a finite-family discovery
engine. Supply the common `system` and `base`, then either an explicit
`candidates` array or a generated `family` such as:

```json
{
  "operation": "discover",
  "system": "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])",
  "base": "-(x0**2 + x1**4)",
  "family": {
    "kind": "ambient_monomials",
    "max_total_degree": 2
  }
}
```

The response contains screening counts, exact mechanism fingerprints,
universality classes, the discrete exponent-law spectrum, registry-relative
law candidates, and diagnostic candidates. `include_cases = true` attaches
every full backend response; it defaults to false so large screens stay
compact. See [V.21](FORMAL_EXPONENT_DISCOVERY_ENGINE.md).

## Status semantics

### `licensed`

The exponent was produced and all measured hypotheses hold: the selected
vertex is simple, every edge order exceeds one, the base has the required
weighted homogeneity, and the maximizer is isolated to the resolution of the
probe. The winning face degree and all potentially competing face degrees must
also have settled numerically.

### `unlicensed`

The algebraic exponent was produced but at least one analytic hypothesis is
unmet, or a potentially competing face degree remains numerically unsettled.
The number is returned because it is diagnostically valuable; the
`scope.blockers` list prevents a caller from mistaking it for a warranted
conclusion.

### `refused`

The setting lies outside this law: examples include an unbounded system, no
simple maximizing vertex, no positively active face, or a winning degree
outside `(0,1)`. Localization evidence reached before the refusal remains in
the response.

### `invalid_request` and `analysis_error`

These are boundary errors rather than mathematical outcomes. They are returned
as JSON envelopes and never interrupt a batch.

## Forward and inverse power

The forward path answers:

```text
geometry + base + perturbation
    -> feasible asymptotic faces
    -> minimum admissible weight q_star
    -> response exponent gamma
    -> active constraints and leading amplitude
```

The inverse path answers:

```text
observed gamma
    -> effective q_star = 1 - 1/gamma
    -> tangent-cone faces carrying that weight
    -> unique, ambiguous, or geometrically inconsistent channel
```

This makes the law useful both for prediction and for diagnosis. It can predict
how a perturbation will move an optimizer, or infer hidden active geometry from
an observed fractional-power response.

## Relationship to the exact core

`categorical_polytope.face_selection` is the exact, rational, explicitly
evidenced model for supplied edge charts and polynomial monomials. The backend
uses `adjudication.polyhedra.predict`, which derives and measures the same law
from a general inequality system and safe expressions. The two layers serve
different roles:

- exact core: theorem objects, exact weights, cancellation and explicit
  positivity witnesses;
- backend predictor: automatic geometric localization, numerical edge-order
  measurement, constraint inference and corpus-aligned admission.

Both preserve the same invariant: the Newton minimum is taken only after
restriction to feasible tangent-cone faces.

## Portable-principle v2 extension

### Mechanism explanation

`mechanism` makes the theory's internal hierarchy queryable:

```text
ambient monomials
    -> feasible face restrictions
    -> admissible weights
    -> minimum q_star
    -> response exponent gamma
```

It also returns every relevant degree, the next competing degree, the
selection margin, tied minimal channels, filtered-face reasons, active
constraints, and the separation between universal exponent information and
the model-specific leading coefficient.

### Term-level perturbation classification

Top-level additive terms are classified independently as:

- `relevant` - positive on an admissible face with `0 < q < 1`;
- `critical` - `q = 1`, requiring a different balance;
- `subleading` - `q > 1`;
- `inactive` - eliminated by sign, cancellation, constancy, or geometry;
- `unresolved` - a mixed-sign initial form needs additional positivity evidence.

Relevant terms receive a role:

- `dominant` - attains the full perturbation's `q_star`;
- `higher_order` - relevant but asymptotically weaker;
- `cancelled_or_suppressed_in_sum` - would have a lower individual weight, but
  does not control the complete perturbation.

Polynomial terms are transported symbolically from ambient coordinates into
the localized edge chart and classified through the exact face-selection core.
Non-polynomial terms fall back to the measured face-restriction predictor. The
full-sum prediction always remains authoritative because independently
classified terms can cancel.

The same transport is run on the complete perturbation. When every relevant
symbolic face is resolved, its exact `q_star` and `gamma` become the public
universality invariants. The numerical predictor's original values remain in
`selection.measured_weighted_degree` and
`scaling.measured_response_exponent`, while `exact_refinement` records the
correction and its supporting faces. This prevents finite-scale drift from
turning `1/4` into a spurious nearby universality class. If symbolic positivity
is unresolved, no refinement is applied.

### Universality classes

An answered case receives an identifier such as:

```text
face-weight:1/4|response:4/3
```

The identifier captures the universal leading exponent while leaving the
coefficient outside the class. Rescaling a perturbation coefficient therefore
does not change the class; changing the winning admissible weight does.

### Portfolio comparison

Related geometries, constraints, bases, or perturbations can be submitted as a
portfolio:

```python
from categorical_polytope.adjudication.polyhedra.backend import FaceSelectionBackend

comparison = FaceSelectionBackend().handle({
    "operation": "portfolio",
    "request_id": "constraint-study",
    "cases": [baseline_case, rescaled_case, constrained_case],
})
```

The response groups cases into universality classes and compares consecutive
cases. Each transition is one of:

- `same_universality_class`;
- `universality_class_transition`;
- `unresolved_transition`.

Transitions report shifts in `q_star` and `gamma`, along with constraints that
became binding, ceased binding, became released, or ceased being released.
This directly operationalizes the implication that adding or changing
constraints can change the asymptotic universality class.

## Portable-principle v3: exact universality phase diagrams

The portfolio operation compares finitely supplied cases. The v3
`phase_diagram` operation instead resolves an entire continuous
one-parameter family from exact affine weighted-degree laws.

```python
phase = FaceSelectionBackend().handle({
    "operation": "phase_diagram",
    "parameter": "theta",
    "domain": ["0", "3/4"],
    "mechanisms": [
        {
            "id": "face-a",
            "face": ["x"],
            "degree": {"intercept": "1/4", "slope": "1/2"},
        },
        {
            "id": "face-b",
            "face": ["y"],
            "degree": {"intercept": "1/2", "slope": "-1/2"},
        },
    ],
    "assumptions": {
        "fixed_admissibility": True,
        "affine_degrees_verified": True,
        "uniform_local_base_maximality": True,
        "uniform_principal_remainder": True,
        "uniform_global_isolation": True,
    },
})
```

The backend computes every pairwise degree crossing and every relevance wall
`q=0` or `q=1` in exact rational arithmetic. It returns:

- all exact breakpoints;
- the winning face mechanisms in each open chamber;
- tied winners at transition walls;
- activation, deactivation, and universality-class transitions; and
- the exact chamber law `gamma(theta) = 1 / (1 - q_star(theta))`.

### Automatic Newton-weight compilation

Mechanisms do not need to arrive with a precomputed degree. Given fixed base
orders `beta_i` and affine monomial exponent laws `alpha_i(theta)`, the backend
derives

```text
q(theta) = sum_i alpha_i(theta) / beta_i
```

exactly:

```json
{
  "operation": "phase_diagram",
  "parameter": "theta",
  "domain": ["0", "3/4"],
  "base_orders": {"x": 4, "y": 2},
  "mechanisms": [
    {
      "id": "face-a",
      "exponents": {"x": {"intercept": 1, "slope": 2}}
    },
    {
      "id": "face-b",
      "exponents": {"y": {"intercept": 1, "slope": -1}}
    }
  ],
  "evaluate_at": ["0", "1/8", "1/4", "1/2"],
  "assumptions": {
    "fixed_admissibility": true,
    "affine_degrees_verified": true,
    "uniform_local_base_maximality": true,
    "uniform_principal_remainder": true,
    "uniform_global_isolation": true
  }
}
```

Each mechanism must supply either `degree` or `exponents`, never both. Base
orders must exceed one; exponent axes must occur in `base_orders`; and exponent
laws must remain nonnegative on the requested closed domain.

### Exact queries and robustness margins

`evaluate_at` requests selection at up to 256 parameter values. Every result
includes:

- the exact selected degree and response exponent;
- whether the point is in an open chamber, on a candidate wall, or on an
  actual universality transition;
- the winning mechanisms, including ties at a wall;
- the nearest actual transition; and
- the exact parameter distance to a change in universality mechanism.

This distance is an asymptotic robustness margin. A large value means the
current mechanism is stable under parameter error; zero means the system is
exactly on a universality transition.

This is not a grid search: between consecutive returned walls, no unreported
degree-order transition can occur under the declared assumptions. The
multi-parameter generalization replaces the wall points by affine hyperplanes,
forming the universality phase fan of Theorem V.17. See
[`FORMAL_FACE_SELECTION_PHASE_FAN.md`](FORMAL_FACE_SELECTION_PHASE_FAN.md).

The operation remains scope-aware. Without explicit verification of fixed
admissibility and affine degree laws, the exact algebraic diagram is returned
as `unlicensed` with blockers. Parameter-dependent geometry, positivity, and
cancellation must be introduced as additional stratum walls.

## Portable-principle v4: stratified qualified selection

v4 makes parameter-dependent qualification executable. A mechanism may carry
an affine `coefficient` law in addition to its degree or exponent law. The
backend adds every exact `coefficient(parameter)=0` root to the phase
stratification and qualifies the mechanism only where that coefficient is
positive.

```json
{
  "operation": "phase_diagram",
  "parameter": "theta",
  "domain": [0, 1],
  "mechanisms": [
    {
      "id": "emerging-low-face",
      "degree": {"intercept": "1/4"},
      "coefficient": {"intercept": "-1/3", "slope": 1}
    },
    {
      "id": "positive-fallback",
      "degree": {"intercept": "1/2"}
    }
  ],
  "evaluate_at": ["1/4", "1/3", "1/2"],
  "assumptions": {
    "fixed_admissibility": true,
    "coefficient_qualification_verified": true,
    "affine_degrees_verified": true,
    "uniform_local_base_maximality": true,
    "uniform_principal_remainder": true,
    "uniform_global_isolation": true
  }
}
```

Every evaluation now contains a `qualified_selection` certificate. Each
mechanism is classified as `qualified`, `cancelled`, `non_positive`,
`zero_weight`, `critical`, `subleading`, or `geometry_filtered`. The minimum is
taken only after this classification.

The three uniform analytic flags are required before the backend promotes

```text
q_star(parameter) -> gamma(parameter) -> gap = Theta(s**gamma(parameter))
```

to a licensed asymptotic consequence. This separates an exact algebraic phase
calculation from a theorem-qualified scaling statement. See
[`FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md`](FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md).

## Portable-principle v5: constructive mixed-sign positivity

The exact polynomial bridge now resolves a mixed-sign weighted-homogeneous
binomial whenever its two combined monomial signatures are distinct. It varies
one relative-interior face coordinate until the positive-to-negative monomial
ratio exceeds the coefficient ratio, then validates the resulting witness
against both the principal part and initial form.

The response retains this proof object in `exact_refinement`:

```json
{
  "positivity_certificates": [
    {
      "face": [0, 1],
      "provenance": "mixed-sign binomial ratio certificate",
      "coordinates": {"c0": 0.125, "c1": 1.0},
      "initial_form_value": 0.75
    }
  ]
}
```

The precise coordinates depend on coefficient ratios and which differing
exponent coordinate is selected. The contractual facts are that all face
coordinates are positive and `initial_form_value > 0`.

General mixed-sign initial forms with three or more distinct signatures remain
`positivity_unresolved` unless another exact certificate or caller witness is
available. See
[`FORMAL_BINOMIAL_POSITIVITY_WITNESS.md`](FORMAL_BINOMIAL_POSITIVITY_WITNESS.md).
