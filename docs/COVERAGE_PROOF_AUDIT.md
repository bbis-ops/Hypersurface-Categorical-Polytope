# API adversarial audit: coverage theorem

Backend: `stealth/ox-alpha@openrouter.ai`

Model output is an untrusted referee report, not a proof. Each item remains
pending until checked against the formal statement and executable tests.

## 1. indistinguishability_ball_contains_x_star

- Target: The open relative ball B_X(x*,rho) ... point evaluation cannot distinguish an everywhere-safe behavior from one failing only in that ball.
- Objection: x* itself lies in B_X(x*,rho) (distance 0 < rho). A test permitted to evaluate at x* trivially distinguishes an everywhere-safe behavior from one failing at every point of that ball. The no-go argument silently assumes either that the failure set excludes all finitely many queryable points, or that the test's query budget/locations are constrained away from x*. As stated, the quantifiers are wrong: 'cannot distinguish' is false for unrestricted point evaluation.
- Model verdict: valid (fatal)
- Proposed repair: Restate as: for any deterministic test issuing finitely many queries q_1,...,q_k chosen adaptively, there exists a behavior agreeing with the safe behavior on {q_1,...,q_k} yet failing on a nonempty open subset of B_X(x*,rho) \ {q_i}; hence no finite-query test certifies safety with certainty. Explicitly exclude the queried points from the failure set.
- Local status: **rejected**
- Local reason: For the actual finite set `S`, `rho(S)>0` and every maximizing `x*` has positive distance from `S`, so `x*` is not a queried point. Querying that `x*` defines a different set with a new empty ball; it does not refute the for-every-finite-`S` statement.

## 2. adaptive_path_conditioning

- Target: For adaptive testing, the indistinguishability argument is conditioned on the realized all-pass path.
- Objection: Conditioning on the realized path is not enough: under an adaptive test, the adversary must exhibit a single fixed failing behavior consistent with ALL responses along the realized path simultaneously, otherwise the argument commits a selection fallacy across branches. Also, for randomized tests the conclusion must be probabilistic (e.g., any randomized test's probability of detecting a fixed hidden failure is bounded by its query budget times nothing—actually detection probability can be made arbitrarily small by hiding the failure off the support), which the prose never states.
- Model verdict: needs-assumption (major)
- Proposed repair: State: fix the realized query sequence Q; construct one behavior f failing on an open set disjoint from Q and matching the safe behavior on Q. For randomized tests, add: for any distribution over tests with bounded query count k, there exists a failing behavior undetected with probability >= 1 - (measure-theoretic bound via union over supports), or simply note randomization does not help against a worst-case fixed failure placed outside the random support.
- Local status: **accepted scope correction**
- Local reason: The fixed all-pass-path construction is sound for deterministic adaptive tests. A randomized algorithm needs a separate probabilistic theorem; the project now explicitly makes no randomized-test claim.

## 3. volume_bound_is_lower_bound_only

- Target: If radius-r Euclidean balls around S cover X, then 1=vol(X) <= n*v_d*r^d, so rho(S) >= (1/(n*v_d))^(1/d).
- Objection: Two defects. First, the inequality chain proves rho(S) >= (1/(n v_d))^{1/d}, but this is only a LOWER bound on the covering radius; the operational guarantee needs an UPPER bound achievable by construction, which the grid supplies — fine — but the prose presents the volume bound as if it were the operative certificate. Second, boundary effects: balls centered near the boundary extend outside X, so vol(X) <= n v_d r^d holds but is loose; more importantly the claimed implication direction requires that rho(S) equal the minimal covering radius, which is true here, so the inequality itself is sound. No fatal error, but the logical role is misstated.
- Model verdict: valid (minor)
- Proposed repair: Relabel explicitly: volume bound gives rho(S) >= (1/(n v_d))^{1/d} (information-theoretic floor); the grid gives rho(S) <= delta (constructive ceiling); the gap between them is a factor depending on d and lattice geometry and should be acknowledged rather than elided.
- Local status: **rejected as already addressed**
- Local reason: The report already labels the volume argument as a necessary information-theoretic lower bound and the Cartesian grid as a constructive sufficient upper bound. Boundary looseness does not invalidate the inequality.

## 4. failure_set_regularity_overclaim

- Target: Detecting every failure set additionally requires that every relevant failure contain a metric ball of the target radius, or another regularity/margin condition.
- Objection: Correct in spirit but the quantifier structure is inverted relative to what is proven. The grid certificate guarantees detection of failures containing a ball of radius delta ONLY IF the test evaluates densely enough AND the failure intersects the sampled set or its delta-neighborhood. A failure set containing a delta-ball can still straddle sample points adversarially unless the covering-radius argument is invoked with closed balls and the failure's ball is centered anywhere in X. The clause as written asserts necessity ('requires') without proving necessity — a failure set of measure zero but nonempty (e.g., a single point) is detectable by luck and undetectable by any finite test with certainty; necessity of the margin condition is plausible but unproven here.
- Model verdict: needs-assumption (major)
- Proposed repair: Either prove the converse (any finite test misses some failure set lacking interior — easy via the same B_X argument) or downgrade the modal claim from 'requires' to 'a sufficient condition is'; state both directions explicitly with the closed-ball convention.
- Local status: **accepted wording correction**
- Local reason: A closed failure ball of radius `delta` is hit when covering radius is at most `delta`; an open failure ball is guaranteed hit only when its radius is strictly larger than the covering radius. The report now states this explicitly as a sufficient condition.

## 5. grid_count_arithmetic

- Target: hence rho<=delta is achieved by n=ceil(1+sqrt(d)/(2 delta))^d. For d=20, delta=.05 this is 46^20 ~=1.80e33.
- Objection: Arithmetic check: ceil(1 + sqrt(20)/(0.1)) = ceil(1 + 44.72) = 46, correct. 46^20 = exp(20 ln 46) = exp(76.66) ≈ 1.83e33, so '~1.80e33' is acceptable to two significant figures. However the formula conflates m (points per axis) with the exponent base correctly, but the strict/non-strict inequality at the boundary: rho = sqrt(d)/(2(m-1)) <= delta requires m-1 >= sqrt(d)/(2delta), i.e., m >= 1 + sqrt(d)/(2delta); ceil achieves this with equality-or-excess, so the endpoint case is handled. No error found; recorded to confirm audit coverage.
- Model verdict: invalid (minor)
- Proposed repair: None needed; optionally write 46^20 ≈ 1.83e33 for precision.
- Local status: **rejected; arithmetic confirmed locally**
- Local reason: The exact integer is `46^20 = 1,799,519,816,997,495,209,117,766,334,283,776`, so `1.80e33` is correct. The model's `1.83e33` came from a rough logarithm.
