"""Exact localization and public JSON contract for curved reduction."""

import io
import json
from fractions import Fraction as Q

import pytest

from categorical_polytope.adjudication.polyhedra.backend import FaceSelectionBackend, main
from categorical_polytope.adjudication.polyhedra.curved import _bounded_in_edge_chart


BOX = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"


def request(**overrides):
    return dict(operation="curved_reduction", system=BOX, base="-(x0**6+x1**6)",
                perturbation="-x0**2+x0*x1**2", **overrides)


def test_backend_certifies_the_original_counterexample():
    result = FaceSelectionBackend().handle(request())
    assert result["answered"] and result["licensed"]
    assert result["operation"] == "polyhedral_curved_reduction"
    assert result["scaling"]["response_exponent_exact"] == "3"
    assert result["scaling"]["leading_coefficient"]["exact"] == "1/432"
    assert result["scope"]["checks"]["unique_global_base_maximizer"]


@pytest.mark.parametrize("system,base,pert", [
    ("([[-1,0],[1,-1],[1,0],[-1,1]], [0,0,1,1])",
     "-(x0**6+(x1-x0)**6)", "-x0**2+x0*(x1-x0)**2"),
    ("([[-2,0],[0,-3],[1,0],[0,1]], [0,0,1,1])",
     "-(x0**6+x1**6)", "-x0**2+x0*x1**2"),
    ("([[-1,0],[0,-1],[1,0],[0,1]], [-2,-3,3,4])",
     "7-((x0-2)**6+(x1-3)**6)", "5-(x0-2)**2+(x0-2)*(x1-3)**2"),
])
def test_exact_transport_preserves_the_sharp_law(system, base, pert):
    payload = request()
    payload.update(system=system, base=base, perturbation=pert)
    result = FaceSelectionBackend().handle(payload)
    assert result["licensed"]
    assert result["scaling"]["leading_coefficient"]["exact"] == "1/432"
    assert result["scaling"]["response_exponent_exact"] == "3"


def test_cancellation_is_decided_after_square_completion():
    payload = request()
    payload["perturbation"] += "-x1**4/4+x1**5"
    result = FaceSelectionBackend().handle(payload)
    assert result["licensed"]
    assert result["scaling"]["response_exponent_exact"] == "6"


@pytest.mark.parametrize("changes", [
    {"base": "-(x0**3+x1**6)"},
    {"base": "-(x0**6+x1**6+x0*x1)"},
    {"perturbation": "-x0**2-x0*x1**2"},
    {"system": "([[-1,0],[0,-1]], [0,0])"},
    {"system": "([[-1,0],[0,-1],[1,0],[0,1]], [-2,0,1,1])"},
])
def test_failed_hypotheses_do_not_get_a_certificate(changes):
    payload = request()
    payload.update(changes)
    result = FaceSelectionBackend().handle(payload)
    assert not result["answered"] and not result["licensed"]
    assert result["status"] == "outside_scope"
    assert result["scope"]["blockers"]


def test_recession_test_keeps_a_single_feasible_direction_unbounded():
    assert not _bounded_in_edge_chart([(Q(1), Q(-1)), (Q(-1), Q(1))])
    assert _bounded_in_edge_chart([(Q(1), Q(-1)), (Q(-1), Q(2))])


def test_hostile_expression_never_executes(monkeypatch):
    import os
    monkeypatch.setattr(os, "system", lambda *_: pytest.fail("expression executed"))
    payload = request()
    payload["perturbation"] = "__import__('os').system('bad')"
    result = FaceSelectionBackend().handle(payload)
    assert not result["licensed"]


def test_cli_reads_the_new_operation(capsys):
    code = main([], stdin=io.StringIO(json.dumps(request())))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["scaling"]["response_exponent_exact"] == "3"


def test_default_face_selection_keeps_its_original_scope_boundary():
    payload = request()
    payload.pop("operation")
    out = FaceSelectionBackend().handle(payload)
    assert not out["licensed"]
    assert out["exact_refinement"]["unresolved_faces"] == [[0, 1]]
