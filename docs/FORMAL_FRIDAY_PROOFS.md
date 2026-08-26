# Formal Friday proofs (H.7–H.10)

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
