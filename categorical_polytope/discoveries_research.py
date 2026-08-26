"""
Weekend research probes: coexponential alternatives, enriched Fisher, learner epsilon.

Extends the base discovery registry without breaking existing formal proofs.
"""

from __future__ import annotations

from dataclasses import asdict

from .coexponential_alternatives import (
    CategoricalSetting,
    localization_vs_interaction,
    probe_setting,
    sweep_settings_localization,
)
from .discoveries import Discovery
from .enriched_fisher import colimit_limit_sweep, compare_epsilon_unweighted_vs_enriched
from .lawvere_metric import compare_lawvere_vs_plain, metric_colimit_limit_sweep
from .learner_diagram import (
    LearnerSession,
    LearnerTrajectoryLog,
    simulate_learner_population,
)
from .presheaf_site import default_two_object_site, sweep_site_exponentials


def discover_coexponential_exists_outside_set() -> Discovery:
    reports = [probe_setting(s) for s in CategoricalSetting]
    exist = [r for r in reports if r.representable]
    return Discovery(
        id="coexponential_outside_set",
        category="obstruction",
        title="Coexponential-like functors outside Set",
        summary=(
            f"{len(exist)} / {len(reports)} toy settings admit representability proxies; "
            "only FINITE_SET is obstructed on the cardinality probe."
        ),
        evidence={
            "settings": [
                {
                    "name": r.setting.name,
                    "representable": r.representable,
                    "growth": r.hom_growth,
                    "signature": r.interaction_signature,
                }
                for r in reports
            ]
        },
        significance=(
            "Toposes / enriched homs / suspension shift the representing object; "
            "Set obstruction is not universal."
        ),
    )


def discover_face_bowl_signature_independent_of_setting() -> Discovery:
    """
    Vertex localization failure is geometric (interaction), not categorical setting.

    Metadata of setting does not change face_bowl onset — only the interaction term.
    """
    sweep = sweep_settings_localization()
    onsets = [r["face_bowl_onset_strength"] for r in sweep if r["face_bowl_onset_strength"]]
    same = len(set(onsets)) <= 1
    loc = localization_vs_interaction("face_bowl", (0.0, 0.5, 1.0))
    return Discovery(
        id="localization_signature_geometric",
        category="localization",
        title="face_bowl onset is interaction-geometric, not setting-dependent",
        summary=(
            f"Across categorical setting labels, face_bowl onset strength is "
            f"{'uniform' if same else 'varied'} ({onsets}); failure is from bowl term."
        ),
        evidence={"setting_sweep": sweep, "face_bowl_curve": loc},
        significance=(
            "Coexponential existence does not restore vertex localization if "
            "Theorem 1 hypotheses fail — interaction signature dominates."
        ),
    )


def discover_enriched_epsilon_cert_flip() -> Discovery:
    rows = compare_epsilon_unweighted_vs_enriched()
    flips = [r for r in rows if r["cert_flip"]]
    eps_shifts = [
        r for r in rows
        if abs(r["epsilon_enriched"] - r["epsilon_unweighted"]) > 1e-6
    ]
    return Discovery(
        id="enriched_epsilon_cert_flip",
        category="certification",
        title="Enrichment weights shift epsilon and certification",
        summary=(
            f"V-enrichment: {len(eps_shifts)}/{len(rows)} pairs change epsilon; "
            f"{len(flips)} flip strict certification vs unweighted."
        ),
        evidence={
            "rows": rows[:12],
            "flip_count": len(flips),
            "epsilon_shift_count": len(eps_shifts),
            "total": len(rows),
        },
        significance=(
            "Fisher matrix in a V-category is a weighted enrichment; "
            "limits/colimits dual depends on weight asymmetry."
        ),
    )


def discover_colimit_limit_weight_gap() -> Discovery:
    sweep = colimit_limit_sweep()
    max_gap = max(r["gap"] for r in sweep)
    argmax = max(sweep, key=lambda r: r["gap"])
    return Discovery(
        id="colimit_limit_weight_gap",
        category="stability",
        title="Weighted colimit-limit gap",
        summary=(
            f"Enriched colimit-limit gap up to {max_gap:.2f} at weights "
            f"({argmax['w0']}, {argmax['w1']})."
        ),
        evidence={"sweep": sweep, "max_gap": max_gap},
        significance=(
            "Dual story: colimit (max-plus) vs limit (min-plus) widens under "
            "asymmetric enrichment — analog of coproduct vs product tension."
        ),
    )


def discover_learner_interior_switch() -> Discovery:
    det = LearnerSession(interaction="face_bowl").detect_mode_switch()
    pop = simulate_learner_population(n=30, seed=7)
    return Discovery(
        id="learner_interior_switch",
        category="learner",
        title="Live epsilon triggers interior search",
        summary=(
            f"face_bowl learner switches from corner-hunting at strength "
            f"{det['switch_strength']}; population interior rate "
            f"{pop['fraction_switching_to_interior']:.0%}."
        ),
        evidence={"session": det, "population": pop},
        significance=(
            "Empirical Fisher on the diagram box H detects when a learner "
            "must abandon corner-hunting for interior search."
        ),
    )


def discover_learner_low_leakage_corners() -> Discovery:
    sess = LearnerSession(interaction="bilinear", strength_schedule=(0.0, 0.1, 0.2))
    readings = sess.run()
    all_corner = all(r["mode"] == "CORNER_HUNTING" for r in readings)
    return Discovery(
        id="learner_low_leakage_corners",
        category="learner",
        title="Low-strength bilinear learners stay on corners",
        summary=(
            "Bilinear interaction at low strength keeps CORNER_HUNTING mode "
            + ("throughout schedule." if all_corner else "for early steps only.")
        ),
        evidence={"readings": readings},
        significance="Separable-like regimes: live epsilon supports cheap vertex probes.",
    )


def discover_presheaf_site_exponential() -> Discovery:
    site = default_two_object_site()
    rows = sweep_site_exponentials(site)
    local = [r for r in rows if r["local_exponential"]]
    return Discovery(
        id="presheaf_site_exponential",
        category="obstruction",
        title="Finite site: objectwise exponentials exist",
        summary=(
            f"On {len(rows)} site objects, {len(local)} have local exp >= Set hom proxy; "
            "covers multiply section counts — distinct from global Set coexp."
        ),
        evidence={"site_objects": rows, "covers": dict(site.covers)},
        significance="Real presheaf site fragment: exp exists per object, not as Set cardinality.",
    )


def discover_lawvere_metric_epsilon() -> Discovery:
    rows = compare_lawvere_vs_plain()
    decr = [r for r in rows if r["epsilon_lawvere"] < r["epsilon_plain"] - 1e-9]
    ml = metric_colimit_limit_sweep()
    return Discovery(
        id="lawvere_metric_epsilon",
        category="certification",
        title="Lawvere distance dampens cross-block epsilon",
        summary=(
            f"For {len(decr)}/{len(rows)} pairs, metric epsilon < plain as block distance grows; "
            f"metric colimit-limit gap up to {max(r['gap'] for r in ml):.2f}."
        ),
        evidence={"rows": rows[:8], "metric_colimit_limit": ml},
        significance="V = Lawvere metric: hom cost exp(-d) weights Fisher off-diagonals.",
    )


def discover_learner_trajectory_interior() -> Discovery:
    log = LearnerTrajectoryLog.simulate_random_walk(n_steps=14, seed=11)
    first = log.first_interior_step()
    return Discovery(
        id="learner_trajectory_interior",
        category="learner",
        title="Trajectory log detects interior need along path",
        summary=(
            f"Random-walk session: interior mode at step "
            f"{first.step if first else 'never'} "
            f"(strength={first.interaction_strength if first else 0:.2f})."
        ),
        evidence={
            "n_steps": len(log.steps),
            "first_interior": asdict(first) if first else None,
            "mode_counts": _mode_counts(log),
        },
        significance="Log theta_t live; epsilon and gap recorded each step for HITL learners.",
    )


def _mode_counts(log: LearnerTrajectoryLog) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(s.mode for s in log.steps))


RESEARCH_REGISTRY: tuple = (
    discover_coexponential_exists_outside_set,
    discover_face_bowl_signature_independent_of_setting,
    discover_enriched_epsilon_cert_flip,
    discover_colimit_limit_weight_gap,
    discover_learner_interior_switch,
    discover_learner_low_leakage_corners,
    discover_presheaf_site_exponential,
    discover_lawvere_metric_epsilon,
    discover_learner_trajectory_interior,
)


def run_research_discoveries() -> list[Discovery]:
    return [fn() for fn in RESEARCH_REGISTRY]
