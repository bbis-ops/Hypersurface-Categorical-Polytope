"""
The face-selection law run forwards, and run backwards.

The domain adjudicates: it is handed a claim and returns a verdict. This module
is the other direction - hand it a polyhedron, a base and a perturbation and it
returns the answer, with everything the answer rests on attached.

    predict(system, base, pert) -> Prediction     geometry  -> exponent
    calibrate(exponent)         -> float          exponent  -> weighted order

Admission is delegated to `PolyhedronDomain.scope`, deliberately. Prediction and
adjudication must never be able to disagree: if this module admitted a case the
adjudicator would refuse, the backend would be answering questions the corpus
has no evidence about, and the evidence is the only reason to believe the
answer. So `scope` decides, and this module presents.

What a `Prediction` carries beyond the number:

  * every face of the tangent cone, admitted or filtered, and for a filtered one
    the reason - inactive, not positive, supercritical, unresolved;
  * which constraints the optimiser slides off and which stay binding;
  * the measured leading coefficient, the model-specific half of the law;
  * the three hypotheses, per case, never folded into the answer.

The last point is the one that matters for a backend. `Prediction.licensed` is
false whenever a hypothesis is unmet, and the exponent is still returned,
because a refusal that hides its reason is worse than a number that states its
warrant. A caller that acts on an unlicensed prediction is choosing to; a
caller that cannot tell is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from . import laws
from .domain import PolyhedronDomain
from .geometry import Polyhedron, Vertex

#: Prediction is defined for edge coordinates. The ambient rule exists to be
#: wrong at a tilted vertex - it is the domain's control, not a predictor.
RULE = "polyhedron/edge_exponent_law"

#: How close to 1 a face degree has to be to count as the critical case, where
#: the balance changes character and 1/(1-q) says nothing.
CRITICAL_MARGIN = 1e-6

#: Relevance classes, in the order the implications list them.
RELEVANT, CRITICAL, SUBLEADING, INACTIVE = (
    "relevant", "critical", "subleading", "inactive")


@dataclass(frozen=True)
class Face:
    """One face of the tangent cone, and what became of it."""

    edges: tuple[int, ...]
    degree: float | None
    relevance: str
    reason: str = ""

    @property
    def admitted(self) -> bool:
        return self.relevance == RELEVANT


@dataclass(frozen=True)
class Hypotheses:
    """
    The three the law needs, measured rather than assumed.

    `licensed` is their conjunction. It is reported, never enforced: an
    unlicensed case still gets an exponent, and the caller still gets to see
    that it is unlicensed.
    """

    simple_vertex: bool
    base_homogeneity: float | None
    edge_orders: tuple[float, ...]
    isolation_margin: float | None

    @property
    def homogeneous(self) -> bool:
        """Hypothesis 2: the base has a weighted principal part here."""
        return (self.base_homogeneity is not None
                and abs(self.base_homogeneity - 1.0) < 1e-3)

    @property
    def orders_above_one(self) -> bool:
        """Every edge order above 1, the rest of hypothesis 2."""
        return bool(self.edge_orders) and all(b > 1.0 for b in self.edge_orders)

    @property
    def isolated(self) -> bool:
        """Lemma 1: no competing maximiser was found outside the probe radius."""
        return self.isolation_margin is not None and self.isolation_margin > 0.0

    @property
    def licensed(self) -> bool:
        return (self.simple_vertex and self.homogeneous
                and self.orders_above_one and self.isolated)

    def unmet(self) -> tuple[str, ...]:
        """Names of the hypotheses that failed, for a caller that logs them."""
        failures = []
        if not self.simple_vertex:
            failures.append("simple vertex")
        if not self.orders_above_one:
            failures.append("edge orders above 1")
        if not self.homogeneous:
            failures.append("weighted principal part")
        if not self.isolated:
            failures.append("isolated maximiser")
        return tuple(failures)


@dataclass(frozen=True)
class Prediction:
    """What the law says about one (polyhedron, base, perturbation)."""

    exponent: float | None
    weighted_degree: float | None
    winning_faces: tuple[tuple[int, ...], ...]
    faces: tuple[Face, ...]
    vertex: tuple[float, ...]
    binding: tuple[int, ...]
    released: tuple[int, ...]
    coefficient: float | None
    coefficient_settled: bool
    hypotheses: Hypotheses | None
    refusal: str = ""
    metrics: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def answered(self) -> bool:
        return self.exponent is not None

    @property
    def licensed(self) -> bool:
        return self.hypotheses is not None and self.hypotheses.licensed

    def by_relevance(self) -> dict[str, tuple[Face, ...]]:
        """Faces sorted into the four classes of implication 6."""
        out: dict[str, list[Face]] = {
            RELEVANT: [], CRITICAL: [], SUBLEADING: [], INACTIVE: []}
        for face in self.faces:
            out[face.relevance].append(face)
        return {name: tuple(group) for name, group in out.items()}

    def report(self) -> str:
        """A human-readable rendering, used by the CLI and by logs."""
        return _render(self)


def _relevance(degree: float) -> str:
    if abs(degree - 1.0) <= CRITICAL_MARGIN:
        return CRITICAL
    return RELEVANT if degree < 1.0 else SUBLEADING


def _reason_for(relevance: str) -> str:
    if relevance == CRITICAL:
        return "critical: q = 1, where the balance changes and 1/(1-q) diverges"
    if relevance == SUBLEADING:
        return "supercritical: q >= 1, so this face opens no gap at small s"
    return ""


def predict(
    system: str,
    base: str,
    pert: str,
    *,
    domain: PolyhedronDomain | None = None,
) -> Prediction:
    """
    Run the law forwards on one case.

    `system` is the literal `([[...]], [...])` pair for `Ax <= b`, and `base`
    and `pert` are expressions in `x0, x1, ...` under the same whitelist the
    adjudicator parses. The vertex is the one the domain would adjudicate: a
    simple vertex that is a local maximum of the base along all its edges,
    preferring a tilted one, since an axis-aligned vertex cannot show the
    effect at all.

    A refusal is not a failure. `refusal` is set, `exponent` is None, and the
    text says which hypothesis of the setting is missing - unbounded, no simple
    maximising vertex, no face carrying the perturbation, or a weighted degree
    outside `(0, 1)` where the law makes no claim.
    """
    domain = domain or PolyhedronDomain()
    admitted, _status, reason, metrics = domain.scope(RULE, system, base, pert)
    faces = _faces_from(metrics)
    vertex_point = tuple(metrics.get("vertex") or ())

    if not admitted:
        return Prediction(
            exponent=None, weighted_degree=metrics.get("weighted_degree"),
            winning_faces=(), faces=faces, vertex=vertex_point,
            binding=(), released=(), coefficient=None,
            coefficient_settled=False, hypotheses=hypotheses_from(metrics),
            refusal=reason, metrics=dict(metrics))

    poly: Polyhedron = metrics.pop("poly")
    vertex: Vertex = metrics.pop("vertex_obj")
    base_fn, pert_fn = metrics.pop("base_fn"), metrics.pop("pert_fn")

    degree = float(metrics["weighted_degree"])
    exponent = float(metrics["predicted_exponent"])
    attaining = [face.edges for face in faces
                 if face.degree is not None
                 and abs(face.degree - degree) <= 1e-6]
    # Only the MINIMAL ones are branches. A larger face attains q* whenever it
    # contains a smaller one that does - it inherits the degree along with the
    # monomial - so reporting every face that attains it would say the optimiser
    # slides off constraints it in fact stays on. On the tilted simplex both
    # {0} and {0,1} read q = 1/4, but the gain lives on the slanted edge alone.
    winning = tuple(f for f in attaining
                    if not any(set(g) < set(f) for g in attaining))
    coefficient, _strength, settled = laws.leading_coefficient(
        base_fn, pert_fn, poly, vertex, exponent)

    # Edge i relaxes active constraint i and keeps the others tight - that is
    # how `geometry._edges` builds the basis - so the winning face names the
    # constraints the optimiser slides off. Where two distinct minimal faces
    # tie, `released` is what any winning branch gives up and `binding` is what
    # every one of them holds.
    active = tuple(metrics.get("active_constraints") or ())
    spanned = set().union(*(set(f) for f in winning)) if winning else set()
    released = tuple(active[i] for i in sorted(spanned) if i < len(active))
    binding = tuple(c for i, c in enumerate(active) if i not in spanned)

    return Prediction(
        exponent=exponent, weighted_degree=degree, winning_faces=winning,
        faces=faces, vertex=vertex_point, binding=binding, released=released,
        coefficient=coefficient, coefficient_settled=settled,
        hypotheses=hypotheses_from(metrics), refusal="",
        metrics={k: v for k, v in metrics.items() if not callable(v)})


def _faces_from(metrics: dict[str, Any]) -> tuple[Face, ...]:
    out: list[Face] = []
    for edges, degree in metrics.get("admissible_faces") or ():
        relevance = _relevance(degree)
        out.append(Face(tuple(edges), degree, relevance, _reason_for(relevance)))
    for edges, why in metrics.get("rejected_faces") or ():
        out.append(Face(tuple(edges), None, INACTIVE, why))
    return tuple(sorted(out, key=lambda f: (len(f.edges), f.edges)))


def hypotheses_from(metrics: dict[str, Any]) -> Hypotheses | None:
    """
    The three hypotheses as the adjudicator recorded them.

    Public because screening reads it straight off a stored row: every
    field it needs has been on the record since v8, so weighing a candidate
    already in the corpus costs a dict lookup rather than a re-measurement.
    """
    if "betas" not in metrics:
        return None
    return Hypotheses(
        simple_vertex=bool(metrics.get("edges")),
        base_homogeneity=metrics.get("base_homogeneity"),
        edge_orders=tuple(metrics.get("betas") or ()),
        isolation_margin=metrics.get("rival_margin"))


def calibrate(exponent: float) -> float:
    """
    Run the law backwards: an observed exponent gives the weighted order.

    Inverting `gamma = 1/(1-q)` gives `q = 1 - 1/gamma`, so a measured
    fractional power identifies the weighted degree of whatever perturbation is
    controlling the response - without knowing the perturbation. That is the
    whole content of implication 8, and it is why a measured exponent is
    evidence about geometry and not only about rates.

    Raises for `gamma <= 1`, where the inverse leaves `(0, 1)` and names no
    admissible face: the law only ever predicts exponents above 1.
    """
    if not math.isfinite(exponent) or exponent <= 1.0:
        raise ValueError(
            f"exponent {exponent} is not above 1, so it inverts to a weighted "
            "degree outside (0, 1), where the law makes no claim")
    return 1.0 - 1.0 / exponent


def consistent_faces(
    prediction: Prediction, observed: float, *, tolerance: float = 0.05
) -> tuple[Face, ...]:
    """
    Which admitted faces could have produced an observed exponent.

    The calibration step on its own returns a number. This turns that number
    into a statement about the geometry: the faces whose own degree matches the
    observed order to within `tolerance`. One match identifies the branch; more
    than one means the measurement does not separate them and a finer one is
    needed; none means the observed response did not come from any face of this
    tangent cone, which is itself informative - it is how the ambient
    counterexample announces itself.
    """
    try:
        target = calibrate(observed)
    except ValueError:
        return ()
    return tuple(face for face in prediction.faces
                 if face.admitted and face.degree is not None
                 and abs(face.degree - target) <= tolerance)


def _render(prediction: Prediction) -> str:
    lines: list[str] = []
    if prediction.vertex:
        # `+ 0.0` so a coordinate solved to -0.0 does not print as "-0".
        point = ", ".join(f"{c + 0.0:g}" for c in prediction.vertex)
        lines.append(f"vertex            ({point})")
    if not prediction.answered:
        lines.append(f"no prediction     {prediction.refusal}")
    else:
        lines.append(f"exponent          gamma = {prediction.exponent:.6g}")
        lines.append(f"weighted degree   q* = {prediction.weighted_degree:.6g}")
        if prediction.coefficient is not None:
            # More digits than anything else here: the coefficient is the
            # sharpest check the domain has (0.472470394 against 3/4**(4/3) on
            # the tilted simplex), and rounding it away hides that.
            settled = "" if prediction.coefficient_settled else "  (still drifting)"
            lines.append(f"leading gap       {prediction.coefficient:.9g}"
                         f" * s**{prediction.exponent:.6g}{settled}")
        winning = ", ".join("{" + ",".join(map(str, f)) + "}"
                            for f in prediction.winning_faces)
        lines.append(f"winning face(s)   {winning or 'none'}")
        lines.append(f"constraints released  {list(prediction.released)}")
        lines.append(f"constraints binding   {list(prediction.binding)}")

    groups = prediction.by_relevance()
    lines.append("")
    lines.append("faces of the tangent cone")
    for name in (RELEVANT, CRITICAL, SUBLEADING, INACTIVE):
        for face in groups[name]:
            edges = "{" + ",".join(map(str, face.edges)) + "}"
            degree = "     -" if face.degree is None else f"{face.degree:6.4f}"
            note = f"  {face.reason}" if face.reason else ""
            lines.append(f"  {edges:<12} q = {degree}  {name}{note}")

    hypotheses = prediction.hypotheses
    lines.append("")
    if hypotheses is None:
        lines.append("hypotheses        not reached")
    else:
        unmet = hypotheses.unmet()
        verdict = "licensed" if hypotheses.licensed else "NOT licensed: " + ", ".join(unmet)
        lines.append(f"hypotheses        {verdict}")
        lines.append(f"  edge orders     {list(hypotheses.edge_orders)}")
        lines.append(f"  homogeneity     {hypotheses.base_homogeneity}")
        lines.append(f"  isolation eta   {hypotheses.isolation_margin}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m categorical_polytope.adjudication.polyhedra.predict",
        description="Predict the singular response exponent at a polyhedral vertex.")
    parser.add_argument("system", help="literal ([[...]], [...]) pair for Ax <= b")
    parser.add_argument("base", help="expression in x0, x1, ... maximised at the vertex")
    parser.add_argument("pert", help="expression in x0, x1, ... added with strength s")
    parser.add_argument("--observed", type=float, default=None,
                        help="an observed exponent to calibrate against")
    args = parser.parse_args(argv)

    prediction = predict(args.system, args.base, args.pert)
    print(prediction.report())
    if args.observed is not None:
        print()
        try:
            order = calibrate(args.observed)
        except ValueError as exc:
            print(f"calibration       {exc}")
            return 1
        matches = consistent_faces(prediction, args.observed)
        named = ", ".join("{" + ",".join(map(str, f.edges)) + "}" for f in matches)
        print(f"calibration       observed {args.observed:g} -> q = {order:.6g}")
        print(f"  consistent with {named or 'no face of this tangent cone'}")
    return 0 if prediction.answered else 1
