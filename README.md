# Newton–Tropical Face Selection at Simple Polyhedral Vertices

This repository's central result is a portable **face-selection law for
singular asymptotics at a simple polyhedral vertex**. It turns local geometry,
weighted polynomial order, and active constraints into a finite prediction of
the winning face and response exponent. The earlier categorical-polytope
lecture is the historical origin of the project; the Newton–tropical
selection principle is now its mathematical center of gravity.

The law is developed in the orthant theorem
[`FORMAL_NEWTON_TROPICAL.md`](docs/FORMAL_NEWTON_TROPICAL.md), the polyhedral
transport and selection theorem
[`FORMAL_FACE_SELECTION.md`](docs/FORMAL_FACE_SELECTION.md), and the
outcome-independent admissibility refinement
[`FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md`](docs/FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md).
The executable contract is documented in
[`FACE_SELECTION_BACKEND.md`](docs/FACE_SELECTION_BACKEND.md).

## Main theorem

Let `v` be a simple maximizing vertex of a full-dimensional polyhedron, and
let its inward edge chart be

```text
Phi(c) = v + sum_i c_i u_i,    c_i >= 0.
```

Suppose the localized base loss has weighted principal part
`D_0(c) = sum_i A_i c_i^beta_i`, with `A_i > 0` and `beta_i > 1`, and the
localized perturbation `R(c)` is polynomial. On every tangent-cone face
`C_S`, restrict `R`, combine equal monomials, discard cancelled layers, and
let `q_S` be the first surviving weighted degree. Qualify the face using only
`(D_0, R, C_S)`: require `0 < q_S < 1`, a nonzero initial form, and a
relative-interior point where both the base cost and leading perturbation gain
are positive.

Then, under the stated uniform-remainder and global-isolation hypotheses,

```text
q*    = min { q_S : C_S is admissible }
gamma = 1 / (1 - q*)
M(s) - F(v) - s G(v) = Theta(s^gamma)    as s -> 0+.
```

The minimizing face predicts which constraints are released; the remaining
constraints stay asymptotically active. The exponent depends on the winning
weighted degree, while the sharp leading coefficient is determined by the
reduced optimization problem on that face. Because admissibility is fixed
before faces are compared and never refers to an observed exponent, this is a
selection theorem rather than a post-hoc fit.

## The three-layer selection principle

The theorem and backend share one end-to-end architecture:

1. **Localization:** replace the original global polyhedron by the tangent
   cone at a simple base-maximizing vertex fixed independently of the
   perturbed optimizer.
2. **Selection:** transport the perturbation into the feasible edge chart,
   restrict it to cone faces, and rank admissible faces by exact weighted
   degree.
3. **Scaling:** convert the winning degree into the response exponent
   `gamma = 1 / (1 - q_star)`.

This single hierarchy:

- organizes the theory around one local geometric object;
- explains the mechanism rather than merely fitting an exponent;
- predicts the exponent before numerical measurement;
- filters irrelevant directions without deleting their audit trail;
- classifies perturbations as relevant, critical, subleading, or inactive;
- reveals which constraints remain binding and which are released;
- identifies cancellation and geometric suppression independently;
- groups perturbations into universality classes; and
- generalizes from one example to finite families, portfolios, and parametric
  phase diagrams.

Within its stated hypotheses, this is a theorem-backed selection law. Across
the repository's checked examples—including the two ambient-axis
counterexamples that motivated exact feasible-chart transport—the hierarchy
has produced the correct mechanism and exponent. Unverified analytic
hypotheses remain visible in the response, so successful calculation is never
silently presented as a licensed theorem conclusion.

The implementation lives in the
[`categorical_polytope`](categorical_polytope/) package and is exposed as a
reusable backend with Python and JSON process interfaces. Its complete data
flow is:

```text
ambient polynomial -> feasible edge chart -> tangent-cone faces
                   -> Newton weights -> qualified q* -> gamma = 1/(1-q*)
```

### The missing geometric step: from an orthant law to a polyhedral law

The orthant Newton–tropical theorem answers a powerful but conditional
question: once feasible coordinates `c_i >= 0`, base orders `beta_i`, and a
perturbation polynomial are already given, which weighted monomial controls
the balance? On its own, that theorem does not say how an arbitrary ambient
polyhedron produces those coordinates, which coordinate subspaces are actual
feasible faces, or whether a formal leading term can generate a positive
improvement on such a face.

The face-selection note supplies exactly that missing geometry. At a simple
vertex, the inward edge generators are linearly independent, so the edge map

```text
Phi(c) = v + sum_i c_i u_i,    c_i >= 0
```

is an isomorphism from the nonnegative orthant onto the tangent cone. It
transports the ambient base and perturbation into intrinsic feasible
coordinates and identifies every cone face with a subset of released edge
coordinates. The orthant balance law can then be applied face by face without
changing its mechanism. In compact form:

```text
orthant balance law
  + exact tangent-cone transport
  + outcome-independent face qualification
  = portable face-selection law at a simple polyhedral vertex
```

This is also what makes the principle **non-circular**. A face is admissible
using only the localized data `(D_0, R)` and the candidate face `C_S`: its
degree must be finite with `0 < q_S < 1`, its initial form must not vanish
identically, and it must admit a relative-interior point where both the base
cost and leading perturbation gain are positive. None of these tests refers
to the eventual response exponent, the observed optimizer path, or a
comparison with another face.

The prohibited circular workflow would be:

```text
observe a numerical optimizer path -> choose its face -> compute its exponent
```

The implemented predictive workflow reverses that logic:

```text
fix the base vertex -> construct its tangent cone -> enumerate every face
-> transport and restrict exactly -> qualify each face independently
-> minimize q_S -> predict the active face and exponent -> test numerically
```

Thus the note is not another calculation layered on top of the orthant
formula. It is the geometric compiler that turns that formula into a finite,
portable, auditable selection principle for any simple polyhedral vertex
satisfying the stated local and global analytic hypotheses. Simplicity is
essential to this formulation: non-simple vertices require an additional
cone decomposition or a separate extension theorem and are not silently
claimed here.

### The decisive insight: feasibility comes before degree

Ambient coordinate axes are not intrinsic to a polyhedron. At a tilted
vertex, an ambient axis may fail to point into the feasible set at all. Reading
an order along that axis can therefore manufacture a mechanism that no
admissible displacement realizes.

The compiler instead solves, exactly,

```text
A_S v = b_S               selected simple vertex
A_S u_i = -e_i            inward edge generators
x = v + sum_i c_i u_i     feasible local chart, c_i >= 0
```

and only then pulls the base and perturbation back to the edge variables
`c_i`. Positive rescaling of an edge changes coefficients, but not Newton
support, weights, winning faces, or the response exponent. That is the
coordinate-invariant content of the law.

The two canonical ambient counterexamples make the distinction concrete. At
the simplex and sheared vertices, exact transport gives the same localized
problem:

```text
D_0(c) = c0^4 + c1^2      -> weights (1/4, 1/2)
W(c)   = c0               -> q* = 1/4
gamma  = 1/(1 - 1/4)      -> 4/3
```

An ambient-axis calculation predicts `2`; feasible-chart transport and direct
measurement give `4/3`. These are not unrelated numerical exceptions. They
identify one structural obstruction: **ambient degree is not authoritative
until it has been transported through the tangent geometry**.

### What the minimum over faces means

`q_star` is not a sum of every directional degree and it is not simply the
lowest monomial degree in the unreduced expression. For each tangent-cone
face, the backend:

1. removes monomials that vanish on that face;
2. combines like signatures exactly, exposing cancellation;
3. takes the first non-cancelling weighted layer;
4. requires `0 < q_F < 1` and a positive relative-interior witness; and
5. minimizes `q_F` over the faces that remain qualified.

This explains several otherwise surprising facts:

- a coefficient can change the leading amplitude without changing the
  exponent class;
- a coefficient crossing zero can remove a mechanism and expose a new
  exponent without any degree laws crossing;
- a high-order ambient term may become low-order after feasible transport;
- a seemingly dominant term may be inactive because it is geometrically
  suppressed or cancels exactly; and
- a larger face may inherit the same degree from a smaller face without
  representing a distinct released-constraint mechanism.

### From one exponent to a phase structure

For a parameterized family with affine mechanism degrees
`q_j(t) = a_j + b_j*t`, selection is the lower envelope of the qualified
degrees. Every possible transition lies on a finite exact wall:

```text
q_i(t) = q_j(t)    mechanisms exchange dominance
q_i(t) = 0         zero-weight boundary
q_i(t) = 1         critical boundary
c_i(t) = 0         qualification/cancellation boundary
```

Between walls, the winning face and mechanism are constant and
`gamma(t) = 1/(1-q_star(t))` is exact. The backend therefore returns a phase
fan and robustness margin rather than a grid of sampled regimes. A narrow
chamber cannot be skipped.

### How to read a result

| Question | Backend evidence |
|---|---|
| What caused the response? | Winning face, initial form, and ambient-term lineage |
| Why this exponent? | Base orders, Newton weights, `q_star`, and the scaling map |
| Which constraints move? | Released constraints; the remainder stay binding |
| Which terms were ignored? | Per-face suppression, cancellation, criticality, or subleading status |
| Is another perturbation equivalent? | Universality and mechanism class identifiers |
| How close is a mechanism change? | Exact phase wall and robustness margin |
| What does an observed exponent imply? | Inverse weight `q = 1 - 1/gamma` and consistent feasible faces |
| Is the conclusion a theorem? | Named hypothesis evidence and explicit license blockers |

The distinction between a calculation and a theorem is deliberate. Exact
finite algebra determines transport, qualification, selection, and scaling;
local maximality, uniform remainder control, and global isolation are analytic
hypotheses. If those hypotheses are not independently established, the backend
returns the calculation as `unlicensed` rather than weakening the scope after
seeing the result.

```python
from categorical_polytope import analyze_face_selection

result = analyze_face_selection({
    "request_id": "tilted-simplex",
    "system": "([[-1,0],[0,-1],[1,1]], [0,0,1])",
    "base": "-((x0+x1-1)**2 + x0**4)",
    "perturbation": "x0",
    "observed_exponent": 4 / 3,
})

assert result["selection"]["weighted_degree"] == 0.25
assert abs(result["scaling"]["response_exponent"] - 4 / 3) < 1e-9
```

Run the same capability as a JSON process:

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --pretty \
  < experiments/face_selection_ambient_v20_request.json
```

After `pip install -e .`, the process entry point is also available as
`categorical-face-selection`. Beyond a single analysis, the backend supports
finite-family `discover`, cross-case `portfolio`, and parametric
`phase_diagram` operations. See [`docs/FACE_SELECTION_BACKEND.md`](docs/FACE_SELECTION_BACKEND.md)
for the complete request and response contracts.

Correctness boundaries are explicit:

- polynomial transport, cancellation, Newton weights, and response exponents
  retain exact rational arithmetic;
- boundedness uses an exhaustive recession-cone check for the supported
  dimensions rather than sampled directions;
- the linear-programming control admits affine objectives only;
- malformed batch items fail independently at a total JSON boundary;
- API-generated candidates remain untrusted and are locally adjudicated;
- shared campaign pacing uses locked, cross-process request reservations.

## Completed mathematical and computational contributions

| Contribution | What is established | Primary artifact |
|---|---|---|
| **Vertex localization and weighted scaling (V.1–V.14)** | Zero interaction threshold, displacement and gap laws, anisotropic balance `q = sum_i alpha_i/beta_i`, saturation ceilings, and explicit failure regimes | [`FORMAL_VERTEX_THRESHOLD.md`](docs/FORMAL_VERTEX_THRESHOLD.md) |
| **Orthant Newton–tropical law (V.15)** | Weighted monomial degrees determine the finite candidate set and convert by `q -> 1/(1-q)` into response exponents | [`FORMAL_NEWTON_TROPICAL.md`](docs/FORMAL_NEWTON_TROPICAL.md) |
| **Qualified face-selection law (V.16)** | Tangent-cone localization, face restriction, non-circular admissibility, minimum admissible degree, active-constraint prediction, and sharp reduced-face asymptotics | [`FORMAL_FACE_SELECTION.md`](docs/FORMAL_FACE_SELECTION.md) and [`FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md`](docs/FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md) |
| **Exact ambient-to-face compiler (V.20)** | Active constraints are converted to an exact edge chart; ambient polynomials are transported with rational arithmetic; cancellation, lineage, and geometric suppression remain auditable | [`FORMAL_AMBIENT_FACE_TRANSPORT.md`](docs/FORMAL_AMBIENT_FACE_TRANSPORT.md) |
| **Phase fan and discovery engine (V.21)** | Finite perturbation families are partitioned into exponent and mechanism classes; exact walls locate dominance, criticality, and cancellation transitions | [`FORMAL_FACE_SELECTION_PHASE_FAN.md`](docs/FORMAL_FACE_SELECTION_PHASE_FAN.md) and [`FORMAL_EXPONENT_DISCOVERY_ENGINE.md`](docs/FORMAL_EXPONENT_DISCOVERY_ENGINE.md) |
| **First-class backend** | Python and JSON interfaces expose analysis, discovery, portfolios, phase diagrams, evidence, and fail-closed theorem licensing | [`FACE_SELECTION_BACKEND.md`](docs/FACE_SELECTION_BACKEND.md) |

The progression is deliberate: V.15 gives the weighted law on an orthant;
V.16 supplies the missing geometric and non-circular selection step; V.20
compiles ambient problems into that theorem exactly; and V.21 applies the
compiler across families to discover and classify new exponent laws.

```bash
python experiments/run_all.py            # quadratic + nonlinear JSON + figures
python -m pytest -q                       # 524 tests + 24 subtests in the current suite
pip install -e ".[dev]"                  # optional matplotlib, pytest
```

Full reproduction: [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Applications & conditional design warnings

The evaluation material is a downstream application of the optimization
theorems, not the repository's foundational claim. It translates geometric
warnings about boundaries, coupling, finite coverage, non-smooth attacks, and
tolerances into evaluation-design checks. These documents do **not** report
measurements of a deployed system.

- [`SAFETY_CAPACITY.md`](docs/SAFETY_CAPACITY.md) gives the conditional map
  from the V-theorems to safety-evaluation design warnings.
- [`EVAL_DESIGN_RECOMMENDATIONS.md`](docs/EVAL_DESIGN_RECOMMENDATIONS.md) and
  [`EVAL_DESIGN_CHECKLIST.md`](docs/EVAL_DESIGN_CHECKLIST.md) separate
  pointwise, distributional, geometric worst-case, and Lipschitz-margin
  claims and provide a fail-closed six-condition evaluation card.
- [`DISTRIBUTIONAL_COVERAGE_AUDIT.md`](docs/DISTRIBUTIONAL_COVERAGE_AUDIT.md)
  proves IID, bounded-shift, and adaptive conditional-detection bounds while
  keeping calibration and support-transfer assumptions explicit.
- [`CANDIDATE_COVERAGE_CERTIFICATE.md`](docs/CANDIDATE_COVERAGE_CERTIFICATE.md)
  records the versioned candidate-space normal form and exact Cartesian
  covering radius; [`COVERAGE_CORRELATION.md`](docs/COVERAGE_CORRELATION.md)
  reports the coverage × escape-search comparison.
- [`VERIFICATION_CERTIFICATE.md`](docs/VERIFICATION_CERTIFICATE.md) records
  the checkpointed adversarial theorem-verification corpus, its honest
  denominators, and resolved or live numerical counterexamples.

## Historical origin: the categorical-polytope lecture

The project began with an optimization metaphor for cartesian closure, the
failure of a coexponential left adjoint to coproduct in `Set`, and neighboring
categorical constructions. That material remains useful context, but it is no
longer the README's organizing result. See
[`SHORT_NOTE.md`](docs/SHORT_NOTE.md),
[`PAPER_OUTLINE.md`](docs/PAPER_OUTLINE.md), and the
[`master overview`](categorical_polytope/Overview.md).

The original coexponential obstruction motivated the search for an
operational substitute; the face-selection law is that substitute in
geometric form.

The earlier vertex, Fisher-factorization, and constructive-search results are
preserved in [`FORMAL_THEOREMS.md`](docs/FORMAL_THEOREMS.md),
[`PAPER_DRAFT.md`](docs/PAPER_DRAFT.md), and the legacy manifest returned by
`python -m categorical_polytope firsts`. In particular,
`formal_bounds.py` encodes the explicit separability bound
`C(theta*) - C(theta_sep) <= Phi(epsilon)`.

## Requirements

- Python 3.10+
- Standard library only

### Optional: model-backed candidate generation

Every theorem, screen, and verdict runs offline on the standard library.
The `--api` flags are candidate *generators* only: proposals are untrusted
data, parsed under an AST whitelist and adjudicated locally, so the results
do not depend on which model produced them.

Any OpenAI-compatible endpoint works. Set one of `LOOP_API_KEY`,
`OPENROUTER_API_KEY`, or `OPENAI_API_KEY` (see `scripts/set_api_key.ps1` /
`.sh`), then pick a model with `--model` / `--base-url`, or a named preset
with `--preset` / `LOOP_API_PRESET` (`openai`, `openrouter`, `nemotron`, `nemotron-super`).

A key alone is not enough: with no model chosen the default id is a paid one,
so verification fails with `402 Payment Required` even when the key is good.
Name a model you can reach —

```bash
python experiments/run_loop_closure.py --check --preset nemotron
```

Presets are listed in `loop_closure.PRESETS` and documented in
[`docs/RESEARCH_DIRECTIONS.md`](docs/RESEARCH_DIRECTIONS.md).

## Run

```bash
cd categorical_polytope
python -m categorical_polytope
```

## Layout

| Module | Role |
|--------|------|
| `face_selection.py` | Exact face restriction, admissibility, weighted selection, and scaling |
| `ambient_face_compiler.py` | Exact ambient-to-edge polynomial transport and term lineage |
| `face_selection_phase.py` | Parametric Newton-weight chambers, walls, and transitions |
| `adjudication/polyhedra/backend.py` | Stable Python/JSON backend, discovery, portfolio, and audit contracts |
| `vertex_threshold.py` | Vertex localization, weighted displacement, and gap laws |
| `interaction_search.py` | Locally verified perturbation and interaction screening |
| `base_search.py` | Base self-failure and off-corner maximizer search |
| `set_category.py` | Finite `Set`: hom cardinalities, coexponential obstruction |
| `cartesian_closed.py` | Product–exponential (curry) adjunction witness |
| `conceptual_polytope.py` | Bounded diagram scores, extremal maximizers, coproduct blocks |
| `neighboring_vertices.py` | Closed monoidal, Chu/Dialectica, continuations, coalgebra/comonad |
| `hypersurface_box.py` | Box \(H\): \(C(b,k)\), quasiconvex \(r(\lambda,\sigma)\), \(\theta_{\max}\in\mathrm{ext}(H)\) |
| `adversarial_probe.py` | Vertex localization + componentwise probe under cross-information bound |
| `fisher_factorization.py` | Fisher off-diagonal leakage; when separable optimization is nearly optimal |
| `bridge_fisher_adversarial.py` | Map cross-information proxy to Fisher coupling |
| `extremal_substitute.py` | Operational substitute when coexponential is absent; limits |
| `vertex_probe.py` | Constructive near-optimal probe: search only ext(H) with certificate |
| `decomposition_stability.py` | Coproduct robustness to independence violations; design rules |
| `formal_bounds.py` | \(\epsilon_0\), \(\Phi(\varepsilon)\) theorem constants |
| `fisher_pruned_search.py` | Theorem 3: top-\(k\) Fisher-pruned vertex search |
| `firsts.py` | Deliverables manifest + run experiments |
| `nonlinear_objective.py` | Non-quadratic \(C\), empirical Fisher, vertex vs separable |
| `__main__.py` | Demo CLI |

## Earlier categorical and optimization theory (encoded)

1. **CCC corner** — \( \mathrm{Hom}(A \times X, Y) \cong \mathrm{Hom}(X, Y^A) \) as an explicit bijection on finite sets.
2. **Vanishing corner** — No object \(C\) with \(|\mathrm{Hom}(C,Z)| = |\mathrm{Hom}(Y, A \sqcup Z)|\) for all \(Z\) unless the functor is degenerate (cardinality obstruction).
3. **Polytope metaphor** — Separate monotone objectives in composition vs naturality; quasiconvex adjunction directions; global max at vertices \(\mathrm{ext}(\mathcal{P})\); coproduct blocks with bounded cross-naturality.
4. **Neighboring vertices** — When coexponential ⊣ coproduct is empty in `Set`, walk to closed monoidal, Chu/Dialectica, continuations, or coalgebra/comonad corners (dual-flavored structure without set-theoretic co-curry).

## Neighboring vertices (from the lecture)

| Vertex | What you get instead of coexponential |
|--------|----------------------------------------|
| Closed monoidal (\(\otimes \dashv [-,=]\)) | Internal hom for tensor, not cartesian product |
| Dialectica / Chu | Linear or relational duals, not set-theoretic co-curry |
| Continuations | Right adjoints to sum-like types encoded differently |
| Coalgebra / comonad | Final coalgebras, not left adjoint to \(\sqcup\) |

Reversing arrows is a **strategy**, not a guarantee of representability on the dual side.

5. **Box \(H\)** — \(C\) separately increasing in \(b,k\); \(r\) quasiconvex-decreasing in \(\sigma\), increasing in \(\lambda\); \(\theta_{\max}\in\mathrm{ext}(H)\); for a box, \(\theta_{\max}=(\lambda_{\max},\sigma_{\min},k_{\max},B_{\max})\).
6. **Adversarial probe** — Bounded cross-information between blocks \(\Rightarrow\) worst-case \(\theta\) at block vertices; explicit componentwise probe.

```python
from categorical_polytope import default_hypersurface_problem

problem = default_hypersurface_problem(cross_info_bound=0.25)
probe = problem.build_componentwise_probe()
worst = problem.localize_worst_case()
print(probe.to_theta(), worst.to_theta())
```

7. **Fisher factorization** — Off-diagonal Fisher blocks quantify leakage; small \(\varepsilon = \|F_{\mathrm{off}}\|_F/\|F_{\mathrm{diag}}\|_F\) implies separable per-block optimization is nearly optimal.

```python
from categorical_polytope import build_block_fisher, BlockLayout, QuadraticJointObjective

layout = BlockLayout(names=("A", "B"), sizes=(2, 2))
fisher = build_block_fisher(layout, off_diag_coupling=0.05)
obj = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0))
print(obj.factorization_analysis())
```

8. **Vertex probe algorithm** — Constructive near-optimal probe by enumerating `ext(H)` only.

```python
from categorical_polytope import VertexProbeAlgorithm

probe = VertexProbeAlgorithm(cross_info_bound=0.25).find_near_optimal_probe()
print(probe.theta, probe.certificate.nearly_optimal)
```

9. **Decomposition stability** — Robustness of coproduct splits when Fisher off-diagonals are small.

```python
from categorical_polytope import build_block_fisher, BlockLayout, assess_decomposition

fisher = build_block_fisher(BlockLayout(("A", "B"), (2, 2)), off_diag_coupling=0.08)
report = assess_decomposition(fisher, linear=(1.0, 0.5, 2.0, 3.0))
print(report.strategy, report.coproduct_robust, report.bounds)
```

10. **Non-quadratic \(C\)** — interaction terms beyond the quadratic proxy; local empirical Fisher.

```python
from categorical_polytope import NonlinearStudy

report = NonlinearStudy().analyze(strength=0.15, interaction="bilinear")
print(report.gap, report.leakage.epsilon, report.localization_at_vertex)
python experiments/nonlinear_experiments.py
```
