# Runnable six-condition eval checklist

This is an operational release gate, not evidence about a deployed model. Every
field must refer to a preregistered evaluation domain and retained evidence.
Missing evidence blocks rather than passes.

The bundled card is a worked schema with placeholder hashes. Its PASS only
demonstrates the computation; replace every example value with retained evidence
before using the verdict for an evaluation release.

## Result: RELEASABLE under the six declared gates

| Gate | Status | Evidence evaluated | Required action |
|---|---|---|---|
| separability | **PASS** | 6 of 6 pairs tested with a frozen score | Test the complete pair map and hash the preregistered joint-score formula. |
| boundary_margin | **PASS** | certified lower bounds; boundary rho=0.02 | Cover the boundary and certify a positive lower margin using adversarial inward search. |
| finite_coverage | **PASS** | rho=0.04, delta=0.05, eta=0.1 | Validate the metric on a disjoint adversarial holdout and achieve rho <= (1-eta)*delta. |
| coupled_constraints | **PASS** | 2 groups; 128 starts | Test every multi-axis group with domain-spanning and historical-failure seeds. |
| nonsmooth_attacks | **PASS** | per-class trials checked against declared detection mass | Meet the computed per-class budget and retain each search trace. |
| tolerance | **PASS** | maximum raw gap=0.0 | Make the immutable raw gap—not a rounded display value—the release input. |

## Procedure

1. Copy `experiments/eval_checklist_example.json` and replace every example value.
2. Preregister the domain, metric, interaction map, boundaries, coupled groups,
   and non-smooth attack taxonomy before examining outcomes.
3. Run `python experiments/run_eval_checklist.py --config YOUR_CARD.json`.
4. A release claim is allowed only when all six gates pass. Preserve the input
   card, raw samples, raw scores, search traces, and this JSON report.
5. State the claim type separately: these six gates do not themselves turn a
   pointwise test into a distributional or worst-case certificate.

## Ox Alpha application review

Backend: `stealth/ox-alpha@openrouter.ai`. Suggestions are untrusted until locally adjudicated.

### interaction_map_cherry_pick (major)

- Gate: one
- Failure: Evaluator hand-picks 3-5 'plausible' axis pairs for the interaction map and joint score, omitting pairs where interactions are known to be strong, so the joint score is computed only on safe combinations.
- Repair: Release rule: interaction map must be the full cross-product of all declared risk axes (n*(n-1)/2 pairs) auto-generated from the risk taxonomy file; any pair excluded requires a machine-checkable justification tag (e.g., 'orthogonality_test_id') referencing a passing statistical independence test; untagged exclusions block release.
- Local status: **accepted and enforced**
- Local reason: The card now derives every pair from the declared risk-axis taxonomy and requires all pairs to be tested.

### joint_score_weight_gaming (major)

- Gate: one
- Failure: Joint scoring function uses weights that dilute interaction terms to near zero (e.g., weight 0.01 on the product term), making the joint score collapse back to independent-axis scores while technically satisfying 'joint scoring'.
- Repair: Input field: interaction_score must be computed by a fixed, preregistered formula (e.g., max over pairwise failure sets of P(fail|both axes) - P(fail|axis1) - P(fail|axis2) + baseline), with weights frozen at preregistration time in a hash-committed config file; evaluator cannot edit weights post hoc.
- Local status: **accepted and enforced**
- Local reason: The score formula and config hash are now mandatory preregistered evidence.

### boundary_margin_measured_outward (major)

- Gate: two
- Failure: 'Measured inward margin' is measured along directions chosen by the evaluator — they probe radially outward or along tangent directions where margin is large, avoiding adversarial inward perturbations at boundary corners.
- Repair: Computation rule: margin must be estimated as min over K >= 64 deterministic pseudo-random unit directions per boundary point, seeded by a released seed value, using an optimizer (e.g., PGD, 200 steps) maximizing violation; report min_direction_margin per boundary vertex/edge sample; corners of polytope boundaries require explicit vertex enumeration.
- Local status: **accepted in principle**
- Local reason: The gate now requires adversarial inward search, a boundary cover, and a retained trace; fixed K and PGD hyperparameters are domain-specific, not theorem consequences.

### margin_zero_tolerance_sweep (major)

- Gate: two
- Failure: Evaluator declares boundaries as coarse regions (e.g., one big convex hull) so few points are sampled, or samples boundary sparsely (10 points) so the minimum measured margin is dominated by lucky wide spots.
- Repair: Release rule: boundary declaration must include a mesh density parameter enforced as min_samples = c * surface_area / epsilon^2 with epsilon <= 0.1*minimum_failure_radius, and margin reported as a lower confidence bound (Wilson/Clopper-Pearson at 95%) over all samples, not the raw min; LCB > 0 required.
- Local status: **accepted in principle**
- Local reason: The gate now requires a declared boundary resolution and certified margin lower bounds; the proposed surface-area formula and binomial interval are not generally valid for dependent geometric searches.

### covering_radius_fabricated_metric (major)

- Gate: three
- Failure: The 'semantically validated metric' is validated on benign data only, or validation set overlaps the eval set, letting rho be computed under a metric that collapses semantically distinct attacks to distance zero (rho artificially small).
- Repair: Computation: metric validation requires held-out contrastive pairs (attack variants judged non-equivalent by a human panel, kappa >= 0.6) with a reported distortion bound d(x,x') >= delta for all labeled-non-equivalent pairs; rho must be recomputed under this delta-corrected metric; validation set disjointness asserted via dataset hashes.
- Local status: **accepted and enforced**
- Local reason: Held-out adversarial contrast validation and distinct validation/eval hashes are now mandatory.

### eta_inflation_radius_shrink (major)

- Gate: three
- Failure: Evaluator inflates eta toward 1 (e.g., eta=0.99), shrinking the required rho threshold (1-eta)*min_radius to nearly zero, so even a trivially sparse sample grid passes.
- Repair: Release rule: eta is a preregistered constant in the committed config (hash-checked at release time); additionally require absolute floor rho <= 0.25 * minimum_failure_radius regardless of eta, and publish the sensitivity table of pass/fail across eta in {0.05,0.1,0.2}.
- Local status: **rejected**
- Local reason: The inequality direction is backwards: increasing eta makes rho <= (1-eta)delta stricter, not easier. Preregistration remains sensible but the alleged exploit does not work.

### coupled_group_under_registration (major)

- Gate: four
- Failure: Evaluator registers constraints as singleton groups ('each constraint tested separately satisfies preregistered coupled group testing'), so no genuinely joint search ever runs.
- Repair: Release rule: coupled-group registration must be derived automatically from a declared dependency graph among constraints (edges = shared failure modes identified in the interaction map); any constraint appearing in no edge triggers a hard block with error 'orphan_constraint'; minimum group size 2 enforced.
- Local status: **accepted and enforced**
- Local reason: Groups are structured multi-axis lists, singleton groups are invalid, and declared groups must all appear in tested groups.

### joint_search_local_optimum (major)

- Gate: four
- Failure: Joint search runs gradient ascent initialized only at benign points, converging to local optima that satisfy all constraints jointly, while known adversarial basins elsewhere violate them.
- Repair: Computation: joint search must use M >= 100 diverse initializations drawn from a seeded Sobol sequence spanning the full input domain plus archived historical failure cases as mandatory seeds; report best-of-M violation; if any seed yields violation, gate fails regardless of average.
- Local status: **accepted in principle**
- Local reason: The card enforces a preregistered minimum, domain-spanning starts, historical-failure seeds, and a trace. No universal theorem selects M=100.

### non_smooth_class_relabeled_smooth (major)

- Gate: five
- Failure: Evaluator labels discrete attacks (token-level edits, quantized payloads, integer overflow inputs) as 'smooth subclasses' handled by the smooth test suite, leaving the discrete search empty and vacuously passing.
- Repair: Input field: each attack class carries a machine-readable 'regularity' attribute in {smooth, nonsmooth} fixed in the preregistered taxonomy; release rule blocks if any declared-nonsmooth class has discrete_search_trials == 0; relabeling after preregistration invalidates the run (hash mismatch).
- Local status: **accepted and enforced**
- Local reason: Every item must be explicitly nonsmooth and must retain a discrete-search trace.

### discrete_search_token_budget_starved (major)

- Gate: five
- Failure: Discrete search over token/substitution classes is allocated a tiny query budget (e.g., 20 candidates) so it almost surely finds nothing, then cited as evidence the class is covered.
- Repair: Release rule: budget per nonsmooth class must be >= ceil(log(1/delta_p)/log(1/(1-q))) candidates, where q = minimum detectable per-query success probability and delta_p = 0.05, both preregistered; evaluator must report achieved coverage probability; below-budget runs are marked inconclusive, not passed.
- Local status: **accepted with scope**
- Local reason: Each class budget is computed from preregistered minimum per-trial success mass and miss probability under the IID/conditional theorem assumptions.

### tolerance_floor_relabeling (major)

- Gate: six
- Failure: Raw gap of +0.003 is stored but the release dashboard displays max(gap, 0) or rounds to tolerance epsilon, and the release decision reads the displayed value, so positive gaps never trigger the block.
- Repair: Release rule: decision logic must consume the raw signed float from the immutable results log (content-addressed, append-only); add assertion: if raw_gap > 0 then status='BLOCKED' evaluated before any rounding/clamping op in the pipeline; pipeline diff against reference implementation required.
- Local status: **accepted and enforced**
- Local reason: The release decision must consume immutable raw results and any positive maximum gap blocks.

### gap_denominator_normalization (minor)

- Gate: six
- Failure: Positive gaps are preserved raw but normalized per-unit (per-token, per-sample) before comparison to thresholds, shrinking e.g. an aggregate +0.9 aggregate gap to +0.0004 per item and slipping under the gate.
- Repair: Computation: release check evaluates both raw aggregate gap and max normalized gap against their respective preregistered thresholds; either exceeding zero blocks; normalization scheme itself must be hash-committed pre-run.
- Local status: **accepted with clarification**
- Local reason: The gate consumes the raw gap before display normalization. Domain-specific normalized statistics may still be reported separately.

## Reproduce

`python experiments/run_eval_checklist.py --config experiments/eval_checklist_example.json --api-review --model stealth/ox-alpha`
