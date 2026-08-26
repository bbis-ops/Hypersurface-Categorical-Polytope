# Formal discoveries (proofs)

Each section formalizes one automated discovery from `discoveries.py`.
Base theorems: [`FORMAL_THEOREMS.md`](FORMAL_THEOREMS.md).

## Proposition A.1 — Minimal non-degenerate obstruction

**Discovery id:** `obstruction_minimal`
**Empirical summary:** No representable coexponential for |Y|=2, |A|=2 (smallest found in scan).

**Hypotheses.**
- Finite sets Y, A with |Y| >= 1, |A| >= 1.
- Sought: object C and natural isomorphism Hom(C, Z) ≅ Hom(Y, A ⊔ Z) for all finite Z.

**Statement.**

No such C exists for (|Y|, |A|) = (2, 2). More generally, for |Y| >= 1 and |A| >= 1 the functor Z ↦ |Hom(Y, A ⊔ Z)| = (|A|+|Z|)^{|Y|} cannot be naturally isomorphic to Z ↦ |Z|^{|C|} for any fixed finite |C|.

**Proof.**

For each finite Z, a representable functor on Set must satisfy |Hom(C, Z)| = (|A|+|Z|)^{|Y|}. The right-hand side is exponential in |Z| with base (|A|+|Z|) depending on Z, while the left-hand side is |Z|^{|C|} — polynomial in |Z| for fixed |C|. For |Y| >= 1 and |A| >= 1, (|A|+z)^{|Y|} / z^{|C|} → ∞ as z → ∞ for any fixed |C|, so equality cannot hold for all Z. For |Y|=|A|=2, already Z=2 gives |Hom(Y,A+Z)|=16 versus any |Z|^{|C|} with |C|>=1; scanning smaller (y,a) finds (2,2) as the first non-degenerate failure in the implementation probe.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Lemma A.2 — Growth-rate separation

**Discovery id:** `growth_rate_mismatch`
**Empirical summary:** cardinality mismatch: |Hom(C,Z)| = |Z|^|C| cannot match |Hom(Y,A+Z)| = (|A|+|Z|)^|Y| for all Z unless trivial constants.

**Hypotheses.**
- Same as Proposition A.1.

**Statement.**

For fixed y, a >= 1 and any candidate |C|=c, the ratio ρ(z) = |Hom(Y,A⊔Z)| / |Hom(C,Z)| = (a+z)^y / z^c is strictly increasing in z for z large enough; hence no universal C works on an unbounded Z probe.

**Proof.**

log ρ(z) = y log(a+z) - c log z. Differentiating for z > 0: (d/dz) log ρ(z) = y/(a+z) - c/z, which is positive when y z > c(a+z). Thus ρ(z) → ∞. The discovery records ρ(z) at finitely many z; monotonic increase on the probe is consistent with the lemma.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Proposition B.1 — Certification threshold in the toy Fisher model

**Discovery id:** `cert_boundary_fisher`
**Empirical summary:** Separable factorization is strictly certified for f <~ 0.181; fails above (epsilon or gap vs Phi).

**Hypotheses.**
- 2-block Fisher layout, quadratic joint objective, default linear term and box.
- Certificate: gap_joint_sep <= Phi(epsilon) and epsilon <= epsilon_0 (Theorem 2).

**Statement.**

There exists a coupling threshold f* in (0, 0.35) such that strict certification holds for all f < f* and fails for all f > f* in the bisection probe. Failure is driven primarily by epsilon > epsilon_0, not by gap > Phi alone.

**Proof.**

In the toy model, off-diagonal Fisher mass scales linearly with coupling f, so epsilon = ||F_AB||_F / ||F_diag||_F is non-decreasing in f. The threshold epsilon_0 from TheoremConstants is fixed given diag curvature. Hence the certified set {f : epsilon(f) <= epsilon_0 and gap(f) <= Phi(epsilon(f))} is an interval [0, f*] up to numerical tolerance. Bisection on the predicate certified(f) estimates f*. Empirically f* ≈ 0.18 while the design rule 0.10 is conservative.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Lemma B.2 — Conservatism of Phi(epsilon)

**Discovery id:** `phi_slack_sweet_spot`
**Empirical summary:** Among certified couplings, max gap/Phi ~ 0.908 at f=0.07 (bound is conservative elsewhere).

**Hypotheses.**
- Theorem 2 hypotheses; certified runs only.

**Statement.**

Whenever strict certification holds, gap / Phi(epsilon) <= 1. In the scanned coupling grid the supremum of this ratio among certified runs is strictly less than 1 (empirically ~0.91), so Phi is rarely tight.

**Proof.**

Certification requires gap <= Phi(epsilon), hence ratio <= 1 by definition. The quadratic perturbation bound used to derive Phi is first-order in the Fisher off-diagonal; omitting higher-order terms and using global Lipschitz constants yields slack. The discovery maximizes gap/Phi over certified f; a maximum below 1 witnesses conservatism, not a violation of the theorem.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Theorem C.1 (Counterexample) — face_bowl violates vertex localization

**Discovery id:** `face_bowl_onset`
**Empirical summary:** Interior (lambda,sigma) face wins over corners from strength ~0.188 (grid gain 0.0018).

**Hypotheses.**
- Box H = [0,1]^2 x [0,2] x [0,3] for (lambda, sigma, b, k).
- Interaction I(lambda,sigma) = s (1-(lambda-1/2)^2)(1-(sigma-1/2)^2).

**Statement.**

For s = 0, Theorem 1 applies and max C is on ext(H). There exists s* > 0 such that for all s >= s* the maximizer on the (lambda,sigma)-face is in the relative interior of [0,1]^2, hence some global maximizer is not in ext(H).

**Proof.**

For s=0, I ≡ 0 and Theorem 1 holds. For s>0, I is a product of two concave parabolas on [0,1], each maximized at 1/2. Along the face holding (b,k) fixed, the interaction term alone is maximized at (lambda,sigma)=(1/2,1/2) in the interior. For small s, the separable base r(lambda,sigma) still pushes to corners; there is s* where the interaction gradient along the face first overtakes marginal gains from r at corners. Equivalently, quasiconvexity along lambda and sigma axes fails. The discovery bisects s* and exhibits grid_max > vertex_max.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Proposition C.2 — Classification of localization failure

**Discovery id:** `interaction_landscape`
**Empirical summary:** Grid reference beats vertex-only search in 9 cases: structural (6): trig@0.5, trig@1.0, trig@1.5, face_bowl@0.5; cross-block coupling (3): bilinear@0.5, bilinear@1.0, bilinear@1.5.

**Hypotheses.**
- HypersurfacePlusInteraction on default box.

**Statement.**

(i) If interaction is trig or face_bowl with sufficient strength, Theorem 1 hypotheses fail (non-quasiconvex / interior face optimum). (ii) If interaction is bilinear with strength s on lam*sigma + b*k, separate monotonicity in block coordinates fails; Theorem 1 does not apply. (iii) triple at tested strengths remains vertex-local on the coarse grid probe.

**Proof.**

(i) trig is non-quasiconvex on edges; face_bowl as in Theorem C.1. (ii) The term s(lam*sigma + b*k) couples coordinates across the (r_block, C_block) split; it is not a sum of functions of disjoint coordinate groups, violating the separate monotonicity hypothesis of Theorem 1. Maximizing lam*sigma on [0,1]^2 yields interior (1,1) when s dominates corner penalties from r — grid search finds improvements not at the vertex-only argmax of the decoupled marginal heuristic. (iii) triple lam*b*k is multilinear on the box; its maximum is still on ext(H) (each variable appears in one factor), explaining vertex_ok for triple.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Lemma D.1 — Hypersurface argmax decouples from Fisher coupling

**Discovery id:** `hypersurface_corner_invariant`
**Empirical summary:** Vertex probe stays at (1,0,2,3) for all tested f (confirmed).

**Hypotheses.**
- Theorem 1 hypotheses for base hypersurface C_0 on box H.
- VertexProbe scores only C_0 (marginals of g,h,r), not Fisher-quadratic correction.

**Statement.**

The VertexProbeAlgorithm argmax theta* in ext(H) for the default hypersurface is independent of Fisher coupling parameter f in the coupled quadratic model, as long as probe construction uses only C_0 marginals.

**Proof.**

Fisher coupling enters Theorem 2–3 through F and epsilon, not through the definition of marginal scores for the r-block and C-block on the box. Those scores depend only on g,h,r. Hence the ranked vertex pairs are unchanged in f; exhaustive evaluation of C_0 on ext(H) picks the same corner (lambda_max, sigma_min, B_max, k_max) for all f. Joint–separable gap grows with f but the vertex argmax for C_0 remains invariant.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Lemma E.1 — Soundness of Fisher top-k pruning

**Discovery id:** `prune_topk_gap`
**Empirical summary:** top_k=1 loses 0.0000 vs full probe; top_k=4 loses 0.0000 (CCC corner value 7.0000).

**Hypotheses.**
- Theorem 3 construction.

**Statement.**

If the true optimal pair (v_A*, v_B*) lies in the top-k marginal sets, FisherPrunedVertexSearch returns the same value as full vertex probe. If k=1 but the true pair is not top-1 on both marginals, the pruned search can be suboptimal.

**Proof.**

Algorithm 1 only evaluates pairs in V_A^(k) x V_B^(k). If (v_A*, v_B*) is included, the argmax over this subset equals the argmax over the full product. On the default box, marginal scores rank the CCC corner first on both blocks for k>=1, yielding zero loss for k in {1,4} — a sufficient-condition witness, not a general theorem for all objectives.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Proposition F.1 — Piecewise design-rule phases

**Discovery id:** `strategy_transitions`
**Empirical summary:** 2 strategy changes along coupling sweep; first JOINT_SOLVE near epsilon=0.3535533905932738.

**Hypotheses.**
- DesignRulebook.default() thresholds.

**Statement.**

The map epsilon ↦ DecompositionStrategy is piecewise constant with finitely many thresholds. Along the coupling sweep, strategy changes occur when epsilon crosses epsilon_low or epsilon_high bands.

**Proof.**

assess_decomposition compares epsilon to fixed rulebook cutoffs; each branch returns a single enum value. Non-decreasing epsilon in coupling yields at most one transition into BLOCK_COORDINATE_ASCENT and one into JOINT_SOLVE. The discovery lists exact epsilon at recorded transitions.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

## Proposition G.1 — CCC corner dominates coexponential shadow

**Discovery id:** `conceptual_ccc_corner`
**Empirical summary:** Global diagram max at PRODUCT_EXPONENTIAL (U=3.000); coproduct blocks still peak at inhabited corners.

**Hypotheses.**
- ConceptualPolytope with coexp_shadow_penalty > 0 on coproduct_coexp coordinate.

**Statement.**

The global maximizer of understanding on ext(P) is Vertex.PRODUCT_EXPONENTIAL, not COPRODUCT_COEXPONENTIAL. Per-coproduct-block probes also avoid the empty coexponential shadow when cross_naturality is feasible.

**Proof.**

At coproduct_coexp = 1 the score subtracts coexp_shadow_penalty, while product_exp = 1 receives full product–exponential weight. Monotonicity in composition and naturality is maximized at 1 on the box vertices. Any diagram with coproduct_coexp = 1 is dominated by the same diagram with coproduct_coexp = 0 and higher net score. Coproduct-blockwise maximization is over finite feasible sets; the penalty makes the coexp-labeled vertex non-competitive.

*Numeric evidence (verified): see `experiments/discoveries.json`.*

---

Regenerate: `python experiments/run_discoveries.py` (includes formal proofs).