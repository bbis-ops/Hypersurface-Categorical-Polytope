"""
Close the narrative loop: coexp failure -> live polytope probe -> interior search.

Learner reports structured diagram state (JSON); we measure epsilon and
grid-vertex gap on H each turn. No paid API required (scripted learner).
Optional: any OpenAI-compatible endpoint (OpenAI, OpenRouter, a local server)
via LOOP_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY (stdlib urllib only).

The endpoint is provider-agnostic: pick one with --model / --base-url, or with
a named preset (see PRESETS). Nothing here is specific to one vendor's model.
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

from .confusion_scorer import ConfusionScorer
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
Each turn reply with one bare JSON object and nothing else - no prose, no code
fence. Every number is a plain decimal, never a range and never a string:
{"lam":0.5,"sigma":0.2,"b":1.4,"k":2.0,"confusion":0.3,"topic":"exponential","quote":"one sentence"}
Ranges: lam 0 to 1, sigma 0 to 1, b 0 to 2, k 0 to 3, confusion 0 to 1.
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

    @staticmethod
    def _num(data: dict[str, Any], key: str, default: float) -> float:
        """
        One coordinate, salvaged if the learner wrote it loosely.

        Small models echo the schema's ranges back as values ("1-0", "0-1") or
        quote the number. Losing the whole turn to that would discard a reply
        whose prose is still usable, so a leading numeric token is taken when
        the value is not already a number; `clamped()` then bounds it. A value
        with no number in it at all falls back to `default`.
        """
        value = data.get(key, default)
        if isinstance(value, bool):  # bool is an int; not a coordinate
            return default
        if isinstance(value, (int, float)):
            return float(value)
        m = re.search(r"-?\d+(?:\.\d+)?", str(value))
        return float(m.group(0)) if m else default

    @classmethod
    def from_json(cls, raw: str | dict[str, Any]) -> LearnerDiagramReport:
        if isinstance(raw, str):
            m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
            data = json.loads(m.group(0) if m else raw)
        else:
            data = raw
        if not isinstance(data, dict):
            raise ValueError(f"expected a JSON object, got {type(data).__name__}")
        return cls(
            lam=cls._num(data, "lam", 0.5),
            sigma=cls._num(data, "sigma", 0.0),
            b=cls._num(data, "b", 2.0),
            k=cls._num(data, "k", 3.0),
            confusion=cls._num(data, "confusion", 0.1),
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

    def to_state(self, strength: float | None = None) -> LearnerDiagramState:
        """
        Coordinates on H.

        `strength` overrides the learner's self-reported confusion with an
        externally measured one (see `confusion_scorer`). The rest of the
        report is kept: only the coupling coordinate stops being self-declared.
        """
        c = self.clamped()
        s = c.confusion if strength is None else max(0.0, min(1.0, strength))
        return LearnerDiagramState(c.lam, c.sigma, c.b, c.k, s)


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
    """Resolved OpenAI-compatible endpoint (OpenAI, OpenRouter, a local server)."""

    base_url: str
    model: str
    key_env: str
    reasoning: bool = False

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
_DEFAULT_MODEL = {_OPENROUTER_BASE: "openai/gpt-4o-mini", _OPENAI_BASE: "gpt-4o-mini"}

# Named endpoint presets, selected with --preset or LOOP_API_PRESET.
#   (base_url, model, sends OpenRouter's `reasoning` block)
# These are conveniences only: an explicit --model / --base-url, or the
# LOOP_API_MODEL / LOOP_API_BASE variables, always win. No preset is required,
# and the defaults above are provider-neutral.
PRESETS: dict[str, tuple[str, str, bool]] = {
    "openai": (_OPENAI_BASE, "gpt-4o-mini", False),
    "openrouter": (_OPENROUTER_BASE, "openai/gpt-4o-mini", False),
    # The backend that generated the recorded V.7-V.14 adversarial corpus.
    # Delisted from OpenRouter as of 2026-08-26, so selecting it now only
    # yields a 404. Kept so the `stealth/ox-alpha@...` descriptor stamped into
    # those artifacts stays interpretable; it was never a default, and nothing
    # in the theory depends on it.
    "ox-alpha": (_OPENROUTER_BASE, "stealth/ox-alpha", True),
    # A free id, so `--check` and small runs cost nothing. Free ids rotate and
    # are rate-limited: treat this as a convenience for confirming a key, not
    # as a fixture. Override with --model for any other variant, and force the
    # `reasoning` block off with POLYTOPE_API_REASONING=0 if a run comes back
    # with empty content (the budget went to hidden reasoning, not candidates).
    #
    # Capabilities per OpenRouter's catalog, checked 2026-08-26:
    #   lightning:free  1M ctx, 65,536 max out. NO response_format, NO
    #                   structured_outputs, but reasoning IS supported. 3B
    #                   active of 30B (MoE): fast and cheap, but it holds a
    #                   long structured reply together less reliably, so
    #                   prefer many small batches and lean on the parser's
    #                   salvage path.
    #   super:free      262k ctx, 235,929 max out, and it DOES advertise
    #                   response_format + structured_outputs - the better
    #                   choice when one request must return a large,
    #                   well-formed JSON batch.
    # Prefer `nemotron-super` for candidate generation. Measured 2026-08-26
    # against both, on the real campaign prompts:
    #
    #   lightning:free  advertises NO response_format and NO structured_outputs.
    #                   On a complex prompt it opens with "Here's a thinking
    #                   process:" and writes its whole plan as ordinary content
    #                   - 5841 "reasoning" tokens of a 6000 cap, 23k characters,
    #                   truncated before it ever emits the JSON. Yield 0 of 12.
    #                   `reasoning: {exclude: True}` does not help: the model is
    #                   not using a reasoning channel, so there is nothing for
    #                   the provider to strip. Raising the cap only buys more
    #                   prose. It answered the trivial probe prompt cleanly, so
    #                   the failure only appears on real work.
    #   super:free      advertises response_format AND structured_outputs, and
    #                   `supports_extras` already sends
    #                   response_format={"type":"json_object"}. 235,929 max
    #                   output.
    #                   Both JSON mode and `reasoning.exclude` are honored:
    #                   measured 2026-08-28 on the polyhedra prompt, a batch of
    #                   4 spent 5,377 of 7,760 completion tokens reasoning and
    #                   returned 858 characters of clean `{"candidates":[...]}`
    #                   with none of that reasoning in content. Yield 4 of 4.
    #
    #                   The cost is the reasoning, and it is the whole budget
    #                   question: ~1,940 completion tokens per record on this
    #                   prompt, mostly hidden. Size the cap as n * 1,940 with
    #                   headroom. Undersize it and the request dies at
    #                   finish_reason "length" - and then the provider returns
    #                   the partial reasoning trace in `content`, since there
    #                   is no final content to send. A batch of 12 under a
    #                   10,000-token cap yielded 0 of 12 that way: 28k
    #                   characters of visible plan, cut off mid-sentence. That
    #                   artifact reads exactly like a model with no JSON mode,
    #                   which is the trap - the fix is budget, not a new model.
    #
    # `reasoning` stays on for both: it is free when a model does use a real
    # reasoning channel, and inert when it does not.
    "nemotron": (_OPENROUTER_BASE, "nvidia/nemotron-3.5-lightning:free", True),
    "nemotron-super": (_OPENROUTER_BASE, "nvidia/nemotron-3-super-120b-a12b:free", True),
    # PAID. Checked against OpenRouter's catalog 2026-08-27: JSON mode,
    # structured outputs, and a real reasoning channel - the full set, unlike
    # every free Nemotron except super. 262k context, 235,929 max output,
    # $0.95/M in and $4.00/M out, so a 30-request domain-three campaign is
    # roughly a dollar. `kimi-k2.7-code` is cheaper on output ($3.40/M) and
    # `kimi-k3` far dearer ($15/M); both take the same prompts, so switch with
    # --model rather than adding presets for each.
    "kimi": (_OPENROUTER_BASE, "moonshotai/kimi-k2.6", True),
}


def _wants_reasoning(model: str, preset_flag: bool) -> bool:
    """
    Whether to send OpenRouter's `reasoning` block. POLYTOPE_API_REASONING
    forces it either way; otherwise the preset decides. Capability, not vendor:
    any reasoning model can opt in without being named here.
    """
    flag = os.environ.get("POLYTOPE_API_REASONING", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return preset_flag


def resolve_backend(
    model: str | None = None,
    base_url: str | None = None,
    preset: str | None = None,
) -> ApiBackend | None:
    """Endpoint from explicit args, else preset, else env. None when no key is set."""
    key_env = next((e for e in _KEY_ENVS if os.environ.get(e, "").strip()), "")
    if not key_env:
        return None
    name_hint = (preset or os.environ.get("LOOP_API_PRESET", "")).strip().lower()
    pre_base, pre_model, pre_reasoning = PRESETS.get(name_hint, ("", "", False))
    base = (
        base_url
        or os.environ.get("LOOP_API_BASE", "")
        or os.environ.get("OPENAI_BASE_URL", "")
        or pre_base
    ).strip()
    if not base:
        base = _OPENROUTER_BASE if key_env == "OPENROUTER_API_KEY" else _OPENAI_BASE
    base = base.rstrip("/")
    name = (model or os.environ.get("LOOP_API_MODEL", "") or pre_model).strip()
    return ApiBackend(
        base,
        name or _DEFAULT_MODEL.get(base, "gpt-4o-mini"),
        key_env,
        _wants_reasoning(name, pre_reasoning),
    )


def _payload(backend: ApiBackend, user_prompt: str, *, plain: bool) -> bytes:
    """
    Request body. On OpenRouter we add two extras the protocol wants:
    `response_format` (the learner must emit a bare JSON object) and
    `reasoning.exclude` (for a reasoning model the chain-of-thought is not part
    of the reported diagram state and would only have to be stripped).
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
    preset: str | None = None,
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
    backend = resolve_backend(model, base_url, preset)
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
        text: str | None = None
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
                note = f"{type(exc).__name__}: {exc}"
                # The reply is the whole evidence for why parsing failed.
                # Without it "could not convert string to float" names the
                # symptom and hides which field the model actually botched.
                if text is not None:
                    snippet = " ".join(text.split())[:240]
                    note += f" | reply: {snippet!r}"
                elif text == "":
                    note += " | reply was empty"
                on_fallback(turn, note)
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
    # What the learner claimed, and what scoring its own words produced.
    # `confusion_measured` is None when no scorer ran.
    confusion_reported: float = 0.0
    confusion_measured: float | None = None


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
    preset: str | None = None
    backend: ApiBackend | None = None
    fallbacks: list[dict[str, Any]] = field(default_factory=list)
    # None keeps the self-reported `confusion` field driving the geometry.
    # Supply a scorer (e.g. ConfusionScorer()) to derive the coupling
    # coordinate from the learner's own prose instead.
    score_confusion: Callable[[str], float] | None = None

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
        reset = getattr(self.score_confusion, "reset", None)
        if callable(reset):
            reset()
        made = (
            api_learner_factory(
                self.model,
                self.base_url,
                self.preset,
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
            # Score the learner's own words. The reported coordinate is kept in
            # the artifact either way, so a measured run stays comparable to a
            # self-reported one instead of silently replacing it.
            measured = (
                self.score_confusion(report.quote)
                if self.score_confusion is not None
                else None
            )
            state = report.to_state(measured)
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
                    confusion_reported=report.confusion,
                    confusion_measured=measured,
                )
            )
            prev_mode = probe.search_mode
        return self.turns

    def divergence(self) -> dict[str, Any] | None:
        """
        Gap between the learner's self-reported confusion and the measured one.

        None when no scorer ran. This gap is itself a measurement — the
        calibration error of self-report — and a reported-only protocol cannot
        see it, because there is nothing to compare the claim against.
        """
        pairs = [
            (t.turn, t.confusion_reported, t.confusion_measured)
            for t in self.turns
            if t.confusion_measured is not None
        ]
        if not pairs:
            return None
        diffs = [abs(rep - meas) for _, rep, meas in pairs]
        worst = max(range(len(pairs)), key=lambda i: diffs[i])
        return {
            "n_pairs": len(pairs),
            "mean_abs_error": sum(diffs) / len(diffs),
            "max_abs_error": diffs[worst],
            "worst_turn": pairs[worst][0],
            "reported": [round(rep, 4) for _, rep, _ in pairs],
            "measured": [round(meas, 4) for _, _, meas in pairs],
            "overclaims": sum(1 for _, rep, meas in pairs if rep > meas),
            "underclaims": sum(1 for _, rep, meas in pairs if rep < meas),
        }

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
            "confusion_source": (
                "measured" if self.score_confusion is not None else "self_report"
            ),
            "self_report_divergence": self.divergence(),
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
        f"**Backend:** {s['backend']} learner | **Closure at turn:** {s['closure_turn']}"
        f" | **Coupling coordinate:** {s['confusion_source']}",
        "",
    ]
    div = s.get("self_report_divergence")
    if div:
        lines += [
            f"> Coupling was scored from the learner's own prose, not taken from "
            f"its `confusion` field. Self-report sat {div['mean_abs_error']:.3f} "
            f"away on average (worst: turn {div['worst_turn']}, "
            f"{div['max_abs_error']:.3f}); it overclaimed on "
            f"{div['overclaims']} turn(s) and underclaimed on "
            f"{div['underclaims']}.",
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
    ]
    if div:
        lines += [
            "| Turn | mode | epsilon | gap | reported | measured | topic |",
            "|------|------|---------|-----|----------|----------|-------|",
        ]
    else:
        lines += [
            "| Turn | mode | epsilon | gap | topic |",
            "|------|------|---------|-----|-------|",
        ]
    for t in session.turns:
        L = t.learner
        P = t.probe
        cells = [
            str(t.turn),
            P["search_mode"],
            f"{P['epsilon']:.4f}",
            f"{P['gap_vertex_grid']:.4f}",
        ]
        if div:
            cells += [
                f"{t.confusion_reported:.3f}",
                f"{t.confusion_measured:.3f}" if t.confusion_measured is not None else "-",
            ]
        cells.append(str(L.get("topic", "")))
        lines.append("| " + " | ".join(cells) + " |")
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
    if div:
        lines.append(
            "*Disclaimer: lam/sigma/b/k come from the learner's structured report "
            "(protocol); the coupling coordinate is scored from its prose against "
            "a fixed proposition ledger. Neither is read from transformer "
            "activations. The probe is the mathematical witness.*"
        )
    else:
        lines.append(
            "*Disclaimer: theta comes from learner structured report (protocol), "
            "not from transformer activations. The probe is the mathematical witness.*"
        )
    return "\n".join(lines)


def _explain_failure(detail: str, backend: ApiBackend) -> str:
    """
    Append the next thing to try to a transport error.

    A bare `HTTP Error 402` reads as a bad key, when it usually means the key
    is fine and the *model* costs money. The distinction is worth spelling out:
    the default model is only a placeholder, not a requirement.
    """
    hints = (
        ("401", "the key was rejected - check it was pasted whole"),
        ("403", "the key is not allowed to use this model"),
        (
            "402",
            f"the key works but {backend.model} is a paid model with no credit "
            "behind it; choose a free id with --model, or --preset nemotron",
        ),
        ("404", f"{backend.host} does not serve {backend.model} - check the id"),
        ("429", "rate limited; free tiers cap requests per minute - retry shortly"),
    )
    for code, why in hints:
        if f"HTTP Error {code}" in detail:
            return f"{detail} ({why})"
    if detail.startswith(("ValueError", "JSONDecodeError", "TypeError", "KeyError")):
        return (
            f"{detail} (the key and endpoint are fine - {backend.model} replied, "
            "but not with the JSON the protocol asks for)"
        )
    return detail


def check_backend(
    model: str | None = None,
    base_url: str | None = None,
    preset: str | None = None,
) -> dict[str, Any]:
    """
    One round-trip against the configured endpoint. Writes no artifacts.

    Used by `--check` so a key can be validated without committing a session
    file that might later be mistaken for a real run.
    """
    problems: list[str] = []
    made = api_learner_factory(
        model, base_url, preset, on_fallback=lambda _t, why: problems.append(why)
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
        return {
            "ok": False,
            "backend": backend.descriptor(),
            "detail": _explain_failure(problems[0], backend),
        }
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
    preset: str | None = None,
    measured_confusion: bool = False,
) -> dict[str, Any]:
    """
    Run the loop and save its artifacts.

    `measured_confusion` scores the coupling coordinate from the learner's own
    prose instead of trusting the `confusion` value it reports about itself.
    """
    from pathlib import Path as P

    artifact_dir = artifact_dir or P(__file__).resolve().parents[1] / "experiments"
    sess = LoopClosureSession(
        use_api=use_api,
        model=model,
        base_url=base_url,
        preset=preset,
        score_confusion=ConfusionScorer() if measured_confusion else None,
    )
    sess.run()
    sess.save(artifact_dir)
    return sess.summary()
