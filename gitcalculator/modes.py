"""Design, Sweep and Attack: inverse, parametric and adversarial calculation.

The face-selection law maps geometry to an exponent exactly, so it can be run
in more directions than forward:

* **Design** reads the exponent spectrum of a vertex. In the edge chart the
  coordinates are the slacks of the active constraints (c = b_S − A_S·x), so a
  monomial c^α is the perturbation ∏ slackᵢ^αᵢ, with weighted degree Σ αᵢ/βᵢ.
  Every exponent the qualified-face law (or V.22) can produce at this vertex
  lies in {1/(1 − q) : q in that semigroup, 0 < q < 1}; each one is synthesized
  and certified.
* **Sweep** compiles a phase fan from a family G(t) automatically: exact walls
  where transported coefficients vanish, plus certified brackets around any
  other change of outcome, such as a positivity wall.
* **Attack** generates counterexamples for the input itself: lower-order
  intrusions, suppressions, sign flips, base cross terms and facet tilts, each
  re-certified.

The browser engine (web/modes.js) implements the same three modes.
"""

from __future__ import annotations

import re
from fractions import Fraction
from itertools import combinations
from typing import Any, Mapping

from categorical_polytope.curved_reduction import ReductionNotApplicable, reduce_quadratic_channel

from . import exact as X
from .certify import LocalModel, certify

EPS = "1/100"


def _localize(system: str, base: str, perturbation: str = "x0"):
    return certify({"system": system, "base": base, "perturbation": perturbation}, {})


def _minimal_winners(certificate: Mapping[str, Any], axes) -> str:
    faces = next((l.get("values", {}).get("faces", []) for l in certificate.get("links", []) if l["id"] == "faces"), [])
    winners = [set(f["face"]) for f in faces if f.get("winning")]
    minimal = [w for w in winners if not any(o < w for o in winners)]
    return " ".join("{" + ",".join(sorted(w)) + "}" for w in sorted(minimal, key=sorted))


def outcome(request: Mapping[str, Any]) -> dict[str, Any]:
    """The certificate-only answer, with the V.22 reduction as a fallback."""
    certificate, model = certify(request, {})
    proved = certificate["status"] in {"theorem", "zero_response"}
    verdict = "proved" if proved else "unlicensed" if certificate.get("gamma") else "refused"
    gamma = certificate.get("gamma")
    if not proved and model is not None and model.dimension == 2 and model.gain:
        try:
            reduction = reduce_quadratic_channel(model.loss, model.gain, axes=model.axes)
            verdict, gamma = "proved-v22", X.label(reduction.exponent)
        except ReductionNotApplicable:
            pass
    return {"verdict": verdict, "gamma": gamma, "q_star": certificate.get("q_star"), "status": certificate["status"],
            "winners": _minimal_winners(certificate, model.axes if model else ()) if model else "",
            "open": certificate.get("open_links", [])}


# --- Design -----------------------------------------------------------------------

def affine_text(row, bound, n: int) -> str:
    """The slack b − a·x of one constraint, written in x0..x{n-1}."""
    terms = ([(bound, None)] if bound else []) + [(-a, f"x{k}") for k, a in enumerate(row) if a]
    if not terms:
        return "0"
    pieces = []
    for index, (c, var) in enumerate(terms):
        magnitude = abs(c)
        body = (var if magnitude == 1 else f"{X.label(magnitude)}*{var}") if var else X.label(magnitude)
        pieces.append(("-" if c < 0 else "") + body if index == 0 else f" {'-' if c < 0 else '+'} {body}")
    return "".join(pieces)


def _slack_power(slack: str, power: int) -> str:
    base = slack if re.fullmatch(r"\w+", slack) else f"({slack})"
    return base if power == 1 else f"{base}**{power}"


def slack_monomial(slacks, alpha) -> str:
    return "*".join(_slack_power(slacks[i], p) for i, p in enumerate(alpha) if p) or "1"


def spectrum(model: LocalModel, limit: int = 50_000) -> tuple[list[tuple[Fraction, list[tuple[int, ...]]]], bool]:
    betas = [beta for beta, _ in model.principal.values()]
    groups: dict[Fraction, list[tuple[int, ...]]] = {}
    total = 1
    for beta in betas:
        total *= beta

    def visit(prefix: tuple[int, ...]) -> None:
        if len(prefix) == len(betas):
            if any(prefix):
                q = X.weighted_degree(prefix, model.weights)
                if q < 1:
                    groups.setdefault(q, []).append(prefix)
            return
        for a in range(betas[len(prefix)]):
            visit(prefix + (a,))

    if total <= limit:
        visit(())
    return sorted(groups.items()), total > limit


def design(system: str, base: str, target: str | None = None) -> dict[str, Any]:
    certificate, model = _localize(system, base)
    links = certificate["links"]
    if model is None or model.weights is None:
        return {"status": "not_applicable", "links": links,
                "reason": certificate.get("reason") or "the exponent spectrum needs the exact diagonal principal part (Hypothesis 2)"}
    slacks = [affine_text(model.rows[j], model.rhs[j], model.dimension) for j in model.active]
    groups, truncated = spectrum(model)
    entries = []
    for q, alphas in groups:
        gamma = 1 / (1 - q)
        entries.append({"q": X.label(q), "gamma": X.label(gamma), "gamma_value": float(gamma), "mechanism_count": len(alphas),
                        "mechanisms": [{"alpha": list(a), "monomial": X.monomial_text(a, model.axes),
                                        "perturbation": slack_monomial(slacks, a)} for a in alphas[:8]]})
    statuses = {l["id"]: l["status"] for l in links}
    result: dict[str, Any] = {
        "status": "complete", "base_proved": all(statuses.get(k) == "exact" for k in ("H0", "H1", "H2")),
        "vertex": [X.label(v) for v in model.vertex], "weights": [X.label(w) for w in model.weights],
        "orders": [beta for beta, _ in model.principal.values()],
        "slacks": [{"axis": a, "constraint": model.active[i], "expression": slacks[i]} for i, a in enumerate(model.axes)],
        "spectrum": entries, "truncated": truncated,
    }
    if target is not None and str(target).strip():
        gamma_t = X.to_fraction(str(target).strip())
        if gamma_t <= 1:
            result["target"] = {"gamma": X.label(gamma_t), "error": "a fractional response needs γ > 1"}
            return result
        q_t = 1 - 1 / gamma_t
        hit = next((e for e in entries if Fraction(e["q"]) == q_t), None)
        below = [e["gamma"] for e in entries if Fraction(e["gamma"]) < gamma_t]
        above = [e["gamma"] for e in entries if Fraction(e["gamma"]) > gamma_t]
        result["target"] = {"gamma": X.label(gamma_t), "q": X.label(q_t), "achievable": hit is not None,
                            "nearest_below": below[-1] if below else None, "nearest_above": above[0] if above else None}
        if hit:
            result["target"]["candidates"] = [dict(m, check=outcome({"system": system, "base": base, "perturbation": m["perturbation"]}))
                                              for m in hit["mechanisms"][:4]]
    return result


# --- Sweep --------------------------------------------------------------------------

def _at(expression: str, t: Fraction) -> str:
    return re.sub(r"\bt\b", f"({t.numerator}/{t.denominator})", expression)


def _interpolate(points: list[tuple[Fraction, Fraction]]) -> dict[int, Fraction]:
    """Exact Lagrange interpolation, returned as power -> coefficient."""
    result: dict[int, Fraction] = {}
    for i, (ti, yi) in enumerate(points):
        if not yi:
            continue
        basis = {0: Fraction(1)}
        denominator = Fraction(1)
        for j, (tj, _) in enumerate(points):
            if i == j:
                continue
            nxt: dict[int, Fraction] = {}
            for p, c in basis.items():
                nxt[p + 1] = nxt.get(p + 1, Fraction(0)) + c
                nxt[p] = nxt.get(p, Fraction(0)) - c * tj
            basis = nxt
            denominator *= ti - tj
        for p, c in basis.items():
            result[p] = result.get(p, Fraction(0)) + yi * c / denominator
    return {p: c for p, c in result.items() if c}


def _roots(law: Mapping[int, Fraction], lo: Fraction, hi: Fraction) -> list[dict[str, Fraction]]:
    def value(t: Fraction) -> Fraction:
        return sum((c * t**p for p, c in law.items()), Fraction(0))

    degree = max(law, default=0)
    if degree == 0:
        return []
    if degree == 1:
        root = -law.get(0, Fraction(0)) / law[1]
        return [{"at": root}] if lo <= root <= hi else []
    if degree == 2:
        a, b, c = law[2], law.get(1, Fraction(0)), law.get(0, Fraction(0))
        disc = b * b - 4 * a * c
        if disc < 0:
            return []
        rn, rd = _isqrt(disc.numerator), _isqrt(disc.denominator)
        if rn is not None and rd is not None:
            root = Fraction(rn, rd)
            return [{"at": r} for r in sorted({(-b - root) / (2 * a), (-b + root) / (2 * a)}) if lo <= r <= hi]
    found, steps = [], 256
    previous, sign_previous = lo, _sign(value(lo))
    if sign_previous == 0:
        found.append({"at": lo})
    for i in range(1, steps + 1):
        x = lo + (hi - lo) * i / steps
        sign_x = _sign(value(x))
        if sign_x == 0:
            found.append({"at": x})
        elif sign_previous and sign_x != sign_previous:
            left, right = previous, x
            for _ in range(60):
                middle = (left + right) / 2
                if _sign(value(middle)) == sign_previous:
                    left = middle
                else:
                    right = middle
            found.append({"lo": left, "hi": right})
        previous, sign_previous = x, sign_x
    return found


def _isqrt(value: int) -> int | None:
    if value < 0:
        return None
    root = int(value**0.5)
    for candidate in (root - 1, root, root + 1):
        if candidate >= 0 and candidate * candidate == value:
            return candidate
    from math import isqrt
    root = isqrt(value)
    return root if root * root == value else None


def _sign(value: Fraction) -> int:
    return (value > 0) - (value < 0)


def sweep(system: str, base: str, perturbation: str, lo: str = "-1", hi: str = "1") -> dict[str, Any]:
    low, high = X.to_fraction(lo), X.to_fraction(hi)
    if not low < high:
        return {"status": "not_applicable", "reason": "the range needs from < to"}
    certificate, model = _localize(system, base)
    if model is None or model.weights is None:
        return {"status": "not_applicable", "reason": "the phase fan needs the exact diagonal principal part (Hypothesis 2)",
                "links": certificate["links"]}
    # Each transported coefficient is a polynomial in t of degree at most the
    # expression's total degree; one spare sample guards that bound.
    degree = X.total_degree(X.parse(re.sub(r"\bt\b", "x0", perturbation), model.dimension)) or 0
    samples = [low + (high - low) * Fraction(k, degree + 1) for k in range(degree + 2)]
    gains = [_localize(system, base, _at(perturbation, t))[1].gain for t in samples]
    laws = {s: _interpolate([(t, g.get(s, Fraction(0))) for t, g in zip(samples, gains)]) for s in set().union(*gains)}
    laws = {s: law for s, law in laws.items() if law}
    walls = [dict(kind="coefficient", monomial=X.monomial_text(s, model.axes), **root)
             for s, law in laws.items() for root in _roots(law, low, high)]

    def position(wall):
        return wall["at"] if "at" in wall else (wall["lo"] + wall["hi"]) / 2

    def signature_of(o):
        return f"{o['verdict']}|{o['gamma']}|{o['winners']}"

    def at(t: Fraction):
        return outcome({"system": system, "base": base, "perturbation": _at(perturbation, t)})

    walls.sort(key=position)
    unique = [w for i, w in enumerate(walls) if i == 0 or position(w) != position(walls[i - 1])]
    cuts = [low, *map(position, unique), high]
    chambers, extra = [], []
    for a, b in zip(cuts, cuts[1:]):
        if not a < b:
            continue
        points = [a + (b - a) * Fraction(k, 4) for k in (1, 2, 3)]
        outs = [at(p) for p in points]
        start = a
        for j in range(1, 3):
            if signature_of(outs[j]) != signature_of(outs[j - 1]):
                left, right, wanted = points[j - 1], points[j], signature_of(outs[j - 1])
                for _ in range(48):
                    middle = (left + right) / 2
                    left, right = (middle, right) if signature_of(at(middle)) == wanted else (left, middle)
                extra.append({"kind": "outcome", "monomial": None, "lo": left, "hi": right})
                chambers.append({"from": start, "to": left, "outcome": outs[j - 1]})
                start = right
        chambers.append({"from": start, "to": b, "outcome": outs[-1]})
    every = sorted(unique + extra, key=position)
    return {
        "status": "complete", "range": [X.label(low), X.label(high)],
        "coefficient_laws": [{"monomial": X.monomial_text(s, model.axes), "degree": X.label(X.weighted_degree(s, model.weights)),
                              "law": X.poly_text({(p,): c for p, c in law.items()}, ("t",))} for s, law in sorted(laws.items())],
        "walls": [{"kind": w["kind"], "monomial": w["monomial"], "at": X.label(w.get("at")), "lo": X.label(w.get("lo")),
                   "hi": X.label(w.get("hi")), "value": float(position(w)), "outcome": at(w["at"]) if "at" in w else None} for w in every],
        "chambers": [{"from": X.label(c["from"]), "to": X.label(c["to"]), "from_value": float(c["from"]), "to_value": float(c["to"]),
                      "outcome": c["outcome"]} for c in chambers],
    }


# --- Attack -------------------------------------------------------------------------

def _decimal(x: Fraction) -> str | None:
    d, twos, fives = x.denominator, 0, 0
    while d % 2 == 0:
        d //= 2
        twos += 1
    while d % 5 == 0:
        d //= 5
        fives += 1
    if d != 1:
        return None
    places = max(twos, fives)
    scaled = abs(x * 10**places)
    digits = str(scaled.numerator).rjust(places + 1, "0")
    body = f"{digits[:-places]}.{digits[-places:]}" if places else digits
    return ("-" if x < 0 else "") + body


def attack(system: str, base: str, perturbation: str, limit: int = 24) -> dict[str, Any]:
    request = {"system": system, "base": base, "perturbation": perturbation}
    certificate, model = certify(request, {})
    if model is None:
        return {"status": "not_applicable", "reason": certificate.get("reason") or "no simple base maximizer",
                "links": certificate["links"]}
    start = outcome(request)
    slacks = [affine_text(model.rows[j], model.rhs[j], model.dimension) for j in model.active]
    mutations: list[dict[str, Any]] = []

    def add(kind, description, expectation, **changed):
        mutations.append({"kind": kind, "description": description, "expectation": expectation, "input": dict(request, **changed)})

    add("control", "Double the perturbation: rescaling should not change the class.", "unchanged",
        perturbation=f"2*({perturbation})")
    if model.weights is not None:
        groups, _ = spectrum(model, 4000)
        cutoff = Fraction(start["q_star"]) if start["q_star"] else Fraction(1)
        for q, alphas in [g for g in groups if g[0] < cutoff][:4]:
            alpha, monomial = alphas[0], slack_monomial(slacks, alphas[0])
            text = X.monomial_text(alpha, model.axes)
            add("intrusion", f"Add +{EPS}·{text} (degree {X.label(q)} below the current cutoff {X.label(cutoff)}).", "γ drops",
                perturbation=f"({perturbation}) + {EPS}*{monomial}")
            add("suppression", f"Add −{EPS}·{text}: a negative layer below the winner.", "may disqualify",
                perturbation=f"({perturbation}) - {EPS}*{monomial}")
        faces = next((l.get("values", {}).get("faces", []) for l in certificate["links"] if l["id"] == "faces"), [])
        winners = [f for f in faces if f.get("winning")]
        smallest = min((len(f["face"]) for f in winners), default=0)
        flipped: set[tuple[int, ...]] = set()
        for face in [f for f in winners if len(f["face"]) == smallest]:
            members = [model.axes.index(a) for a in face["face"]]
            restricted = {s: c for s, c in model.gain.items() if all(s[i] == 0 for i in range(model.dimension) if i not in members)}
            q_face = min(X.weighted_degree(s, model.weights) for s in restricted)
            for signature, coefficient in sorted(restricted.items()):
                if X.weighted_degree(signature, model.weights) != q_face or signature in flipped or len(flipped) >= 3:
                    continue
                flipped.add(signature)
                add("sign flip", f"Flip the sign of the winning term {X.label(coefficient)}·{X.monomial_text(signature, model.axes)}.",
                    "winner lost", perturbation=f"({perturbation}) - ({X.label(2 * coefficient)})*{slack_monomial(slacks, signature)}")
        for i, j in combinations(range(model.dimension), 2):
            if model.weights[i] + model.weights[j] <= 1:
                cross = f"{_slack_power(slacks[i], 1)}*{_slack_power(slacks[j], 1)}"
                add("base cross term", f"Add {EPS}·{model.axes[i]}·{model.axes[j]} to the base loss: a cross term at or below the principal weight.",
                    "H2 fails", base=f"({base}) - {EPS}*{cross}")
    tilt = Fraction(1, 100)
    for j in model.active:
        for k in range(model.dimension):
            rows = [list(r) for r in model.rows]
            rhs = list(model.rhs)
            rows[j][k] += tilt
            rhs[j] += tilt * model.vertex[k]
            texts = [[_decimal(a) for a in r] for r in rows]
            bounds = [_decimal(b) for b in rhs]
            if any(t is None for r in texts for t in r) or any(b is None for b in bounds):
                continue
            add("facet tilt", f"Tilt facet {j} about v (coefficient of x{k} + 0.01): the edges move, the vertex stays.", "portability",
                system=f"([{','.join('[' + ','.join(r) + ']' for r in texts)}], [{','.join(bounds)}])")
    results = []
    for mutation in mutations[:limit]:
        result = outcome(mutation["input"])
        results.append(dict(mutation, outcome=result,
                            changed=(result["verdict"], result["gamma"]) != (start["verdict"], start["gamma"])))
    changed = [r for r in results if r["changed"]]
    return {"status": "complete", "base": start, "mutations": results,
            "summary": {"total": len(results), "changed": len(changed), "unchanged": len(results) - len(changed),
                        "kinds_changed": sorted({r["kind"] for r in changed}),
                        "kinds_stable": sorted({r["kind"] for r in results} - {r["kind"] for r in changed})}}
