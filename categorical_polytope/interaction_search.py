"""
Search over candidate interaction terms for vertex-localization failures.

`vertex_threshold` shows that whether an interaction breaks vertex localization
is decided by one scalar: its inward derivative at the degenerate corner. That
makes screening cheap - four derivative evaluations per candidate instead of a
grid search that provably cannot see the effect - so it is worth running over
many candidates rather than the five hand-written modes.

Candidates are expression strings in lam, sigma, b, k. They come from a built-in
bank (the free default) or from a model via `--api`. Model output is DATA: every
expression is parsed with an AST whitelist and evaluated by a restricted
interpreter. `eval` is never called on it, so a hostile or malformed response can
only be rejected, not executed.

The screen reports, per candidate:
  - gamma: inward slope at the corner, per unit strength
  - s*:    critical strength (0 when the base vertex is degenerate and gamma > 0)
  - predicted vs measured gap, and whether the universal quadratic law holds
  - smoothness: candidates with unbounded inward derivative obey a DIFFERENT
    scaling law and are flagged rather than silently mis-fit

Stdlib only.
"""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable

from .hypersurface_box import BoxBounds, Theta
from .nonlinear_objective import (
    HypersurfacePlusInteraction,
    Objective,
    default_nonlinear_bounds,
)


from .vertex_threshold import (
    _AXES,
    _PUSH_TOL,
    amplitude_bound,
    directional_gap,
    estimate_homogeneity,
    inward_curvatures,
    inward_derivatives,
    is_coupled,
    universal_gap,
    vertex_margin,
)


# Shared by all proposal rounds in one experiment process. This prevents a
# successful round from being followed immediately by the next API request.
_LAST_PROPOSAL_REQUEST_AT: float | None = None

# --------------------------------------------------------------------------
# Restricted expression evaluation
# --------------------------------------------------------------------------

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)

_ALLOWED_FUNCS: dict[str, Callable[..., float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
    "tanh": math.tanh,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
}

_ALLOWED_VARS = ("lam", "sigma", "b", "k")
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}

MAX_EXPR_CHARS = 200
MAX_AST_NODES = 80
MAX_ABS_EXPONENT = 8.0


class UnsafeExpression(ValueError):
    """Candidate rejected before evaluation."""


def _validate(tree: ast.AST) -> None:
    count = 0
    for node in ast.walk(tree):
        count += 1
        if count > MAX_AST_NODES:
            raise UnsafeExpression("expression too large")
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpression(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise UnsafeExpression("only numeric literals allowed")
        if isinstance(node, ast.Name):
            if node.id not in _ALLOWED_VARS and node.id not in _ALLOWED_CONSTS:
                if node.id not in _ALLOWED_FUNCS:
                    raise UnsafeExpression(f"unknown name: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
                raise UnsafeExpression("only whitelisted math functions may be called")
            if node.keywords:
                raise UnsafeExpression("keyword arguments not allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            rhs = node.right
            if not isinstance(rhs, ast.Constant) or not isinstance(
                rhs.value, (int, float)
            ):
                raise UnsafeExpression("exponent must be a numeric literal")
            if abs(float(rhs.value)) > MAX_ABS_EXPONENT:
                raise UnsafeExpression("exponent too large")


def compile_expression(expr: str) -> Callable[[Theta], float]:
    """
    Parse a candidate into a callable. Raises UnsafeExpression if it uses
    anything outside the whitelist. The returned callable walks the AST itself;
    `eval` is never invoked.
    """
    if not expr or len(expr) > MAX_EXPR_CHARS:
        raise UnsafeExpression("empty or over-long expression")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"syntax error: {exc}") from exc
    _validate(tree)

    def walk(node: ast.AST, env: dict[str, float]) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body, env)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            return _ALLOWED_CONSTS[node.id]
        if isinstance(node, ast.UnaryOp):
            v = walk(node.operand, env)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left, env), walk(node.right, env)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            return left**right
        if isinstance(node, ast.Call):
            fn = _ALLOWED_FUNCS[node.func.id]  # type: ignore[union-attr]
            return float(fn(*[walk(a, env) for a in node.args]))
        raise UnsafeExpression("unreachable")

    def evaluate(theta: Theta) -> float:
        env = {a: getattr(theta, a) for a in _ALLOWED_VARS}
        return walk(tree, env)

    return evaluate


# --------------------------------------------------------------------------
# Candidates
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    name: str
    expr: str
    source: str = "builtin"
    note: str = ""


BUILTIN_CANDIDATES: tuple[Candidate, ...] = (
    Candidate("linear_sigma", "sigma", note="simplest inward push"),
    Candidate("bilinear", "lam*sigma + b*k", note="repo mode"),
    Candidate("triple", "lam*b*k", note="repo mode"),
    Candidate("trig", "sin(pi*lam)*cos(pi*sigma)*b", note="repo mode"),
    Candidate(
        "face_bowl",
        "(1-(lam-0.5)**2)*(1-(sigma-0.5)**2)",
        note="repo mode",
    ),
    Candidate("sin_lam", "sin(pi*lam)"),
    Candidate("tanh_sigma", "tanh(sigma)"),
    Candidate("log1p_sigma", "log(1+sigma)"),
    Candidate("rational_sigma", "sigma/(1+sigma)"),
    Candidate("sigma_sq", "sigma**2", note="flat to first order: no push"),
    Candidate("sqrt_sigma", "sqrt(sigma)", note="non-smooth: different exponent"),
    Candidate("cbrt_sigma", "sigma**0.3333333333333333", note="non-smooth"),
    Candidate("sigma_times_b", "b*sigma"),
    Candidate("one_minus_lam", "1-lam"),
    Candidate("exp_neg_lam", "exp(-lam)"),
    Candidate("cos_pi_sigma", "cos(pi*sigma)", note="flat at sigma=0"),
    # Frontier finds (model-proposed), kept as regression fixtures for each regime:
    Candidate("cone_dist", "((1-lam)**2 + sigma**2)**0.5", source="model",
              note="V.9 coupled: directional law, additive over-predicts 2x"),
    Candidate("diag_kink", "abs(sigma - (1-lam))", source="model",
              note="V.9 coupled crease"),
    Candidate("c1_power", "sigma**1.5", source="model",
              note="V.10 fractional 1<alpha<2: C^1 not C^2, gap ~ s^4"),
    Candidate("angular_ridge", "atan(sigma/((1-lam)+0.002))", source="model",
              note="V.11 saturating: amplitude-limited, derivative law invalid"),
)


# --------------------------------------------------------------------------
# Screening
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreenResult:
    candidate: Candidate
    ok: bool
    reason: str = ""
    axis: str = ""
    gamma: float = 0.0
    curvature: float = 0.0
    s_star: float = float("inf")
    predicted_gap: float = 0.0       # additive law (V.7)
    directional_gap: float = 0.0     # directional law (V.9), correct when coupled
    measured_gap: float = 0.0
    amp_bound: float = float("inf")  # sampled s*(sup P-P(corner)) ceiling
    alpha: float = 1.0               # leading homogeneity degree on the push axis
    gap_exponent: float = 0.0        # measured d log(gap)/d log(s): the robust signature
    smooth: bool = True
    coupled: bool = False
    saturating: bool = False         # derivative law exceeds the amplitude ceiling
    breaks: bool = False

    @property
    def best_prediction(self) -> float:
        """The law that should apply: directional for coupled, additive otherwise."""
        return self.directional_gap if self.coupled else self.predicted_gap

    @property
    def predicted_exponent(self) -> float:
        """Exponent the regime predicts: 2 for quadratic/coupled, 2/(2-alpha) fractional."""
        if abs(self.alpha - 1.0) > 0.1:
            a = min(self.alpha, 1.999)
            return 2.0 / (2.0 - a)
        return 2.0

    @property
    def regime(self) -> str:
        if not self.breaks:
            return "safe"
        if self.saturating:
            return "saturating"      # amplitude-limited; leading-order law invalid
        # A steep-but-smooth gate reads as quadratic locally but scales sub-2:
        # its linearization is valid only over a tiny radius (a near-singular
        # ridge). Classify it by its measured exponent, not its corner slope.
        if self.gap_exponent and self.gap_exponent < 1.8 and abs(self.alpha - 1.0) <= 0.1:
            return "saturating"
        # A super-quadratic finite-s exponent signals that a remote bump/gate,
        # not the local corner expansion, controls the measured maximum. As s
        # shrinks it can transition back to the quadratic asymptotic regime.
        if self.gap_exponent > 2.2 and abs(self.alpha - 1.0) <= 0.1:
            return "finite-scale"
        if abs(self.alpha - 1.0) > 0.1:
            return "fractional"      # V.8/V.10 exponent 2/(2-alpha)
        return "coupled" if self.coupled else "quadratic"

    @property
    def law_holds(self) -> bool:
        """
        Whether the regime's law predicts the gap. Judged on the s-INDEPENDENT
        exponent (robust), not a single-s coefficient: a term with large
        higher-order coefficients has the right exponent but a finite-s
        coefficient offset, and is not a counterexample.
        """
        if self.regime not in ("quadratic", "coupled") or not self.gap_exponent:
            return False
        return abs(self.gap_exponent - 2.0) < 0.15

    def row(self) -> str:
        if not self.ok:
            return f"  {self.candidate.name:<16} REJECTED  {self.reason}"
        star = "0" if self.s_star == 0.0 else ("inf" if self.s_star == float("inf") else f"{self.s_star:.3g}")
        tag = {"quadratic": "", "coupled": "  COUPLED", "fractional": f"  alpha~{self.alpha:.2f}",
               "saturating": "  SATURATING", "finite-scale": "  FINITE-SCALE", "safe": ""}[self.regime]
        law = "yes" if self.law_holds else (
            "n/a" if self.regime in ("fractional", "saturating", "finite-scale") else "no "
        )
        return (
            f"  {self.candidate.name:<16} {self.axis:<6} gamma={self.gamma:>9.4f} "
            f"s*={star:<4} pred={self.best_prediction:.3e} meas={self.measured_gap:.3e} "
            f"law={law}{tag}"
        )


def _is_smooth_at_corner(
    interaction: Callable[[Theta], float],
    theta: Theta,
    bounds: BoxBounds,
    axis: str,
) -> bool:
    """
    A finite inward derivative should be stable as h shrinks. sqrt-type terms
    have a divergent derivative and obey a different scaling law, so they must
    not be fitted with the quadratic formula.
    """
    obj: Objective = interaction
    d1 = inward_derivatives(obj, theta, bounds, h=1e-3)[axis]
    d2 = inward_derivatives(obj, theta, bounds, h=1e-5)[axis]
    if max(abs(d1), abs(d2)) < 1.0:
        return True
    return abs(d2) <= 3.0 * abs(d1) + 1.0


def _local_max(
    objective: Objective,
    bounds: BoxBounds,
    start: Theta,
    *,
    passes: int = 8,
    samples: int = 600,
) -> float:
    """Coordinate-wise fine local search inward from a corner."""
    intervals = {"lam": bounds.lam, "sigma": bounds.sigma, "b": bounds.b, "k": bounds.k}
    cur = start
    best = objective(cur)
    width = {a: (intervals[a][1] - intervals[a][0]) for a in _AXES}
    for p in range(passes):
        shrink = 0.5**p
        for axis in _AXES:
            lo, hi = intervals[axis]
            here = getattr(cur, axis)
            span = width[axis] * shrink
            for i in range(samples + 1):
                v = here - span + 2.0 * span * i / samples
                if v < lo or v > hi:
                    continue
                trial = Theta(
                    *[
                        v if a == axis else getattr(cur, a)
                        for a in _AXES
                    ]
                )
                val = objective(trial)
                if val > best:
                    best, cur = val, trial
    return best


def screen_candidate(
    candidate: Candidate,
    bounds: BoxBounds | None = None,
    *,
    s: float = 0.01,
) -> ScreenResult:
    """Apply the vertex_threshold criterion to one candidate expression."""
    bounds = bounds or default_nonlinear_bounds()
    try:
        interaction = compile_expression(candidate.expr)
    except UnsafeExpression as exc:
        return ScreenResult(candidate, ok=False, reason=str(exc))

    base = HypersurfacePlusInteraction(bounds, strength=0.0, interaction="bilinear")
    vm = vertex_margin(base, bounds)
    corner = vm.theta

    try:
        probe = interaction(corner)
        ders = inward_derivatives(interaction, corner, bounds)
        curv = inward_curvatures(base, corner, bounds)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return ScreenResult(candidate, ok=False, reason=f"not evaluable: {exc}")
    numeric = (probe, *ders.values(), *curv.values())
    if any(not isinstance(v, (int, float)) for v in numeric):
        return ScreenResult(candidate, ok=False, reason="complex/non-real evaluation")
    if any(math.isnan(v) or math.isinf(v) for v in numeric):
        return ScreenResult(candidate, ok=False, reason="non-finite derivative")

    axis = max(ders, key=lambda a: ders[a])
    gamma = ders[axis]
    if gamma <= _PUSH_TOL:
        return ScreenResult(
            candidate, ok=True, axis=axis, gamma=gamma,
            curvature=curv[axis], s_star=float("inf"), breaks=False,
            reason="no inward push",
        )

    smooth = _is_smooth_at_corner(interaction, corner, bounds, axis)
    c = curv[axis]
    predicted = 0.0
    directional = 0.0
    coupled = False
    if smooth and c > 0.0:
        predicted = universal_gap(base, interaction, bounds, s)
        directional = directional_gap(base, interaction, bounds, s)
        coupled = is_coupled(base, interaction, bounds, s)

    try:
        alpha = estimate_homogeneity(interaction, corner, bounds, axis)
        amp = amplitude_bound(interaction, bounds, s)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return ScreenResult(candidate, ok=False, reason=f"not evaluable: {exc}")

    def gap_at(strength: float) -> float:
        def combined(theta: Theta) -> float:
            return base(theta) + strength * interaction(theta)

        return _local_max(combined, bounds, corner) - combined(corner)

    try:
        measured = gap_at(s)
        measured_lo = gap_at(s / 4.0)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return ScreenResult(candidate, ok=False, reason=f"search failed: {exc}")

    # The s-independent scaling exponent: the robust signature of the regime.
    from math import log as _log

    exponent = (
        _log(measured / measured_lo) / _log(4.0)
        if measured > 1e-13 and measured_lo > 1e-13
        else 0.0
    )

    # A derivative-based prediction above the amplitude ceiling s*sup|P| is
    # invalid: the perturbation saturates (near-singular ridge) and the gap is
    # amplitude-limited, not curvature-limited.
    pred_for = directional if coupled else predicted
    saturating = pred_for > amp * 1.05

    return ScreenResult(
        candidate,
        ok=True,
        axis=axis,
        gamma=gamma,
        curvature=c,
        s_star=0.0 if vm.degenerate else vm.margin / gamma,
        predicted_gap=predicted,
        directional_gap=directional,
        measured_gap=measured,
        amp_bound=amp,
        alpha=alpha,
        gap_exponent=exponent,
        smooth=smooth,
        coupled=coupled,
        saturating=saturating,
        breaks=measured > 1e-12,
    )


def screen_all(
    candidates: tuple[Candidate, ...] | list[Candidate] | None = None,
    bounds: BoxBounds | None = None,
    *,
    s: float = 0.01,
) -> list[ScreenResult]:
    """Screen a bank, worst offenders (largest measured gap) first."""
    items = list(candidates if candidates is not None else BUILTIN_CANDIDATES)
    out = [screen_candidate(c, bounds, s=s) for c in items]
    out.sort(key=lambda r: (-r.measured_gap, r.candidate.name))
    return out


# --------------------------------------------------------------------------
# Optional model-proposed candidates
# --------------------------------------------------------------------------

PROPOSAL_PROMPT = """You are proposing candidate interaction terms for a study of
when vertex (corner) search fails on a box.

Setting: maximize C = b + k + [1-(1-lam)^2] + [1-sigma^2] + s*P(lam,sigma,b,k)
over the box lam in [0,1], sigma in [0,1], b in [0,2], k in [0,3].
The unperturbed maximum sits at the corner (lam,sigma,b,k) = (1,0,2,3), where the
objective is FLAT to first order in lam and sigma.

Propose {n} distinct candidate P, as expressions in lam, sigma, b, k.
Allowed: + - * / ** and sin cos tan exp log sqrt abs tanh atan sinh cosh, and pi.
Numeric exponents only. No other names, no assignments, no calls except those.

Aim for variety: smooth terms with different inward slopes at that corner,
terms that are flat there, and NON-SMOOTH terms (fractional powers of sigma or
of 1-lam) whose derivative at the corner is unbounded.

Reply with JSON only, no prose:
{{"candidates":[{{"name":"short_slug","expr":"...","why":"one clause"}}]}}
"""

FRONTIER_PROMPT = """You are proposing candidate interaction terms to STRESS-TEST a
theory of when corner (vertex) search fails on a box.

Setting: maximize C = b + k + [1-(1-lam)^2] + [1-sigma^2] + s*P(lam,sigma,b,k)
over lam in [0,1], sigma in [0,1], b in [0,2], k in [0,3], with small s>0.
The unperturbed max is the corner (1,0,2,3). Write x = 1-lam >= 0 and y = sigma >= 0
for the two "slack" directions; the objective is -x^2 - y^2 near the corner (flat
to first order, curvature 2 on each).

The theory already explains three regimes of the optimality gap Delta(s):
  - separable smooth terms: Delta ~ s^2 (additive over x and y)
  - single-variable NON-SMOOTH terms x^a or y^a (0<a<1): Delta ~ s^(2/(2-a))
  - degree-1 COUPLED terms like sqrt(x^2+y^2) or |y-x|: directional law, Delta ~ s^2

Propose {n} candidate P chosen to ESCAPE all three, i.e. to break the theory's
assumptions. Aim specifically for:
  1. COUPLED + NON-SMOOTH together, with DIFFERENT homogeneity in x vs y,
     e.g. sqrt(y) mixed with x, or (x^2+y)^0.5, or y^0.5 * x^0.5.
  2. Terms whose second derivative along a slack axis is NEGATIVE (adds curvature
     of the wrong sign), e.g. involving +x^2 or +y^2 with a plus sign.
  3. Terms that could move the maximizer far from the corner, or create a second
     competing bump away from it.
  4. Anisotropic mixes where x and y scale very differently.

Use x=1-lam and y=sigma written out in lam and sigma. Allowed operators:
+ - * / ** and sin cos tan exp log sqrt abs tanh atan sinh cosh, and pi.
Numeric exponents only. No other names, no assignments.

Reply with JSON only, no prose:
{{"candidates":[{{"name":"short_slug","expr":"...","why":"which assumption it attacks"}}]}}
"""


def propose_candidates(
    n: int = 12,
    *,
    model: str | None = None,
    base_url: str | None = None,
    frontier: bool = False,
    retries: int = 8,
    min_interval: float = 30.0,
    prompt: str | None = None,
    parser: Any = None,
) -> tuple[list[Any], str]:
    """
    Ask a model for candidate expressions. Returns (candidates, backend-or-reason).

    Every proposal is validated by `compile_expression` before it is kept, so an
    unparseable or unsafe reply degrades to fewer candidates, never to execution.

    Requests are paced and retry with server-aware exponential backoff on HTTP
    429 / transient errors, since hosted reasoning models rate-limit
    aggressively. ``POLYTOPE_API_MIN_INTERVAL`` and
    ``POLYTOPE_API_MAX_TOKENS`` can override the conservative defaults.
    """
    import os
    import sys
    import time
    import urllib.error
    import urllib.request
    from datetime import datetime
    from email.utils import parsedate_to_datetime
    from random import uniform

    from .loop_closure import resolve_backend

    proposal_model = model or os.environ.get("POLYTOPE_API_MODEL", "").strip() or None
    backend = resolve_backend(proposal_model, base_url)
    if backend is None:
        return [], "no API key set"

    key = os.environ[backend.key_env].strip()
    text_prompt = prompt or (FRONTIER_PROMPT if frontier else PROPOSAL_PROMPT).format(n=n)
    parse = parser or parse_proposals
    try:
        token_cap = int(os.environ.get("POLYTOPE_API_MAX_TOKENS", "").strip())
    except ValueError:
        token_cap = 0
    if token_cap <= 0:
        # A compact JSON record is normally well below 256 tokens per item.
        # Avoid reserving 16k completion tokens for every request: providers
        # commonly include the requested cap in their token-rate accounting.
        token_cap = max(3072, min(8192, n * 256))

    try:
        paced_interval = float(
            os.environ.get("POLYTOPE_API_MIN_INTERVAL", str(min_interval)).strip()
        )
    except ValueError:
        paced_interval = min_interval
    paced_interval = max(0.0, paced_interval)
    rate_state_path = os.environ.get("POLYTOPE_API_RATE_STATE", "").strip()
    try:
        configured_batch_size = int(
            os.environ.get("POLYTOPE_API_CONFIGURED_BATCH_SIZE", str(n)).strip()
        )
    except ValueError:
        configured_batch_size = n
    configured_batch_size = max(n, configured_batch_size)
    try:
        request_timeout = float(os.environ.get("POLYTOPE_API_TIMEOUT", "120").strip())
    except ValueError:
        request_timeout = 120.0
    request_timeout = max(30.0, request_timeout)

    body: dict[str, Any] = {
        "model": backend.model,
        "messages": [{"role": "user", "content": text_prompt}],
        "temperature": 0.95,
        # Reasoning models spend completion tokens on hidden reasoning before any
        # content; too small a cap returns content=null with finish_reason
        # "length". Give it room.
        "max_tokens": token_cap,
    }
    if backend.supports_extras:
        body["response_format"] = {"type": "json_object"}
        if backend.model == "stealth/ox-alpha":
            effort = os.environ.get("POLYTOPE_API_REASONING_EFFORT", "low").strip().lower()
            if effort not in {"low", "medium", "high"}:
                effort = "low"
            body["reasoning"] = {"effort": effort, "exclude": True}
    data_bytes = json.dumps(body).encode("utf-8")

    def retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
        """Read either seconds or an HTTP date from Retry-After."""
        raw = exc.headers.get("Retry-After") if exc.headers else None
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(raw)
                now = datetime.now(retry_at.tzinfo)
                return max(0.0, (retry_at - now).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    def wait_before_retry(
        attempt: int, reason: str, exc: urllib.error.HTTPError | None = None,
        minimum_delay: float = 0.0,
    ) -> None:
        server_delay = retry_after_seconds(exc) if exc is not None else None
        backoff = min(120.0, 5.0 * (2**attempt))
        delay = max(backoff, server_delay or 0.0, minimum_delay) + uniform(0.0, 1.0)
        # An accidental day-long Retry-After should not hang an experiment.
        delay = min(delay, 300.0)
        print(
            f"  API {reason}; retry {attempt + 2}/{retries} "
            f"in {delay:.1f}s",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(delay)

    global _LAST_PROPOSAL_REQUEST_AT
    last = "unknown error"
    for attempt in range(retries):
        shared_remaining = 0.0
        if rate_state_path:
            from .api_rate_limit import seconds_until_allowed

            shared_remaining = seconds_until_allowed(rate_state_path)
        local_remaining = 0.0
        if _LAST_PROPOSAL_REQUEST_AT is not None:
            local_remaining = paced_interval - (time.monotonic() - _LAST_PROPOSAL_REQUEST_AT)
        remaining = max(0.0, local_remaining, shared_remaining)
        if remaining > 0:
            print(f"  pacing API request for {remaining:.1f}s", file=sys.stderr, flush=True)
            time.sleep(remaining)
        req = urllib.request.Request(
            f"{backend.base_url}/chat/completions",
            data=data_bytes,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        _LAST_PROPOSAL_REQUEST_AT = time.monotonic()
        if rate_state_path:
            from .api_rate_limit import reserve_request

            reserve_request(
                rate_state_path, base_interval=paced_interval, batch_size=n
            )
        try:
            with urllib.request.urlopen(req, timeout=request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, dict) or not data.get("choices"):
                error = data.get("error", {}) if isinstance(data, dict) else {}
                error_text = json.dumps(error, sort_keys=True) if error else "missing choices"
                rate_like = "rate" in error_text.lower() or "429" in error_text
                last = f"provider error: {error_text}"
                if rate_like and rate_state_path:
                    from .api_rate_limit import note_throttle

                    note_throttle(
                        rate_state_path, base_interval=paced_interval,
                        batch_size=n, reason=last,
                    )
                    # Yield immediately.  The parent will honor the shared
                    # cooldown and smaller recommended batch; retrying the same
                    # oversized request only spends another rate-limit slot.
                    return [], last
                raise ValueError(last)
            choice = data["choices"][0]
            text = choice["message"].get("content")
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code == 429 and rate_state_path:
                from .api_rate_limit import note_throttle

                note_throttle(
                    rate_state_path, base_interval=paced_interval, batch_size=n,
                    retry_after=retry_after_seconds(exc), reason=last,
                )
                # The scheduler is the retry controller for throttles.  It will
                # wait on this state file and launch a smaller batch.
                return [], last
            if exc.code in (408, 409, 425, 429, 500, 502, 503, 504) and attempt < retries - 1:
                wait_before_retry(attempt, last, exc)
                continue
            return [], last
        except (urllib.error.URLError, OSError, KeyError, IndexError,
                json.JSONDecodeError, ValueError) as exc:
            last = f"{type(exc).__name__}: {exc}"
            if attempt < retries - 1:
                wait_before_retry(attempt, last)
                continue
            return [], last

        if rate_state_path:
            from .api_rate_limit import note_success

            note_success(
                rate_state_path, base_interval=paced_interval,
                configured_batch_size=configured_batch_size,
            )

        if isinstance(text, str) and text.strip():
            parsed = parse(text)
            # Optional provenance log for large verification campaigns. This
            # contains only the model response and request metadata, never the
            # API key. Logging parse-empty replies is essential for honest yield
            # accounting instead of silently treating them as no proposal.
            raw_log = os.environ.get("POLYTOPE_API_RAW_LOG", "").strip()
            if raw_log:
                try:
                    from pathlib import Path

                    log_path = Path(raw_log)
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    with log_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps({
                            "utc": datetime.now().astimezone().isoformat(),
                            "backend": backend.descriptor(),
                            "requested_n": n,
                            "parsed_items": len(parsed),
                            "usage": data.get("usage", {}),
                            "response": text,
                        }) + "\n")
                except OSError as exc:
                    print(f"  API raw-log write failed: {exc}", file=sys.stderr, flush=True)
            return parsed, backend.descriptor()

        finish = choice.get("finish_reason")
        last = f"{backend.descriptor()}: {'hit token cap' if finish == 'length' else 'empty content'}"
        if attempt < retries - 1:
            time.sleep(1.0)
            continue
    return [], last


def parse_proposals(text: Any) -> list[Candidate]:
    """
    Extract candidates from a model reply. Treats the reply purely as data:
    a non-string reply (e.g. null content from a reasoning model) or anything
    that does not parse under the whitelist yields no candidates, never an error.
    """
    import re

    if not isinstance(text, str):
        return []

    payload: Any = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                payload = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []
    if not isinstance(payload, dict):
        return []
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        return []

    out: list[Candidate] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        expr = str(item.get("expr", "")).strip()
        name = str(item.get("name", "")).strip() or f"proposed_{len(out)}"
        name = re.sub(r"[^A-Za-z0-9_]", "_", name)[:24]
        if not expr or expr in seen:
            continue
        try:
            compile_expression(expr)
        except UnsafeExpression:
            continue
        seen.add(expr)
        out.append(
            Candidate(name, expr, source="model", note=str(item.get("why", ""))[:80])
        )
    return out


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def search_report(results: list[ScreenResult], *, s: float = 0.01) -> list[str]:
    breaks = [r for r in results if r.ok and r.breaks]
    safe = [r for r in results if r.ok and not r.breaks]
    rejected = [r for r in results if not r.ok]
    nonsmooth = [r for r in breaks if not r.smooth]
    coupled = [r for r in breaks if r.regime == "coupled"]
    fractional = [r for r in breaks if r.regime == "fractional"]
    saturating = [r for r in breaks if r.regime == "saturating"]

    lines = [
        f"Interaction search: {len(results)} candidates at s={s}",
        "",
        f"  {len(breaks)} break vertex localization, {len(safe)} safe, "
        f"{len(rejected)} rejected",
        "",
        "BREAKS (largest measured gap first):",
    ]
    lines += [r.row() for r in breaks]
    if safe:
        lines += ["", "SAFE (no inward push at the degenerate corner):"]
        lines += [f"  {r.candidate.name:<16} {r.reason or 'gap below tolerance'}" for r in safe]
    if rejected:
        lines += ["", "REJECTED:"]
        lines += [r.row() for r in rejected]
    if nonsmooth:
        lines += [
            "",
            "NON-SMOOTH candidates found: unbounded inward derivative at the",
            "corner. These break localization but do NOT follow the quadratic",
            "law - they need their own exponent. See fractional_exponent_law.",
        ]
    if coupled:
        lines += [
            "",
            "COUPLED candidates found: the perturbation couples flat axes, so the",
            "additive law (V.7) over-predicts. 'pred' shows the directional law",
            "(V.9), which matches. See directional_gap.",
        ]
    if fractional:
        lines += [
            "",
            "FRACTIONAL / HIGHER-ORDER candidates (homogeneity alpha != 1): gap",
            "follows the unified exponent law Delta ~ s^(2/(2-alpha)) (V.10), not",
            "the quadratic law. See fractional_exponent_law / gap_exponent.",
        ]
    if saturating:
        lines += [
            "",
            "SATURATING candidates: a near-singular bounded ridge (e.g. atan(y/x)).",
            "The corner-derivative law predicts more than the amplitude ceiling",
            "s*sup|P|, so leading-order theory is INVALID; the gap is amplitude-",
            "limited. See amplitude_bound.",
        ]
    return lines
