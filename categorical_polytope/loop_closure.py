"""
Close the narrative loop: coexp failure -> live polytope probe -> interior search.

Learner reports structured diagram state (JSON); we measure epsilon and
grid-vertex gap on H each turn. No paid API required (scripted learner).
Optional: any OpenAI-compatible endpoint (OpenAI, OpenRouter/Ox Alpha, local)
via LOOP_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY (stdlib urllib only).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .learner_diagram import LearnerDiagramState, SearchMode, recommend_search_mode
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    default_nonlinear_bounds,
    empirical_fisher_at,
    grid_maximize,
    vertex_maximize,
)
from .formal_bounds import certify_suboptimality, theorem_constants_from_fisher
LOOP_SYSTEM_PROMPT = """You are learning category theory on a diagram polytope H.
Dimensions: lam, sigma (adjunction face), b, k (blocks), confusion in [0,1].
Facts: (1) Product/exp corner is inhabited (curry). (2) Coexponential for coproduct
does NOT exist in Set — cardinality obstruction. (3) Strong cross-naturality couples
the face; corner-only search can fail (face_bowl).
Each turn reply with JSON only:
{"lam":0-1,"sigma":0-1,"b":0-2,"k":0-3,"confusion":0-1,"topic":"...","quote":"one sentence"}
"""


@dataclass(frozen=True)
class LearnerDiagramReport:
    """Learner's claimed internal diagram coordinates."""

    lam: float
    sigma: float
    b: float
    k: float
    confusion: float
    topic: str
    quote: str

    @classmethod
    def from_json(cls, raw: str | dict[str, Any]) -> LearnerDiagramReport:
        if isinstance(raw, str):
            m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
            data = json.loads(m.group(0) if m else raw)
        else:
            data = raw
        return cls(
            lam=float(data.get("lam", 0.5)),
            sigma=float(data.get("sigma", 0.0)),
            b=float(data.get("b", 2.0)),
            k=float(data.get("k", 3.0)),
            confusion=float(data.get("confusion", 0.1)),
            topic=str(data.get("topic", "general")),
            quote=str(data.get("quote", "")),
        )

    def clamped(self) -> LearnerDiagramReport:
        bnd = default_nonlinear_bounds()
        return LearnerDiagramReport(
            lam=max(bnd.lam[0], min(bnd.lam[1], self.lam)),
            sigma=max(bnd.sigma[0], min(bnd.sigma[1], self.sigma)),
            b=max(bnd.b[0], min(bnd.b[1], self.b)),
            k=max(bnd.k[0], min(bnd.k[1], self.k)),
            confusion=max(0.0, min(1.0, self.confusion)),
            topic=self.topic,
            quote=self.quote,
        )

    def to_state(self) -> LearnerDiagramState:
        c = self.clamped()
        return LearnerDiagramState(c.lam, c.sigma, c.b, c.k, c.confusion)


@dataclass(frozen=True)
class LiveProbeResult:
    """One live probe of the learner's polytope position."""

    epsilon: float
    gap_vertex_grid: float
    certified_separable: bool
    search_mode: str
    reason: str
    value_vertex: float
    value_grid: float


def probe_diagram_state(state: LearnerDiagramState) -> LiveProbeResult:
    """Live epsilon + localization witness on reported theta."""
    bounds = default_nonlinear_bounds()
    obj = HypersurfacePlusInteraction(
        bounds=bounds,
        strength=state.interaction_strength,
        interaction="face_bowl",
    )
    theta = state.to_theta()
    fisher = empirical_fisher_at(obj, theta, bounds)
    leak = fisher.leakage()
    th_v, v_v = vertex_maximize(obj, bounds)
    th_g, v_g = grid_maximize(obj, bounds, steps=9)
    gap = v_g - v_v
    const = theorem_constants_from_fisher(
        leak,
        [fisher.matrix[i][i] for i in range(4)],
        theta_joint=(th_g.lam, th_g.sigma, th_g.b, th_g.k),
    )
    cert, _, _ = certify_suboptimality(leak.epsilon, 0.0, const)
    mode, reason = recommend_search_mode(
        leak.epsilon,
        gap_vertex_grid=gap,
        certified_separable=cert,
        epsilon_0=const.epsilon_0,
    )
    return LiveProbeResult(
        epsilon=leak.epsilon,
        gap_vertex_grid=gap,
        certified_separable=cert,
        search_mode=mode.name,
        reason=reason,
        value_vertex=v_v,
        value_grid=v_g,
    )


# Scripted learner: internal polytope trajectory (no API)
SCRIPTED_LEARNER_ARC: tuple[dict[str, Any], ...] = (
    {
        "lam": 1.0,
        "sigma": 0.0,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.05,
        "topic": "product_exp",
        "quote": "Curry lives at the product corner — I'm comfortable there.",
    },
    {
        "lam": 0.95,
        "sigma": 0.05,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.12,
        "topic": "coproduct",
        "quote": "Coproduct is disjoint union; I probe each block at a vertex.",
    },
    {
        "lam": 0.9,
        "sigma": 0.1,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.22,
        "topic": "coexp_empty",
        "quote": "Coexponential in Set? I can't find a representing object.",
    },
    {
        "lam": 0.85,
        "sigma": 0.2,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.35,
        "topic": "cross_natural",
        "quote": "Cross-naturality mixes my lambda-sigma face — corners feel wrong.",
    },
    {
        "lam": 0.78,
        "sigma": 0.32,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.48,
        "topic": "face_interior",
        "quote": "Maybe the true picture is interior on the face, not a corner.",
    },
    {
        "lam": 0.72,
        "sigma": 0.38,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.55,
        "topic": "interior_search",
        "quote": "I should search the interior; corner-hunting failed me.",
    },
    {
        "lam": 0.68,
        "sigma": 0.42,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.62,
        "topic": "adjoint",
        "quote": "Adjoints reverse arrows — factorization is only approximate.",
    },
    {
        "lam": 0.62,
        "sigma": 0.48,
        "b": 2.0,
        "k": 3.0,
        "confusion": 0.7,
        "topic": "closure",
        "quote": "Coexp shadow + Fisher epsilon + interior search — the loop closes.",
    },
)


LearnerFn = Callable[[int, str], LearnerDiagramReport]


def scripted_learner(turn: int, user_prompt: str) -> LearnerDiagramReport:
    idx = min(turn, len(SCRIPTED_LEARNER_ARC) - 1)
    return LearnerDiagramReport.from_json(SCRIPTED_LEARNER_ARC[idx])


@dataclass(frozen=True)
class ApiBackend:
    """Resolved OpenAI-compatible endpoint (OpenAI, OpenRouter/Ox Alpha, local)."""

    base_url: str
    model: str
    key_env: str

    @property
    def host(self) -> str:
        return urllib.parse.urlsplit(self.base_url).netloc or self.base_url

    @property
    def supports_extras(self) -> bool:
        """OpenRouter accepts `response_format` and `reasoning`; plain OpenAI-compat may not."""
        return self.host.endswith("openrouter.ai")

    def descriptor(self) -> str:
        """Reproducibility stamp recorded in the artifact."""
        return f"{self.model}@{self.host}"


_KEY_ENVS = ("LOOP_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_OPENAI_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL = {_OPENROUTER_BASE: "stealth/ox-alpha", _OPENAI_BASE: "gpt-4o-mini"}


def resolve_backend(
    model: str | None = None,
    base_url: str | None = None,
) -> ApiBackend | None:
    """Endpoint from explicit args, else env. None when no key is set."""
    key_env = next((e for e in _KEY_ENVS if os.environ.get(e, "").strip()), "")
    if not key_env:
        return None
    base = (
        base_url
        or os.environ.get("LOOP_API_BASE", "")
        or os.environ.get("OPENAI_BASE_URL", "")
    ).strip()
    if not base:
        base = _OPENROUTER_BASE if key_env == "OPENROUTER_API_KEY" else _OPENAI_BASE
    base = base.rstrip("/")
    name = (model or os.environ.get("LOOP_API_MODEL", "")).strip()
    return ApiBackend(base, name or _DEFAULT_MODEL.get(base, "gpt-4o-mini"), key_env)


def _payload(backend: ApiBackend, user_prompt: str, *, plain: bool) -> bytes:
    """
    Request body. On OpenRouter we add two extras the protocol wants:
    `response_format` (the learner must emit a bare JSON object) and
    `reasoning.exclude` (Ox Alpha is a reasoning model; the chain-of-thought is
    not part of the reported diagram state and would only have to be stripped).
    `plain=True` drops both for the retry against endpoints that reject them.
    """
    body: dict[str, Any] = {
        "model": backend.model,
        "messages": [
            {"role": "system", "content": LOOP_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    if backend.supports_extras and not plain:
        body["response_format"] = {"type": "json_object"}
        body["reasoning"] = {"exclude": True}
    return json.dumps(body).encode("utf-8")


def api_learner_factory(
    model: str | None = None,
    base_url: str | None = None,
    *,
    on_fallback: Callable[[int, str], None] | None = None,
) -> tuple[LearnerFn, ApiBackend] | None:
    """
    Real-model learner over any OpenAI-compatible /chat/completions endpoint.

    Returns None when no key is set (caller keeps the scripted arc). A failed or
    unparseable turn degrades to the scripted report for that turn and reports it
    through `on_fallback`: a silent fallback would make an --api run
    indistinguishable from a scripted one in the saved artifact.
    """
    backend = resolve_backend(model, base_url)
    if backend is None:
        return None
    key = os.environ[backend.key_env].strip()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    # Optional OpenRouter leaderboard attribution; opt-in, no placeholder identity.
    if os.environ.get("LOOP_API_REFERER", "").strip():
        headers["HTTP-Referer"] = os.environ["LOOP_API_REFERER"].strip()
        headers["X-Title"] = (
            os.environ.get("LOOP_API_TITLE", "").strip() or "categorical-polytope"
        )

    def _post(user_prompt: str, *, plain: bool) -> str:
        req = urllib.request.Request(
            f"{backend.base_url}/chat/completions",
            data=_payload(backend, user_prompt, plain=plain),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _learn(turn: int, user_prompt: str) -> LearnerDiagramReport:
        try:
            try:
                text = _post(user_prompt, plain=False)
            except urllib.error.HTTPError as exc:
                # Endpoint rejected response_format/reasoning: retry without them.
                if exc.code not in (400, 404, 422) or not backend.supports_extras:
                    raise
                text = _post(user_prompt, plain=True)
            return LearnerDiagramReport.from_json(text)
        except (
            urllib.error.URLError,
            OSError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            if on_fallback is not None:
                on_fallback(turn, f"{type(exc).__name__}: {exc}")
            return scripted_learner(turn, user_prompt)

    return _learn, backend


def openai_learner_factory(model: str = "gpt-4o-mini") -> LearnerFn | None:
    """Back-compat shim over `api_learner_factory`."""
    made = api_learner_factory(model)
    return made[0] if made else None


@dataclass
class LoopClosureTurn:
    turn: int
    facilitator_prompt: str
    learner: dict[str, Any]
    probe: dict[str, Any]
    tutor_note: str
    loop_event: str = ""


@dataclass
class LoopClosureSession:
    """
    Full loop: facilitator prompts -> learner JSON state -> live probe -> tutor note.
    """

    learner_fn: LearnerFn = field(default_factory=lambda: scripted_learner)
    turns: list[LoopClosureTurn] = field(default_factory=list)
    use_api: bool = False
    model: str | None = None
    base_url: str | None = None
    backend: ApiBackend | None = None
    fallbacks: list[dict[str, Any]] = field(default_factory=list)

    FACILITATOR_PROMPTS: tuple[str, ...] = (
        "Turn 0: Where do you place product and curry on the diagram?",
        "Turn 1: How do you read coproduct as a block?",
        "Turn 2: What goes wrong with coexponential in Set?",
        "Turn 3: Does cross-naturality couple your face coordinates?",
        "Turn 4: Is your maximum still on a corner of (lam,sigma)?",
        "Turn 5: The probe recommends a search mode — what do you do?",
        "Turn 6: How do adjoints change your diagram position?",
        "Turn 7: Summarize the closed loop: coexp, epsilon, corners vs interior.",
    )

    def run(self, *, max_turns: int | None = None) -> list[LoopClosureTurn]:
        self.fallbacks.clear()
        made = (
            api_learner_factory(
                self.model,
                self.base_url,
                on_fallback=lambda t, why: self.fallbacks.append(
                    {"turn": t, "error": why}
                ),
            )
            if self.use_api
            else None
        )
        learn, self.backend = made if made else (self.learner_fn, None)
        self.use_api = self.backend is not None
        self.turns.clear()
        prompts = self.FACILITATOR_PROMPTS[: max_turns or len(self.FACILITATOR_PROMPTS)]
        prev_mode = SearchMode.CORNER_HUNTING.name
        for i, prompt in enumerate(prompts):
            report = learn(i, prompt).clamped()
            state = report.to_state()
            probe = probe_diagram_state(state)
            event = ""
            if probe.search_mode == SearchMode.INTERIOR_SEARCH.name and prev_mode != probe.search_mode:
                event = "LOOP_CLOSURE: coexp confusion + face coupling -> interior search"
            note = _tutor_note(probe.search_mode, report.quote)
            self.turns.append(
                LoopClosureTurn(
                    turn=i,
                    facilitator_prompt=prompt,
                    learner=asdict(report),
                    probe={
                        "epsilon": probe.epsilon,
                        "gap_vertex_grid": probe.gap_vertex_grid,
                        "certified_separable": probe.certified_separable,
                        "search_mode": probe.search_mode,
                        "reason": probe.reason,
                        "value_vertex": probe.value_vertex,
                        "value_grid": probe.value_grid,
                    },
                    tutor_note=note,
                    loop_event=event,
                )
            )
            prev_mode = probe.search_mode
        return self.turns

    def closure_turn(self) -> int | None:
        for t in self.turns:
            if t.loop_event:
                return t.turn
        return None

    def summary(self) -> dict[str, Any]:
        ct = self.closure_turn()
        return {
            "backend": self.backend.descriptor() if self.backend else "scripted",
            "api_fallbacks": list(self.fallbacks),
            "n_turns": len(self.turns),
            "closure_turn": ct,
            "closure_quote": self.turns[ct].learner.get("quote") if ct is not None else None,
            "modes": [t.probe["search_mode"] for t in self.turns],
            "epsilons": [t.probe["epsilon"] for t in self.turns],
            "gaps": [t.probe["gap_vertex_grid"] for t in self.turns],
            "narrative": (
                "Coexp absent in Set (cardinality) -> learner raises confusion on the "
                "(lam,sigma) face -> live probe sees grid beating vertices -> "
                "INTERIOR_SEARCH closes the operational substitute loop."
            ),
        }

    def save(self, root: Path) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        jpath = root / "loop_closure_session.json"
        jpath.write_text(
            json.dumps(
                {"summary": self.summary(), "turns": [asdict(t) for t in self.turns]},
                indent=2,
            ),
            encoding="utf-8",
        )
        paths["json"] = jpath
        paths["md"] = root / "LOOP_CLOSURE.md"
        paths["md"].write_text(loop_closure_markdown(self), encoding="utf-8")
        return paths


def _tutor_note(mode: str, quote: str) -> str:
    if mode == SearchMode.INTERIOR_SEARCH.name:
        return (
            f"Probe: INTERIOR_SEARCH. Your report: \"{quote}\" — "
            "corner-hunting is unsound; search the face interior."
        )
    if mode == SearchMode.BLOCK_COORDINATE.name:
        return f"Probe: block passes advised. Learner: \"{quote}\""
    return f"Probe: corner/separable OK. Learner: \"{quote}\""


def loop_closure_markdown(session: LoopClosureSession) -> str:
    s = session.summary()
    lines = [
        "# Loop closure: live polytope probe while internalizing coexp failure",
        "",
        s["narrative"],
        "",
        f"**Backend:** {s['backend']} learner | **Closure at turn:** {s['closure_turn']}",
        "",
    ]
    if s.get("api_fallbacks"):
        lines += [
            f"> **{len(s['api_fallbacks'])} turn(s) fell back to the scripted arc** "
            "after endpoint errors; this run is not a clean real-learner trace.",
            "",
        ]
    lines += [
        "```mermaid",
        "flowchart LR",
        "  A[Set: no coexp] --> B[Learner state on H]",
        "  B --> C[Live epsilon + gap]",
        "  C --> D{mode?}",
        "  D -->|gap small| E[CORNER_HUNTING]",
        "  D -->|gap large| F[INTERIOR_SEARCH]",
        "  F --> G[Loop closed]",
        "```",
        "",
        "## Timeline",
        "",
        "| Turn | mode | epsilon | gap | topic |",
        "|------|------|---------|-----|-------|",
    ]
    for t in session.turns:
        L = t.learner
        P = t.probe
        lines.append(
            f"| {t.turn} | {P['search_mode']} | {P['epsilon']:.4f} | "
            f"{P['gap_vertex_grid']:.4f} | {L.get('topic','')} |"
        )
    lines.append("")
    if s.get("closure_quote"):
        lines.append(f"**At closure:** \"{s['closure_quote']}\"")
        lines.append("")
    lines.append("## Turn detail")
    lines.append("")
    for t in session.turns:
        lines.append(f"### Turn {t.turn}")
        if t.loop_event:
            lines.append(f"**{t.loop_event}**")
        lines.append(f"- Facilitator: {t.facilitator_prompt}")
        lines.append(f"- Learner quote: {t.learner.get('quote','')}")
        lines.append(f"- Tutor: {t.tutor_note}")
        lines.append("")
    lines.append(
        "*Disclaimer: theta comes from learner structured report (protocol), "
        "not from transformer activations. The probe is the mathematical witness.*"
    )
    return "\n".join(lines)


def check_backend(
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """
    One round-trip against the configured endpoint. Writes no artifacts.

    Used by `--check` so a key can be validated without committing a session
    file that might later be mistaken for a real run.
    """
    problems: list[str] = []
    made = api_learner_factory(
        model, base_url, on_fallback=lambda _t, why: problems.append(why)
    )
    if made is None:
        return {
            "ok": False,
            "backend": None,
            "detail": "no key in " + " / ".join(_KEY_ENVS),
        }
    learn, backend = made
    report = learn(0, LoopClosureSession.FACILITATOR_PROMPTS[0]).clamped()
    if problems:
        return {"ok": False, "backend": backend.descriptor(), "detail": problems[0]}
    return {
        "ok": True,
        "backend": backend.descriptor(),
        "detail": (
            f"learner replied topic={report.topic!r} "
            f"lam={report.lam:.2f} sigma={report.sigma:.2f} "
            f"confusion={report.confusion:.2f}"
        ),
    }


def run_loop_closure(
    artifact_dir: Path | None = None,
    *,
    use_api: bool = False,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    from pathlib import Path as P

    artifact_dir = artifact_dir or P(__file__).resolve().parents[1] / "experiments"
    sess = LoopClosureSession(use_api=use_api, model=model, base_url=base_url)
    sess.run()
    sess.save(artifact_dir)
    return sess.summary()
