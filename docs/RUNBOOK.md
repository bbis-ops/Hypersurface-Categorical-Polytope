# Runbook — reproduce the portable selection principle

Reproduce the repository's Newton–tropical results from saved inputs, inspect
their algebra and scope decisions, and retain the evidence for another reader.
The main route covers exact transport, positivity, phase transitions,
finite-family discovery, curved reduction, finite-scale accuracy, and the
activation/contact expansion. The original categorical demos have their own
[historical reproduction route](#historical-demos-and-paper-materials).

[**Run the evidence suite →**](#one-command-reproduction) · [Choose a result](#choose-a-result-to-reproduce) · [Read a certificate](#how-to-read-the-evidence) · [Run the tests](#regression-tests)

| 01 · Prepare | 02 · Reproduce | 03 · Inspect | 04 · Extend |
| :--- | :--- | :--- | :--- |
| [Environment](#environment-and-working-directory) | [Canonical results](#choose-a-result-to-reproduce) | [Evidence and scope](#how-to-read-the-evidence) | [Your own perturbations](#reproduce-your-own-finite-family) |

---

## Environment and working directory

Run commands from the **repository root**, the directory containing
`pyproject.toml`, `experiments/`, `tests/`, and the inner
`categorical_polytope/` package. Do not run them from that inner package folder.

```bash
python --version
python -c "import categorical_polytope; print(categorical_polytope.__file__)"
```

Python **3.10 or newer** is required. The canonical evidence suite uses the
standard library and the local package. It requires no API credentials,
network service, model, plotting library, or editable installation.

| Optional purpose | Install |
| :--- | :--- |
| Run the complete pytest suite | `python -m pip install pytest` |
| Editable package, tests, and historical figures | `python -m pip install -e ".[dev]"` |
| Historical notebook | `python -m pip install -e ".[notebook]"` |

Commands below work in PowerShell and POSIX shells as written. Backend
commands use `--input` rather than shell-specific input redirection.

## One-command reproduction

```bash
python experiments/reproduce_principle.py
```

The [reproduction runner](../experiments/reproduce_principle.py) executes
**13 evidence cases**. It sends requests through the public JSON process,
checks expected mathematical invariants and statuses, and runs the two exact
algebra scripts. An expected refusal is checked as carefully as a successful
prediction. Each case prints `PASS` or `FAIL`; the final line reports the
number passed. Exit zero means every selected reproduction matched its checks.

Each invocation creates a fresh directory under `tmp/principle-reproduction/`:

| Artifact | What it records |
| :--- | :--- |
| `manifest.json` | Overall result, selected cases, Python/platform, Git revision and working-tree state, source SHA-256 hashes, commands, timings, and checks |
| `<case>/request.json` | Actual backend request, including any derived control input |
| `<case>/response.json` | Full backend JSON, including hypothesis evidence and numerical diagnostics |
| `<case>/output.txt` | An algebra script's output instead of a backend response |
| `<case>/stderr.txt` | Process diagnostics; empty on a quiet run |
| `<case>/checks.json` | Expected and observed results and the case's pass/fail decision |

The path is printed at startup. Outputs are ignored by Git; existing experiment
reports and campaign checkpoints are not regenerated. A custom output
directory must be new:

```bash
python experiments/reproduce_principle.py --output-dir tmp/reviewer-evidence
```

Run one result or several together:

```bash
python experiments/reproduce_principle.py --only transport discovery finite-scale
```

The runner records failures and continues. An interrupted run leaves a
manifest with `status: "running"` and completed case records; it is not a
successful reproduction. Each child process has a 120-second limit. The two
algebra scripts run with Python assertions enabled.

```mermaid
flowchart LR
  input("Saved request<br/>or derived control")
  run("Public backend<br/>or exact algebra script")
  inspect("Check expected values<br/>and scope decisions")
  record("Preserve full evidence<br/>and source hashes")
  input --> run --> inspect --> record
  classDef source fill:#102734,stroke:#8199a4,color:#edf2f4
  classDef operation fill:#173b46,stroke:#87b8bd,color:#edf2f4
  classDef result fill:#283b3b,stroke:#d9b77b,stroke-width:2px,color:#fff1d6
  class input source
  class run,inspect operation
  class record result
  linkStyle default stroke:#9b875f,stroke-width:2px
```

## Choose a result to reproduce

Use the case name with `--only`. The sections below give direct commands and
the evidence to inspect when working without the runner.

| Case | Result | Expected observation |
| :--- | :--- | :--- |
| `transport` | [V.20 · two tilted geometries](#exact-feasible-chart-transport--v20) | Different charts, the same class: $q_\ast=1/4$, $\gamma=4/3$ |
| `binomial` | [V.19 · signed positivity](#constructive-binomial-positivity--v19) | Positive relative-interior witness; $\gamma=2$ |
| `phase` | [V.17 · degree crossing](#exact-phase-and-qualification-walls--v17v18) | Wall at $\theta=1/4$, tied exponent $8/5$ |
| `qualification` | [V.18 · coefficient cancellation](#exact-phase-and-qualification-walls--v17v18) | Wall at $\theta=1/3$; exponent changes from $2$ to $4/3$ after the wall |
| `discovery` | [V.21 · finite exponent spectrum](#finite-family-exponent-discovery--v21) | Six candidates, three classes, one critical term, one cancellation diagnostic |
| `curved` | [V.22 · exact elimination](#curved-channel-resolution-and-cancellation--v22) | $\gamma=3$, sharp coefficient $1/432$ |
| `finite-scale` | [Accuracy near cancellation](#finite-scale-accuracy-is-a-separate-question) | `outside_tolerance` at $s=10^{-9}$; `within_tolerance` at $s=10^{-12}$ |
| `selector-limit` | [Signed higher-layer control](#curved-channel-resolution-and-cancellation--v22) | Original selector refuses the curved example and names the unresolved face |
| `curved-cancellation` | [A new reduced leading order](#curved-channel-resolution-and-cancellation--v22) | $\gamma=6$, sharp coefficient $3125/46656$ |
| `inverse` | [Observation-to-face diagnosis](#inverse-diagnosis-and-missing-hypotheses) | $4/3$ matches the simplex channel; $2$ matches no feasible face |
| `phase-unlicensed` | [Missing analytic warrant](#inverse-diagnosis-and-missing-hypotheses) | The wall is computed, but the result is `unlicensed` |
| `activation` | [Activation/contact expansion](#activation-and-contact-with-the-critical-curve) | Exact coexistence, zero value, and stationarity through degree 20 |
| `corrected-note` | [Corrected categorical note](#corrected-categorical-note) | Rational counterexamples, valid residual bounds, and scaling checks pass |

---

## Exact feasible-chart transport — V.20

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/face_selection_ambient_v20_request.json --pretty
```

The [saved portfolio](../experiments/face_selection_ambient_v20_request.json)
contains the simplex and sheared-simplex counterexamples. In both, exact
transport gives the base loss $c_0^4+c_1^2$ and perturbation $c_0$. Thus

$$
(w_0,w_1)=\left(\frac14,\frac12\right),\qquad
q_\ast=\frac14,\qquad \gamma=\frac43.
$$

Inspect each element of `cases`:

- `ambient_hierarchy.weight_layer.exact_pullback_axial_orders` is
  `{"c0": 4, "c1": 2}`.
- `universality_class.id` is `face-weight:1/4|response:4/3`.
- `selection.winning_faces` is `[[0]]`.

The transition is `same_universality_class`, while
`ambient_transport_change.changed` is `true`. This demonstrates transport
across two different feasible charts. The historically incorrect ambient-axis
prediction was $2$; it is not the exponent returned by this request.

[Principle and calculations →](FORMAL_AMBIENT_FACE_TRANSPORT.md) · [Regression tests →](../tests/test_ambient_face_compiler.py)

## Constructive binomial positivity — V.19

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/face_selection_binomial_v19_request.json --pretty
```

For loss $x_0^2+x_1^4$ and perturbation $-2x_0+x_1^2$, inspect
`exact_refinement.positivity_certificates`. The full-face certificate uses
$(c_0,c_1)=(1/8,1)$: both coordinates are positive, and the initial form has
value $3/4$. Its provenance is `mixed-sign binomial ratio certificate`.
The selected class is `face-weight:1/2|response:2`.

This point certifies positivity of the homogeneous initial form. It is not
being asserted to be the perturbed optimizer.

[Constructive positivity theorem →](FORMAL_BINOMIAL_POSITIVITY_WITNESS.md) · [Saved request →](../experiments/face_selection_binomial_v19_request.json)

## Exact phase and qualification walls — V.17–V.18

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/face_selection_phase_v17_request.json --pretty
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/face_selection_qualified_v18_request.json --pretty
```

The [V.17 request](../experiments/face_selection_phase_v17_request.json)
derives $q_a(\theta)=1/4+\theta/2$ and $q_b(\theta)=1/2-\theta/2$ from
the supplied base orders and affine exponent laws. Their crossing is exact:

$$
\theta=\frac14,\qquad q_\ast=\frac38,\qquad \gamma=\frac85.
$$

Inspect `phase_diagram.transitions[0]` and `evaluations[2]`. Both mechanisms
win at the wall; its robustness distance is exactly zero. This is a finite
exact wall computation, not a sampled parameter grid.

The [V.18 request](../experiments/face_selection_qualified_v18_request.json)
instead varies the coefficient of the lower-weight mechanism through zero:

| Parameter | Winning mechanism | Exponent |
| :--- | :--- | :--- |
| $1/4$ | `positive-fallback` | $2$ |
| $1/3$ | `positive-fallback`; the emerging mechanism is `cancelled` | $2$ |
| $1/2$ | `emerging-low-face` | $4/3$ |

The requests explicitly attest analytic assumptions in their `assumptions`
objects. Replaying those flags does not independently prove those assumptions.
The [`phase-unlicensed` control](#inverse-diagnosis-and-missing-hypotheses)
shows what happens when they are omitted.

[Phase theorem →](FORMAL_FACE_SELECTION_PHASE_FAN.md) · [Qualification theorem →](FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md)

## Finite-family exponent discovery — V.21

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/face_selection_discovery_v21_request.json --pretty
```

The [six-candidate request](../experiments/face_selection_discovery_v21_request.json)
uses loss $x_0^2+x_1^4$ and includes an explicitly cancelled term.

| Class | Representative members |
| :--- | :--- |
| $q_\ast=1/4$, $\gamma=4/3$ | $x_1$ |
| $q_\ast=1/2$, $\gamma=2$ | $x_0$, $x_1^2$, $x_1-x_1+x_0$ |
| $q_\ast=3/4$, $\gamma=4$ | $x_0x_1$ |

Expect `candidate_count: 6`, screening counts `relevant: 5` and `critical: 1`,
and three `universality_classes`. The $x_0^2$ candidate is critical at $q=1$.
The cancelled-linear candidate retains a cancellation count of one while
remaining in the $q_\ast=1/2$ class.

The supplied registry already contains the $4/3$ class. The other two classes
are `unregistered` law candidates relative to that registry. This label does
not claim literature novelty or completeness over every possible perturbation.

[Discovery principle →](FORMAL_EXPONENT_DISCOVERY_ENGINE.md) · [Contract tests →](../tests/test_face_selection_discovery.py)

## Curved-channel resolution and cancellation — V.22

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/curved_reduction_request.json --pretty
```

The [canonical request](../experiments/curved_reduction_request.json) has
loss $x^6+y^6$ and perturbation $-x^2+xy^2$. Exact square completion gives

$$
-x^2+xy^2=\frac{y^4}{4}-\left(x-\frac{y^2}{2}\right)^2.
$$

Inspect `reduction.reduced_polynomial`, `reduction.checks`, and `scaling`.
The result is `licensed`, with `response_exponent_exact: "3"` and
`leading_coefficient.exact: "1/432"`.

Two derived requests expose why this result matters:

```bash
python experiments/reproduce_principle.py --only selector-limit curved curved-cancellation
```

- **`selector-limit`** removes `operation` from the same request, invoking
  the original face selector. It must return `refused`, `licensed: false`,
  unresolved face `[[0,1]]`, and a `higher_order_unresolved` blocker. Its CLI
  exit code is **1**, which is expected here. Refusal does not mean zero gain.
- **`curved`** resolves that gain by the supported quadratic reduction.
- **`curved-cancellation`** adds $-y^4/4+y^5$. The reduced quartic cancels,
  the leading term becomes quintic, and the licensed law becomes
  $\Delta(s)\sim(3125/46656)s^6$.

Each derived input is preserved as `request.json`; replay it directly with
the backend's `--input` option.

[Reduction theorem →](FORMAL_CURVED_REDUCTION.md) · [The original selector's boundary →](MATHEMATICAL_AUDIT.md)

## Finite-scale accuracy is a separate question

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input experiments/curved_finite_scale_requests.json --pretty
```

The [two-scale batch](../experiments/curved_finite_scale_requests.json) holds
$\varepsilon=10^{-9}$ fixed in

$$
R_\varepsilon=-\left(x-\frac{y^2}{2}\right)^2
+\varepsilon y^4+y^5.
$$

Both responses retain the exponent-3 asymptotic license. At relative tolerance
$1/10$, the separately certified finite-scale outcomes differ:

| Scale | `finite_scale.status` | Required evidence |
| :--- | :--- | :--- |
| $s=10^{-9}$ | `outside_tolerance` | The ratio interval lies above $11/10$ |
| $s=10^{-12}$ | `within_tolerance` | The entire ratio interval lies inside $[9/10,11/10]$ |

Inspect `bounds_certified`, `gap_interval`, `gap_to_prediction_ratio`, and
`witness.feasible`. The runner checks the tolerance inequalities using the
authoritative rational `exact` strings. The algorithm can stop once it proves
the decision, so do not expect a narrow interval in the first case.

`licensed: true` and a successful process exit do not establish finite-scale
accuracy. Increasing the subdivision budget can refine an unresolved interval;
it cannot change a certified `outside_tolerance` result for the same scale,
polynomial, and approximation.

[Finite-scale contract, bounds, and crossover →](CURVED_FINITE_SCALE.md)

## Inverse diagnosis and missing hypotheses

```bash
python experiments/reproduce_principle.py --only inverse phase-unlicensed
```

The inverse batch copies the simplex case and supplies observations $4/3$ and
$2$. Both forward predictions remain in `face-weight:1/4|response:4/3`.
The first inverse response is `matched`, with minimal consistent face `[[0]]`;
the second is `no_face_match`. The observation does not choose the forward law.

The phase control removes the V.17 request's `assumptions` object. Its exact
wall at $1/4$ and tied exponent $8/5$ remain available, but `status` becomes
`unlicensed` and `scope.blockers` records the missing warrant. The process exit
is still zero: an explicitly unlicensed calculation is a valid response.

[Forward, inverse, and licensing contracts →](FACE_SELECTION_BACKEND.md)

## Activation and contact with the critical curve

```bash
python experiments/activation_contact_check.py
```

The [exact algebra script](../experiments/activation_contact_check.py) prints
`Exact coexistence, zero value, and stationarity verified through degree 20.`
It checks coefficients of $\lambda_c(s)$, where
$\varepsilon_c(s)=s\lambda_c(s)$:

| Power of $s$ | Coefficient in $\lambda_c(s)$ |
| :--- | :--- |
| $0$ | $-1/4$ |
| $6$ | $1/2^{14}$ |
| $12$ | $-1/2^{22}$ |
| $13$ | $-9/2^{26}$ |
| $18$ | $7/2^{32}$ |
| $19$ | $9/2^{32}$ |
| $20$ | $135/2^{38}$ |

The script independently verifies the truncated algebra. Global activation,
analytic factorization, and the contact law are proved in the
[activation/contact note](RESEARCH_ACTIVATION_CONTACT_LAW.md); they do not
follow from checking finitely many coefficients alone. This is a research-note
verification, not a backend operation for parameter paths.

## Corrected categorical note

```bash
python experiments/note_publication_check.py
```

The [rational reproduction](../experiments/note_publication_check.py) checks
the localization counterexample, quadratic residual identity, valid separation
bound, sharpness, objective scaling, and pruning examples. The one-pass example
has gap $3/40$ and valid residual bound $3/32$; the independent solve has gap
$1/5$ and separation bound $1/3$.

This verifies the corrected worked examples. The legacy `formal_bounds.Phi`
and older `certified` fields retain their documented meanings; they do not
implement the replacement theorem simply because this reproduction passes.

[Corrected proofs →](FORMAL_THEOREMS.md) · [Revision record →](ORIGINAL_NOTE_REVIEW.md)

---

## How to read the evidence

| Evidence | What it establishes |
| :--- | :--- |
| Exact rational chart, polynomial, weight, or coefficient | An algebraic result for the supplied input |
| `licensed` | Named checks or supplied attestations meet the operation's contract; inspect which kind of evidence each check uses |
| `unlicensed`, `refused`, or `outside_scope` | A computation or model lacks the requested theorem license; read its blockers |
| `finite_scale.bounds_certified` | A rigorous interval for the supplied full polynomial at the requested scale |
| `finite_scale.status` | Whether that interval decides the requested approximation tolerance |
| Passing reproduction or regression test | Agreement with the stated finite checks; the general argument remains in the proof source |

The general face-selection backend combines exact polynomial transport with
numerical localization and analytic diagnostics. Phase requests can contain
caller-supplied assumption attestations. V.22's supported exact polynomial
class and the rational finite-scale intervals have their own contracts.
Read these distinctions before calling a result independently certified.

Backend CLI exits are **0** for `licensed`, `unlicensed`, and `complete`;
other top-level statuses produce **1**. A `complete` portfolio or discovery
still requires inspection of its cases. Finite-scale `outside_tolerance` can
accompany a top-level `licensed` result and exit zero. The reproduction
runner's exit instead reports whether its expected outcomes were reproduced.

Retain the entire evidence directory and manifest when sharing a result.
Source hashes identify the executed code even with local changes. Numerical
display values and timings may vary; the runner checks exact invariants and
specified decisions rather than byte-identical full responses.

## Regression tests

Install `pytest` as described above. These focused groups cover the
mathematical core and public contracts without starting a campaign:

```bash
python -m pytest -q -p no:cacheprovider tests/test_newton_tropical.py tests/test_face_selection.py tests/test_face_selection_phase.py
python -m pytest -q -p no:cacheprovider tests/test_ambient_face_compiler.py tests/test_face_selection_discovery.py tests/test_face_selection_backend.py tests/test_face_selection_portable_asset.py
python -m pytest -q -p no:cacheprovider tests/test_curved_reduction.py tests/test_curved_reduction_backend.py tests/test_curved_finite_scale.py
```

Run the full repository suite when validating a wider change:

```bash
python -m pytest -q -p no:cacheprovider
```

Use the count collected by your checkout; this runbook does not hard-code a
suite size. `unittest discover` alone misses pytest-style function tests.

## Document rendering

A proof that renders as literal text has not been published. GitHub's Markdown
pass runs before its math renderer and rewrites some characters; its KaTeX
instance then refuses a set of macros outright. Both failures are invisible in
a local preview and appear only on github.com.

[`ghmath.py`](../experiments/ghmath.py) is the publication control. It is
standard library only and checks every tracked Markdown file:

```bash
python experiments/ghmath.py README.md docs categorical_polytope experiments
```

It exits non-zero when a document contains a rendering **error**, so it can gate
a merge. Advisory **warnings** are reported but do not fail; add `--strict` to
fail on those too. `--fix` repairs the auto-fixable rules in place, and
`--list-rules` prints the catalogue with the commit that first fixed each one.

Every rule was extracted from a defect this repository actually shipped, not
from documentation. The recurring ones are bare `<` and `>`, which let GitHub
inject alignment characters and break table rows; `\operatorname`, which KaTeX
refuses in both its plain and starred forms; `\{` and `\}`, whose backslash the
Markdown pass eats; a literal `*`, which is consumed as emphasis; the LaTeX
delimiters `\[ \] \( \)`, which GitHub does not treat as math at all, so the
formula prints verbatim; and an indented `$$` block, which does not render.

The control is included in the reproduction suite as the `docs-rendering` case,
so a rendering regression fails the same run as a mathematical one.

Two limits are worth stating. The banned-macro list is assembled from observed
failures, not from a published GitHub allowlist, so it cannot catch a macro that
has not bitten yet. And it verifies macro legality and escaping, not that the
rendered output is correct: a formula can pass every rule and still be wrong.
Read the rendered page before publishing.

## Reproduce your own finite family

Copy the [V.21 request](../experiments/face_selection_discovery_v21_request.json)
to a new JSON file, then change `candidates`, `system`, or `base`. Preserve
the exact expressions, request, and scope evidence. To generate a finite
monomial family, remove `candidates` and supply:

```json
{
  "family": {
    "kind": "ambient_monomials",
    "max_total_degree": 2
  },
  "include_cases": true
}
```

This is a request fragment; retain the outer `operation`, `system`, and `base`.
Replay the complete file with:

```bash
python -m categorical_polytope.adjudication.polyhedra.backend --input path/to/your-request.json --pretty
```

Generated families are capped at 256 members. `include_cases: true` retains
the full per-candidate evidence. Keep `known_class_ids` explicit when reporting
registry-relative discoveries. The canonical runner checks fixed expected
results; use the backend directly for a changed mathematical problem.

## Further reproduction routes

These routes regenerate additional evidence. They are not invoked by the
canonical runner.

| Topic | Command | Output or interpretation |
| :--- | :--- | :--- |
| Earlier leading coefficients | `python experiments/appendix_leading_coefficients.py` | Numerical comparisons for $9/32$, the coupled $1/4$ law, and fractional exponents; requires NumPy |
| Polyhedral ledger, read-only check | `python experiments/run_polyhedra.py --check` | Replays local cases and prints verdicts without saving the ledger/report |
| Combined earlier laws | `python experiments/run_combined_law.py` | Regenerates `experiments/combined_law.json` and `experiments/COMBINED_LAW.md` |
| Finite candidate coverage | `python experiments/run_candidate_coverage.py` | Regenerates `experiments/candidate_coverage_certificate.json` and [its report](CANDIDATE_COVERAGE_CERTIFICATE.md) |
| Distributional assumptions | `python experiments/run_distributional_coverage_audit.py` | Regenerates `experiments/distributional_coverage_audit.json` and [its report](DISTRIBUTIONAL_COVERAGE_AUDIT.md) |
| Evaluation checklist | `python experiments/run_eval_checklist.py` | Regenerates `experiments/eval_checklist_report.json` and [its report](EVAL_DESIGN_CHECKLIST.md) |

Install NumPy separately for the appendix if needed:
`python -m pip install numpy`. Its numerical optimizer output is a diagnostic
comparison, not a rational finite-scale certificate.

The archived [verification certificate](VERIFICATION_CERTIFICATE.md) and
[campaign checkpoint](../experiments/verification_campaign.json) record a
larger search history. Resume commands can generate candidates, change the
checkpoint, and, with `--api`, contact a model endpoint. Canonical reproduction
does not require restarting that campaign. An API proposal history is not a
deterministic replacement for saved-input reproduction.

## Historical demos and paper materials

<details>
<summary><strong>Reproduce the original categorical and Fisher work</strong></summary>

```bash
python -m categorical_polytope
python -m categorical_polytope firsts
python -m categorical_polytope discover
python experiments/run_all.py
```

`run_all.py` is the historical experiment/report pipeline. It runs quadratic
and nonlinear sweeps, optional plots, report generation, discovery/research/
Friday probes, tutor work, and downstream reports. It writes tracked files
under `experiments/` and `docs/`; inspect `git diff` afterward. Some child
commands are not enforced with `check=True`, so its final “All experiments
complete” message is not by itself a pass certificate.

The older leakage cutoffs `0.10` and `0.25` are demonstration settings, not
universal accuracy thresholds. A local Hessian or unsuccessful grid search
does not prove global vertex localization. Use the corrected note's
hypotheses and bounds when interpreting these demos.

For the notebook, install the `notebook` extra and run:

```bash
jupyter notebook notebooks/fisher_extremal_demo.ipynb
```

Read the [short note](SHORT_NOTE.md), [Overview](../categorical_polytope/Overview.md),
[corrected proofs](FORMAL_THEOREMS.md), and [expanded manuscript](PAPER_DRAFT.md)
with the [revision record](ORIGINAL_NOTE_REVIEW.md).
The older [LaTeX short note](short_note.tex) and generated
[experiment report](EXPERIMENT_REPORT.md) are historical sources.
The [build guide](BUILD_PDF.md) targets the separate face-selection manuscript.

</details>

## Troubleshooting

| Symptom | Next action |
| :--- | :--- |
| `No module named categorical_polytope` | Return to the repository root or install editable in the Python environment you are using |
| `No module named pytest` | Install `pytest`; the canonical runner remains usable without it |
| A reproduction fails | Open its `checks.json`, `stderr.txt`, and response; retain the manifest before changing inputs |
| `--output-dir already exists` | Choose a new directory so previous evidence remains available |
| A valid backend command exits 1 | Read its status; an intentional refusal can be the expected mathematical boundary |
| `finite_scale.status` is `not_resolved` | Inspect `reason`, `bounds_certified`, and limits; an unresolved interval does not decide accuracy |
| A phase calculation is `unlicensed` | Inspect missing assumptions; do not turn flags on merely to obtain a licensed label |
| Outputs differ from an archived report | Compare commit, hashes, request, backend version, and exact fields before comparing rounded measurements |
| A formula shows as raw LaTeX on GitHub | Run `python experiments/ghmath.py <path>`; a rendering error names the rule and the line |
| `ghmath.py` reports only warnings | The exit status is 0 by design; warnings need a human decision, so review them rather than auto-fixing |

---

[**Return to the evidence suite ↑**](#one-command-reproduction) · [Backend contracts](FACE_SELECTION_BACKEND.md) · [Project overview](../README.md)
