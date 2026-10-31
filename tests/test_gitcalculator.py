"""Regression tests for the gitcalculator (docs/GITCALCULATOR.md)."""

from __future__ import annotations

import io
import json
import re
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
