"""
Turn-based category-learning tutor with live epsilon after each turn.

Hooks LearnerTrajectoryLog to a simulated LLM loop (no API required).
Replace `respond` with a real model call for human/LLM sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .category_learning_session import CategoryLearningSession, LearningBeat
from .learner_diagram import LearnerDiagramState, LearnerTrajectoryLog, SearchMode


@dataclass
class TutorTurn:
    """One exchange in a category-learning session."""

    turn: int
    user_message: str
    tutor_reply: str
    confusion: float
    lam: float
    sigma: float
    epsilon: float
    gap_vertex_grid: float
    search_mode: str
    phenomenology_note: str = ""


ResponseFn = Callable[[str, LearnerDiagramState, str], str]

# Layer-2 hook: score the learner's own utterance instead of counting turns.
# Returns interaction_strength for this turn. See confusion_scorer.py.
ConfusionFn = Callable[[str, LearnerTrajectoryLog], float]

# The canonical adjunction-learning dialogue. Promoted to a module constant so
# calibration and regression tests can reference the same reference trajectory.
SCRIPTED_PROMPTS: tuple[str, ...] = (
    "I'm fine with product and curry.",
    "Coproduct is just disjoint union, right?",
    "Where is the coexponential in Set?",
    "Cross-naturality seems to mix my blocks.",
    "Maybe the best picture is not at a corner?",
    "I keep trying corners but they feel wrong.",
    "Adjoint functors reverse arrows — still confused.",
    "Should I search the interior of the face?",
)


def _default_respond(user_message: str, state: LearnerDiagramState, mode: str) -> str:
    """Template tutor (swap for LLM API)."""
    u = user_message.lower()
    if "product" in u or "curry" in u or "exp" in u:
        return (
            "Product and exponential adjunction live at the CCC corner: "
            "maximize along product_exp first."
        )
    if "coproduct" in u or "disjoint" in u:
        return "Coproduct blocks factor; probe each summand at its vertex."
    if "coexp" in u or "co-exponential" in u:
        return (
            "In Set there is no global coexponential — treat it as a shadow. "
            "Use extremal selection + Fisher epsilon instead."
        )
    if mode == SearchMode.INTERIOR_SEARCH.name:
        return (
            "Your diagram coupling is too strong for corner-only search. "
            "Explore interior (lambda, sigma) on the face, not just vertices."
        )
    if mode == SearchMode.BLOCK_COORDINATE.name:
        return (
            "Moderate Fisher leakage: run block coordinate passes before "
            "trusting separable factorization."
        )
    return (
        "Stay at the feasible corner unless grid-vertex gap or epsilon "
        "says otherwise. What adjunction confuses you?"
    )


@dataclass
class CategoryLearningTutor:
    """
    Interactive session: each turn updates confusion and logs live epsilon.
    """

    log: LearnerTrajectoryLog = field(
        default_factory=lambda: LearnerTrajectoryLog(interaction="face_bowl")
    )
    turns: list[TutorTurn] = field(default_factory=list)
    respond: ResponseFn = field(default_factory=lambda: _default_respond)
    base_confusion: float = 0.05
    confusion_per_turn: float = 0.04
    # None keeps the legacy turn-index ramp; supply a ConfusionFn (e.g.
    # confusion_scorer.ConfusionScorer) to measure the learner instead.
    score_confusion: ConfusionFn | None = None

    def process_turn(
        self,
        user_message: str,
        *,
        lam: float | None = None,
        sigma: float | None = None,
        confusion: float | None = None,
    ) -> TutorTurn:
        t = len(self.turns)
        if confusion is not None:
            conf = confusion
        elif self.score_confusion is not None:
            # Measure the learner's own utterance. `user_message` is in hand
            # before the state is built, so the loop needs no reordering.
            conf = min(0.95, max(0.0, self.score_confusion(user_message, self.log)))
        else:
            conf = min(0.95, self.base_confusion + t * self.confusion_per_turn)
        state = LearnerDiagramState(
            lam=lam if lam is not None else max(0.5, 1.0 - t * 0.05),
            sigma=sigma if sigma is not None else min(0.5, t * 0.06),
            b=2.0,
            k=3.0,
            interaction_strength=conf,
        )
        rec = self.log.append_state(state, step=t)
        reply = self.respond(user_message, state, rec.mode)
        phen = ""
        if t > 0 and rec.mode != self.turns[-1].search_mode:
            phen = f"Turn {t}: mode {self.turns[-1].search_mode} -> {rec.mode}"
        turn = TutorTurn(
            turn=t,
            user_message=user_message,
            tutor_reply=reply,
            confusion=conf,
            lam=state.lam,
            sigma=state.sigma,
            epsilon=rec.epsilon,
            gap_vertex_grid=rec.gap_vertex_grid,
            search_mode=rec.mode,
            phenomenology_note=phen,
        )
        self.turns.append(turn)
        return turn

    def run_scripted_dialogue(
        self,
        prompts: tuple[str, ...] = SCRIPTED_PROMPTS,
    ) -> list[TutorTurn]:
        """Canned adjunction-learning dialogue (human/LLM scale)."""
        self.turns.clear()
        self.log = LearnerTrajectoryLog(interaction="face_bowl")
        reset = getattr(self.score_confusion, "reset", None)
        if callable(reset):
            reset()
        for msg in prompts:
            self.process_turn(msg)
        return self.turns

    def summary(self) -> dict[str, Any]:
        first_int = self.log.first_interior_step()
        phen = [t.phenomenology_note for t in self.turns if t.phenomenology_note]
        return {
            "n_turns": len(self.turns),
            "first_interior_turn": first_int.step if first_int else None,
            "first_interior_confusion": first_int.interaction_strength if first_int else None,
            "mode_sequence": [t.search_mode for t in self.turns],
            "phenomenology": phen,
            "qualitative": (
                "Dialogue arc: corners while blocks feel separable; "
                "coexp + cross-naturality raise gap; tutor steers to interior search."
            ),
        }

    def save(self, root: Path) -> tuple[Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        import json

        jpath = root / "category_tutor_session.json"
        mpath = root / "CATEGORY_TUTOR_PHENOMENOLOGY.md"
        payload = {"summary": self.summary(), "turns": [t.__dict__ for t in self.turns]}
        jpath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = [
            "# Category tutor session (turn loop)",
            "",
            self.summary()["qualitative"],
            "",
            "## Turns",
            "",
        ]
        for t in self.turns:
            lines.append(f"### Turn {t.turn} ({t.search_mode})")
            lines.append(f"- **User:** {t.user_message}")
            lines.append(f"- **Tutor:** {t.tutor_reply}")
            lines.append(
                f"- eps={t.epsilon:.4f}, gap={t.gap_vertex_grid:.4f}, "
                f"confusion={t.confusion:.2f}"
            )
            if t.phenomenology_note:
                lines.append(f"- *{t.phenomenology_note}*")
            lines.append("")
        mpath.write_text("\n".join(lines), encoding="utf-8")
        return jpath, mpath


def run_default_tutor_session(artifact_dir: Path | None = None) -> dict[str, Any]:
    from pathlib import Path as P

    artifact_dir = artifact_dir or P(__file__).resolve().parents[1] / "experiments"
    tutor = CategoryLearningTutor()
    tutor.run_scripted_dialogue()
    tutor.save(artifact_dir)
    return tutor.summary()
