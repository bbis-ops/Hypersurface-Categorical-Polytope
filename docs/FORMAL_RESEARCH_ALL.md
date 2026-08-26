# Formal proofs: research + Friday (H.1–H.10)

## Proposition H.1 — Localization is interaction-geometric

**Discovery:** `localization_signature_geometric`

**Statement.** If I violates axis quasiconvexity (e.g. face_bowl), the onset strength s* for grid > vertex is independent of whether a coexponential exists in the ambient category.

**Proof.** Theorem C.1 uses only calculus on H and the form of I. The coexponential functor is absent from the argmax. Toy sweep labels settings with different hom-cardinality growth but runs the same I on H; equal onset in evidence confirms decoupling.

## Lemma H.2 — Weighted enrichment moves epsilon

**Discovery:** `enriched_epsilon_cert_flip`

**Statement.** epsilon_w = ||W o F_off|| / ||W o F_diag|| can differ from epsilon; strict certification in Theorem 2 can flip when weights stress cross-blocks.

**Proof.** W scales off-diagonals differently from diagonals. Increasing cross_weight or asymmetric block_weights raises epsilon_w without changing the underlying statistical sample. certify_suboptimality is evaluated on epsilon_w, so certification is enrichment-dependent.

## Proposition H.3 — Live epsilon detects interior need

**Discovery:** `learner_interior_switch`

**Statement.** If C(theta_grid) - C(theta_vertex) > tau, corner-hunting is unsound. A live session with increasing interaction strength exhibits a phase transition to INTERIOR_SEARCH.

**Proof.** Directly Theorem C.1: when the maximum is not in ext(H), any algorithm restricted to vertices is suboptimal. empirical_fisher_at supplies epsilon_hat for Theorem 2 thresholds; gap_vertex_grid supplies the localization witness. recommend_search_mode prioritizes the gap witness over epsilon when gap > tau.

## Lemma H.4 — Objectwise exponential on a finite site

**Discovery:** `presheaf_site_exponential`

**Statement.** For each object c, (F^G)(c) = F(c)^{G(c)} exists as a set; this does not globalize to a Set coexponential representing Z -> Hom(Y, A+Z) for all Z.

**Proof.** Exponentials in presheaf categories are computed pointwise. The site probe lists exp_size per object and cover products; Set obstruction remains global. Local true, global false.

## Lemma H.5 — Lawvere weighting reduces leakage

**Discovery:** `lawvere_metric_epsilon`

**Statement.** epsilon_Lawvere <= epsilon_plain for large d_01, with strict inequality when off-diagonal Fisher mass is positive.

**Proof.** Off-diagonal terms scale by exp(-d); diagonal blocks at bi=bj use weight 1. Increasing d shrinks the enriched off-diagonal norm without changing the plain Fisher matrix.

## Proposition H.6 — Trajectory logging witnesses interior phase

**Discovery:** `learner_trajectory_interior`

**Statement.** Along a strength-ramping random walk, there exists a step t with INTERIOR_SEARCH recommended before later block-coordinate steps.

**Proof.** Each append_state computes empirical Fisher and grid-vertex gap. When gap > tau, recommend_search_mode returns INTERIOR_SEARCH (Proposition H.3). Ramping strength triggers the same phase transition as LearnerSession.detect_mode_switch.

## Proposition H.7 — Enriched UP local vs global

**Discovery:** `enriched_coexp_up`

**Hypotheses.**
- Presheaf or pointed enrichment; probe Z in a finite range.

**Statement.** A representing object for the enriched hom functor may exist locally (per site object or via suspension proxy) while the global Set universal property Hom(C,Z) ~= Hom(Y,A+Z) still fails.

**Proof.** Pointwise exponentials F(c)^{G(c)} define a presheaf C, not a single set C. Cardinality growth in Z remains incompatible with |Z|^{|C|} for one fixed |C|. Fisher certification and vertex localization on box H are unchanged because they depend on the objective, not on representability of the coexp functor.

## Lemma H.8 — Lawvere delays epsilon_0 crossing

**Discovery:** `lawvere_face_bowl_threshold`

**Hypotheses.**
- face_bowl on H; block Fisher coupling scales with strength.
- Lawvere weight exp(-d) on off-diagonals.

**Statement.** epsilon_Lawvere crosses epsilon_0 at a strictly later strength than epsilon_plain (or not at all in [0,0.9] when d is large). INTERIOR_SEARCH onset from grid-vertex gap is independent of d.

**Proof.** gap_vertex_grid depends only on C on H, not on the Lawvere metric. epsilon_plain and epsilon_Lawvere use the same Fisher matrix but different norms; exp(-d) shrinks off-diagonal mass, delaying the threshold crossing that triggers block-coordinate advice.

## Theorem H.9 — Certification sheaf on a finite site

**Discovery:** `sheafified_certificate`

**Hypotheses.**
- Finite site with covers; stalks carry (epsilon, Phi, delta).

**Statement.** There is a presheaf of certification data whose sections over c are (epsilon_c, Phi_c, delta_c) and whose restrictions on a cover satisfy relative descent; global certification uses max epsilon.

**Proof.** Build CertificateSheaf: each object gets a section from a block Fisher with stalk-scaled coupling. Restriction maps are inclusions on the cover diagram. gluing_ok checks relative agreement on overlaps (UV with U,V). This internalizes Theorem 2 bounds as geometric data in the site, not a single global scalar.

## Proposition H.10 — Category-learning phenomenology

**Discovery:** `category_learning_phenomenology`

**Hypotheses.**
- Scripted or turn-based adjunction curriculum.
- Live epsilon after each state.

**Statement.** A learner internalizing adjunctions exhibits CORNER_HUNTING while blocks feel separable, then INTERIOR_SEARCH once cross-naturality and face_bowl coupling raise grid-vertex gap above tolerance.

**Proof.** CategoryLearningSession and CategoryLearningTutor log states in H. Early beats have low strength and zero gap; coexp confusion increases strength and gap. recommend_search_mode switches when gap > tau (Proposition H.3). Phenomenology strings record the narrative at each switch — observable in human or LLM tutoring loops.
