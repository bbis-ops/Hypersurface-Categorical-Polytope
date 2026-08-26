"""
Human / LLM-scale category-learning session with live epsilon detector.

Scripted adjunction-learning trajectory (confusion ramp) plus phenomenology notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .learner_diagram import (
    LearnerDiagramState,
    LearnerTrajectoryLog,
    SearchMode,
)


@dataclass(frozen=True)
class LearningBeat:
    """One pedagogical moment in a category-learning session."""

    step: int
    topic: str
    learner_confusion: float
    lam: float
    sigma: float
    narrative: str


# Scripted session: internalizing product/exp vs coproduct/coexp confusion
ADJUNCTION_CURRICULUM: tuple[LearningBeat, ...] = (
    LearningBeat(0, "product_exp_corner", 0.05, 1.0, 0.0, "Comfortable with curry / product."),
    LearningBeat(1, "coproduct_blocks", 0.12, 0.95, 0.05, "Coproduct as disjoint union — OK."),
    LearningBeat(2, "coexp_empty", 0.22, 0.9, 0.1, "Coexponential in Set? Feels undefined."),
    LearningBeat(3, "cross_natural", 0.35, 0.85, 0.2, "Cross-naturality couples blocks."),
    LearningBeat(4, "face_bowl", 0.48, 0.75, 0.35, "Best picture may be interior on (lam,sigma) face."),
    LearningBeat(5, "naturality_swap", 0.55, 0.7, 0.42, "Cannot keep corner-only search."),
    LearningBeat(6, "review_adjunction", 0.62, 0.65, 0.5, "Adjoint functors — arrows reversed."),
    LearningBeat(7, "consolidation", 0.75, 0.6, 0.55, "Accept interior + block passes."),
)


@dataclass
class CategoryLearningSession:
    """
    Run a scripted category-learning path through the diagram box.

    Logs live epsilon and search-mode recommendations each beat.
    """

    curriculum: tuple[LearningBeat, ...] = field(default_factory=lambda: ADJUNCTION_CURRICULUM)
    log: LearnerTrajectoryLog = field(
        default_factory=lambda: LearnerTrajectoryLog(interaction="face_bowl")
    )
    phenomenology: list[str] = field(default_factory=list)

    def run(self) -> LearnerTrajectoryLog:
        self.phenomenology.clear()
        prev_mode = SearchMode.CORNER_HUNTING.name
        for beat in self.curriculum:
            state = LearnerDiagramState(
                lam=beat.lam,
                sigma=beat.sigma,
                b=2.0,
                k=3.0,
                interaction_strength=beat.learner_confusion,
            )
            rec = self.log.append_state(state, step=beat.step)
            note = f"Step {beat.step} ({beat.topic}): {beat.narrative}"
            if rec.mode != prev_mode:
                note += (
                    f" [MODE SWITCH {prev_mode} -> {rec.mode}: "
                    f"eps={rec.epsilon:.4f}, gap={rec.gap_vertex_grid:.4f}]"
                )
                self.phenomenology.append(note)
            prev_mode = rec.mode
        return self.log

    def summary(self) -> dict[str, Any]:
        first_int = self.log.first_interior_step()
        modes = [s.mode for s in self.log.steps]
        return {
            "n_steps": len(self.log.steps),
            "first_interior_step": first_int.step if first_int else None,
            "first_interior_strength": first_int.interaction_strength if first_int else None,
            "mode_sequence": modes,
            "phenomenology": self.phenomenology,
            "qualitative": _qualitative_summary(self.phenomenology, first_int),
        }

    def save_artifacts(self, root: Path) -> tuple[Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        json_path = root / "category_learning_session.json"
        md_path = root / "CATEGORY_LEARNING_PHENOMENOLOGY.md"
        payload = {
            "summary": self.summary(),
            "trajectory": self.log.to_dict(),
        }
        import json

        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md = _phenomenology_markdown(self)
        md_path.write_text(md, encoding="utf-8")
        return json_path, md_path


def _qualitative_summary(
    phenomenology: list[str],
    first_int: object,
) -> str:
    if not first_int:
        return "Learner stayed on corner-hunting throughout (unlikely for face_bowl ramp)."
    return (
        "Typical arc: early beats use separable corner probes; confusion (face_bowl) "
        "raises grid-vertex gap; detector forces INTERIOR_SEARCH when the learner "
        "treats adjunction faces as coupled rather than corner-only."
    )


def _phenomenology_markdown(session: CategoryLearningSession) -> str:
    s = session.summary()
    lines = [
        "# Category-learning phenomenology (live epsilon)",
        "",
        s["qualitative"],
        "",
        "## Mode sequence",
        "",
        " -> ".join(s["mode_sequence"]),
        "",
        f"**First interior step:** {s['first_interior_step']} "
        f"(strength={s['first_interior_strength']})",
        "",
        "## Switch events",
        "",
    ]
    for p in s["phenomenology"] or ["(no mode switches)"]:
        lines.append(f"- {p}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **Before switch:** learner behaves as if maximum insight is at a CCC corner.",
            "- **At switch:** empirical Fisher + grid gap witness that face interaction "
            "dominates — matching 'coexp empty, use interior on (lam,sigma)'.",
            "- **After switch:** block-coordinate / interior search matches studying "
            "adjunctions without assuming global factorization.",
            "",
        ]
    )
    return "\n".join(lines)


def run_default_session(artifact_dir: Path | None = None) -> dict[str, Any]:
    from pathlib import Path as P

    artifact_dir = artifact_dir or P(__file__).resolve().parents[1] / "experiments"
    sess = CategoryLearningSession()
    sess.run()
    sess.save_artifacts(artifact_dir)
    return sess.summary()
