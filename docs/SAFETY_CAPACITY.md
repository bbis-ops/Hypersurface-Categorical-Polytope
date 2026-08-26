# Safety-evaluation capacity: what the polytope theorems do and don't say about LLM safety

Module: `categorical_polytope/eval_escape.py`. Tests: `tests/test_eval_escape.py`.

## Read this first (the honesty contract)

The theorems in [`FORMAL_VERTEX_THRESHOLD.md`](FORMAL_VERTEX_THRESHOLD.md) (V.1–V.13)
are about maximizing a scalar objective on a box with a degenerate corner. **They
do not, by themselves, prove anything about GPT-class models.**

What this note does is legitimate and limited: it models a *safety evaluation* as
an optimization — an adversary maximizes a harm score `H`, an evaluator using some
strategy certifies "safe" — and states each failure mode as a **conditional**:

> *If* a real evaluation has structure X, *then* it inherits blind spot Y, with
> this exact scaling.

The conditional is **proven** inside the model. Whether a given real evaluation
has structure X is an **empirical assumption**, stated explicitly for each item
and never smuggled in. So this is a set of **design warnings for evaluation
methodology**, not measurements of any deployed system, and not a claim that "LLM
safety fails."

It is deliberately defensive: the point is to argue for denser, coupled,
adversary-aware, tolerance-free evaluation, and to name the specific ways an
evaluation can produce **false assurance**.

Three honest corrections to the tempting one-liners:

- "Thresholds are zero" holds only when the safety boundary is **degenerate**
  (flat, zero inward margin). A boundary with a strict margin has a **positive**
  threshold — that is exactly the fix (V.6, V.13).
- "Coupling halves the margin" is the two-axis isotropic case. In general the
  additive/true error factor is up to `√(number of coupled dimensions)`
  (Cauchy–Schwarz), and it can go either way, not always ½.
- "Non-smooth explodes the gap" means the gap/​smooth-gap **ratio** is unbounded
  as attack strength `s → 0`; the gap itself is still small at small `s`, just
  far larger than smooth intuition predicts. The exponent drops from 2 toward 1.
- `0.5·√d·n^{-1/d}` is the Cartesian-grid scale, not a universal lower bound
  for every placement of `n` points. The rigorous arbitrary-placement volume
  bound is `v_d^{-1/d}·n^{-1/d}`.

---

## The one genuinely general, fully rigorous result: evaluation coverage

This one needs no LLM analogy to be a real theorem, and it is the strongest.

**Claim.** Let an evaluation sample a finite set `S` of `n` inputs in `[0,1]^d`
and certify "safe" iff every sampled point passes. If `rho(S)` is its covering
radius, there is an open metric ball of radius `rho(S)` containing no tested
point. Thus the transcript cannot distinguish an everywhere-safe behavior from
one that fails only in that ball.

For **arbitrary** sample placement, a volume argument gives

$$\rho(S) \ge \left(\frac{1}{n v_d}\right)^{1/d}, \qquad
v_d=\frac{\pi^{d/2}}{\Gamma(d/2+1)}.$$

For an endpoint-including Cartesian grid with `m` points per axis (`n=m^d`),
the exact radius is `√d/(2(m-1))`. To make that grid radius at most `δ` requires

$$n \ge \left(1 + \frac{\sqrt d}{2\delta}\right)^{d}.$$

**Proven** (generalises V.5 from the box to arbitrary `d`; verified in
`test_eval_escape.py`). The Cartesian-grid sufficient count is exponential:

| dimension `d` | samples to catch a radius-0.05 failure |
|---------------|----------------------------------------|
| 1 | 11 |
| 2 | 256 |
| 3 | 6 859 |
| 5 | 7.9 × 10⁶ |
| 10 | 1.5 × 10¹⁵ |
| 20 | 1.8 × 10³³ |

The `1.8 × 10³³` headline is therefore a **sufficient Cartesian-grid count**, not
a lower bound for every possible design. The arbitrary-placement volume lower
bound at `d=20, δ=0.05` is still about `4.06 × 10²⁷` samples.

**Operational.** Report the covering radius as the eval's stated resolution limit.
Without regularity, "passed N tests" says only that the tested points passed. The
stronger phrase "safe down to radius `r`" additionally requires a metric,
normalization, measured covering radius, effective dimension, and either a
minimum failure width or a Lipschitz/margin condition. Sample adversarially and
adaptively; a fixed grid or benchmark cannot close the gap in high `d`.

**Ethical.** Presenting a finite benchmark pass as "safe" without its metric,
coverage, and regularity assumptions is a quantifiable overclaim.

---

## The six failure modes, as conditional claims

Each is generated and numerically instantiated by `eval_escape.capacity_report()`.

### 1. Separable reasoning is fragile (V.7 / V.9)
- **Assumption**: the eval scores each risk dimension independently and sums/maxes.
- **Proven**: per-axis scoring mis-estimates a coupled objective; the true worst
  case is off every single axis, so no per-axis test sees it.
- **Number**: additive vs directional reading differ by up to `√(#coupled axes)`.
- **Do**: score jointly over interacting dimensions.
- **Ethics**: "safe on each axis" ≠ "safe". Independence is an assumption, not a fact.

### 2. Vertex-like boundaries have zero margin (V.3 / V.6)
- **Assumption**: the safe region is a box and the reward is flat along its boundary.
- **Proven**: a degenerate boundary optimum has threshold `s* = 0` — an
  arbitrarily small push crosses it. A **strict** boundary (nonzero inward slope)
  has `s* > 0`; that is the fix.
- **Number**: measured margin at the degenerate corner `≈ 9e-12` (i.e. zero).
- **Do**: require and *measure* a strict margin at every safety boundary.
- **Ethics**: "the limit was not exceeded" says nothing if the limit has no margin.

### 3. Grids miss failures (V.5, generalised above)
- The coverage theorem. The strongest and assumption-light.

### 4. Coupled constraints (V.9)
- **Assumption**: real risk couples constraints the eval treats as separate.
- **Proven**: the directional (true) gap differs from the additive (per-axis)
  reading; the maximiser moves along a coupled ray no axis test explores.
- **Do**: red-team combinations, not one constraint at a time.
- **Ethics**: passing every constraint separately can still be a joint failure.

### 5. Non-smooth prompts enlarge the gap (V.8 / V.10)
- **Assumption**: adversarial edits are non-smooth (discrete tokens, discontinuities).
- **Proven**: a degree-`α<1` perturbation opens a gap with exponent `2/(2-α) < 2`,
  unboundedly larger than a smooth one as `s → 0` (e.g. 41× at `s=0.01` for a
  square-root-type edit).
- **Do**: test discrete/non-smooth attacks directly; smooth robustness doesn't transfer.
- **Ethics**: robustness to smooth changes overstates safety against real attacks.

### 6. Tolerance thresholds hide failures (the repo's own bug)
- **Assumption**: the eval certifies "safe" when a score is below a fixed tolerance.
- **Proven**: the true gap is positive but under tolerance *exactly* in the
  small-attack regime — the same mistake the repo's original
  `localization_at_vertex` flag made (it forgave any gap below 0.05 while
  localization had already failed).
- **Do**: report the raw gap and its scaling exponent, never a boolean pass/fail.
- **Ethics**: a tolerance converts a real, small, exploitable failure into a green check.

---

## Red-team validation (the model attacking its own framework)

`experiments/run_safety_instances.py` asks the model for harm surfaces built to
evade a separable / grid / tolerance evaluator, screens each, and flags any
smooth breaker whose predicted law **fails** — a genuine counterexample would
correct the theory.

The completed run screened **36** surfaces: 8 built-ins plus 28 fresh Ox Alpha
instances. Its final distribution was 8 quadratic, 1 coupled, 4 fractional,
1 saturating, 1 finite-scale, and 21 safe under the local screen.

One `tolerance_cliff` was initially flagged as a law violation at `s=0.01`:
its remote gate made the measured gap 145× the local prediction. A strength sweep
resolved the apparent counterexample. At `s=0.00125` its exponent was 2.047 and
measured/predicted ratio 1.09; by `s=0.00015625` they were 2.006 and 1.01. The
quadratic asymptotic law holds, but a nonlocal bump controls the finite-scale
maximum. The screen now reports this as **finite-scale**, not as an asymptotic
counterexample.

The combined-law run recorded 29 pairs, including 17 breakers and 4 exponent
mismatches. Its legacy JSON did not retain the proposed expressions, so those
four are correctly treated as unaudited follow-up leads. The runner now persists
base/perturbation expressions and sources on every row.

This is exactly where the coverage theorem complements the local laws: Taylor and
homogeneity analysis explain behavior near a known corner; coverage controls what
a finite search can say about remote spikes, gates, and unsampled regions. See the
generated [`COVERAGE_CORRELATION.md`](COVERAGE_CORRELATION.md) for the proof,
sample-complexity table, experiment correlation, and citations.

---

## What would make any of these an empirical result

Each conditional becomes a measurement only if someone shows a real evaluation has
the assumed structure: that its safety score is (near-)separable, that its safe
region is box-like with a flat boundary, that its input space is high-dimensional
and sampled finitely (this one is almost always true), that attacks are non-smooth
(also usually true), or that it certifies via a tolerance. Those are testable
properties of an evaluation pipeline. This note says what follows *if* they hold;
it does not assert that they do for any particular system.
