"""Conjectures: a candidate law, tested against everything the calculator can certify.

Finding a new law is mathematical work that the calculator does not do. Once
someone has an insight, the calculator can make it testable and shareable. A
conjecture is a rule written in a small, safe language over certified features
of an input, such as

    min(face_gamma, curved_gamma)

and a corpus of inputs to test it on: the repository's presets, or a family
G(t) or G(t, u) on a grid of rational points. For every input the calculator
first asks whether an established theorem decides the answer: the
face-selection theorem, zero response (Lemma 2), or the V.22 curved reduction.
Where one does, the conjecture must agree with it, and a disagreement refutes
the conjecture outright. Where none does, certified lower bounds
Δ(s) ≥ L(s) test the prediction at finite scales. A contradiction there comes
with a witness point of P that anyone can check in exact arithmetic. It is
strong evidence, not an asymptotic proof, and the verdicts say which is which.

Recorded conjectures live in ``conjectures/``; ``verify`` recomputes them, as
the tape does for calculations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from . import exact as X
from .certify import certify
from .counter import ambient_axes_prediction
from .measure import measure
from .presets import PRESETS, preset_request
from .provenance import ROOT, code_id, fingerprint, git_state, python_files

SCHEMA = "gitcalculator.conjecture.v1"
FOLDER = ROOT / "conjectures"
MAX_RULE = 2000
MAX_INSTANCES = 225


# --- the rule language ------------------------------------------------------------------
# Values: a Fraction, NONE (zero response, an infinite exponent), UNKNOWN (no
# claim), or a boolean. Arithmetic with UNKNOWN is UNKNOWN; min and max skip it;
# comparisons and logic are three-valued.

class _Special:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


NONE = _Special("none")        # Δ(s) = 0 for all small s
UNKNOWN = _Special("unknown")  # the rule makes no claim here

FEATURES = {
    "theorem_gamma": "γ where an established theorem decides it: the face law, V.22, or none for proved zero response",
    "face_gamma": "γ = 1/(1 − q*) from the exact face data, licensed or not",
    "face_q": "q* from the exact face data, licensed or not",
    "curved_gamma": "γ of the V.22 curved reduction, where it is licensed",
    "ambient_gamma": "γ read along the ambient axes instead of the edge chart",
    "min_positive_q": "the least weighted degree among monomials of R with a positive coefficient",
    "beta_min": "the smallest loss order βᵢ along the edges",
    "beta_max": "the largest loss order βᵢ along the edges",
    "n": "the dimension",
    "isolated": "true when Hypothesis 0 (global isolation of v) holds exactly",
    "principal": "true when Hypothesis 2 (diagonal principal part) holds exactly",
    "licensed": "true when the face-selection theorem or zero response is proved",
    "t": "the family parameter t",
    "u": "the family parameter u",
}
FUNCTIONS = {"min", "max", "abs", "if", "known"}


class RuleError(ValueError):
    pass


_TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_][A-Za-z_0-9]*)|(<=|>=|==|!=|[-+*/^(),<>]))")


def _tokens(text: str) -> list[tuple[str, str]]:
    out, at = [], 0
    text = text.strip()
    while at < len(text):
        found = _TOKEN.match(text, at)
        if not found or found.end() == at:
            raise RuleError(f"cannot read the rule at {text[at:at + 12]!r}")
        number, name, op = found.groups()
        out.append(("num", number) if number else ("name", name) if name else ("op", op))
        at = found.end()
    return out + [("end", "")]


def parse_rule(text: str) -> tuple:
    """Parse a rule into a small tree; nothing in it is ever executed as code."""
    if not isinstance(text, str) or not text.strip():
        raise RuleError("write a rule, such as min(face_gamma, curved_gamma)")
    if len(text) > MAX_RULE:
        raise RuleError("the rule is too long")
    tokens, at = _tokens(text), 0

    def peek():
        return tokens[at]

    def take(kind=None, value=None):
        nonlocal at
        token = tokens[at]
        if (kind and token[0] != kind) or (value and token[1] != value):
            raise RuleError(f"expected {value or kind} near {token[1] or 'the end'}")
        at += 1
        return token

    binding = {"or": 1, "and": 2, "==": 4, "!=": 4, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "^": 8}

    def expression(power=0):
        kind, value = take()
        if kind == "num":
            left = ("num", Fraction(value))
        elif kind == "name" and value == "not":
            left = ("not", expression(3))
        elif kind == "name" and value in FUNCTIONS:
            take("op", "(")
            args = [] if peek() == ("op", ")") else [expression()]
            while peek() == ("op", ","):
                take()
                args.append(expression())
            take("op", ")")
            arity = {"abs": 1, "if": 3, "known": 1}.get(value)
            if (arity and len(args) != arity) or (value in {"min", "max"} and not args):
                raise RuleError(f"{value} takes {arity or 'one or more'} argument(s)")
            left = ("call", value, args)
        elif kind == "name" and value in {"none", "unknown", "true", "false"}:
            left = ("const", value)
        elif kind == "name":
            if value not in FEATURES:
                raise RuleError(f"unknown name {value!r}; the features are {', '.join(sorted(FEATURES))}")
            left = ("feature", value)
        elif (kind, value) == ("op", "-"):
            left = ("neg", expression(7))
        elif (kind, value) == ("op", "("):
            left = expression()
            take("op", ")")
        else:
            raise RuleError(f"unexpected {value or 'end of rule'}")
        while True:
            kind, value = peek()
            op = value if kind == "op" or value in {"and", "or"} else None
            if op not in binding or binding[op] <= power:
                return left
            take()
            right = expression(binding[op] - (1 if op == "^" else 0))
            left = ("bin", op, left, right)

    tree = expression()
    if peek()[0] != "end":
        raise RuleError(f"unexpected {peek()[1]!r} after the rule")
    return tree


def referenced(tree: tuple) -> set[str]:
    """The features a rule reads."""
    if tree[0] == "feature":
        return {tree[1]}
    children = tree[2] if tree[0] == "call" else tree[1:] if tree[0] in {"neg", "not"} else tree[2:] if tree[0] == "bin" else ()
    return set().union(*(referenced(c) for c in children if isinstance(c, tuple))) if children else set()


def _order(value) -> tuple[int, Fraction]:
    return (1, Fraction(0)) if value is NONE else (0, value)


def evaluate(tree: tuple, features: Mapping[str, Any]):
    kind = tree[0]
    if kind == "num":
        return tree[1]
    if kind == "const":
        return {"none": NONE, "unknown": UNKNOWN, "true": True, "false": False}[tree[1]]
    if kind == "feature":
        value = features.get(tree[1])
        return UNKNOWN if value is None else value
    if kind == "neg":
        value = evaluate(tree[1], features)
        return -value if isinstance(value, Fraction) else UNKNOWN
    if kind == "not":
        value = evaluate(tree[1], features)
        return (not value) if isinstance(value, bool) else UNKNOWN
    if kind == "call":
        name, args = tree[1], tree[2]
        if name == "if":
            condition = evaluate(args[0], features)
            if not isinstance(condition, bool):
                return UNKNOWN
            return evaluate(args[1] if condition else args[2], features)
        values = [evaluate(a, features) for a in args]
        if name == "known":
            return values[0] is not UNKNOWN
        if name == "abs":
            return abs(values[0]) if isinstance(values[0], Fraction) else UNKNOWN
        present = [v for v in values if v is NONE or isinstance(v, Fraction)]
        if not present:
            return UNKNOWN
        return (min if name == "min" else max)(present, key=_order)
    op, a, b = tree[1], evaluate(tree[2], features), evaluate(tree[3], features)
    if op in {"and", "or"}:
        if op == "and":
            return False if a is False or b is False else (True if a is True and b is True else UNKNOWN)
        return True if a is True or b is True else (False if a is False and b is False else UNKNOWN)
    if op in {"<", "<=", ">", ">=", "==", "!="}:
        if not all(v is NONE or isinstance(v, Fraction) for v in (a, b)):
            return UNKNOWN
        x, y = _order(a), _order(b)
        return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y, "==": x == y, "!=": x != y}[op]
    if not (isinstance(a, Fraction) and isinstance(b, Fraction)):
        return UNKNOWN
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b if b else UNKNOWN
    if b.denominator != 1 or abs(b) > 64:
        return UNKNOWN  # integer powers only
    return a ** int(b) if a or b > 0 else UNKNOWN


# --- corpora --------------------------------------------------------------------------------

def _grid(lo: Fraction, hi: Fraction, k: int) -> list[Fraction]:
    return [lo + (hi - lo) * Fraction(2 * i + 1, 2 * k) for i in range(k)]


def _at(expression: str, values: Mapping[str, Fraction]) -> str:
    for name, value in values.items():
        expression = re.sub(rf"\b{name}\b", f"({value.numerator}/{value.denominator})", expression)
    return expression


def plan(corpus: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The inputs a corpus stands for, each with its parameters."""
    kind = corpus.get("kind", "presets")
    if kind == "presets":
        names = corpus.get("names") or list(PRESETS)
        return [{"label": name, "params": {}, "input": preset_request(name)} for name in names]
    if kind == "inputs":
        return [{"label": item.get("label") or f"input {i + 1}", "params": {},
                 "input": {k: item[k] for k in ("system", "base", "perturbation")}}
                for i, item in enumerate(corpus["inputs"])]
    if kind == "family":
        k = max(1, min(15, int(corpus.get("points", 5))))
        names = [p for p in ("t", "u") if re.search(rf"\b{p}\b", corpus["perturbation"])]
        if not names:
            raise RuleError("a family needs the parameter t, or t and u, in G")
        axes = {p: _grid(X.to_fraction(corpus.get(p, ["-1", "1"])[0]), X.to_fraction(corpus.get(p, ["-1", "1"])[1]), k)
                for p in names}
        points = [{"t": t} for t in axes["t"]] if names == ["t"] else (
            [{"u": u} for u in axes["u"]] if names == ["u"] else [{"t": t, "u": u} for u in axes["u"] for t in axes["t"]])
        return [{"label": ", ".join(f"{p} = {X.label(v)}" for p, v in point.items()),
                 "params": {p: X.label(v) for p, v in point.items()},
                 "input": {"system": corpus["system"], "base": corpus["base"], "perturbation": _at(corpus["perturbation"], point)}}
                for point in points]
    raise RuleError(f"unknown corpus kind {kind!r}")


# --- one instance ---------------------------------------------------------------------------

def _curved(inputs: Mapping[str, Any], model) -> dict[str, Any] | None:
    from .receipt import _curved as curved
    return curved(inputs, model)


def features(inputs: Mapping[str, Any], params: Mapping[str, str]):
    """Certified features of one input, and the established answer where a theorem decides it."""
    certificate, model = certify(inputs, {})
    links = {l["id"]: l["status"] for l in certificate.get("links", [])}
    curved = _curved(inputs, model) or {}
    ambient = ambient_axes_prediction(model) or {}
    status = certificate.get("status")
    fraction = lambda v: X.to_fraction(v) if v is not None else None
    found: dict[str, Any] = {
        "face_gamma": fraction(certificate.get("gamma")), "face_q": fraction(certificate.get("q_star")),
        "curved_gamma": fraction(curved.get("gamma")) if curved.get("status") == "licensed" else None,
        "ambient_gamma": fraction(ambient.get("gamma")),
        "isolated": links.get("H0") == "exact", "principal": links.get("H2") == "exact",
        "licensed": status in {"theorem", "zero_response"},
        "t": fraction(params.get("t")), "u": fraction(params.get("u")),
    }
    if model is not None:
        found["n"] = Fraction(model.dimension)
        if model.weights:
            betas = [1 / w for w in model.weights]
            found["beta_min"], found["beta_max"] = min(betas), max(betas)
            positive = [X.weighted_degree(s, model.weights) for s, c in model.gain.items() if c > 0]
            found["min_positive_q"] = min(positive) if positive else None
    established = None
    if status == "theorem" and certificate.get("gamma"):
        established = {"gamma": X.to_fraction(certificate["gamma"]), "by": "the face-selection theorem"}
    elif status == "zero_response":
        established = {"gamma": NONE, "by": "Lemma 2"}
    elif curved.get("status") == "licensed":
        established = {"gamma": X.to_fraction(curved["gamma"]), "by": "V.22"}
    found["theorem_gamma"] = established["gamma"] if established else None
    return found, established, model


def _show(value) -> str | None:
    if value is NONE:
        return "none"
    if value is UNKNOWN or value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return X.label(value)


def _witness(model, row: Mapping[str, Any]) -> dict[str, Any]:
    c = [X.to_fraction(v) for v in row["witness_c"]]
    return {"s": row["s"], "lower_bound": row["lower_bound"], "c": row["witness_c"],
            "x": [X.label(v) for v in model.point(c)], "axes": list(model.axes)}


def trial(rule: str | tuple, item: Mapping[str, Any], budget: str = "standard") -> dict[str, Any]:
    """Test the rule on one input."""
    tree = parse_rule(rule) if isinstance(rule, str) else rule
    found, established, model = features(item["input"], item["params"])
    prediction = evaluate(tree, found)
    out: dict[str, Any] = {"label": item["label"], "params": dict(item["params"]),
                           "features": {k: _show(found.get(k)) for k in sorted(referenced(tree)) if found.get(k) is not None},
                           "prediction": _show(prediction) if prediction is NONE or isinstance(prediction, Fraction) else None,
                           "established": {"gamma": _show(established["gamma"]), "by": established["by"]} if established else None}
    if isinstance(prediction, bool) or not (prediction is NONE or isinstance(prediction, Fraction)):
        return out | {"verdict": "no claim", "detail": "the rule makes no prediction here"}
    if isinstance(prediction, Fraction) and prediction <= 0:
        return out | {"verdict": "no claim", "detail": "a response exponent must be positive"}
    if established:
        if _order(prediction) == _order(established["gamma"]):
            return out | {"verdict": "agrees", "detail": f"proved by {established['by']}"}
        return out | {"verdict": "refuted", "input": dict(item["input"]), "detail": f"{established['by']} proves "
                      f"{'zero response' if established['gamma'] is NONE else 'γ = ' + X.label(established['gamma'])}"}
    if model is None or not model.polynomial:
        return out | {"verdict": "untestable", "detail": "no certified bounds here: the vertex is not simple, or F and G are not polynomial"}
    if prediction is NONE:
        bounds = measure(model, [], budget=budget)
        rows = bounds.get("rows") or []
        tail = rows[-3:]
        if len(tail) == 3 and all(r["lower_bound"] != "0" and r["feasible"] for r in tail):
            return out | {"verdict": "contradicted", "detail": "certified Δ(s) > 0 at every one of the smallest tested scales",
                          "input": dict(item["input"]), "witness": _witness(model, rows[-1])}
        if not bounds.get("positive_gain_found"):
            return out | {"verdict": "consistent", "detail": "no certified positive response at any tested scale"}
        return out | {"verdict": "inconclusive", "detail": "a positive response at some scales, not at the smallest"}
    bounds = measure(model, [{"id": "conjecture", "label": "conjecture", "gamma": prediction}], budget=budget)
    verdict = next((v for v in bounds.get("verdicts", []) if v["id"] == "conjecture"), None)
    if bounds.get("status") != "complete" or verdict is None:
        return out | {"verdict": "inconclusive", "detail": bounds.get("reason") or bounds.get("summary") or "no certified bounds"}
    if bounds.get("measured_exponent") is not None:
        out["measured"] = str(bounds["measured_exponent"])  # a string survives JSON in every language unchanged
    if verdict["verdict"] == "contradicted":
        series = [r for r in bounds["rows"] if r["lower_bound"] != "0" and r["feasible"]]
        return out | {"verdict": "contradicted", "detail": verdict["detail"], "input": dict(item["input"]),
                      "witness": _witness(model, series[-1])}
    if verdict["verdict"] == "consistent":
        return out | {"verdict": "consistent", "detail": verdict["detail"]}
    return out | {"verdict": "inconclusive", "detail": verdict.get("detail") or "too few certified scales"}


# --- a whole trial ------------------------------------------------------------------------

ORDER = ("refuted", "contradicted", "agrees", "consistent", "inconclusive", "untestable", "no claim")


def assemble(meta: Mapping[str, Any], corpus: Mapping[str, Any], budget: str, instances: Sequence[Mapping[str, Any]],
             provenance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    counts = {v: sum(1 for i in instances if i["verdict"] == v) for v in ORDER}
    status = ("refuted" if counts["refuted"] else "contradicted" if counts["contradicted"]
              else "survives" if counts["agrees"] + counts["consistent"] else "untested")
    if provenance is None:
        git = git_state()
        provenance = {"commit": git.get("commit"), "short": git.get("short"),
                      "code_id": code_id(python_files("categorical_polytope")),
                      "calculator_id": fingerprint(python_files("gitcalculator"), "calc")}
    return {"schema": SCHEMA, "name": meta.get("name"), "title": meta.get("title") or meta.get("name") or "Conjecture",
            "statement": meta.get("statement") or "", "rule": meta["rule"], "corpus": dict(corpus), "budget": budget,
            "status": status, "counts": counts, "instances": list(instances), "recorded_with": dict(provenance)}


def run(meta: Mapping[str, Any], corpus: Mapping[str, Any], budget: str = "standard",
        progress: Callable[[int, int, dict], None] | None = None) -> dict[str, Any]:
    tree = parse_rule(meta["rule"])
    items = plan(corpus)
    if len(items) > MAX_INSTANCES:
        raise RuleError(f"a corpus is limited to {MAX_INSTANCES} inputs")
    instances = []
    for k, item in enumerate(items):
        instances.append(trial(tree, item, budget))
        if progress:
            progress(k + 1, len(items), instances[-1])
    return assemble(meta, corpus, budget, instances)


def signature(record: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": record["status"],
            "instances": {i["label"]: f"{i['prediction']} → {i['verdict']}" for i in record["instances"]}}


def record_conjecture(meta: Mapping[str, Any], corpus: Mapping[str, Any], budget: str = "standard",
                      folder: Path = FOLDER) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", meta.get("name") or ""):
        raise RuleError("a recorded conjecture needs a name of lowercase letters, digits and dashes")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{meta['name']}.json"
    path.write_text(json.dumps(run(meta, corpus, budget), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def recorded(folder: Path = FOLDER) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]


def verify(folder: Path = FOLDER) -> list[dict[str, Any]]:
    """Recompute every recorded conjecture and report verdicts that changed."""
    report = []
    for stored in recorded(folder):
        now = run(stored, stored["corpus"], stored["budget"])
        old, new = signature(stored), signature(now)
        changed = [f"status: {old['status']} → {new['status']}"] if old["status"] != new["status"] else []
        changed += [f"{label}: {old['instances'].get(label)} → {new['instances'].get(label)}"
                    for label in sorted(set(old["instances"]) | set(new["instances"]))
                    if old["instances"].get(label) != new["instances"].get(label)]
        report.append({"name": stored["name"], "status": now["status"], "unchanged": not changed, "changed": changed})
    return report


# --- the sheet ------------------------------------------------------------------------------

def _corpus_text(corpus: Mapping[str, Any]) -> str:
    if corpus.get("kind", "presets") == "presets":
        return "the repository's canonical examples and counterexamples (`python -m gitcalculator presets`)"
    if corpus["kind"] == "inputs":
        return f"{len(corpus['inputs'])} listed inputs"
    window = ", ".join(f"${p} \\in [{X.label(X.to_fraction(corpus[p][0]))}, {X.label(X.to_fraction(corpus[p][1]))}]$"
                       for p in ("t", "u") if p in corpus and re.search(rf"\b{p}\b", corpus["perturbation"]))
    return (f"the family `G = {corpus['perturbation']}` on `{corpus['system']}` with `F = {corpus['base']}`, "
            f"at {corpus.get('points', 5)} rational points per parameter over {window}")


def _tex_decimal(value: str) -> str:
    """``1.25e-5`` as TeX, ``1.25 \\times 10^{-5}``; the digits are exact."""
    mantissa, _, exponent = str(value).partition("e")
    if "." in mantissa:
        mantissa = mantissa.rstrip("0").rstrip(".")  # the same number, without trailing zeros
    return f"{mantissa} \\times 10^{{{int(exponent)}}}" if exponent and int(exponent) else mantissa


def _gamma_text(value: str | None) -> str:
    if value is None:
        return "—"
    return "zero response" if value == "none" else f"γ = {value}"


STATUS_TEXT = {
    "refuted": "refuted by a theorem",
    "contradicted": "contradicted by certified bounds",
    "survives": "survives every test",
    "untested": "untested",
}


def sheet(record: Mapping[str, Any], *, calculator: str | None = None) -> str:
    """The trial as GitHub Markdown (checked by experiments/ghmath.py in the tests)."""
    from .sheet import code, link, text
    counts, instances = record["counts"], record["instances"]
    out = [f"### Conjecture: {text(record['title'])} · {STATUS_TEXT[record['status']]}", ""]
    if record.get("statement"):
        out += [line if line.strip() else "" for line in str(record["statement"]).strip().splitlines()] + [""]
    out += [f"Rule: {code(record['rule'])}", "",
            f"Tested on {len(instances)} input{'s' if len(instances) != 1 else ''}: {_corpus_text(record['corpus'])}. "
            f"Certified bounds at the {text(record['budget'])} budget.", ""]
    out += ["| Verdict | Inputs | Meaning |", "| :--- | ---: | :--- |"]
    meaning = {"agrees": "an established theorem gives the same answer",
               "refuted": "an established theorem gives a different answer",
               "consistent": "certified lower bounds follow the predicted order",
               "contradicted": "certified lower bounds outgrow the predicted order (finite-scale evidence)",
               "inconclusive": "the bounds have not separated", "untestable": "no certified evidence is available",
               "no claim": "the rule abstains"}
    out += [f"| {v} | {counts[v]} | {meaning[v]} |" for v in ORDER if counts.get(v)]
    out.append("")
    against = [i for i in instances if i["verdict"] in {"refuted", "contradicted"}]
    if against:
        out += ["#### Against the conjecture", ""]
        for item in against:
            line = (f"- **{text(item['label'])}**: predicted {_gamma_text(item['prediction'])}; {text(item['detail'])}.")
            if item.get("witness"):
                w = item["witness"]
                point = ", ".join(w["x"])
                line += (f" At $s = {_tex_decimal(w['s'])}$, the point $x = ({point})$ of $P$ gives "
                         f"$\\Delta(s) \\ge {_tex_decimal(w['lower_bound'])}$, with "
                         f"$c = ({', '.join(_tex_decimal(v) for v in w['c'])})$ in the edge chart.")
            if calculator and item.get("input"):
                line += f" [Solve it]({link(item['input'], calculator)})."
            out.append(line)
        out.append("")
    out += ["#### Every input", "", "| Input | Prediction | Established | Verdict |", "| :--- | :--- | :--- | :--- |"]
    for item in instances:
        established = item.get("established")
        out.append(f"| {text(item['label'])} | {_gamma_text(item['prediction'])} | "
                   f"{text(_gamma_text(established['gamma']) + ' by ' + established['by']) if established else '—'} | {text(item['verdict'])} |")
    provenance = record.get("recorded_with") or {}
    out += ["", f"<sub>Recorded with commit {code(provenance.get('short') or '—')} · Python {code(provenance.get('code_id') or '—')}"
            f" · {code(provenance.get('calculator_id') or '—')}</sub>", "", "Reproduce it:", "", "```bash", command(record), "```", ""]
    return "\n".join(out)


def command(record: Mapping[str, Any]) -> str:
    from .sheet import shell
    corpus = record["corpus"]
    parts = ["python -m gitcalculator conjecture test", "--rule", shell(record["rule"])]
    if corpus.get("kind", "presets") == "family":
        parts += ["--system", shell(corpus["system"]), "--base", shell(corpus["base"]), "--perturbation", shell(corpus["perturbation"])]
        for p in ("t", "u"):
            if p in corpus and re.search(rf"\b{p}\b", corpus["perturbation"]):
                parts += [f"--{p}-from", shell(corpus[p][0]), f"--{p}-to", shell(corpus[p][1])]
        parts += ["--points", str(corpus.get("points", 5))]
    if record.get("budget") and record["budget"] != "standard":
        parts += ["--budget", record["budget"]]
    return " ".join(parts)


def render_text(record: Mapping[str, Any]) -> str:
    lines = [f"conjecture  {record['title']}", f"rule        {record['rule']}",
             f"status      {STATUS_TEXT[record['status']].upper()}", ""]
    width = max([10] + [len(i["label"]) for i in record["instances"]])
    for item in record["instances"]:
        established = item.get("established")
        lines.append(f"  {item['label']:<{width}}  predicted {_gamma_text(item['prediction']):<18} "
                     f"{('theorem: ' + _gamma_text(established['gamma'])) if established else '':<24} {item['verdict']}")
        if item["verdict"] in {"refuted", "contradicted"}:
            lines.append(f"  {'':<{width}}  {item['detail']}")
            if item.get("witness"):
                w = item["witness"]
                lines.append(f"  {'':<{width}}  witness: s = {w['s']}, x = ({', '.join(w['x'])}), Δ(s) ≥ {w['lower_bound']}")
    lines += ["", "  " + ", ".join(f"{record['counts'][v]} {v}" for v in ORDER if record["counts"].get(v))]
    return "\n".join(lines)
