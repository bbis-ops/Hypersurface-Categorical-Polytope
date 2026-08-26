# Concrete safety-evaluation design recommendations

## Required claim types

Every result must label itself as one of these non-interchangeable claims:

1. **Pointwise:** the listed test inputs passed. No neighborhood claim.
2. **Distributional:** under a named sampling distribution, a failure region of
   probability mass at least `mu` is missed with probability at most `alpha`.
3. **Geometric worst-case:** every failure containing a specified metric ball is
   hit because the tested set has a measured covering radius.
4. **Margin-certified:** a regularity bound extends sampled scores globally.

## Mandatory eval card

Publish: domain and exclusions; metric and normalization and its semantic
validation; discrete strata;
sample-selection rule; number of unique samples; empirical covering radius or an
explicit statement that it is unknown; effective-dimension justification;
failure-width or regularity assumption; raw score margin; scorer false-negative
rate; sample dependence/cluster provenance; distribution-shift assumption; and
the exact claim type above.

## Design rules

### High-dimensional geometry

Do not imply worst-case coverage from a large test count alone. In 20 normalized
Euclidean dimensions, a radius-0.05 Cartesian guarantee needs
`1,799,519,816,997,495,209,117,766,334,283,776` points. When this is infeasible, reduce the justified intrinsic
dimension, prove structure/regularity, or downgrade the claim to pointwise or
distributional. Never silently substitute one claim type for another.
An intrinsic-dimension claim must define the restricted deployment domain and
validate that inputs remain on it; an estimator alone cannot erase ambient
off-manifold regions from a worst-case claim.

### Anisotropic inputs

Use domain-specific radii instead of pretending every coordinate has equal
meaning. For scaled L-infinity radii `(0.02,0.05,0.10)`, a sufficient grid uses
`(26, 11, 6)` points per axis, `1,716`
total. Report the units and rationale for each radius.

### Distributional evaluation

For IID samples, `n >= log(alpha)/log(1-mu)`. Detecting a failure region with
mass at least 1% with 95% confidence needs `299` independent draws.
This says nothing about rare regions under another distribution, correlated
samples, or worst-case geometry.

Name both the evaluation and deployment distributions. If
`dP_deploy/dP_eval <= W`, deployment failure mass `mu` implies eval mass at least
`mu/W`. With `mu=1%`, `W=5`, and scorer sensitivity 90%, the 95%-confidence count
is `1663` IID draws. If absolute continuity or finite `W`
cannot be justified, do not transfer the distributional claim. For correlated
samples, use an explicit dependence-specific bound or independent clusters;
a generic effective-sample-size estimate is not a worst-case certificate.

### Lipschitz-margin certification

If harm score `H` is `L`-Lipschitz, the tested maximum is `M`, and covering
radius is `rho`, then `sup H <= M+L*rho`. Example: `M=-0.2`, `L=2`, `rho=0.05`
gives global upper bound `-0.10`, certified below
threshold zero. `L` must be proven or conservatively bounded over the entire
claimed domain. A held-out empirical maximum gradient is still only a lower
bound on the unknown global supremum unless an additional statistical function
class makes its upper confidence bound valid.

### Mixed discrete/continuous structure

Worst-case claims require a cover in every safety-relevant categorical stratum.
Twelve strata, three continuous dimensions, and radius 0.10 require
`12,000` Cartesian tests. If a stratum is excluded, name it and make no claim
there.
Preregister the taxonomy and declared intersection depth. Post-hoc merging or
splitting cannot upgrade the headline claim; uncovered cells remain explicit.

### Adaptive red-teaming

Adaptivity can find failures efficiently but does not itself establish coverage.
Report discovered failures separately from residual assurance. Stop only when a
stated certificate is met (covering radius, distributional confidence, or
regularity-margin bound), not merely when search stops finding new examples.
The IID formula applies only to IID draws with a fixed stopping rule. Adaptive
distributional testing needs a valid sequential method (for example, a confidence
sequence); geometric covering-radius calculations remain valid for any realized
set, adaptive or not.

### Numerical and boundary convention

Declare a compact claimed domain and use a safety factor: target measured
covering radius `rho <= (1-eta)*delta` for some reported `eta>0`, rather than
depending on floating-point equality at an open-ball boundary.

## Recommended release language

> We evaluated N unique inputs selected by [rule] over [domain] using [metric].
> This supports a [pointwise/distributional/geometric/margin-certified] claim.
> The measured covering radius is rho [or unknown]. The claim assumes [failure
> width / distribution / Lipschitz constant / strata]. No guarantee is made
> outside those assumptions.

## API adversarial review

Backend: `stealth/ox-alpha@openrouter.ai`. Model feedback is untrusted until locally adjudicated.

### distribution_shift_unmodeled (major)

- Issue: All worst-case and distributional guarantees are conditional on the eval distribution equaling deployment distribution. Clause 3's (1-mu)^n is meaningless if the failure mass mu under deployment differs from the sampling distribution; covariate shift, temporal drift, and adversarial adaptation can concentrate failures in low-sampled regions. No requirement to state or bound the shift.
- Proposed repair: Require an explicit shift model: report importance-weighted estimates under a declared P_deploy/P_eval ratio bound, plus a sensitivity analysis over plausible shift magnitudes; re-run coverage audits periodically against live traffic.
- Local status: **accepted for distributional claims**
- Local reason: Geometric worst-case coverage is distribution-free, but distributional transfer requires named eval/deployment distributions. The standard now supports a density-ratio bound W and refuses transfer without absolute continuity and finite W.

### metric_validity (major)

- Issue: Clause 1 requires reporting 'input metric' but never its validity: Lipschitz claims (Clause 4) are vacuous if the metric does not reflect semantic proximity (e.g., token-edit distance vs. meaning). An arbitrary metric makes any H 'Lipschitz' with huge L, so the M+L*rho bound is trivially loose.
- Proposed repair: Require the metric be justified against a task-relevant equivalence relation, with a reported distortion/identifiability analysis; disallow bounds whose looseness factor exceeds a stated threshold without flagging them as non-informative.
- Local status: **accepted**
- Local reason: A mathematically valid metric can still be operationally meaningless. The eval card now requires semantic/task validation and reports when L*rho makes a certificate non-informative.

### l_estimation (major)

- Issue: Clause 4 assumes known L but gives no operational procedure for estimating it. Empirical max-gradient estimates from finite samples systematically underestimate L, invalidating the sup bound; adversarial or heavy-tailed H makes plug-in L estimation unsound.
- Proposed repair: Require L estimated on a held-out probe set with a one-sided confidence bound (e.g., upper quantile), plus a stated assumption class for H (e.g., smoothness, sub-Gaussian gradient); if L cannot be certified, downgrade the claim to pointwise.
- Local status: **accepted issue; proposed repair strengthened**
- Local reason: A held-out empirical maximum gradient does not certify global L. The standard requires a proven or conservative domain-wide bound, or a stated function class that validates a one-sided statistical bound; otherwise the claim is downgraded.

### randomized_adaptive_sampling (major)

- Issue: Clauses 2-3 silently assume fixed, pre-registered sampling. Adaptive selection of tested points (choosing where to test after seeing results) biases the covering radius and the (1-mu)^n calculation; deterministic grids fail when the adversary knows the grid. No randomization or stopping-rule requirement exists.
- Proposed repair: Mandate pre-registration of the sampling design; require randomized (not gridded) covering sets for any probabilistic claim; for adaptive testing, apply sequential correction (e.g., alpha-spending, confidence sequences) before issuing any pass/fail statement.
- Local status: **partially accepted**
- Local reason: The IID formula is invalid after adaptive dependent selection without sequential correction. However covering radius is a deterministic property of any realized set, adaptive or fixed, and does not require preregistration or randomization.

### iid_correlation_violation (major)

- Issue: Clause 3's (1-mu)^n assumes independence; real safety eval samples are correlated (shared templates, near-duplicate prompts, clustered strata), inflating effective sample size. The stated miss probability is then optimistic by potentially orders of magnitude.
- Proposed repair: Replace n with an estimated effective sample size via block bootstrap or autocorrelation-corrected variance; require reporting of the dependence structure (cluster IDs, template provenance) alongside every distributional claim.
- Local status: **accepted issue; generic ESS repair rejected**
- Local reason: The exact miss formula requires independence. A generic bootstrap/autocorrelation ESS is not a worst-case detection certificate; the standard instead requires independent clusters or an explicit dependence-specific probability bound.

### intrinsic_dimension_misreporting (major)

- Issue: Clause 1 reports 'effective dimension' but no definition or estimator is given. Covering radius in ambient dimension is misleading: data may lie on a low-dimensional manifold, making brute-force grids falsely 'infeasible' (Clause 6), or conversely high intrinsic dimension makes rho-based worst-case bounds vacuous while appearing rigorous.
- Proposed repair: Specify the estimator (e.g., maximum-likelihood intrinsic dimension, persistent homology) with uncertainty; require both ambient and intrinsic radii; reclassify Clause 6 feasibility relative to intrinsic-dimension scaling.
- Local status: **accepted with domain restriction**
- Local reason: Using intrinsic dimension for a worst-case claim requires defining and validating a restricted deployment domain or manifold. An uncertain dimension estimate alone cannot remove ambient off-manifold inputs from scope.

### confidence_calibration (major)

- Issue: No clause addresses calibration of the reported probabilities themselves. The judge/scorer H may have miscalibrated scores; the miss probability (1-mu)^n treats mu as exact though it is itself estimated with error, compounding into unquantified downstream risk. Pointwise 'pass' labels carry no false-negative rate.
- Proposed repair: Require conformal or Bayesian intervals on mu and on scorer reliability (judge-vs-human agreement with a calibrated CI); propagate these into the final guarantee as an explicit composite error bound rather than a single nominal number.
- Local status: **partially accepted**
- Local reason: The theorem treats mu as a target lower bound, not an estimate, so it needs no interval by itself. Scorer false negatives do matter: the implementation now uses effective detection mass mu times sensitivity and requires uncertainty to be propagated.

### stratum_boundary_vagueness (major)

- Issue: Clause 5's 'safety-relevant stratum' is undefined and gameable: partitioning can be chosen post hoc to make all strata covered, and mixed spaces allow degenerate categorical collapses. No minimum stratum resolution, no handling of intersectional strata.
- Proposed repair: Fix the stratum taxonomy before testing, require power analysis per stratum (min n per cell), forbid merging/splitting after seeing results, and require intersectional cells down to a declared depth with explicit 'uncovered' flags propagated into the headline claim.
- Local status: **accepted**
- Local reason: The standard now requires a preregistered taxonomy and intersection depth. Post-hoc cell changes cannot upgrade the claim, and uncovered cells remain explicit.

### closed_open_ball_edge_case (minor)

- Issue: Clause 2's closed/open ball distinction is operationally fragile: boundary behavior depends on the metric's topology and floating-point representation; a failure region exactly at radius rho yields ambiguous detection guarantees, and compactness of the domain is assumed but not required.
- Proposed repair: Require an explicit margin convention (test only with rho' = c*rho, c>1), declare domain compactness, and specify numeric tolerance for boundary membership checks.
- Local status: **accepted operationally**
- Local reason: The theorem already declares the compact cube and handles exact open/closed quantifiers. Implementations now require a reported positive safety factor eta so floating-point equality is never the certificate boundary.


## Reproduce

`python experiments/run_eval_design_recommendations.py --api-review --model stealth/ox-alpha`

For the formal IID, bounded-shift, and adaptive conditional-detection results,
including the separately adjudicated API audit, see
[`DISTRIBUTIONAL_COVERAGE_AUDIT.md`](DISTRIBUTIONAL_COVERAGE_AUDIT.md).
