# Coverage theorem × model-generated escape searches

This report connects the finite-sample coverage theorem to the completed
`COMBINED_LAW` and `SAFETY_INSTANCES` searches. The theorem is geometric; the
model-generated searches are finite empirical probes. The latter illustrate the
blind spots but cannot validate exhaustive coverage.

## The rigorous statement

Let `X=[0,1]^d` with Euclidean distance and let `S={x_1,...,x_n}` be the inputs
actually tested. Define the covering radius

`rho(S) = max_(x in X) min_(s in S) ||x-s||_2`.

Because `X` is compact, a maximizer `x*` exists. The open metric ball
`B_X(x*,rho(S))` contains no tested point. Therefore an all-safe behavior and a
behavior that fails only inside this ball give exactly the same `n` test results.
This remains true for a deterministic adaptive evaluator on its all-pass
transcript: construct one fixed failing behavior after deriving that finite path;
it returns the same pass observations and therefore induces the same path.

The radius has the volume lower bound

`rho(S) >= (1/(n*v_d))^(1/d)`, where `v_d=pi^(d/2)/Gamma(d/2+1)`.

Proof: if radius-`r` balls around the samples cover the unit-volume cube, their
union has volume at most `n*v_d*r^d`, hence `1 <= n*v_d*r^d`.

For an endpoint-including Cartesian grid with `m` points per axis (`n=m^d`), the
covering radius is exactly half a cell diagonal:

`rho_grid = sqrt(d)/(2(m-1))`.

Thus a grid with `rho_grid <= delta` is sufficient to hit every **open failure
ball of radius greater than `delta`** (and every closed ball of radius at least
`delta`). At `delta=0.05`:

| dimension | necessary for any placement (volume bound) | sufficient Cartesian grid |
|-----------|--------------------------------------------|-----------------------------|
| 1 | 10 | 11 |
| 2 | 128 | 256 |
| 3 | 1,910 | 6,859 |
| 5 | 607,928 | 7,962,624 |
| 10 | 4,015,427,964,584 | 1,531,578,985,264,449 |
| 20 | 4,063,162,758,168,324,687,102,214,144 | 1,799,519,816,997,495,209,117,766,334,283,776 |

The headline `46^20 = 1,799,519,816,997,495,209,117,766,334,283,776 ≈ 1.80×10^33`
is therefore a **Cartesian-grid sufficient count**, not a lower bound for every
possible sampling design. Even the assumption-light volume lower bound in 20-D
is about `4.06×10^27` samples.

## What “passed N tests” licenses

Without a regularity assumption, it licenses only: “the tested points passed.”
To extend that observation to neighborhoods, report all of:

1. the metric and normalization on the input space;
2. the empirical covering radius of the tested set;
3. the effective/intrinsic dimension used in any dimension-only bound; and
4. a minimum failure width or a Lipschitz/margin condition connecting sampled
   outcomes to nearby inputs.

If every relevant failure set contains a **closed** relative ball of radius
`delta`, a cover with radius at most `delta` detects every such failure. For open
failure balls, require their radius to be strictly greater than the covering
radius. This is the precise version of “safe down to radius `r(N,d)`.”

## Correlation with the completed searches

### Safety instances

- Screened: **36**.
- Regimes: quadratic=8, coupled=1, fractional=4, saturating=1, finite-scale=1, safe=21.
- Asymptotic-law violations after scale classification: **0**.

The model generated thin interior spikes, coupled surfaces, fractional ridges,
and steep gates. Those are constructive examples of failure sets that a fixed
axis/grid/local evaluator can miss. The `tolerance_cliff` initially looked like a
quadratic-law violation at `s=0.01`; a strength sweep showed its exponent returning
to `2` and measured/predicted ratio returning to `1` as `s` decreased. It is a
finite-scale remote-gate transition—exactly the kind of nonlocal feature for which
coverage, rather than a local Taylor law, is the relevant diagnostic.

### Combined law

- Rows recorded: **12**.
- Breaking pairs: **9**; base-self-fail: **2**.
- Exponent mismatches flagged for follow-up: **0**.

The combined-law rows include their source expressions and are auditable.

These probes broaden adversarial search. Their observed attack yield is directly
reportable, but their candidate count is not a covering design: arbitrary
expressions have no declared finite-dimensional metric here.

## The registered candidate-space bridge

The separate [`CANDIDATE_COVERAGE_CERTIFICATE.md`](CANDIDATE_COVERAGE_CERTIFICATE.md)
implements the missing bridge without pretending that arbitrary expression text
is Cartesian. Registry v1 defines one bounded normal-form parameter family per
law, maps its coordinates independently to `[0,1]`, uses normalized Euclidean
distance, and evaluates an endpoint-including Cartesian grid. Its exact radius is
`sqrt(d)/(2(m-1))`.

The positive detection statement is explicitly conditional on minimum-width
assumption `R(rho)`: every relevant counterexample set in the registered family
contains a closed relative ball of radius at least `rho`. Numerical survivors or
unresolved grid points withhold the corresponding certificate. Registry v1 was
designed after the open campaign and calibrated with boundary probes, so its
current run is exploratory; the frozen registry supports later confirmatory use.

This yields two non-conflicting outputs: the open API campaign measures observed
adversarial-search behavior, while the registered layer makes a restricted,
metric coverage claim. Neither is automatically a coverage claim over all
candidate functions, prompt space, or deployed-model behavior.

## Scope and citations

This is a theorem about finite point evaluation on a metric space, not evidence
about any deployed model. “Dimension” means the dimension of the chosen metric
model, ideally effective/intrinsic dimension—not token count or embedding width.

Covering numbers and metric entropy are standard notions originating with
[Kolmogorov and Tikhomirov (1959/1961)](https://www.mathnet.ru/eng/rm7289).
A modern worst-case global-optimization result likewise constructs adversarial
functions that agree on the sampled trajectory while differing at an unsampled
point: [Xu et al., 2024, JOTA](https://doi.org/10.1007/s10957-024-02399-1).
Classical high-dimensional sphere-covering context appears in
[Rogers, 1963](https://doi.org/10.1112/S0025579300004083).

## Reproduce

`python experiments/run_coverage_correlation.py`
