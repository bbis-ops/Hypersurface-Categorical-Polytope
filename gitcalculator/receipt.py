"""One calculation, end to end: compute, certify, attack, measure, pin.

A receipt lays every step of the theorem out in four columns:

    theorem clause | what the backend computed | the exact certificate | the counter-arguments

and ends with a verdict, certified measurements, and git provenance. Its id is
a content address over the input, the code identity, and the discrete outcome,
so the same calculation on the same code always prints the same id.
"""

from __future__ import annotations

import hashlib
import json
import time
from fractions import Fraction
from typing import Any, Mapping

from categorical_polytope.adjudication.polyhedra.backend import FaceSelectionBackend

from . import exact as X
from .certify import certify
from .counter import REGISTRY, Context, ambient_axes_prediction, assess
from .measure import measure
from .provenance import provenance

SCHEMA = "gitcalculator.receipt.v1"
INPUT_KEYS = ("system", "base", "perturbation", "observed_exponent", "observation_tolerance")
STEP_CHALLENGES = {
    "standing": (), "vertex": ("non-simple",), "transport": ("ambient-axes",),
    "H0": ("isolation-probe",), "H1": (), "H2": ("homogeneity-probe",), "H3": (),
    "faces": ("interior-zero", "critical-layer", "tied-coefficient"),
    "H5": ("signed-channel", "signed-sharp"),
    "selection": ("empty-not-zero", "active-set", "finite-scale", "inverse-tolerance"),
}
VERDICTS = {
    "proved": "Every hypothesis of the theorem is discharged in exact arithmetic.",
    "proved-v22": "The curved-reduction theorem V.22 applies, with exact checks.",
    "licensed": "The backend licenses the answer, but some hypotheses rest on numerical probes.",
    "unlicensed": "An exponent was computed, but a hypothesis fails or is unresolved.",
    "refused": "The input lies outside the law as stated.",
    "contradicted": "Certified lower bounds contradict a licensed exponent: a candidate counterexample.",
}
_BACKEND: FaceSelectionBackend | None = None


def backend() -> FaceSelectionBackend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = FaceSelectionBackend()
    return _BACKEND


def normalize(request: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(request)
    if "perturbation" not in data and "pert" in data:
        data["perturbation"] = data["pert"]
    return {k: data[k] for k in INPUT_KEYS if data.get(k) is not None}


def _blocker_kind(text: str) -> str:
    return text.split(" on face")[0].split(":")[0].strip()


def _curved(request: Mapping[str, Any], model) -> dict[str, Any] | None:
    if model is None or model.dimension != 2 or not model.polynomial:
        return None
    response = backend().handle({"operation": "curved_reduction",
                                 **{k: request[k] for k in ("system", "base", "perturbation")}})
    if response.get("status") != "licensed":
        return {"status": response.get("status"), "blockers": (response.get("scope") or {}).get("blockers", [])}
    scaling, reduction = response["scaling"], response.get("reduction") or {}
    return {
        "status": "licensed",
        "gamma": scaling["response_exponent_exact"],
        "coefficient": scaling["leading_coefficient"]["exact"],
        "effective_weight": scaling["effective_weight_exact"],
        "eliminated_axis": reduction.get("eliminated_axis"),
        "identity": reduction.get("identity"),
        "proof_basis": (response.get("scope") or {}).get("proof_basis"),
    }


def _predictions(response, certificate, alternatives) -> list[dict[str, Any]]:
    predictions = []
    universality = response.get("universality_class") or {}
    backend_gamma = universality.get("response_exponent_label")
    if response.get("answered") and backend_gamma:
        coefficient = (response.get("scaling") or {}).get("leading_coefficient") or {}
        predictions.append({"id": "backend", "label": f"face selector ({response.get('status')})",
                            "gamma": Fraction(backend_gamma),
                            "coefficient": coefficient.get("value") if coefficient.get("settled") else None})
    if certificate.get("gamma") and certificate["gamma"] != backend_gamma:
        predictions.append({"id": "exact-faces", "label": f"exact face data ({certificate['status']})",
                            "gamma": Fraction(certificate["gamma"])})
    curved = alternatives.get("curved_reduction") or {}
    if curved.get("status") == "licensed":
        predictions.append({"id": "curved", "label": "V.22 curved reduction", "gamma": Fraction(curved["gamma"]),
                            "coefficient": Fraction(curved["coefficient"])})
    naive = alternatives.get("ambient_axes") or {}
    feasible = certificate.get("gamma") or backend_gamma
    if naive.get("gamma") and naive["gamma"] != feasible:
        predictions.append({"id": "ambient-axes", "label": "ambient-axis counterfactual",
                            "gamma": Fraction(naive["gamma"])})
    return predictions


def _backend_column(key: str, response: Mapping[str, Any]) -> str:
    scope = response.get("scope") or {}
    hyp = scope.get("hypotheses") or {}
    loc = response.get("localization") or {}
    sel = response.get("selection") or {}
    ref = response.get("exact_refinement") or {}
    if key == "standing":
        return f"localization {loc.get('status', '—')}" + (f"; refusal: {scope['refusal']}" if scope.get("refusal") else "")
    if key == "vertex":
        cons = loc.get("constraints") or {}
        return (f"vertex {loc.get('vertex')}, binding {cons.get('binding')}, released {cons.get('released')}, "
                f"simple_vertex={hyp.get('simple_vertex')}")
    if key == "transport":
        ah = response.get("ambient_hierarchy") or {}
        return f"{ah.get('chart_source', 'no exact chart')}; {ah.get('arithmetic', ah.get('status', '—'))}"
    if key == "H0":
        return f"isolation probe: isolated_maximizer={hyp.get('isolated_maximizer')}, margin {hyp.get('isolation_margin')}"
    if key in ("H1", "H2"):
        return (f"edge orders {hyp.get('edge_orders')}, base_homogeneity {hyp.get('base_homogeneity')}, "
                f"weighted_principal_part={hyp.get('weighted_principal_part')}")
    if key == "H3":
        pa = response.get("perturbation_analysis") or {}
        return f"{pa.get('term_count', '—')} top-level term(s), {pa.get('status', '—')}"
    if key == "faces":
        faces = sel.get("faces") or []
        return "; ".join(f"{f.get('edges')}: {f.get('relevance')}" + (f" q={f['degree']:.6g}" if f.get("degree") else "")
                         for f in faces) or "—"
    if key == "H5":
        return (f"selection_complete={ref.get('selection_complete')}, unresolved faces {ref.get('unresolved_faces', [])}")
    universality = response.get("universality_class") or {}
    return (f"status {response.get('status')}, class {universality.get('id', '—')}"
            + (f"; blockers: {', '.join(map(_blocker_kind, scope['blockers']))}" if scope.get("blockers") else ""))


def _verdict(response, certificate, alternatives, measurement) -> tuple[str, str]:
    contradicted = {v["id"] for v in measurement.get("verdicts", []) if v.get("verdict") == "contradicted"}
    status, cert = response.get("status"), certificate.get("status")
    curved = alternatives.get("curved_reduction") or {}
    if (status == "licensed" and "backend" in contradicted) or (cert == "theorem" and "exact-faces" in contradicted):
        return "contradicted", "Certified lower bounds outgrow the licensed exponent; please report this input."
    if cert in {"theorem", "zero_response"}:
        return "proved", certificate["conclusion"]
    if curved.get("status") == "licensed" and "curved" not in contradicted:
        return "proved-v22", f"Δ(s) ~ {curved['coefficient']}·s^{curved['gamma']}"
    gamma = (response.get("universality_class") or {}).get("response_exponent_label")
    if status == "licensed":
        return "licensed", f"Δ(s) = Θ(s^{gamma})"
    if status == "unlicensed":
        return "unlicensed", f"candidate Δ(s) = Θ(s^{gamma}), not licensed"
    if certificate.get("gamma"):
        return "refused", f"refused; the exact face data suggest γ = {certificate['gamma']} without a license"
    return "refused", "no exponent"


def signature(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """The discrete outcome: what the tape records and history compares."""
    answer = receipt["answer"]
    return {
        "verdict": answer["verdict"], "gamma": answer["gamma"], "q_star": answer["q_star"],
        "backend": receipt["backend"]["signature"],
        "certificate": {"status": receipt["certificate"]["status"],
                        "links": {l["id"]: l["status"] for l in receipt["certificate"]["links"]}},
        "curved": receipt["alternatives"].get("curved_reduction"),
        "ambient_gamma": (receipt["alternatives"].get("ambient_axes") or {}).get("gamma"),
        "measurement": {v["id"]: v.get("verdict") for v in receipt["measurement"].get("verdicts", [])},
        "counter": {c["id"]: c["effect"] for c in receipt["counterarguments"]},
    }


def backend_signature(response: Mapping[str, Any]) -> dict[str, Any]:
    universality = response.get("universality_class") or {}
    scope = response.get("scope") or {}
    return {
        "status": response.get("status"), "licensed": response.get("licensed"),
        "gamma": universality.get("response_exponent_label"), "q_star": universality.get("weighted_degree_label"),
        "blockers": sorted({_blocker_kind(b) for b in scope.get("blockers") or []}),
        "refusal": scope.get("refusal"),
    }


def calculate(request: Mapping[str, Any], *, budget: str = "standard", include_backend: bool = False) -> dict[str, Any]:
    """Run one complete gitcalculator calculation and return its receipt."""
    timings: dict[str, float] = {}
    clock = time.perf_counter()
    inputs = normalize(request)
    response = backend().handle(dict(inputs, request_id=request.get("request_id")))
    timings["backend"] = time.perf_counter() - clock

    clock = time.perf_counter()
    certificate, model = certify(inputs, response)
    timings["certificate"] = time.perf_counter() - clock

    clock = time.perf_counter()
    alternatives: dict[str, Any] = {}
    curved = _curved(inputs, model)
    if curved:
        alternatives["curved_reduction"] = curved
    naive = ambient_axes_prediction(model)
    if naive:
        alternatives["ambient_axes"] = naive
    timings["alternatives"] = time.perf_counter() - clock

    clock = time.perf_counter()
    predictions = _predictions(response, certificate, alternatives)
    measurement = measure(model, predictions, budget=budget)
    measurement["predictions"] = [{"id": p["id"], "label": p["label"], "gamma": X.label(p["gamma"])} for p in predictions]
    timings["measurement"] = time.perf_counter() - clock

    ctx = Context(inputs, response, certificate, model, measurement, alternatives)
    counter = assess(ctx)
    effects = {c["id"]: c for c in counter}
    verdict, headline = _verdict(response, certificate, alternatives, measurement)

    universality = response.get("universality_class") or {}
    curved_ok = (alternatives.get("curved_reduction") or {}).get("status") == "licensed"
    if certificate.get("status") == "theorem":
        gamma, q_star = certificate["gamma"], certificate["q_star"]
    elif verdict == "proved-v22" and curved_ok:
        gamma, q_star = alternatives["curved_reduction"]["gamma"], None
    else:
        gamma = universality.get("response_exponent_label") or certificate.get("gamma")
        q_star = universality.get("weighted_degree_label") or certificate.get("q_star")
    coefficient = None
    if curved_ok and verdict == "proved-v22":
        coefficient = {"exact": alternatives["curved_reduction"]["coefficient"], "source": "V.22 exact"}
    elif ((response.get("scaling") or {}).get("leading_coefficient") or {}).get("settled"):
        coefficient = {"value": response["scaling"]["leading_coefficient"]["value"], "source": "backend, measured"}

    steps = []
    for link in certificate.get("links", []):
        steps.append({
            "id": link["id"], "clause": link["clause"], "statement": link["statement"], "doc": link["doc"],
            "backend": _backend_column(link["id"], response),
            "certificate": {k: link[k] for k in ("status", "method", "detail")},
            "challenges": [{"id": cid, "effect": effects[cid]["effect"]} for cid in STEP_CHALLENGES.get(link["id"], ())],
        })

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "input": inputs,
        "answer": {
            "verdict": verdict, "meaning": VERDICTS[verdict], "headline": headline,
            "gamma": gamma, "q_star": q_star, "coefficient": coefficient,
            "backend_status": response.get("status"), "certificate_status": certificate.get("status"),
        },
        "steps": steps,
        "certificate": {k: v for k, v in certificate.items() if k != "links"} | {"links": certificate.get("links", [])},
        "alternatives": alternatives,
        "measurement": measurement,
        "counterarguments": counter,
        "backend": {
            "signature": backend_signature(response),
            "asset_version": response.get("asset_version"),
            "universality_class": universality.get("id"),
            "blockers": (response.get("scope") or {}).get("blockers", []),
            "refusal": (response.get("scope") or {}).get("refusal"),
        },
    }
    if include_backend:
        receipt["backend"]["response"] = response
    documents = {s["doc"] for s in steps} | {src for c in counter for src in c["sources"]}
    receipt["provenance"] = provenance(sorted(documents))
    receipt["timings"] = {k: round(v, 3) for k, v in timings.items()}
    receipt["signature"] = signature(receipt)
    address = json.dumps({"schema": SCHEMA, "input": inputs, "code": receipt["provenance"]["code_id"],
                          "calculator": receipt["provenance"]["calculator_id"], "signature": receipt["signature"]},
                         sort_keys=True, ensure_ascii=False)
    receipt["id"] = "gc-" + hashlib.sha256(address.encode()).hexdigest()[:16]
    return receipt


# --- rendering ------------------------------------------------------------------------

MARK = {"exact": "■", "probed": "◐", "failed": "✗", "unresolved": "?", "not_reached": "·", "not_applicable": "·"}
EFFECT_MARK = {"blocks": "✗ blocks ", "caveat": "! caveat ", "averted": "✓ averted", "clear": "· clear  "}


def render_text(receipt: Mapping[str, Any], *, width: int = 92) -> str:
    """The printed tape."""
    rule = "─" * width
    a, p = receipt["answer"], receipt["provenance"]
    git = p["git"]
    out = [f"gitcalculator receipt {receipt['id']}", rule]
    inp = receipt["input"]
    out += [f"INPUT     P = {{x : A·x ≤ b}} with (A, b) = {inp['system']}",
            f"          F = {inp['base']}", f"          G = {inp['perturbation']}", rule]
    out += [f"ANSWER    {a['verdict'].upper()}   {a['headline']}",
            f"          γ = {a['gamma']}   q* = {a['q_star']}" +
            (f"   C = {a['coefficient'].get('exact') or format(a['coefficient'].get('value'), '.6g')} ({a['coefficient']['source']})"
             if a.get("coefficient") else ""),
            f"          {a['meaning']}", rule, "THEOREM LEDGER   clause · backend · exact certificate · challenged by"]
    for step in receipt["steps"]:
        cert = step["certificate"]
        out.append(f" {MARK.get(cert['status'], '?')} {step['clause']:<40} {cert['status']}")
        out.append(f"     backend   {step['backend'][:width - 15]}")
        out.append(f"     exact     {cert['detail'][:width - 15]}")
        if step["challenges"]:
            out.append("     attacked  " + ", ".join(f"{c['id']} ({c['effect']})" for c in step["challenges"]))
    out += [rule, "COUNTER-ARGUMENTS"]
    for c in receipt["counterarguments"]:
        out.append(f" {EFFECT_MARK[c['effect']]}  {c['id']:<18} {c['detail'][:width - 32]}")
    m = receipt["measurement"]
    out += [rule, "MEASUREMENT   certified lower bounds Δ(s) ≥ L(s) at points verified in P"]
    if m.get("status") == "complete" and m.get("rows"):
        for row in m["rows"][-5:]:
            out.append(f"   s = {row['s']:<12} L(s) ≥ {row['lower_bound']:<20} support {{{', '.join(row['support'])}}}")
        out.append(f"   measured exponent {m.get('measured_exponent')}")
        for v in m.get("verdicts", []):
            out.append(f"   {v['id']:<14} γ = {v['gamma']:<6} {v.get('verdict')}: {v.get('detail', '')}"[:width + 3])
    else:
        out.append(f"   {m.get('reason') or m.get('summary') or 'no data'}")
    out += [rule, "PROVENANCE",
            f"   commit {git.get('short')} on {git.get('branch')}" + (" (working tree differs)" if git.get("dirty") else ""),
            f"   code {p['code_id']}   calculator {p['calculator_id']}   {p['runtime']['engine']} {p['runtime']['python']}"]
    for path in ("categorical_polytope/adjudication/polyhedra/backend.py", "categorical_polytope/face_selection.py",
                 "categorical_polytope/ambient_face_compiler.py", "gitcalculator/certify.py", "gitcalculator/measure.py"):
        if path in p["sources"]:
            out.append(f"   {p['sources'][path][:12]}  {path}")
    out.append(f"   {p['verify']}")
    return "\n".join(out)


def counter_catalogue() -> list[dict[str, Any]]:
    return [argument.describe() for argument in REGISTRY]
