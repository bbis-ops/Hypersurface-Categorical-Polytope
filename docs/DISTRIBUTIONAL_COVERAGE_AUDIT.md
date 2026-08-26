# Distributional coverage: theorem and API audit

## Theorem D.1 — IID detection

For a failure set `F` fixed independently of the evaluation sample, IID draws
from `P_eval`, failure mass at least `mu`, and fresh detector randomness with
per-failure sensitivity at least `q`, independent across draws,

`P(no detection in n draws) <= (1-mu*q)^n`.

Thus `mu=0.01`, `q=0.9`, and target miss probability `0.05` require **332**
draws; the computed upper bound is
`0.049711`.

## Corollary D.2 — bounded deployment shift

If `P_deploy << P_eval` and `dP_deploy/dP_eval <= W` for a certified finite
upper bound `W`, then deployment failure
mass `mu_dep` implies eval mass at least `mu_dep/W`. Substitute this into D.1.
For `mu_dep=0.01`, `q=0.9`, `W=5`, and miss probability `0.05`, the requirement
is **1663** IID draws.

This covers reweighting within eval support. It does not cover deployment-only
failure modes: those violate absolute continuity or force an unbounded ratio.

## Theorem D.3 — adaptive conditional detection

Let `F_i` contain all inputs, evaluator choices, detector state, and outcomes
through step `i`, and let `A_i` be no detection through that step. If on every
reachable history in `A_(i-1)`, `P(D_i | F_(i-1)) >= p` almost surely, then the
tower property gives

`P(A_n) = product_i P(no D_i | A_(i-1)) <= (1-p)^n`.

This permits adaptive/dependent selection only when the conditional lower bound
is valid uniformly over every surviving history. Optional stopping requires a
sequentially valid guarantee; a fixed-`n` formula cannot be reused after choosing
`n` from the observed data.

## Scope

The failure set is fixed before sampling. `mu`, `q`, `W`, and `p` are theorem
parameters, not automatically valid estimates. If calibration data give
simultaneous bounds `mu>=mu_L`, `q>=q_L`, and `W<=W_U` with failure probability
`delta_cal`, then a conservative unconditional statement is

`P(miss) <= (1-mu_L*q_L/W_U)^n + delta_cal`.

Scorer errors correlated across samples must be absorbed into a justified
conditional `p`; otherwise D.3 does not apply. A budgeted or stateful detector
does not inherit a constant `q` merely because inputs are IID.

## Ox Alpha adversarial review

Backend: `stealth/ox-alpha@openrouter.ai`. API output is untrusted until locally adjudicated.

### iid_theorem_core_valid (minor)

- Target: iid
- Objection: The base theorem is correct as stated: fixed F, IID inputs, per-draw detection prob >= mu*q, so P(no detection) <= (1-mu*q)^n by independence of the Bernoulli indicators.
- Model verdict: valid
- Proposed repair: None needed; but note the bound requires detection events across draws to be conditionally independent given membership in F — 'independently across draws' must be an explicit assumption on the detector's noise, not implied by input IID.
- Local status: **confirmed**
- Local reason: The IID calculation is correct. The statement now explicitly requires fresh independent detector randomness in addition to IID inputs.

### detector_noise_dependence (major)

- Target: iid
- Objection: 'Detects failure with probability at least q independently across draws' smuggles in detector independence. A single shared detector (same model, same prompt template) can have correlated false negatives: if it systematically misses one failure mode in F, q collapses. Input IID does not decorrelate a deterministic or stateful detector.
- Model verdict: needs-assumption
- Proposed repair: State that D_i are conditionally independent given {X_i in F}, or prove a weaker bound via Azuma/McDiarmid under bounded conditional variance.
- Local status: **accepted clarification**
- Local reason: IID inputs alone do not decorrelate a shared stateful scorer. Correlated scorer behavior must instead satisfy the uniform conditional-p hypothesis of Theorem D.3.

### fixed_vs_adaptive_failure_set (major)

- Target: iid
- Objection: The theorem silently assumes F is fixed before sampling. If F is chosen adaptively (e.g., red-teamed into existence using observed draws), mu is no longer a pre-specified property and the multiplicative bound fails; adaptive F selection inflates apparent coverage.
- Model verdict: valid
- Proposed repair: Require F measurable w.r.t. a sigma-algebra independent of the sample, or pay a union-bound/complexity penalty over the class of candidate failure sets.
- Local status: **confirmed as already scoped**
- Local reason: The report already states that F is fixed before sampling. Adaptive selection from a function class requires a separate uniform-complexity correction.

### shift_ac_support (major)

- Target: shift
- Objection: Absolute continuity plus density bound W gives P_deploy(F) = ∫_F r dP_eval <= W·P_eval(F), so P_eval(F) >= P_deploy(F)/W >= mu_dep/W. Inequality direction is correct. However AC only guarantees r exists; it says nothing about W being finite or known, and heavy-tail deployments routinely violate finite-W.
- Model verdict: valid
- Proposed repair: Make finiteness and a certified upper bound on ||dP_deploy/dP_eval||_∞ an explicit audited hypothesis; otherwise the corollary is vacuous.
- Local status: **confirmed**
- Local reason: The density-ratio direction is correct. The corollary now emphasizes that W must be a certified finite upper bound.

### shift_vacuous_when_mu_eval_zero (major)

- Target: shift
- Objection: If P_eval(F)=0 then AC forces P_deploy(F)=0, so the corollary cannot be applied to deployment-only failures — precisely the interesting regime. The corollary only bounds miss probability for failures already visible under eval distribution at rate >= mu_dep/W.
- Model verdict: valid
- Proposed repair: State explicitly: the shift correction covers reweighted known failure modes only; novel-mode risk needs separate support assumptions.
- Local status: **accepted limitation**
- Local reason: A finite ratio excludes deployment-only support. The report now states that the corollary covers reweighting within eval support, not novel support.

### shift_estimation_of_w (major)

- Target: shift
- Objection: W is typically estimated empirically from samples; plug-in estimates of sup density ratios are biased downward (max of noisy ratios), so (1 - mu_dep*q/W)^n computed with an estimated W understates miss probability.
- Model verdict: valid
- Proposed repair: Use a high-probability upper confidence bound on W and propagate through the exponential; do not report point-estimate guarantees.
- Local status: **accepted**
- Local reason: A plug-in maximum ratio is not a certificate. The operational bound now uses a simultaneous upper confidence bound W_U and propagates calibration failure probability.

### adaptive_conditional_bounds_correct (minor)

- Target: adaptive
- Objection: The iterated conditioning argument is valid: define M_i = event of no detection through i. Then P(M_i | H_(i-1)) <= 1-p on every history, so E[1_{M_i}|H_(i-1)] <= 1{M_(i-1)}(1-p); tower property telescopes to P(M_n) <= (1-p)^n. Independence genuinely unnecessary; only a uniform supermartingale-style lower bound on conditional detection probability is required.
- Model verdict: valid
- Proposed repair: None for the math; ensure p is a.s. uniform over ALL histories realized with positive probability, including histories generated by adversarial input selection.
- Local status: **confirmed**
- Local reason: The adaptive proof is correctly a tower-property argument and needs no independence once a uniform conditional detection lower bound holds.

### adaptive_history_definition (major)

- Target: adaptive
- Objection: The quantifier is over 'every no-detection history' but the filtration must be specified. If the evaluator adapts its probing strategy using past outcomes, H_(i-1) includes those choices; the bound holds only if the p-lower-bound survives this richer filtration. A detector whose recall degrades as the adversary learns it violates the a.s. bound on some reachable histories.
- Model verdict: needs-assumption
- Proposed repair: Define the filtration explicitly and require inf over all H_(i-1) in the filtration of P(D_i|H_(i-1)) >= p, verified against the actual (possibly adaptive) evaluation policy.
- Local status: **accepted**
- Local reason: The report now defines the filtration to include inputs, policy choices, detector state, and outcomes, with p required on every reachable no-detection history.

### optional_stopping_not_needed_but_related (minor)

- Target: adaptive
- Objection: No optional stopping is invoked, correctly — the argument is a pure product of conditional bounds via the tower rule. But if anyone extends to random stopping times T (e.g., stop when confidence reached), P(M_T) <= (1-p)^T is NOT automatic; one needs P(M_T) = sum_t P(M_t, T=t)-style care or a supermartingale argument, since (1-p)^t varies with t.
- Model verdict: valid
- Proposed repair: For random stopping times use Wald-type reasoning or bound P(M_T) <= max_t P(M_t), which loses tightness; state assumptions explicitly.
- Local status: **confirmed scope warning**
- Local reason: The fixed-n theorem is valid. Random stopping requires a separately constructed sequential guarantee; the report explicitly forbids reusing the fixed-n formula after data-dependent stopping.

### estimation_vs_theorem_conflation (fatal)

- Target: interpretation
- Objection: All three results are conditional on parameters (mu, q, W, p) that are unobservable population quantities. The most common referee failure is presenting (1 - mu_hat*q_hat/W_hat)^n as a guarantee: estimation error in mu, q, W compounds multiplicatively inside an exponent, and small-sample q estimates are notoriously optimistic (detectors validated on easy failures).
- Model verdict: valid
- Proposed repair: Report only high-probability statements: with probability 1-δ over calibration data, P(no detection) <= (1 - (mu_L)(q_L)/W_U)^n + δ, with explicit lower/upper confidence bounds; never present point estimates as certificates.
- Local status: **accepted**
- Local reason: The report now gives the conservative calibrated statement (1-mu_L*q_L/W_U)^n + delta_cal rather than treating point estimates as theorem parameters.

### q_and_mu_interaction (minor)

- Target: iid
- Objection: P(detect) >= mu*q assumes detection probability factors as P(X in F)*P(D|X in F). If the evaluator's detection procedure itself depends on how many failures occur (e.g., budgeted inspection), q is not constant and the product form breaks.
- Model verdict: needs-assumption
- Proposed repair: Assume per-draw unconditional detection probability directly >= mu*q, or model budgeted detection explicitly.
- Local status: **accepted clarification**
- Local reason: The constant-q formula requires fresh per-draw detection or an unconditional/conditional lower bound. Budgeted and stateful detectors must be modeled through D.3.

### density_ratio_two_sided (minor)

- Target: shift
- Objection: Only an upper bound on r is used. Fine for this direction, but note asymmetry: the reverse transfer (eval-certified safety implies deploy-safety) needs a LOWER bound on r or an upper bound on the reciprocal, which fails whenever P_eval has larger support — the typical case.
- Model verdict: valid
- Proposed repair: Do not read the corollary symmetrically; certify each transfer direction separately with the appropriate ratio bound.
- Local status: **rejected**
- Local reason: For eval-to-deployment safety transfer, P_deploy(F)<=W*P_eval(F) follows from the same upper bound r=dP_deploy/dP_eval<=W. A lower bound on r is neither needed nor sufficient for this direction.


## Reproduce

`python experiments/run_distributional_coverage_audit.py --api --model stealth/ox-alpha`
