"""
Friday–Saturday immediate probes (batch 2).
"""

from __future__ import annotations

from .discoveries import Discovery
from .enriched_coexp import fisher_cert_vs_vertex_localization, probe_enriched_universal_property
from .coexponential_alternatives import CategoricalSetting
from .lawvere_face_bowl import probe_lawvere_face_bowl_onset
from .sheaf_certificate import full_sheaf_report, probe_sheafified_certificate
from .category_learning_session import run_default_session
from .presheaf_site import larger_site, sweep_site_exponentials


def discover_enriched_coexp_up() -> Discovery:
    bundle = fisher_cert_vs_vertex_localization(
        fisher_couplings=(0.0, 0.1, 0.25),
        interaction="face_bowl",
        strengths=(0.0, 0.5, 1.0),
    )
    pres = probe_enriched_universal_property(CategoricalSetting.PRESHEAF_TOY)
    pnt = probe_enriched_universal_property(CategoricalSetting.POINTED_SUSPENSION)
    loc_fb = [r for r in bundle["localization"] if r["interaction"] == "face_bowl"]
    return Discovery(
        id="enriched_coexp_up",
        category="obstruction",
        title="Enriched UP: presheaf/pointed vs Fisher–localization decoupling",
        summary=(
            f"Presheaf UP exact={pres.up_holds_on_probe}; pointed UP exact={pnt.up_holds_on_probe}. "
            "Fisher cert and vertex_ok remain decoupled on the same box."
        ),
        evidence={
            "presheaf": {
                "exists": pres.representing_object_exists,
                "up": pres.up_holds_on_probe,
                "hom_coproduct": pres.hom_coproduct,
                "hom_rep": pres.hom_representing,
            },
            "pointed": {
                "exists": pnt.representing_object_exists,
                "up": pnt.up_holds_on_probe,
            },
            "bundle": bundle,
            "face_bowl_localization": loc_fb,
        },
        significance=(
            "Enriched representing objects may exist locally; Theorem 1 / Fisher "
            "still diagnose factorization vs geometry independently."
        ),
    )


def discover_lawvere_face_bowl_threshold() -> Discovery:
    probe = probe_lawvere_face_bowl_onset()
    onsets = probe["onsets_by_distance"]
    delayed = probe.get("prediction_epsilon_delayed", False)
    return Discovery(
        id="lawvere_face_bowl_threshold",
        category="learner",
        title="Lawvere damping delays epsilon_0 crossing (interior gap-driven)",
        summary=(
            f"epsilon > epsilon_0: plain crosses at {probe.get('epsilon_cross_plain')}; "
            f"Lawvere (d=2) at {probe.get('epsilon_cross_lawvere_d2') or 'not in [0,0.9]'} "
            f"(prediction={delayed}). INTERIOR onset ~{probe.get('interior_onset_plain_d0')} is gap-only."
        ),
        evidence=probe,
        significance=probe["prediction"],
    )


def discover_sheafified_certificate() -> Discovery:
    report = full_sheaf_report()
    rows = report["coupling_sweep"]
    glued = sum(1 for r in rows if r["gluing_ok"])
    large = report["sites"][-1]["gluing_ok"] if report["sites"] else False
    return Discovery(
        id="sheafified_certificate",
        category="certification",
        title="epsilon / Phi / delta as a sheaf over the site",
        summary=(
            f"CertificateSheaf: {glued}/{len(rows)} couplings glue on 3-object site; "
            f"5-object larger_site gluing_ok={large}; global epsilon = max stalk."
        ),
        evidence=report,
        significance=(
            "Certification is geometric: stalks over U,V,UV with restriction — "
            "descent holds in toy probe."
        ),
    )


def discover_category_learning_phenomenology() -> Discovery:
    summary = run_default_session()
    return Discovery(
        id="category_learning_phenomenology",
        category="learner",
        title="Adjunction-learning session forces interior search",
        summary=summary["qualitative"],
        evidence=summary,
        significance=(
            "Human/LLM-scale narrative: confusion on coexp couples faces; "
            "live detector switches mode when grid beats vertices."
        ),
    )


def discover_larger_site_coexp() -> Discovery:
    rows = sweep_site_exponentials(larger_site())
    local = sum(1 for r in rows if r["local_exponential"])
    return Discovery(
        id="larger_site_coexp",
        category="obstruction",
        title="Larger site: objectwise exponentials",
        summary=(
            f"5-object site: {local}/{len(rows)} objects have local exp >= Set hom proxy."
        ),
        evidence={"objects": rows},
        significance="Extends presheaf probe beyond 3-object toy.",
    )


FRIDAY_REGISTRY: tuple = (
    discover_enriched_coexp_up,
    discover_lawvere_face_bowl_threshold,
    discover_sheafified_certificate,
    discover_category_learning_phenomenology,
    discover_larger_site_coexp,
)


def run_friday_discoveries() -> list[Discovery]:
    return [fn() for fn in FRIDAY_REGISTRY]
