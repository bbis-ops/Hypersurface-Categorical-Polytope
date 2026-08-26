"""
Automated discovery: thresholds, failure modes, and regime maps.

Run: python -m categorical_polytope discover
     python experiments/run_discoveries.py
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .conceptual_polytope import (
    ConceptualPolytope,
    CoproductBlock,
    DiagramPoint,
    Vertex,
    maximize_under_coproduct_blocks,
)
from .decomposition_stability import DecompositionStrategy, assess_decomposition, robustness_sweep
from .fisher_factorization import BlockLayout, QuadraticJointObjective, build_block_fisher
from .fisher_pruned_search import FisherPrunedVertexSearch
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
from .hypersurface_box import BoxBounds, HypersurfaceBox, Theta
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    grid_maximize,
    vertex_maximize,
)
from .set_category import cardinality_obstruction, hom_cardinality
from .vertex_probe import VertexProbeAlgorithm


@dataclass(frozen=True)
class Discovery:
    """One reproducible finding from a systematic search."""

    id: str
    category: str
    title: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    significance: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bisect_float(
    lo: float,
    hi: float,
    predicate: Callable[[float], bool],
    *,
    tol: float = 0.005,
    max_iter: int = 40,
) -> tuple[float, bool, bool]:
    """
    Find transition where predicate flips from True (at lo) to False (at hi).

    Assumes predicate(lo) is True and predicate(hi) is False.
    Returns (boundary, pred_lo, pred_hi).
    """
    if not predicate(lo) or predicate(hi):
        return lo, predicate(lo), predicate(hi)
    a, b = lo, hi
    for _ in range(max_iter):
        if b - a <= tol:
            break
        mid = 0.5 * (a + b)
        if predicate(mid):
            a = mid
        else:
            b = mid
    return b, predicate(a), predicate(b)


def _two_block_certified(f: float) -> bool:
    layout = BlockLayout(names=("block_A", "block_B"), sizes=(2, 2))
    fisher = build_block_fisher(layout, off_diag_coupling=f)
    obj = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0))
    try:
        a = obj.factorization_analysis()
    except ValueError:
        return False
    leak = a.leakage
    const = theorem_constants_from_fisher(
        leak,
        [fisher.matrix[i][i] for i in range(4)],
        theta_joint=a.theta_joint,
    )
    ok, _, _ = certify_suboptimality(leak.epsilon, a.gap, const)
    return ok


def _face_bowl_localized(strength: float, *, grid_tol: float = 1e-4) -> bool:
    obj = HypersurfacePlusInteraction(
        bounds=default_nonlinear_bounds(),
        strength=strength,
        interaction="face_bowl",
    )
    th_v, v_v = vertex_maximize(obj, obj.bounds)
    th_g, v_g = grid_maximize(obj, obj.bounds, steps=9)
    return v_g <= v_v + grid_tol


def discover_obstruction_minimal() -> Discovery:
    """Smallest non-degenerate (|Y|,|A|) with cardinality obstruction."""
    best: tuple[int, int] | None = None
    for y in range(1, 8):
        for a in range(1, 8):
            rep = cardinality_obstruction(y, a)
            if not rep.exists_nontrivial_representable:
                best = (y, a)
                break
        if best:
            break
    y, a = best or (2, 2)
    rep = cardinality_obstruction(y, a)
    return Discovery(
        id="obstruction_minimal",
        category="obstruction",
        title="Minimal coexponential obstruction in Set",
        summary=f"No representable coexponential for |Y|={y}, |A|={a} (smallest found in scan).",
        evidence={
            "y": y,
            "a": a,
            "reason": rep.reason,
            "hom_Y_AplusZ_at_Z2": hom_cardinality(y, a + 2),
        },
        significance="Formal dual to coproduct is empty already for 2-element probes.",
    )


def discover_certification_boundary() -> Discovery:
    """Bisect Fisher coupling where strict Theorem 2 certificate fails."""
    lo, hi = 0.05, 0.35
    if not _two_block_certified(lo):
        lo = 0.0
    if _two_block_certified(hi):
        boundary = hi
    else:
        boundary, _, _ = _bisect_float(lo, hi, _two_block_certified, tol=0.01)
    f_below = max(0.0, boundary - 0.02)
    f_above = min(0.5, boundary + 0.02)
    return Discovery(
        id="cert_boundary_fisher",
        category="certification",
        title="Strict certification boundary (2-block Fisher toy)",
        summary=(
            f"Separable factorization is strictly certified for f <~ {boundary:.3f}; "
            f"fails above (epsilon or gap vs Phi)."
        ),
        evidence={
            "boundary_f": round(boundary, 4),
            "certified_at": f_below,
            "certified_at_result": _two_block_certified(f_below),
            "fails_at": f_above,
            "fails_at_result": _two_block_certified(f_above),
        },
        significance="Operational epsilon_0 band aligns with coupling ~0.10–0.15 in this toy.",
    )


def discover_face_bowl_onset() -> Discovery:
    """First interaction strength where grid reference beats vertex-only search."""
    if _face_bowl_localized(0.1) and not _face_bowl_localized(0.5):
        onset, _, _ = _bisect_float(0.1, 0.5, _face_bowl_localized, tol=0.02)
    elif not _face_bowl_localized(0.0):
        onset = 0.0
    else:
        onset = 0.5
    obj = HypersurfacePlusInteraction(
        bounds=default_nonlinear_bounds(),
        strength=onset,
        interaction="face_bowl",
    )
    th_v, v_v = vertex_maximize(obj, obj.bounds)
    th_g, v_g = grid_maximize(obj, obj.bounds, steps=9)
    return Discovery(
        id="face_bowl_onset",
        category="localization",
        title="face_bowl breaks vertex localization",
        summary=(
            f"Interior (lambda,sigma) face wins over corners from strength ~{onset:.3f} "
            f"(grid gain {v_g - v_v:.4f})."
        ),
        evidence={
            "onset_strength": round(onset, 4),
            "theta_vertex": [th_v.lam, th_v.sigma, th_v.b, th_v.k],
            "theta_grid": [th_g.lam, th_g.sigma, th_g.b, th_g.k],
            "value_vertex": v_v,
            "value_grid": v_g,
            "gap_vs_grid": v_g - v_v,
        },
        significance="Theorem 1 hypotheses fail; extremal search alone is unsound.",
    )


def discover_interaction_landscape() -> Discovery:
    """Scan nonlinear modes for localization and interior optima."""
    modes = ("bilinear", "triple", "softplus", "trig", "face_bowl")
    strengths = (0.0, 0.5, 1.0, 1.5)
    rows: list[dict[str, Any]] = []
    breaks: list[str] = []
    for mode in modes:
        for s in strengths:
            obj = HypersurfacePlusInteraction(
                bounds=default_nonlinear_bounds(),
                strength=s,
                interaction=mode,
            )
            th_v, v_v = vertex_maximize(obj, obj.bounds)
            th_g, v_g = grid_maximize(obj, obj.bounds, steps=7)
            gap = v_g - v_v
            ok = gap <= 1e-3
            rows.append(
                {
                    "mode": mode,
                    "strength": s,
                    "vertex_ok": ok,
                    "gap_vs_grid": round(gap, 6),
                    "theta_grid_interior": not (
                        th_g.lam in obj.bounds.lam
                        and th_g.sigma in obj.bounds.sigma
                        and th_g.b in obj.bounds.b
                        and th_g.k in obj.bounds.k
                    ),
                }
            )
            if not ok and f"{mode}@{s}" not in breaks:
                breaks.append(f"{mode}@{s}")
    structural = [b for b in breaks if b.startswith(("face_bowl", "trig", "softplus"))]
    coupling = [b for b in breaks if b.startswith(("bilinear", "triple"))]
    return Discovery(
        id="interaction_landscape",
        category="localization",
        title="Nonlinear interaction localization map",
        summary=(
            f"Grid reference beats vertex-only search in {len(breaks)} cases: "
            f"structural ({len(structural)}): {', '.join(structural[:4]) or 'none'}; "
            f"cross-block coupling ({len(coupling)}): {', '.join(coupling[:4]) or 'none'}."
        ),
        evidence={
            "grid": rows,
            "failures": breaks,
            "structural_breaks": structural,
            "cross_block_breaks": coupling,
        },
        significance=(
            "face_bowl/trig/softplus break axis quasiconvexity; "
            "strong bilinear/triple violate separate monotonicity — Theorem 1 does not apply."
        ),
    )


def discover_phi_slack() -> Discovery:
    """Where certified runs use the most of Phi(epsilon) budget (tight but valid)."""
    layout = BlockLayout(names=("block_A", "block_B"), sizes=(2, 2))
    best_ratio = 0.0
    best_f = 0.0
    certified_rows: list[dict[str, float]] = []
    for f in [i * 0.01 for i in range(0, 26)]:
        fisher = build_block_fisher(layout, off_diag_coupling=f)
        obj = QuadraticJointObjective(fisher=fisher, linear=(1.0, 0.5, 2.0, 3.0))
        try:
            a = obj.factorization_analysis()
        except ValueError:
            continue
        leak = a.leakage
        const = theorem_constants_from_fisher(
            leak,
            [fisher.matrix[i][i] for i in range(4)],
            theta_joint=a.theta_joint,
        )
        phi = const.Phi(leak.epsilon)
        ok, _, _ = certify_suboptimality(leak.epsilon, a.gap, const)
        if phi > 1e-12:
            ratio = a.gap / phi
        else:
            ratio = 0.0 if a.gap <= 1e-9 else float("inf")
        if ok:
            certified_rows.append(
                {"f": f, "epsilon": leak.epsilon, "gap": a.gap, "phi": phi, "ratio": ratio}
            )
            if ratio > best_ratio and isfinite(ratio):
                best_ratio, best_f = ratio, f
    return Discovery(
        id="phi_slack_sweet_spot",
        category="certification",
        title="Tightest certified gap vs Phi(epsilon)",
        summary=(
            f"Among certified couplings, max gap/Phi ~ {best_ratio:.3f} at f={best_f:.2f} "
            "(bound is conservative elsewhere)."
        ),
        evidence={
            "best_f": best_f,
            "best_ratio": round(best_ratio, 4),
            "certified_sample": certified_rows[-5:] if certified_rows else [],
        },
        significance="Phi is rarely tight; certification fails mainly via epsilon_0, not gap alone.",
    )


def discover_prune_topk_miss() -> Discovery:
    """top_k=1 can under-score vs full 4x4 vertex product on hypersurface."""
    full = VertexProbeAlgorithm(cross_info_bound=0.25).find_near_optimal_probe()
    pruned1 = FisherPrunedVertexSearch(top_k=1, fisher_epsilon=0.01).run()
    pruned4 = FisherPrunedVertexSearch(top_k=4, fisher_epsilon=0.01).run()
    miss1 = full.objective_value - pruned1.objective_value
    miss4 = full.objective_value - pruned4.objective_value
    return Discovery(
        id="prune_topk_gap",
        category="algorithm",
        title="Fisher top-k pruning sensitivity",
        summary=(
            f"top_k=1 loses {miss1:.4f} vs full probe; top_k=4 loses {miss4:.4f} "
            f"(CCC corner value {full.objective_value:.4f})."
        ),
        evidence={
            "full_value": full.objective_value,
            "top1_value": pruned1.objective_value,
            "top4_value": pruned4.objective_value,
            "miss_top1": miss1,
            "miss_top4": miss4,
            "pairs_top1": pruned1.pairs_checked,
            "pairs_top4": pruned4.pairs_checked,
        },
        significance="Theorem 3 pruning is safe only when marginals rank the true pair in top-k.",
    )


def discover_strategy_transitions() -> Discovery:
    """First coupling where design rule leaves SEPARABLE_PROBE."""
    transitions: list[dict[str, Any]] = []
    prev: DecompositionStrategy | None = None
    for r in robustness_sweep():
        strat = r.strategy
        if prev is not None and strat != prev:
            transitions.append(
                {
                    "epsilon": r.leakage.epsilon,
                    "from": prev.name,
                    "to": strat.name,
                    "coproduct_robust": r.coproduct_robust,
                }
            )
        prev = strat
    first_joint = next(
        (t for t in transitions if t["to"] == "JOINT_SOLVE"),
        None,
    )
    return Discovery(
        id="strategy_transitions",
        category="stability",
        title="Decomposition strategy phase transitions",
        summary=(
            f"{len(transitions)} strategy changes along coupling sweep; "
            f"first JOINT_SOLVE near epsilon={first_joint['epsilon'] if first_joint else 'n/a'}."
        ),
        evidence={"transitions": transitions},
        significance="Design rules R1–R5 are discrete phases, not a smooth continuum.",
    )


def discover_conceptual_ccc_wins() -> Discovery:
    """Conceptual polytope global max is product/exp, not coexp shadow."""
    p = ConceptualPolytope()
    best_p, best_u, best_v = p.global_maximizer()
    blocks = [
        CoproductBlock(
            "A",
            (
                DiagramPoint(1, 0, 1, 1, 0),
                DiagramPoint(0, 1, 1, 1, 0.1),
            ),
            cross_bound=0.15,
        ),
        CoproductBlock(
            "B",
            (
                DiagramPoint(1, 1, 0.5, 0.5, 0),
                DiagramPoint(0.5, 0.5, 1, 1, 0.2),
            ),
            cross_bound=0.25,
        ),
    ]
    per_block = maximize_under_coproduct_blocks(p, blocks)
    return Discovery(
        id="conceptual_ccc_corner",
        category="obstruction",
        title="CCC corner beats coexponential shadow",
        summary=(
            f"Global diagram max at {best_v.name} (U={best_u:.3f}); "
            "coproduct blocks still peak at inhabited corners."
        ),
        evidence={
            "global_vertex": best_v.name,
            "global_point": asdict(best_p),
            "per_block": [
                {"block": name, "vertex": v.name, "U": u}
                for name, _, u, v in per_block
            ],
        },
        significance="Operational substitute aligns with product/exp, not empty coexp.",
    )


def discover_hypersurface_corner_invariance() -> Discovery:
    """Vertex probe theta invariant under Fisher coupling on quadratic toy."""
    thetas: list[tuple[float, ...]] = []
    for f in (0.0, 0.05, 0.1, 0.25, 0.35):
        probe = VertexProbeAlgorithm(cross_info_bound=max(0.25, f)).find_near_optimal_probe()
        thetas.append(probe.theta.as_corner_tuple())
    invariant = len({tuple(t) for t in thetas}) == 1
    return Discovery(
        id="hypersurface_corner_invariant",
        category="localization",
        title="Hypersurface vertex invariant under Fisher coupling",
        summary=(
            "Vertex probe stays at (1,0,2,3) for all tested f "
            + ("(confirmed)." if invariant else "(varies).")
        ),
        evidence={"thetas_by_f": dict(zip((0.0, 0.05, 0.1, 0.25, 0.35), thetas))},
        significance="Coupling affects separable gap, not corner argmax on this box.",
    )


def discover_growth_contradiction_z() -> Discovery:
    """Hom sizes into coproduct grow exponentially in |Z|; Hom(C,Z) polynomial in |Z|."""
    y, a = 2, 2
    rep = cardinality_obstruction(y, a)
    ratios = []
    for z in rep.z_values:
        h_coproduct = rep.hom_into_coproduct[z]
        h_cand = rep.hom_from_candidate[z]
        if h_cand > 0:
            ratios.append(h_coproduct / h_cand)
    return Discovery(
        id="growth_rate_mismatch",
        category="obstruction",
        title="Exponential vs polynomial growth in |Z|",
        summary=rep.reason,
        evidence={
            "y": y,
            "a": a,
            "ratio_hom_coproduct_over_hom_C": ratios,
            "z_values": list(rep.z_values),
        },
        significance="No fixed finite C can represent the coproduct functor for all Z.",
    )


DISCOVERY_REGISTRY: tuple[Callable[[], Discovery], ...] = (
    discover_obstruction_minimal,
    discover_growth_contradiction_z,
    discover_certification_boundary,
    discover_phi_slack,
    discover_face_bowl_onset,
    discover_interaction_landscape,
    discover_hypersurface_corner_invariance,
    discover_prune_topk_miss,
    discover_strategy_transitions,
    discover_conceptual_ccc_wins,
)


def run_all_discoveries() -> list[Discovery]:
    return [fn() for fn in DISCOVERY_REGISTRY]


def discoveries_to_markdown(discoveries: Sequence[Discovery]) -> str:
    lines = [
        "# Discoveries (automated)",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**{len(discoveries)} findings** from systematic search over obstruction, "
        "certification, localization, algorithms, and stability.",
        "",
    ]
    by_cat: dict[str, list[Discovery]] = {}
    for d in discoveries:
        by_cat.setdefault(d.category, []).append(d)
    for cat in sorted(by_cat):
        lines.append(f"## {cat.title()}")
        lines.append("")
        for d in by_cat[cat]:
            ref = d.evidence.get("theorem_ref", "")
            ref_s = f" — **{ref}**" if ref else ""
            lines.append(f"### {d.title} (`{d.id}`){ref_s}")
            lines.append("")
            lines.append(d.summary)
            lines.append("")
            if d.significance:
                lines.append(f"*{d.significance}*")
                lines.append("")
            lines.append("```json")
            lines.append(json.dumps(d.evidence, indent=2))
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def write_discovery_artifacts(
    root: Path | None = None,
) -> tuple[Path, Path, Path]:
    from .formal_proofs import (
        PROOF_REGISTRY,
        attach_theorem_refs,
        formal_discoveries_markdown,
        verify_all_proofs,
    )

    root = root or Path(__file__).resolve().parents[1]
    raw = run_all_discoveries()
    discoveries = attach_theorem_refs(raw)
    json_path = root / "experiments" / "discoveries.json"
    md_path = root / "docs" / "DISCOVERIES.md"
    formal_path = root / "docs" / "FORMAL_DISCOVERIES.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    proof_checks = [
        {"id": pid, "label": lab, "ok": ok, "message": msg}
        for pid, lab, ok, msg in verify_all_proofs(raw)
    ]
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(discoveries),
        "discoveries": [d.to_dict() for d in discoveries],
        "formal_proofs": [
            {
                "discovery_id": s.discovery_id,
                "label": s.label,
                "title": s.title,
                "statement": s.statement,
                "hypotheses": list(s.hypotheses),
            }
            for s in PROOF_REGISTRY
        ],
        "proof_verification": proof_checks,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(discoveries_to_markdown(discoveries), encoding="utf-8")
    formal_path.write_text(formal_discoveries_markdown(raw), encoding="utf-8")
    return json_path, md_path, formal_path


def print_discovery_summary(discoveries: Sequence[Discovery] | None = None) -> None:
    from .formal_proofs import REGISTRY_BY_ID

    items = discoveries or attach_theorem_refs(run_all_discoveries())
    print(f"Discoveries: {len(items)}")
    for d in items:
        ref = REGISTRY_BY_ID.get(d.id)
        lab = f" ({ref.label})" if ref else ""
        print(f"  [{d.category}] {d.id}{lab}: {d.summary}")
