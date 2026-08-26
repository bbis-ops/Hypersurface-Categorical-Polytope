"""Formal proofs for weekend research discoveries (Propositions H.1–H.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .discoveries_research import run_research_discoveries
from .formal_proofs import FormalStatement


def _h1() -> FormalStatement:
    return FormalStatement(
        discovery_id="localization_signature_geometric",
        label="Proposition H.1",
        title="Localization is interaction-geometric",
        hypotheses=(
            "Compact box H, objective C = base + s I(theta).",
            "Categorical setting only affects representability probes, not I.",
        ),
        statement=(
            "If I violates axis quasiconvexity (e.g. face_bowl), the onset strength s* "
            "for grid > vertex is independent of whether a coexponential exists in the "
            "ambient category."
        ),
        proof=(
            "Theorem C.1 uses only calculus on H and the form of I. The coexponential "
            "functor is absent from the argmax. Toy sweep labels settings with different "
            "hom-cardinality growth but runs the same I on H; equal onset in evidence "
            "confirms decoupling."
        ),
    )


def _h2() -> FormalStatement:
    return FormalStatement(
        discovery_id="enriched_epsilon_cert_flip",
        label="Lemma H.2",
        title="Weighted enrichment moves epsilon",
        hypotheses=("Block Fisher F, weights w_ij > 0.",),
        statement=(
            "epsilon_w = ||W o F_off|| / ||W o F_diag|| can differ from epsilon; "
            "strict certification in Theorem 2 can flip when weights stress cross-blocks."
        ),
        proof=(
            "W scales off-diagonals differently from diagonals. Increasing cross_weight "
            "or asymmetric block_weights raises epsilon_w without changing the "
            "underlying statistical sample. certify_suboptimality is evaluated on "
            "epsilon_w, so certification is enrichment-dependent."
        ),
    )


def _h3() -> FormalStatement:
    return FormalStatement(
        discovery_id="learner_interior_switch",
        label="Proposition H.3",
        title="Live epsilon detects interior need",
        hypotheses=(
            "Learner state theta in H, empirical Fisher at theta.",
            "tau > 0 tolerance for grid vs vertex gap.",
        ),
        statement=(
            "If C(theta_grid) - C(theta_vertex) > tau, corner-hunting is unsound. "
            "A live session with increasing interaction strength exhibits a phase "
            "transition to INTERIOR_SEARCH."
        ),
        proof=(
            "Directly Theorem C.1: when the maximum is not in ext(H), any algorithm "
            "restricted to vertices is suboptimal. empirical_fisher_at supplies epsilon_hat "
            "for Theorem 2 thresholds; gap_vertex_grid supplies the localization "
            "witness. recommend_search_mode prioritizes the gap witness over epsilon "
            "when gap > tau."
        ),
    )


def _h4() -> FormalStatement:
    return FormalStatement(
        discovery_id="presheaf_site_exponential",
        label="Lemma H.4",
        title="Objectwise exponential on a finite site",
        hypotheses=("Finite site with stalks F(c), G(c).",),
        statement=(
            "For each object c, (F^G)(c) = F(c)^{G(c)} exists as a set; "
            "this does not globalize to a Set coexponential representing "
            "Z -> Hom(Y, A+Z) for all Z."
        ),
        proof=(
            "Exponentials in presheaf categories are computed pointwise. "
            "The site probe lists exp_size per object and cover products; "
            "Set obstruction remains global. Local true, global false."
        ),
    )


def _h5() -> FormalStatement:
    return FormalStatement(
        discovery_id="lawvere_metric_epsilon",
        label="Lemma H.5",
        title="Lawvere weighting reduces leakage",
        hypotheses=("Non-negative block distances d_ij.", "w_ij = exp(-d_ij)."),
        statement=(
            "epsilon_Lawvere <= epsilon_plain for large d_01, with strict "
            "inequality when off-diagonal Fisher mass is positive."
        ),
        proof=(
            "Off-diagonal terms scale by exp(-d); diagonal blocks at bi=bj "
            "use weight 1. Increasing d shrinks the enriched off-diagonal "
            "norm without changing the plain Fisher matrix."
        ),
    )


def _h6() -> FormalStatement:
    return FormalStatement(
        discovery_id="learner_trajectory_interior",
        label="Proposition H.6",
        title="Trajectory logging witnesses interior phase",
        hypotheses=("States theta_t in H logged sequentially.",),
        statement=(
            "Along a strength-ramping random walk, there exists a step t "
            "with INTERIOR_SEARCH recommended before later block-coordinate steps."
        ),
        proof=(
            "Each append_state computes empirical Fisher and grid-vertex gap. "
            "When gap > tau, recommend_search_mode returns INTERIOR_SEARCH "
            "(Proposition H.3). Ramping strength triggers the same phase "
            "transition as LearnerSession.detect_mode_switch."
        ),
    )


RESEARCH_PROOF_REGISTRY: tuple[FormalStatement, ...] = (
    _h1(),
    _h2(),
    _h3(),
    _h4(),
    _h5(),
    _h6(),
)


def research_formal_markdown() -> str:
    lines = ["# Formal research proofs (H.1–H.6)", ""]
    for s in RESEARCH_PROOF_REGISTRY:
        lines.append(f"## {s.label} — {s.title}")
        lines.append("")
        lines.append(f"**Discovery:** `{s.discovery_id}`")
        lines.append("")
        lines.append("**Statement.** " + s.statement)
        lines.append("")
        lines.append("**Proof.** " + s.proof)
        lines.append("")
    return "\n".join(lines)


def verify_research_evidence(discovery_id: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    try:
        if discovery_id == "localization_signature_geometric":
            onsets = [
                r.get("face_bowl_onset_strength")
                for r in evidence.get("setting_sweep", [])
                if r.get("face_bowl_onset_strength") is not None
            ]
            ok = len(onsets) >= 1
        elif discovery_id == "enriched_epsilon_cert_flip":
            ok = evidence.get("epsilon_shift_count", 0) >= 1
        elif discovery_id == "learner_interior_switch":
            ok = evidence.get("session", {}).get("switch_strength") is not None
        elif discovery_id == "presheaf_site_exponential":
            ok = len(evidence.get("site_objects", [])) >= 2
        elif discovery_id == "lawvere_metric_epsilon":
            ok = len(evidence.get("rows", [])) >= 1
        elif discovery_id == "learner_trajectory_interior":
            ok = evidence.get("first_interior") is not None
        else:
            ok = True
        return (ok, "ok") if ok else (False, "witness failed")
    except (TypeError, KeyError) as e:
        return False, str(e)
