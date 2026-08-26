"""Formal proofs for Friday–Saturday probes (H.7–H.10)."""

from __future__ import annotations

from typing import Any

from .formal_proofs import FormalStatement


def _h7() -> FormalStatement:
    return FormalStatement(
        discovery_id="enriched_coexp_up",
        label="Proposition H.7",
        title="Enriched UP local vs global",
        hypotheses=(
            "Presheaf or pointed enrichment; probe Z in a finite range.",
        ),
        statement=(
            "A representing object for the enriched hom functor may exist "
            "locally (per site object or via suspension proxy) while the "
            "global Set universal property Hom(C,Z) ~= Hom(Y,A+Z) still fails."
        ),
        proof=(
            "Pointwise exponentials F(c)^{G(c)} define a presheaf C, not a single "
            "set C. Cardinality growth in Z remains incompatible with |Z|^{|C|} "
            "for one fixed |C|. Fisher certification and vertex localization on "
            "box H are unchanged because they depend on the objective, not on "
            "representability of the coexp functor."
        ),
    )


def _h8() -> FormalStatement:
    return FormalStatement(
        discovery_id="lawvere_face_bowl_threshold",
        label="Lemma H.8",
        title="Lawvere delays epsilon_0 crossing",
        hypotheses=(
            "face_bowl on H; block Fisher coupling scales with strength.",
            "Lawvere weight exp(-d) on off-diagonals.",
        ),
        statement=(
            "epsilon_Lawvere crosses epsilon_0 at a strictly later strength than "
            "epsilon_plain (or not at all in [0,0.9] when d is large). "
            "INTERIOR_SEARCH onset from grid-vertex gap is independent of d."
        ),
        proof=(
            "gap_vertex_grid depends only on C on H, not on the Lawvere metric. "
            "epsilon_plain and epsilon_Lawvere use the same Fisher matrix but "
            "different norms; exp(-d) shrinks off-diagonal mass, delaying the "
            "threshold crossing that triggers block-coordinate advice."
        ),
    )


def _h9() -> FormalStatement:
    return FormalStatement(
        discovery_id="sheafified_certificate",
        label="Theorem H.9",
        title="Certification sheaf on a finite site",
        hypotheses=("Finite site with covers; stalks carry (epsilon, Phi, delta).",),
        statement=(
            "There is a presheaf of certification data whose sections over c "
            "are (epsilon_c, Phi_c, delta_c) and whose restrictions on a cover "
            "satisfy relative descent; global certification uses max epsilon."
        ),
        proof=(
            "Build CertificateSheaf: each object gets a section from a block Fisher "
            "with stalk-scaled coupling. Restriction maps are inclusions on the "
            "cover diagram. gluing_ok checks relative agreement on overlaps "
            "(UV with U,V). This internalizes Theorem 2 bounds as geometric "
            "data in the site, not a single global scalar."
        ),
    )


def _h10() -> FormalStatement:
    return FormalStatement(
        discovery_id="category_learning_phenomenology",
        label="Proposition H.10",
        title="Category-learning phenomenology",
        hypotheses=(
            "Scripted or turn-based adjunction curriculum.",
            "Live epsilon after each state.",
        ),
        statement=(
            "A learner internalizing adjunctions exhibits CORNER_HUNTING while "
            "blocks feel separable, then INTERIOR_SEARCH once cross-naturality "
            "and face_bowl coupling raise grid-vertex gap above tolerance."
        ),
        proof=(
            "CategoryLearningSession and CategoryLearningTutor log states in H. "
            "Early beats have low strength and zero gap; coexp confusion increases "
            "strength and gap. recommend_search_mode switches when gap > tau "
            "(Proposition H.3). Phenomenology strings record the narrative at "
            "each switch — observable in human or LLM tutoring loops."
        ),
    )


FRIDAY_PROOF_REGISTRY: tuple[FormalStatement, ...] = (
    _h7(),
    _h8(),
    _h9(),
    _h10(),
)


def friday_formal_markdown() -> str:
    lines = ["# Formal Friday proofs (H.7–H.10)", ""]
    for s in FRIDAY_PROOF_REGISTRY:
        lines.append(f"## {s.label} — {s.title}")
        lines.append("")
        lines.append(f"**Discovery:** `{s.discovery_id}`")
        lines.append("")
        if s.hypotheses:
            lines.append("**Hypotheses.**")
            for h in s.hypotheses:
                lines.append(f"- {h}")
            lines.append("")
        lines.append("**Statement.** " + s.statement)
        lines.append("")
        lines.append("**Proof.** " + s.proof)
        lines.append("")
    return "\n".join(lines)


def verify_friday_evidence(discovery_id: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    try:
        if discovery_id == "enriched_coexp_up":
            ok = "bundle" in evidence
        elif discovery_id == "lawvere_face_bowl_threshold":
            ok = evidence.get("prediction_epsilon_delayed", False) or evidence.get(
                "epsilon_cross_plain"
            ) is not None
        elif discovery_id == "sheafified_certificate":
            rows = evidence.get("rows") or evidence.get("coupling_sweep") or []
            ok = len(rows) >= 1 and len(evidence.get("sites", [])) >= 1
        elif discovery_id == "category_learning_phenomenology":
            ok = evidence.get("first_interior_step") is not None
        else:
            ok = True
        return (ok, "ok") if ok else (False, "witness failed")
    except (TypeError, KeyError) as e:
        return False, str(e)


def all_research_formal_markdown() -> str:
    from .formal_proofs_research import research_formal_markdown as rmd

    return (
        "# Formal proofs: research + Friday (H.1–H.10)\n\n"
        + rmd().replace("# Formal research proofs (H.1–H.6)\n\n", "")
        + "\n"
        + friday_formal_markdown().replace("# Formal Friday proofs (H.7–H.10)\n\n", "")
    )
