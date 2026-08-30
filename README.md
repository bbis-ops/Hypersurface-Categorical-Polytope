# Categorical Polytope Lecture

Standalone codification of the "conceptual polytope" lecture: optimization metaphors,
cartesian closed curry, and the failure of coexponential left adjoints to coproduct in `Set`.

Not tied to Aegis-Ops, www.echovalidum.com, or any other repository.

**Master overview:** [`categorical_polytope/Overview.md`](categorical_polytope/Overview.md) — theorems, proofs sketches, module map, notebook bridge.

**Safety-evaluation capacity (conditional):** [`docs/SAFETY_CAPACITY.md`](docs/SAFETY_CAPACITY.md) — the V-theorems recast as *design warnings* for safety-evaluation methodology (separable scoring, box boundaries, finite-grid coverage, coupling, non-smooth attacks, tolerance thresholds), each a proven conditional over an optimization model of evaluation with its LLM mapping stated as an explicit assumption — plus an assumption-light coverage theorem. For arbitrary `n` samples in `[0,1]^d`, the covering radius obeys `rho >= v_d^(-1/d)n^(-1/d)`; a Cartesian grid has `rho ~ 0.5·sqrt(d)n^(-1/d)`. See the generated [`coverage × escape-search report`](docs/COVERAGE_CORRELATION.md). Module [`eval_escape.py`](categorical_polytope/eval_escape.py). Not a measurement of any deployed system.

**Concrete eval-design standard:** [`docs/EVAL_DESIGN_RECOMMENDATIONS.md`](docs/EVAL_DESIGN_RECOMMENDATIONS.md) — separates pointwise, distributional, geometric worst-case, and Lipschitz-margin claims; covers anisotropic, mixed categorical/continuous, shifted-distribution, scorer-sensitivity, and adaptive designs; includes a locally adjudicated model referee review (backend of record: `stealth/ox-alpha@openrouter.ai`). Module [`eval_design.py`](categorical_polytope/eval_design.py).

**Distributional coverage theorem:** [`docs/DISTRIBUTIONAL_COVERAGE_AUDIT.md`](docs/DISTRIBUTIONAL_COVERAGE_AUDIT.md) — rigorous IID, bounded deployment-shift, and adaptive conditional-detection bounds, including calibration uncertainty and the limits of support transfer; adversarially reviewed through a model API (backend of record: `stealth/ox-alpha@openrouter.ai`) and adjudicated locally.

**Runnable six-condition checklist:** [`docs/EVAL_DESIGN_CHECKLIST.md`](docs/EVAL_DESIGN_CHECKLIST.md) — an executable, fail-closed eval card for separability, boundary margin, finite coverage, coupled constraints, non-smooth attacks, and tolerance handling. The included JSON is a worked schema, not real evaluation evidence.

**Registered candidate-space coverage:** [`docs/CANDIDATE_COVERAGE_CERTIFICATE.md`](docs/CANDIDATE_COVERAGE_CERTIFICATE.md) — a separate, versioned normal-form layer for V.7–V.14 with an explicit parameter map, normalized metric, exact Cartesian covering radius, and a stated minimum-failure-width assumption. Registry v1 is an exploratory calibration designed after the open campaign; freezing it enables later confirmatory runs. The open API corpus remains adversarial evidence and is not misreported as a Cartesian cover.

**Adversarial theorem-verification campaign:** [`docs/VERIFICATION_CERTIFICATE.md`](docs/VERIFICATION_CERTIFICATE.md) records the checkpointed V.7–V.14 corpus, honest in-scope denominators, provider token accounting, and every live or resolved numerical counterexample. [`docs/THREE_DAY_API_PLAN.md`](docs/THREE_DAY_API_PLAN.md) defines the 72-hour high-reasoning verification event (backend of record: `stealth/ox-alpha@openrouter.ai`) and its heartbeat/recovery procedure.

**Vertex-localization threshold (V.1–V.14):** [`docs/FORMAL_VERTEX_THRESHOLD.md`](docs/FORMAL_VERTEX_THRESHOLD.md) — the interaction-strength threshold for vertex localization is exactly zero; exact displacement/gap laws; the weighted anisotropic master law `Δ ~ s^{1/(1-q)}`, where `q=Σαᵢ/βᵢ` (reducing to `β/(β-α)` isotropically); the directional law for coupled perturbations; the amplitude ceiling for saturating ridges; and base self-failure (interior/off-corner maxima). Modules: [`vertex_threshold.py`](categorical_polytope/vertex_threshold.py), [`interaction_search.py`](categorical_polytope/interaction_search.py), [`base_search.py`](categorical_polytope/base_search.py). Model proposals (`--api`) are only candidate generators; every result is verified locally with stdlib math.

**Exact ambient-to-face compiler (V.20):** [`docs/FORMAL_AMBIENT_FACE_TRANSPORT.md`](docs/FORMAL_AMBIENT_FACE_TRANSPORT.md) — reconstructs the feasible edge chart exactly from active constraints, transports ambient base and perturbation polynomials with rational arithmetic, retains top-level term lineage and cancellation, reports geometric suppression on every face, selects the qualified weighted degree, and converts it to the response exponent. It resolves the simplex and sheared ambient-axis counterexamples as one structural family: the ambient control predicts `2`, while feasible-chart transport and measurement give `4/3`. Backend: [`ambient_face_compiler.py`](categorical_polytope/ambient_face_compiler.py) and [`backend.py`](categorical_polytope/adjudication/polyhedra/backend.py).

**Finite exponent-law discovery engine (V.21):** [`docs/FORMAL_EXPONENT_DISCOVERY_ENGINE.md`](docs/FORMAL_EXPONENT_DISCOVERY_ENGINE.md) — screens explicit or generated perturbation families through the exact compiler, partitions them into universality and mechanism classes, emits registry-relative exponent-law candidates, and elevates cancellation, critical boundaries, observed-exponent mismatches, and unresolved mechanisms for diagnosis. Reproducible request: [`experiments/face_selection_discovery_v21_request.json`](experiments/face_selection_discovery_v21_request.json).

## Face-selection backend quick start

The face-selection law is the repository's end-to-end **Newton-tropical
selection principle**. It turns what first appears to be a technical
asymptotic calculation into one portable mechanism:

1. **Localization:** replace the original global polyhedron by the tangent
   cone at the selected simple maximizing vertex.
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

## Four deliverables ("firsts")

| # | Artifact | Location |
|---|----------|----------|
| 1 | **Theorems** (vertex localization, \(\Phi(\varepsilon)\), constructive probe) | [`docs/FORMAL_THEOREMS.md`](docs/FORMAL_THEOREMS.md) |
| 2 | **Algorithms** (vertex search + Fisher-pruned top-\(k\)) | `vertex_probe.py`, `fisher_pruned_search.py` |
| 3 | **Numerical demo** (2- and 3-block toys) | `experiments/run_experiments.py`, [`notebooks/fisher_extremal_demo.ipynb`](notebooks/fisher_extremal_demo.ipynb) |
| 4 | **Short note** (categorical map + abstract) | [`docs/SHORT_NOTE.md`](docs/SHORT_NOTE.md) |
| — | Extended paper outline | [`docs/PAPER_OUTLINE.md`](docs/PAPER_OUTLINE.md) |

```bash
python -m categorical_polytope firsts     # manifest paths
python experiments/run_all.py           # quadratic + nonlinear JSON + figures
python -m pytest -q                     # 524 tests + 24 subtests in the current suite
pip install -e ".[dev]"                 # optional matplotlib, pytest
```

Full reproduction: [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

**Paper assets:** [`docs/PAPER_DRAFT.md`](docs/PAPER_DRAFT.md), [`docs/FORMAL_THEOREMS.md`](docs/FORMAL_THEOREMS.md), [`docs/FORMAL_RESEARCH_ALL.md`](docs/FORMAL_RESEARCH_ALL.md) (H.1–H.10), [`docs/FRIDAY_DISCOVERIES.md`](docs/FRIDAY_DISCOVERIES.md), [`docs/RESEARCH_DIRECTIONS.md`](docs/RESEARCH_DIRECTIONS.md), [`docs/EXPERIMENT_REPORT.md`](docs/EXPERIMENT_REPORT.md), [`docs/BUILD_PDF.md`](docs/BUILD_PDF.md).

Explicit bound: \(C(\theta^\star)-C(\theta_{\mathrm{sep}}) \le \Phi(\varepsilon)\) with \(\Phi(\varepsilon)=\frac{1}{2}\frac{\varepsilon^2}{\lambda_{\min}}\|\theta^\star\|^2\|F_{\mathrm{diag}}\|_F\) — see `formal_bounds.py`.

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
| `face_selection.py` | Exact face restriction, admissibility, weighted selection, and scaling |
| `ambient_face_compiler.py` | Exact ambient-to-edge polynomial transport and term lineage |
| `face_selection_phase.py` | Parametric Newton-weight chambers, walls, and transitions |
| `adjudication/polyhedra/backend.py` | Stable Python/JSON backend, discovery, portfolio, and audit contracts |
| `__main__.py` | Demo CLI |

## Theory (encoded)

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
