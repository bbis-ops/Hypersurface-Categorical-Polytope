"""The repository's counter-arguments, made executable.

Each entry is a claim the repository has refuted, the refuting example as the
documents state it, and two executable parts:

* ``witness`` - a request exhibiting the counterexample, with the outcome the
  current code must produce (checked by ``python -m gitcalculator counter``
  and replayed across history to find when the code began to handle it);
* ``assess`` - how the counter-argument bears on *your* input: ``blocks`` (it
  prevents a theorem conclusion), ``caveat`` (it limits how to read the answer),
  ``averted`` (your input is exposed to it and the procedure handled it), or
  ``clear`` (your input is outside its reach).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Mapping

from categorical_polytope.ambient_face_compiler import transport_ambient_polynomial

from . import exact as X
from .certify import LocalModel, _faces, certify

SQUARE = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
PYRAMID = ("([[-1,0,0],[0,-1,0],[1,0,0],[0,1,0],[0,0,-1],[1,0,1],[-1,0,1],[0,1,1],[0,-1,1]], "
           "[0,0,1,1,0,1,0,1,0])")
# Issue #33: a qualified face under the diagonal weights, a mixed loss term below them, and no response at all.
ABSORPTION = {"system": SQUARE, "base": "-(x0**4+x1**4+x0*x1)", "perturbation": "x0*x1"}


@dataclass
class Context:
    """Everything the calculator knows about one input."""

    request: Mapping[str, Any]
    response: Mapping[str, Any]
    certificate: Mapping[str, Any]
    model: LocalModel | None
    measurement: Mapping[str, Any]
    alternatives: Mapping[str, Any] = field(default_factory=dict)

    def link(self, key: str) -> Mapping[str, Any]:
        return next((l for l in self.certificate.get("links", []) if l["id"] == key), {})

    def status(self, key: str) -> str | None:
        return self.link(key).get("status")

    def faces(self) -> list[Mapping[str, Any]]:
        return (self.link("faces").get("values") or {}).get("faces") or []

    def verdict(self, prediction: str) -> Mapping[str, Any]:
        return next((v for v in self.measurement.get("verdicts", []) if v["id"] == prediction), {})


@dataclass(frozen=True)
class CounterArgument:
    id: str
    title: str
    claim: str
    refutation: str
    sources: tuple[str, ...]
    witness: Mapping[str, Any]
    expect_text: str
    expect: Callable[[Mapping[str, Any]], bool]
    assess: Callable[[Context], tuple[str, str]]

    def describe(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "claim": self.claim, "refutation": self.refutation,
                "sources": list(self.sources), "witness": dict(self.witness), "expect": self.expect_text}


# --- the ambient-axis counterfactual ---------------------------------------------

def ambient_axes_prediction(model: LocalModel | None) -> dict[str, Any] | None:
    """What the law would say if the ambient axes at v replaced the feasible chart.

    Each axis points toward the side of P its coordinate can move to; the base
    orders are read along those axes. This reproduces the "ambient-axis control"
    of V.20 and is reported only as a counterfactual.
    """
    if model is None or not model.polynomial or model.base_at_vertex is None:
        return None
    n = model.dimension
    corners = X.vertices(model.rows, model.rhs) or []
    signs = []
    for k in range(n):
        low = min((c[k] for c in corners), default=model.vertex[k])
        signs.append(1 if model.vertex[k] == low else -1)
    generators = {f"a{k}": tuple(Fraction(signs[k] if j == k else 0) for j in range(n)) for k in range(n)}
    zero = (0,) * n
    base = transport_ambient_polynomial(model.base, model.vertex, generators).polynomial
    gain = transport_ambient_polynomial(model.perturbation, model.vertex, generators).polynomial
    loss = {s: -c for s, c in base.items() if s != zero and c}
    orders = []
    for k in range(n):
        pure = [(s[k], c) for s, c in loss.items() if s[k] and sum(s) == s[k]]
        if not pure or min(pure)[1] <= 0 or min(pure)[0] < 2:
            return None
        orders.append(min(pure)[0])
    axes = tuple(generators)
    ghost = LocalModel(model.rows, model.rhs, model.base_tree, model.perturbation_tree, model.base,
                       model.perturbation, model.vertex, (), axes, generators, model.rho, True,
                       loss=loss, gain={s: c for s, c in gain.items() if s != zero and c},
                       weights=tuple(Fraction(1, b) for b in orders))
    if not ghost.gain:
        return None
    _, q_star = _faces(ghost, {})
    feasible = [k for k in range(n) if all(X.dot(model.rows[j], generators[axes[k]]) <= 0
                                           for j in range(len(model.rows))
                                           if X.dot(model.rows[j], model.vertex) == model.rhs[j])]
    return {
        "directions": {a: [X.label(x) for x in generators[a]] for a in axes},
        "infeasible_directions": [axes[k] for k in range(n) if k not in feasible],
        "orders": dict(zip(axes, orders)),
        "q_star": X.label(q_star),
        "gamma": X.label(1 / (1 - q_star)) if q_star is not None else None,
    }


# --- assessments ---------------------------------------------------------------------

def _feasible_gamma(ctx: Context) -> str | None:
    return ctx.certificate.get("gamma") or (ctx.response.get("universality_class") or {}).get("response_exponent_label")


def _ambient(ctx: Context):
    naive = ctx.alternatives.get("ambient_axes")
    feasible = _feasible_gamma(ctx)
    if not naive or naive.get("gamma") is None or feasible is None:
        return "clear", "No ambient-axis counterfactual applies to this input."
    if naive["gamma"] == feasible:
        return "clear", f"The ambient axes give the same exponent γ = {feasible} here."
    verdict = ctx.verdict("ambient-axes").get("verdict")
    tail = {"contradicted": " Certified lower bounds contradict the ambient answer.",
            "consistent": " The measurement does not separate the two exponents."}.get(verdict, "")
    moves = naive.get("infeasible_directions") or []
    return "averted", (f"Ambient axes would give γ = {naive['gamma']}"
                       + (f" (direction {', '.join(moves)} leaves P)" if moves else "")
                       + f"; the feasible chart gives γ = {feasible}." + tail)


def _signed(ctx: Context):
    h5 = ctx.link("H5")
    if h5.get("status") == "unresolved":
        terms = ", ".join((h5.get("values") or {}).get("uncontrolled") or [])
        gain = ctx.measurement.get("measured_exponent")
        return "blocks", (f"Uncontrolled positive terms {terms} sit below the selection cutoff, so the license is withheld"
                          + (f"; certified lower bounds grow like s^{gain}." if gain else "."))
    absorbed = (h5.get("values") or {}).get("absorbed") or []
    if absorbed:
        return "averted", f"Higher positive terms are absorbed by negative monomials ({'; '.join(absorbed)})."
    return "clear", "Every positive monomial is dominated by the base at the selected order."


def _sharp(ctx: Context):
    if ctx.certificate.get("q_star") and ctx.status("H5") == "unresolved":
        gamma = ctx.certificate.get("gamma")
        verdict = ctx.verdict("exact-faces").get("verdict")
        return "blocks", (f"A face qualifies with γ = {gamma}, but a signed term below it is uncontrolled; "
                          f"the qualified minimum is not a theorem here." +
                          (" Certified lower bounds contradict it." if verdict == "contradicted" else ""))
    return "clear", "No qualified minimum rests on an uncontrolled signed layer."


def _interior(ctx: Context):
    stuck = [f for f in ctx.faces() if f.get("status") == "unresolved"]
    if stuck:
        names = "; ".join(f"{{{', '.join(f['face'])}}}: {f.get('initial_form')}" for f in stuck)
        return "blocks", f"Mixed-sign initial forms without a positive witness: {names}."
    return "clear", "Every initial form is decided by its signs or an exact witness."


def _empty(ctx: Context):
    if ctx.certificate.get("status") == "zero_response":
        lemma = "Lemma A (absorption by the loss)" if ctx.status("absorption") == "exact" else "Lemma 2"
        return "averted", f"{lemma} certifies Δ(s) = 0 for small s, so here the refusal does mean no response."
    if ctx.certificate.get("q_star") or ctx.response.get("status") in {"licensed", "unlicensed"}:
        return "clear", "A response exponent was produced."
    if ctx.measurement.get("positive_gain_found"):
        gain = ctx.measurement.get("measured_exponent")
        return "caveat", ("The selector finds no qualified face, yet certified lower bounds are positive"
                          + (f" and scale like s^{gain}." if gain else "."))
    return "caveat", "No qualified face. That alone proves neither zero response nor a competing law."


def _active(ctx: Context):
    answered = ctx.certificate.get("status") == "theorem" or ctx.response.get("status") == "licensed"
    winners = [set(f["face"]) for f in ctx.faces() if f.get("winning")]
    minimal = [w for w in winners if not any(other < w for other in winners)]
    if not answered or not minimal:
        return "clear", "No licensed leading channel to compare with the optimizer."
    leading = set().union(*minimal)
    support = set(ctx.measurement.get("support_at_smallest_s") or [])
    extra = sorted(support - leading)
    channel = " or ".join("{" + ", ".join(sorted(w)) + "}" for w in minimal)
    if extra:
        return "caveat", (f"The leading channel is {channel}, but the measured optimizer also moves along "
                          f"{', '.join(extra)}: released constraints describe the leading channel only.")
    return "clear", f"The measured optimizer stays on the leading channel {channel}."


def _homogeneity(ctx: Context):
    h2 = ctx.status("H2")
    if h2 == "exact":
        return "averted", "H2 is verified exactly; the numerical homogeneity probe is not relied on."
    if h2 == "failed" and ctx.response.get("status") == "licensed":
        return "blocks", ("The backend licenses this from a homogeneity probe, but H2 fails exactly: "
                          + ctx.link("H2").get("detail", ""))
    if h2 == "failed":
        return "averted", "H2 fails exactly and the backend also withholds the license."
    if h2 in (None, "not_reached"):
        return "clear", "The principal part was not reached."
    return "caveat", "The principal part is only probed numerically for this input."


def _isolation(ctx: Context):
    status = ctx.status("H0")
    detail = ctx.link("H0").get("detail", "")
    if status == "exact":
        return "averted", f"H0 is proved: {ctx.link('H0').get('method')}."
    if status == "failed":
        if ctx.measurement.get("boundary_dominated"):
            detail += " The certified lower bounds are attained far from v, at the rival."
        return "blocks", detail
    if status in {"probed", "unresolved"}:
        return "caveat", "Uniqueness of the base maximizer rests on a finite probe."
    return "clear", "H0 was not reached."


def _critical(ctx: Context):
    critical = [f for f in ctx.faces() if f.get("status") == "critical"]
    if critical:
        return "caveat", ("A degree-one layer competes with the base at equal order on "
                          + ", ".join("{" + ", ".join(f["face"]) + "}" for f in critical)
                          + "; it adds nothing for small s when dominated (Lemma 2).")
    return "clear", "No face sits at the critical degree q = 1."


def _ties(ctx: Context):
    winners = [f for f in ctx.faces() if f.get("winning")]
    minimal = [f for f in winners if not any(set(g["face"]) < set(f["face"]) for g in winners)]
    initial_terms = max((f.get("initial_form", "").count(" + ") + f.get("initial_form", "").count(" - ") + 1
                         for f in minimal), default=0)
    if len(minimal) > 1 or initial_terms > 1:
        return "caveat", (f"{len(minimal)} minimal winning face(s) tie at q*; every tied term enters the coefficient, "
                          "while the exponent depends only on q*.")
    return "clear", "One minimal winning face with a one-term initial form."


def _finite(ctx: Context):
    rows = [v for v in ctx.measurement.get("verdicts", []) if v.get("coefficient_ratio")]
    if rows:
        best = rows[0]
        return "caveat", (f"At the smallest certified scale the lower bound is {best['coefficient_ratio']}× the "
                          f"leading term of '{best['id']}'. Asymptotic validity is not an accuracy statement at fixed s.")
    if _feasible_gamma(ctx):
        return "caveat", "The law is a limit s → 0; accuracy at a given s needs its own bound."
    return "clear", "No exponent to scale."


def _inverse(ctx: Context):
    inverse = ctx.response.get("inverse") or {}
    if "observed_exponent" not in ctx.request:
        return "clear", "No observed exponent was supplied."
    return "caveat", (f"Inverse status {inverse.get('status')}: matching uses the numerical predictor's face degrees "
                      f"within tolerance {inverse.get('tolerance')}, not exact reconstruction.")


def _simple(ctx: Context):
    if ctx.status("vertex") == "failed":
        return "blocks", ctx.link("vertex").get("detail", "")
    return "clear", "The selected vertex is simple."


def _absorbed(ctx: Context):
    candidate = any(f.get("winning") for f in ctx.faces())
    if ctx.status("absorption") == "exact":
        pairs = (ctx.link("absorption").get("values") or {}).get("pairs") or []
        return "averted", (("A face qualifies under the diagonal weights, but the loss" if candidate else "The loss") +
                           " absorbs every positive term of the gain" + (f" ({'; '.join(pairs)})" if pairs else "") +
                           ", so Lemma A proves Δ(s) = 0 for small s.")
    if ctx.status("H2") == "failed" and candidate:
        return "caveat", ("Hypothesis 2 fails, so the face data's exponent is only a candidate: a mixed term of the loss "
                          "below the diagonal weights can absorb the gain it divides.")
    return "clear", "The principal part is diagonal, or no face candidate rests on a non-diagonal one."


def _absorption_witness(response: Mapping[str, Any]) -> bool:
    return response.get("status") in {"unlicensed", "refused"} and certify(ABSORPTION, response)[0]["status"] == "zero_response"


def _status(*allowed: str) -> Callable[[Mapping[str, Any]], bool]:
    return lambda response: response.get("status") in allowed


REGISTRY: tuple[CounterArgument, ...] = (
    CounterArgument(
        "ambient-axes", "Ambient axes decide the exponent",
        "Probing F and G along the ambient coordinate axes at v gives the Newton data.",
        "At the simplex vertex (0,1), the ambient direction (1,0) leaves P and sees quadratic decay, predicting γ = 2. "
        "The feasible chart u₀ = (1,−1), u₁ = (0,−1) gives D = c₀⁴ + c₁², R = c₀, and Δ(s) = 3·4^(−4/3)·s^(4/3).",
        ("README.md#the-decisive-example-feasibility-comes-before-degree",
         "docs/FORMAL_AMBIENT_FACE_TRANSPORT.md#why-ambient-axes-fail"),
        {"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4)", "perturbation": "x0"},
        "licensed with universality class face-weight:1/4|response:4/3",
        lambda r: r.get("status") == "licensed"
        and (r.get("universality_class") or {}).get("id") == "face-weight:1/4|response:4/3",
        _ambient),
    CounterArgument(
        "signed-channel", "A non-positive initial form excludes gain",
        "Former Lemma 2: a face whose first weighted layer is non-positive contributes nothing.",
        "D₀ = x⁶ + y⁶, R = −x² + xy²: no coordinate face qualifies, yet −x² + xy² = y⁴/4 − (x − y²/2)² opens a curved "
        "channel and Δ(s) ~ s³/432.",
        ("docs/MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant",
         "docs/FORMAL_FACE_SELECTION.md#6-upper-control-on-unqualified-faces"),
        {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2"},
        "not licensed, with an explicit higher_order_unresolved blocker",
        lambda r: r.get("status") != "licensed"
        and any("higher_order_unresolved" in b for b in (r.get("scope") or {}).get("blockers") or []),
        _signed),
    CounterArgument(
        "signed-sharp", "A qualified face fixes the exponent despite signed terms below it",
        "Once some face qualifies, its least degree gives the exponent.",
        "Adding y⁵ to the signed example qualifies the y face (q = 5/6, γ = 6), but the curved witness gives "
        "Δ(s) ≥ c·s³, which no Θ(s⁶) law allows.",
        ("docs/MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant",),
        {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2+x1**5"},
        "not licensed",
        lambda r: r.get("status") != "licensed",
        _sharp),
    CounterArgument(
        "interior-zero", "Negative axis forms rule out gain",
        "If every coordinate-axis initial form is negative, the perturbation cannot help.",
        "D₀ = x⁴ + y⁴, R = −(x − y)² + x³: both axis forms are negative and the full form is non-positive, "
        "but x = y = 3s/8 gives 27s⁴/2048 > 0.",
        ("docs/MATHEMATICAL_AUDIT.md#2-why-uniform-remainders-did-not-repair-the-proof",),
        {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "-(x0-x1)**2+x0**3"},
        "not licensed",
        _status("unlicensed", "refused"),
        _interior),
    CounterArgument(
        "empty-not-zero", "No qualified face means no response",
        "A refusal for lack of a qualified face shows that the perturbation does not help.",
        "The signed example is refused by the selector, yet Δ(s) ~ s³/432 > 0. An empty qualified set establishes "
        "neither zero response nor a competing law.",
        ("docs/FORMAL_FACE_SELECTION.md#10-scope", "docs/FACE_SELECTION_BACKEND.md#refused"),
        {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2"},
        "refused (and the calculator's certified lower bounds are positive)",
        _status("refused"),
        _empty),
    CounterArgument(
        "active-set", "The winning face is the optimizer's support",
        "The released constraints of the winning face are exactly the perturbed optimizer's support.",
        "J = −x⁴ − y⁴ + s(x + y²): the minimal degree 1/4 lies on the x axis, yet x_s = (s/4)^(1/3) and "
        "y_s = (s/2)^(1/2) are both positive for every small s.",
        ("docs/MATHEMATICAL_AUDIT.md#6-exponent-selection-does-not-fix-the-active-set",),
        {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "x0+x1**2"},
        "licensed with γ = 4/3 on the x axis",
        lambda r: r.get("status") == "licensed"
        and (r.get("universality_class") or {}).get("response_exponent_label") == "4/3",
        _active),
    CounterArgument(
        "homogeneity-probe", "A measured homogeneity near one proves the principal part",
        "base_homogeneity ≈ 1 establishes Hypothesis 2.",
        "F = −(x0² + x0·x1 + x1²) on the square: the probe measures homogeneity 1.0, but the cross term x0·x1 has the "
        "principal weight, so in_w(D) is not the diagonal D₀ that Hypothesis 2 requires.",
        ("docs/FORMAL_FACE_SELECTION.md#4-hypotheses-with-uniform-remainders",
         "docs/PRINCIPLE_DOCUMENTATION_REVIEW.md#substantive-corrections-and-clarifications"),
        {"system": SQUARE, "base": "-(x0**2+x0*x1+x1**2)", "perturbation": "x0"},
        "answered (the exact H2 check, not the backend, is what rejects it)",
        _status("licensed", "unlicensed"),
        _homogeneity),
    CounterArgument(
        "isolation-probe", "Finding no rival maximizer proves uniqueness",
        "A finite rival search establishes Hypothesis 0.",
        "F = −((x0(1 − x0))² + x1²) has two global maximizers, (0,0) and (1,0). The tie breaks the local law: "
        "moving to the other maximizer already gains s·(G(w) − G(v)).",
        ("docs/FORMAL_FACE_SELECTION.md#2-global-isolation",),
        {"system": SQUARE, "base": "-((x0*(1-x0))**2 + x1**2)", "perturbation": "x0"},
        "not licensed",
        _status("unlicensed", "refused"),
        _isolation),
    CounterArgument(
        "critical-layer", "Degree-one terms obey the same law",
        "Every face degree q gives γ = 1/(1 − q).",
        "D = x0² + x1², R = x0²: q = 1, so γ is undefined; −x0² + s·x0² ≤ 0 for s < 1 and Δ(s) = 0 for small s.",
        ("docs/FACE_SELECTION_BACKEND.md#term-level-perturbation-classification",
         "docs/FORMAL_FACE_SELECTION.md#6-upper-control-on-unqualified-faces"),
        {"system": SQUARE, "base": "-(x0**2 + x1**2)", "perturbation": "x0**2"},
        "refused (degree outside (0, 1))",
        _status("refused"),
        _critical),
    CounterArgument(
        "tied-coefficient", "One tied monomial determines the coefficient",
        "The winning monomial alone fixes the leading coefficient.",
        "D = x0⁴ + x1⁴, R = x0 + x1: both axes tie at q = 1/4, and Δ(s) = 2·3·4^(−4/3)·s^(4/3). The exponent "
        "depends on q* only; every tied lowest-layer term enters the coefficient.",
        ("docs/PRINCIPLE_DOCUMENTATION_REVIEW.md#substantive-corrections-and-clarifications",),
        {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "x0+x1"},
        "licensed with two minimal winning faces",
        lambda r: r.get("status") == "licensed" and len((r.get("selection") or {}).get("winning_faces") or []) == 2,
        _ties),
    CounterArgument(
        "finite-scale", "The asymptotic law gives the response at a given s",
        "Δ(s) ≈ C·s^γ is accurate whenever the exponent is licensed.",
        "The runbook's finite-scale pair shares the licensed exponent 3, yet one request lies outside a 10% tolerance "
        "at its scale: asymptotic validity and finite-scale accuracy are separate decisions.",
        ("docs/CURVED_FINITE_SCALE.md", "docs/RUNBOOK.md#finite-scale-accuracy-is-a-separate-question"),
        {"operation": "curved_reduction", "system": SQUARE, "base": "-(x0**6+x1**6)",
         "perturbation": "-x0**2+x0*x1**2-x1**4/4+x1**4/1000000000+x1**5",
         "finite_scale": {"s": "1e-9", "relative_tolerance": "1/10"}},
        "licensed exponent 3, yet outside_tolerance at s = 1e-9 (runbook cancellation-crossover)",
        lambda r: r.get("status") == "licensed"
        and (r.get("finite_scale") or {}).get("status") == "outside_tolerance",
        _finite),
    CounterArgument(
        "inverse-tolerance", "Inverse matching identifies the mechanism exactly",
        "An observed exponent recovers the winning mechanism.",
        "The inverse block compares q_obs = 1 − 1/γ_obs with the numerical predictor's admitted face degrees within "
        "an absolute tolerance; it can be ambiguous or unmatched and never reconstructs the objective.",
        ("docs/FACE_SELECTION_BACKEND.md#forward-and-inverse-power",),
        {"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4)", "perturbation": "x0", "observed_exponent": 2},
        "inverse status no_face_match",
        lambda r: (r.get("inverse") or {}).get("status") == "no_face_match",
        _inverse),
    CounterArgument(
        "non-simple", "The law applies at any vertex",
        "Face selection works at every maximizing vertex.",
        "At the apex of a square pyramid four constraints are active in dimension three. The tangent cone is not "
        "simplicial, there is no edge chart, and the theorem does not apply.",
        ("docs/FORMAL_FACE_SELECTION.md#10-scope",),
        {"system": PYRAMID, "base": "x2", "perturbation": "x0"},
        "refused",
        _status("refused"),
        _simple),
    CounterArgument(
        "loss-absorption", "A qualified face fixes the exponent without a diagonal principal part",
        "Under global isolation, the face data's exponent holds even when Hypothesis 2 fails.",
        "D = x⁴ + y⁴ + xy, R = xy: the face {x, y} qualifies with q = 1/2 under the diagonal weights, yet "
        "F + sG = −x⁴ − y⁴ − (1 − s)xy ≤ 0 on the square, so Δ(s) = 0 for s ≤ 1. The mixed loss term absorbs the gain "
        "monomial it divides (Lemma A).",
        ("docs/FORMAL_LOSS_ABSORPTION.md#statement", "docs/FORMAL_FACE_SELECTION.md#4-hypotheses-with-uniform-remainders"),
        ABSORPTION,
        "not licensed by the backend, and zero response proved by Lemma A",
        _absorption_witness,
        _absorbed),
)

EFFECT_ORDER = {"blocks": 0, "caveat": 1, "averted": 2, "clear": 3}


def assess(ctx: Context) -> list[dict[str, Any]]:
    """Apply every counter-argument to one input, most severe first."""
    results = []
    for argument in REGISTRY:
        try:
            effect, detail = argument.assess(ctx)
        except Exception as exc:  # an assessment must never break a calculation
            effect, detail = "caveat", f"assessment failed: {type(exc).__name__}: {exc}"
        results.append({"id": argument.id, "title": argument.title, "effect": effect, "detail": detail,
                        "claim": argument.claim, "refutation": argument.refutation,
                        "sources": list(argument.sources)})
    return sorted(results, key=lambda r: EFFECT_ORDER[r["effect"]])


def check_witnesses(handle: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Run each witness through ``handle`` and test the documented expectation."""
    report = []
    for argument in REGISTRY:
        try:
            response = handle(dict(argument.witness, request_id=f"witness:{argument.id}"))
            passed = bool(argument.expect(response))
            status = response.get("status")
        except Exception as exc:
            passed, status = False, f"error: {type(exc).__name__}: {exc}"
        report.append({"id": argument.id, "expect": argument.expect_text, "status": status, "passed": passed})
    return report
