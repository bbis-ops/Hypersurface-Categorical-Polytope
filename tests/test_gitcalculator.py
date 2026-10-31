"""Regression tests for the gitcalculator (docs/GITCALCULATOR.md)."""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from contextlib import redirect_stdout
from fractions import Fraction

import pytest

from gitcalculator import exact as X
from gitcalculator.__main__ import main
from gitcalculator.certify import LINKS
from gitcalculator.counter import REGISTRY, check_witnesses
from gitcalculator.history import BUNDLE_SCHEMA, BundleSource, replay
from gitcalculator.measure import floor_decimal
from gitcalculator.presets import preset_request
from gitcalculator.provenance import ROOT, blob_id
from gitcalculator.receipt import backend, calculate
from gitcalculator.tape import TAPE, verify

SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"


@pytest.fixture(scope="module")
def receipts():
    names = ("tilted-simplex", "signed-sharp", "cross-term", "critical-layer", "tied-maximizers", "pyramid-apex")
    return {name: calculate(preset_request(name)) for name in names}


def links(receipt):
    return {link["id"]: link["status"] for link in receipt["certificate"]["links"]}


def effects(receipt):
    return {c["id"]: c["effect"] for c in receipt["counterarguments"]}


def verdicts(receipt):
    return {v["id"]: v.get("verdict") for v in receipt["measurement"].get("verdicts", [])}


def test_tilted_simplex_is_proved_in_exact_arithmetic(receipts):
    receipt = receipts["tilted-simplex"]
    assert receipt["answer"]["verdict"] == "proved"
    assert (receipt["answer"]["gamma"], receipt["answer"]["q_star"]) == ("4/3", "1/4")
    assert set(links(receipt).values()) == {"exact"}
    assert receipt["certificate"]["agreement"] == {**receipt["certificate"]["agreement"], "q_star": True, "winning_faces": True}
    assert verdicts(receipt) == {"backend": "consistent", "ambient-axes": "contradicted"}
    assert effects(receipt)["ambient-axes"] == "averted"


def test_signed_sharp_contradicts_the_face_minimum_and_proves_v22(receipts):
    receipt = receipts["signed-sharp"]
    answer = receipt["answer"]
    assert (answer["verdict"], answer["gamma"], answer["coefficient"]["exact"]) == ("proved-v22", "3", "1/432")
    assert links(receipt)["H5"] == "unresolved"
    assert verdicts(receipt) == {"exact-faces": "contradicted", "curved": "consistent"}
    assert effects(receipt)["signed-sharp"] == "blocks"


def test_cross_term_is_licensed_by_the_backend_but_fails_h2_exactly(receipts):
    receipt = receipts["cross-term"]
    assert receipt["answer"]["verdict"] == "licensed"
    assert links(receipt)["H2"] == "failed"
    assert effects(receipt)["homogeneity-probe"] == "blocks"


def test_critical_layer_proves_zero_response(receipts):
    receipt = receipts["critical-layer"]
    assert receipt["answer"]["verdict"] == "proved"
    assert receipt["certificate"]["status"] == "zero_response"
    assert receipt["backend"]["signature"]["status"] == "refused"


def test_tied_maximizers_fail_h0_and_the_bounds_find_the_rival(receipts):
    receipt = receipts["tied-maximizers"]
    assert links(receipt)["H0"] == "failed"
    assert verdicts(receipt) == {"backend": "contradicted"}
    assert receipt["measurement"]["boundary_dominated"] is True


def test_non_simple_vertex_is_refused_exactly(receipts):
    receipt = receipts["pyramid-apex"]
    assert links(receipt)["vertex"] == "failed"
    assert effects(receipt)["non-simple"] == "blocks"


def test_vertex_values_are_evaluated_exactly_not_taken_from_the_centered_pullback():
    """Regression: the compiler's pullback is centered, so F(v) and G(v) must be computed."""
    receipt = calculate({"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4) + 5", "perturbation": "x0 + 7"},
                        budget="quick")
    assert links(receipt)["transport"] == "exact"
    assert receipt["answer"]["verdict"] == "proved" and receipt["answer"]["gamma"] == "4/3"
    assert receipt["measurement"]["pullback_consistent"] is True
    falling = calculate({"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4)", "perturbation": "x0 + 3*x1**3 - x0*x1"},
                        budget="quick")
    assert falling["certificate"]["status"] == "zero_response"


def test_every_lower_bound_is_a_certified_inequality(receipts):
    """Re-check witnesses from their printed decimals, and compare with the exact optimum."""
    request = receipts["tilted-simplex"]["input"]
    rows, rhs = (list(map(lambda r: tuple(map(Fraction, r)), eval(request["system"])[0])),
                 list(map(Fraction, eval(request["system"])[1])))
    base, pert = X.parse(request["base"], 2), X.parse(request["perturbation"], 2)
    vertex, generators = (Fraction(0), Fraction(1)), ((Fraction(1), Fraction(-1)), (Fraction(0), Fraction(-1)))
    for row in receipts["tilted-simplex"]["measurement"]["rows"]:
        c = [Fraction(v) for v in row["witness_c"]]
        x = tuple(vertex[k] + sum(ci * u[k] for ci, u in zip(c, generators)) for k in range(2))
        assert all(X.dot(a, x) <= b for a, b in zip(rows, rhs))
        s = Fraction(row["s"])
        gain = X.evaluate_exact(base, x) - X.evaluate_exact(base, vertex) + s * (
            X.evaluate_exact(pert, x) - X.evaluate_exact(pert, vertex))
        assert gain >= Fraction(row["lower_bound"]) and (gain > 0) == (row["lower_bound"] != "0")
        assert float(Fraction(row["lower_bound"])) <= 3 / 4 ** (4 / 3) * float(s) ** (4 / 3) * (1 + 1e-12)


def test_counter_argument_witnesses_hold_at_head():
    report = check_witnesses(backend().handle)
    assert [r["id"] for r in report if not r["passed"]] == []


def _slug(heading: str) -> str:
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


@pytest.mark.parametrize("source", sorted({doc for _, doc, _ in LINKS.values()}
                                          | {src for argument in REGISTRY for src in argument.sources}))
def test_cited_sources_resolve_to_files_and_headings(source):
    path, _, anchor = source.partition("#")
    text = (ROOT / path).read_text(encoding="utf-8")
    if anchor:
        headings = {_slug(m.group(1)) for m in re.finditer(r"^#+\s+(.+)$", text, re.M)}
        assert anchor in headings, f"{source} has no matching heading"


def test_receipt_ids_are_content_addresses():
    first = calculate(preset_request("tilted-simplex"), budget="quick")
    second = calculate(preset_request("tilted-simplex"), budget="quick")
    other = calculate(dict(preset_request("tilted-simplex"), perturbation="2*x0"), budget="quick")
    assert first["id"] == second["id"] != other["id"]


def test_blob_ids_are_git_object_ids():
    path = ROOT / "categorical_polytope" / "face_selection.py"
    try:
        expected = subprocess.run(["git", "hash-object", str(path)], cwd=ROOT, capture_output=True, text=True,
                                  check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    assert blob_id(path.read_bytes()) == expected
    assert blob_id(b"a\r\nb\n") == blob_id(b"a\nb\n")


def test_bundled_snapshots_are_checked_against_their_blob_ids(tmp_path):
    good = "print('ok')\n"
    bundle = {"schema": BUNDLE_SCHEMA, "states": [{"code_id": "code-x", "commits": [{}],
                                                    "files": {"categorical_polytope/a.py": blob_id(good.encode())}}],
              "blobs": {blob_id(good.encode()): good}}
    source = BundleSource(bundle, tmp_path)
    assert (source.materialize(source.states()[0]) / "categorical_polytope" / "a.py").read_text() == good
    bundle["blobs"][blob_id(good.encode())] = "print('tampered')\n"
    with pytest.raises(ValueError):
        BundleSource(bundle, tmp_path / "other").materialize(source.states()[0])


def _has_history() -> bool:
    try:
        for ref in ("64db362", "90105c2"):
            subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=ROOT, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


@pytest.mark.skipif(not _has_history(), reason="needs the full git history")
def test_history_finds_the_signed_channel_correction():
    history = replay(preset_request("signed-sharp"))
    by_first = {run["first_commit"]["short"][:7]: run for run in history["states"]}
    old = by_first["64db362"]
    assert old["answer"]["core"]["licensed"] is True and old["answer"]["core"]["gamma"] == "6"
    assert [a["verdict"] for a in old["audit"] if a["probe"] == "core"] == ["contradicted"]
    corrected = by_first["90105c2"]
    assert corrected["answer"]["core"]["licensed"] is False
    assert corrected["answer"]["curved"] == {"status": "licensed", "gamma": "3", "coefficient": "1/432"}
    assert any(change["at"]["short"].startswith("90105c2") for change in history["changes"])


def test_the_recorded_tape_has_not_drifted():
    if not any(TAPE.glob("*.json")):
        pytest.skip("no recorded calculations")
    drifted = {row["name"]: row["drift"] for row in verify() if not row["unchanged"]}
    assert drifted == {}


def test_exact_toolkit():
    assert X.curvature(X.parse("-((x0+x1-1)**2 + x0**4)", 2)) == "concave"
    assert X.curvature(X.parse("-(x0**2+x0*x1+x1**2)", 2)) == "unknown"
    assert X.total_degree(X.parse("x0*x1**3 - 2/3", 2)) == 4 and X.total_degree(X.parse("exp(x0)", 1)) is None
    assert X.feasible([[1, 0], [-1, 0]], [1, 0]) and not X.feasible([[1, 0], [-1, 0]], [1, -2])
    assert sorted(X.vertices([[-1, 0], [0, -1], [1, 1]], [0, 0, 1])) == [(0, 0), (0, 1), (1, 0)]
    with pytest.raises(X.UnsafeExpression):
        X.parse("__import__('os')", 1)
    value = Fraction(1, 3)
    assert Fraction(floor_decimal(value)) <= value < Fraction(floor_decimal(value)) + Fraction(1, 10**12)


def test_command_line_prints_a_json_receipt_and_checks_witnesses():
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(["calc", "--preset", "tilted-simplex", "--budget", "quick", "--json"])
    assert code == 0 and json.loads(out.getvalue())["answer"]["verdict"] == "proved"
    with redirect_stdout(io.StringIO()):
        assert main(["counter"]) == 0


def test_command_line_applies_an_observed_exponent_to_a_preset():
    """Regression: --observed was dropped whenever --preset was given."""
    out = io.StringIO()
    with redirect_stdout(out):
        main(["calc", "--preset", "tilted-simplex", "--observed", "2", "--budget", "quick", "--json"])
    receipt = json.loads(out.getvalue())
    assert receipt["input"]["observed_exponent"] == 2.0
    inverse = next(c for c in receipt["counterarguments"] if c["id"] == "inverse-tolerance")
    assert inverse["effect"] == "caveat" and "no_face_match" in inverse["detail"]


# --- the browser engine against the Python implementation ---------------------------

NODE = shutil.which("node")
SQUARE = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])"
DESIGNS = [(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "3/2"), (SQUARE, "-(x0**4+x1**6)", "3/2")]
SWEEPS = [(SQUARE, "-(x0**4 + x1**2)", "(t - 1/3)*x0 + x1", "-1", "1"),
          (SQUARE, "-(x0**4+x1**4)", "-x0**2 + t*x0*x1 - x1**2", "0", "4")]
ATTACKS = [(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "x0**2"), (SQUARE, "-(x0**4+x1**4)", "x0+x1**2")]


def _browser(jobs):
    completed = subprocess.run([NODE, str(ROOT / "tests" / "engine_conformance.js")], input=json.dumps(jobs),
                               capture_output=True, text=True, timeout=300, check=True)
    results = json.loads(completed.stdout)
    assert not [r for r in results if "error" in r], results
    return results


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_browser_engine_matches_the_python_certificate_on_every_preset():
    from gitcalculator.certify import certify
    from gitcalculator.modes import outcome
    from gitcalculator.presets import PRESETS
    names = sorted(PRESETS)
    results = _browser([{"mode": "solve", "request": preset_request(n)} for n in names])
    for name, js in zip(names, results):
        request = preset_request(name)
        python, _ = certify(request, {})
        assert js["status"] == python["status"], name
        assert (js["q_star"], js["gamma"]) == (python.get("q_star"), python.get("gamma")), name
        assert js["links"] == {link["id"]: link["status"] for link in python["links"]}, name
        python_outcome = outcome(request)
        if python_outcome["verdict"] == "proved-v22":
            assert js["curved"] == python_outcome["gamma"], name


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_browser_engine_matches_python_on_design_sweep_and_attack():
    from gitcalculator.modes import attack, design, sweep
    jobs = ([{"mode": "design", "request": {"system": s, "base": b, "target": t}} for s, b, t in DESIGNS]
            + [{"mode": "sweep", "request": {"system": s, "base": b, "perturbation": p, "from": lo, "to": hi}}
               for s, b, p, lo, hi in SWEEPS]
            + [{"mode": "attack", "request": {"system": s, "base": b, "perturbation": p}} for s, b, p in ATTACKS])
    results = iter(_browser(jobs))
    for system, base, target in DESIGNS:
        js, py = next(results), design(system, base, target)
        assert js["spectrum"] == [[e["q"], e["gamma"]] for e in py["spectrum"]]
        assert js["target"] == [py["target"]["achievable"], py["target"]["nearest_below"], py["target"]["nearest_above"]]
    for system, base, perturbation, lo, hi in SWEEPS:
        js, py = next(results), sweep(system, base, perturbation, lo, hi)
        assert [w[:2] for w in js["walls"]] == [[w["kind"], w["at"]] for w in py["walls"]]
        assert all(abs(a[2] - b["value"]) < 1e-9 for a, b in zip(js["walls"], py["walls"]))
        assert js["chambers"] == [[c["outcome"]["verdict"], c["outcome"]["gamma"]] for c in py["chambers"]]
    for system, base, perturbation in ATTACKS:
        js, py = next(results), attack(system, base, perturbation)
        assert js["base"] == [py["base"]["verdict"], py["base"]["gamma"]]
        assert js["mutations"] == [[m["kind"], m["outcome"]["verdict"], m["outcome"]["gamma"], m["changed"]] for m in py["mutations"]]


def test_design_finds_the_quantized_spectrum_and_impossible_targets():
    from gitcalculator.modes import design
    result = design(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "3/2")
    assert [e["gamma"] for e in result["spectrum"]] == ["4/3", "2", "4"]
    assert result["slacks"][1]["expression"] == "1 - x0 - x1"
    assert result["target"]["achievable"] is False
    assert (result["target"]["nearest_below"], result["target"]["nearest_above"]) == ("4/3", "2")
    reachable = design(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "4/3")["target"]
    assert [(c["perturbation"], c["check"]["verdict"], c["check"]["gamma"]) for c in reachable["candidates"]] == [("x0", "proved", "4/3")]


def test_sweep_finds_exact_and_positivity_walls():
    from gitcalculator.modes import sweep
    exact = sweep(SQUARE, "-(x0**4 + x1**2)", "(t - 1/3)*x0 + x1", "-1", "1")
    assert [(w["kind"], w["at"]) for w in exact["walls"]] == [("coefficient", "1/3")]
    assert [c["outcome"]["gamma"] for c in exact["chambers"]] == ["2", "4/3"]
    positivity = sweep(SQUARE, "-(x0**4+x1**4)", "-x0**2 + t*x0*x1 - x1**2", "0", "4")
    wall = next(w for w in positivity["walls"] if w["kind"] == "outcome")
    assert Fraction(wall["lo"]) <= 2 <= Fraction(wall["hi"]) and Fraction(wall["hi"]) - Fraction(wall["lo"]) < Fraction(1, 10**12)
    assert [c["outcome"]["verdict"] for c in positivity["chambers"]] == ["refused", "proved"]


def test_attack_generates_counterexamples_and_keeps_the_control():
    from gitcalculator.modes import attack
    result = attack(SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "x0**2")
    by_kind = {}
    for m in result["mutations"]:
        by_kind.setdefault(m["kind"], []).append(m)
    assert by_kind["control"][0]["changed"] is False
    assert by_kind["intrusion"][0]["outcome"]["gamma"] == "4/3"
    assert any(m["changed"] for m in by_kind["facet tilt"]) and not all(m["changed"] for m in by_kind["facet tilt"])
