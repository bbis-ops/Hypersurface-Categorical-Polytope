# Categorical Polytope Lecture

Standalone codification of the "conceptual polytope" lecture: optimization metaphors,
cartesian closed curry, and the failure of coexponential left adjoints to coproduct in `Set`.

Not tied to AegisOps, Soilith, or any other repository.

**Master overview:** [`categorical_polytope/Overview.md`](categorical_polytope/Overview.md) — theorems, proofs sketches, module map, notebook bridge.

**Safety-evaluation capacity (conditional):** [`docs/SAFETY_CAPACITY.md`](docs/SAFETY_CAPACITY.md) — the V-theorems recast as *design warnings* for safety-evaluation methodology (separable scoring, box boundaries, finite-grid coverage, coupling, non-smooth attacks, tolerance thresholds), each a proven conditional over an optimization model of evaluation with its LLM mapping stated as an explicit assumption — plus an assumption-light coverage theorem. For arbitrary `n` samples in `[0,1]^d`, the covering radius obeys `rho >= v_d^(-1/d)n^(-1/d)`; a Cartesian grid has `rho ~ 0.5·sqrt(d)n^(-1/d)`. See the generated [`coverage × escape-search report`](docs/COVERAGE_CORRELATION.md). Module [`eval_escape.py`](categorical_polytope/eval_escape.py). Not a measurement of any deployed system.

**Concrete eval-design standard:** [`docs/EVAL_DESIGN_RECOMMENDATIONS.md`](docs/EVAL_DESIGN_RECOMMENDATIONS.md) — separates pointwise, distributional, geometric worst-case, and Lipschitz-margin claims; covers anisotropic, mixed categorical/continuous, shifted-distribution, scorer-sensitivity, and adaptive designs; includes a locally adjudicated Ox Alpha referee review. Module [`eval_design.py`](categorical_polytope/eval_design.py).

**Distributional coverage theorem:** [`docs/DISTRIBUTIONAL_COVERAGE_AUDIT.md`](docs/DISTRIBUTIONAL_COVERAGE_AUDIT.md) — rigorous IID, bounded deployment-shift, and adaptive conditional-detection bounds, including calibration uncertainty and the limits of support transfer; adversarially reviewed through the free Ox Alpha API and adjudicated locally.

**Runnable six-condition checklist:** [`docs/EVAL_DESIGN_CHECKLIST.md`](docs/EVAL_DESIGN_CHECKLIST.md) — an executable, fail-closed eval card for separability, boundary margin, finite coverage, coupled constraints, non-smooth attacks, and tolerance handling. The included JSON is a worked schema, not real evaluation evidence.

**Registered candidate-space coverage:** [`docs/CANDIDATE_COVERAGE_CERTIFICATE.md`](docs/CANDIDATE_COVERAGE_CERTIFICATE.md) — a separate, versioned normal-form layer for V.7–V.14 with an explicit parameter map, normalized metric, exact Cartesian covering radius, and a stated minimum-failure-width assumption. Registry v1 is an exploratory calibration designed after the open campaign; freezing it enables later confirmatory runs. The open API corpus remains adversarial evidence and is not misreported as a Cartesian cover.

**Adversarial theorem-verification campaign:** [`docs/VERIFICATION_CERTIFICATE.md`](docs/VERIFICATION_CERTIFICATE.md) records the checkpointed V.7–V.14 corpus, honest in-scope denominators, provider token accounting, and every live or resolved numerical counterexample. [`docs/THREE_DAY_API_PLAN.md`](docs/THREE_DAY_API_PLAN.md) defines the active 72-hour high-reasoning Ox Alpha event and its heartbeat/recovery procedure.

**Vertex-localization threshold (V.1–V.14):** [`docs/FORMAL_VERTEX_THRESHOLD.md`](docs/FORMAL_VERTEX_THRESHOLD.md) — the interaction-strength threshold for vertex localization is exactly zero; exact displacement/gap laws; the weighted anisotropic master law `Δ ~ s^{1/(1-q)}`, where `q=Σαᵢ/βᵢ` (reducing to `β/(β-α)` isotropically); the directional law for coupled perturbations; the amplitude ceiling for saturating ridges; and base self-failure (interior/off-corner maxima). Modules: [`vertex_threshold.py`](categorical_polytope/vertex_threshold.py), [`interaction_search.py`](categorical_polytope/interaction_search.py), [`base_search.py`](categorical_polytope/base_search.py). Model proposals (`--api`) are only candidate generators; every result is verified locally with stdlib math.

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
python -m unittest discover -s tests -v   # 13 tests
pip install -e ".[dev]"                     # optional matplotlib, pytest
```

Full reproduction: [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

**Paper assets:** [`docs/PAPER_DRAFT.md`](docs/PAPER_DRAFT.md), [`docs/FORMAL_THEOREMS.md`](docs/FORMAL_THEOREMS.md), [`docs/FORMAL_RESEARCH_ALL.md`](docs/FORMAL_RESEARCH_ALL.md) (H.1–H.10), [`docs/FRIDAY_DISCOVERIES.md`](docs/FRIDAY_DISCOVERIES.md), [`docs/RESEARCH_DIRECTIONS.md`](docs/RESEARCH_DIRECTIONS.md), [`docs/EXPERIMENT_REPORT.md`](docs/EXPERIMENT_REPORT.md), [`docs/BUILD_PDF.md`](docs/BUILD_PDF.md).

Explicit bound: \(C(\theta^\star)-C(\theta_{\mathrm{sep}}) \le \Phi(\varepsilon)\) with \(\Phi(\varepsilon)=\frac{1}{2}\frac{\varepsilon^2}{\lambda_{\min}}\|\theta^\star\|^2\|F_{\mathrm{diag}}\|_F\) — see `formal_bounds.py`.

## Requirements

- Python 3.10+
- Standard library only

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
