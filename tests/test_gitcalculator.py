"""Regression tests for the gitcalculator (docs/GITCALCULATOR.md)."""

from __future__ import annotations

import io
import json
import re
import shutil
import socket
import subprocess
import threading
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
from gitcalculator.site import LEDGER_SCHEMA, PYODIDE_VERSION, render_page, server
from gitcalculator.tape import TAPE, verify
from gitcalculator.visit import visit

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


def _site(root, head, blobs, page=None):
    """A small published calculator: the real page, a one-preset ledger, a bundle and a stub Pyodide."""
    (root / "index.html").write_text(page or render_page(head), encoding="utf-8")
    ledger = {"schema": LEDGER_SCHEMA, "head": head, "live_engine": True,
              "presets": {"tilted-simplex": {"receipt": {"id": "gc-0"}, "history": {"states": []}}}}
    (root / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    bundle = {"schema": BUNDLE_SCHEMA, "head": head, "blobs": blobs, "documents": {}, "calculator": {"files": {}},
              "states": [{"code_id": "code-x", "commits": [], "files": {f"categorical_polytope/{i}.py": b
                                                                        for i, b in enumerate(blobs)}}],
              "pyodide": {"version": PYODIDE_VERSION, "index": "./pyodide/"}}
    (root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    runtime = root / "pyodide"
    runtime.mkdir(exist_ok=True)
    (runtime / "pyodide.js").write_text("// loader\n")
    (runtime / "pyodide.asm.js").write_text("// runtime\n")
    (runtime / "pyodide.asm.wasm").write_bytes(b"\0asm\x01\0\0\0")
    (runtime / "python_stdlib.zip").write_bytes(b"PK\x03\x04" + bytes(26))
    (runtime / "pyodide-lock.json").write_text(json.dumps({"info": {"version": PYODIDE_VERSION}}))


@pytest.fixture
def published(tmp_path):
    """Serve ``tmp_path`` the way GitHub Pages serves the calculator, and yield its address."""
    httpd = server(tmp_path, 0, quiet=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()


def test_visit_checks_every_file_a_browser_loads(tmp_path, published):
    head = {"commit": "f" * 40, "short": "fffffff", "dirty": False}
    good = "print('ok')\n"
    _site(tmp_path, head, {blob_id(good.encode()): good})
    report = visit(published)
    assert report["ok"], report["problems"]
    assert [row["path"] for row in report["files"]][:3] == ["index.html", "ledger.json", "bundle.json"]
    assert {row["path"] for row in report["files"] if row["status"] == 200} >= {"pyodide/pyodide.asm.wasm"}
    assert any("not in this clone" in note for note in report["files"][0]["notes"])
    assert report["checked_against_git"] is False

    out = io.StringIO()
    with redirect_stdout(out):
        assert main(["visit", published]) == 0
        assert main(["visit", published, "--commit", "e" * 40]) == 1
    assert "every file it loads checks out" in out.getvalue() and "serving build fffffff, not eeeeeee" in out.getvalue()

    bundle = json.loads((tmp_path / "bundle.json").read_text())
    bundle["blobs"][blob_id(good.encode())] = "print('tampered')\n"
    (tmp_path / "bundle.json").write_text(json.dumps(bundle))
    assert any("does not hash to its id" in p for p in visit(published)["problems"])

    _site(tmp_path, head, {blob_id(good.encode()): good})
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    ledger["head"] = {"commit": "e" * 40}
    (tmp_path / "ledger.json").write_text(json.dumps(ledger))
    (tmp_path / "pyodide" / "python_stdlib.zip").unlink()
    problems = visit(published)["problems"]
    assert "ledger.json: from build eeeeeee, but the page is build fffffff" in problems
    assert "pyodide/python_stdlib.zip: HTTP 404" in problems

    engine = (ROOT / "gitcalculator" / "web" / "engine.js").read_text(encoding="utf-8")
    page = render_page(head).replace(engine, engine + "/* edited after the build */\n", 1)
    _site(tmp_path, head, {blob_id(good.encode()): good}, page=page)
    assert "index.html: the inlined engine.js does not hash to its stamped blob id" in visit(published)["problems"]

    with socket.socket() as probe:  # an address where nothing listens
        probe.bind(("127.0.0.1", 0))
        closed = f"http://127.0.0.1:{probe.getsockname()[1]}/"
    unreachable = visit(closed)
    assert not unreachable["ok"] and unreachable["files"][0]["status"] is None


def _git_text(spec):
    try:
        return subprocess.run(["git", "show", spec], cwd=ROOT, check=True, capture_output=True).stdout.decode()
    except (OSError, subprocess.CalledProcessError):
        return None


@pytest.mark.skipif(_git_text("HEAD:gitcalculator/web/engine.js") is None, reason="needs git and a commit with the engine")
def test_visit_compares_a_clean_build_with_its_commit(tmp_path, published):
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    head = {"commit": commit, "short": commit[:7], "dirty": False}
    engine, modes = _git_text("HEAD:gitcalculator/web/engine.js"), _git_text("HEAD:gitcalculator/web/modes.js")
    stamp = {"engine_blob": blob_id(engine.encode()), "modes_blob": blob_id(modes.encode()),
             "commit": commit, "short": commit[:7]}
    page = (f"<!doctype html><title>gitcalculator</title><script>window.GITCALC_BUILD = {json.dumps(stamp)};</script>\n"
            f"<script>\n{engine}</script>\n<script>\n{modes}</script>\n")
    committed = _git_text("HEAD:gitcalculator/presets.py")
    _site(tmp_path, head, {blob_id(committed.encode()): committed}, page=page)
    report = visit(published, commit=commit)
    assert report["ok"] and report["checked_against_git"], report["problems"]
    assert "every blob is an object in this repository" in report["files"][2]["notes"]

    stray = "print('never committed, 7f3a')\n"
    _site(tmp_path, head, {blob_id(committed.encode()): committed, blob_id(stray.encode()): stray}, page=page)
    assert any("not objects in this repository" in p for p in visit(published, commit=commit)["problems"])

    head = dict(head, dirty=True, dirty_paths=["gitcalculator/presets.py"])
    _site(tmp_path, head, {blob_id(committed.encode()): committed, blob_id(stray.encode()): stray}, page=page)
    assert visit(published)["ok"]
    assert "uncommitted changes" in " ".join(visit(published, commit=commit)["problems"])


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


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_browser_engine_facets_match_exact_python_geometry():
    """The 3D picture draws facets the browser computes; Python recomputes them exactly."""
    from gitcalculator.certify import parse_system
    names = ("cube-3d", "pyramid-apex", "tilted-simplex")
    results = _browser([{"mode": "geometry", "request": preset_request(n)} for n in names])
    for name, js in zip(names, results):
        rows, rhs = parse_system(preset_request(name)["system"])
        corners = X.vertices(rows, rhs)
        expected = [[i for i, c in enumerate(corners) if X.dot(row, c) == b] for row, b in zip(rows, rhs)]
        assert js["facets"] == expected, name
    cube, pyramid, _ = results
    assert sorted(len(f) for f in cube["facets"]) == [4] * 6 and cube["simple"] and len(cube["active"]) == 3
    assert sorted(len(f) for f in pyramid["facets"] if len(f) >= 3) == [3, 3, 3, 3, 4]
    assert not pyramid["simple"] and len(pyramid["active"]) == 4


# --- proof sheets and the tape from GitHub ------------------------------------------

def _ghmath():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ghmath", ROOT / "experiments" / "ghmath.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def every_receipt():
    from gitcalculator.presets import PRESETS
    return {name: calculate(preset_request(name), budget="quick") for name in sorted(PRESETS)}


def test_proof_sheets_render_on_github_and_pin_their_links(every_receipt):
    from gitcalculator.sheet import sheet
    check = _ghmath().check_text
    for name, receipt in every_receipt.items():
        markdown = sheet(receipt, repository="https://github.com/o/r", ref="abc123", calculator="https://o.github.io/r/")
        assert check(markdown) == [], (name, check(markdown))
        assert markdown.startswith(f"### {receipt['answer']['headline'].replace('>', chr(92) + '>').replace('~', chr(92) + '~')} · ")
        statuses = [line.split(" | ")[1] for line in markdown.splitlines() if line.startswith("| [")]
        assert statuses == [link["status"].replace("_", " ") for link in receipt["certificate"]["links"]], name
        assert "https://github.com/o/r/blob/abc123/docs/" in markdown and "https://o.github.io/r/?system=" in markdown
    proved = sheet(every_receipt["cube-3d"])
    assert "\\frac{1}{1 - \\tfrac{1}{6}} = \\tfrac{6}{5}" in proved
    assert "\\Delta(s) \\sim \\tfrac{1}{432}\\, s^{3}" in sheet(every_receipt["signed-sharp"])
    unpinned = sheet(every_receipt["cube-3d"], repository="https://github.com/o/r", ref="abc123", linkable=[])
    assert "/blob/" not in unpinned and "/commit/" not in unpinned  # nothing links where the files are not known to exist


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_browser_writes_the_same_proof_sheet(every_receipt):
    from gitcalculator.sheet import sheet
    from gitcalculator.presets import PRESETS
    options = [{}, {"repository": "https://github.com/o/r", "ref": "abc123", "calculator": "https://o.github.io/r/",
                    "linkable": ["docs/FORMAL_FACE_SELECTION.md"]}]
    jobs = [{"mode": "sheet", "receipt": r, "options": o} for r in every_receipt.values() for o in options]
    jobs += [{"mode": "solve-sheet", "request": preset_request(n), "options": options[1]} for n in sorted(PRESETS)]
    results = _browser(jobs)
    expected = [sheet(r, **o) for r in every_receipt.values() for o in options]
    assert [r["markdown"] for r in results[:len(expected)]] == expected
    check = _ghmath().check_text
    assert {n: check(r["markdown"]) for n, r in zip(sorted(PRESETS), results[len(expected):]) if check(r["markdown"])} == {}


def test_command_line_prints_a_proof_sheet():
    out = io.StringIO()
    with redirect_stdout(out):
        assert main(["calc", "--preset", "cube-3d", "--budget", "quick", "--markdown"]) == 0
    text = out.getvalue()
    assert text.startswith("### Δ(s) = Θ(s^6/5) · proved\n\n```math\n") and "python -m gitcalculator calc --system" in text


def test_a_new_calculation_can_be_recorded_on_the_tape(tmp_path):
    from gitcalculator import tape
    request = {"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4)", "perturbation": "x0 + x1**3"}
    path = tape.record("orthant-check", request, tmp_path)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["input"] == request and stored["name"] == "orthant-check"
    assert [row["unchanged"] for row in tape.verify(tmp_path)] == [True]
    with pytest.raises(SystemExit):
        main(["tape", "record", "Not A Name", "--system", SIMPLEX, "--base", "-x0", "--perturbation", "x0"])
    with pytest.raises(SystemExit):
        main(["tape", "record", "two-inputs-missing", "--system", SIMPLEX])


# --- the phase map ----------------------------------------------------------------------

def test_phase_map_finds_the_chambers_and_exact_coefficient_laws():
    from gitcalculator.modes import phase_map
    from gitcalculator.presets import MAP_PRESETS
    family = MAP_PRESETS["two-edges"]
    result = phase_map(family["system"], family["base"], family["perturbation"], resolution=6)
    shares = {(o["verdict"], o["gamma"], o["winners"]): o["cells"] for o in result["outcomes"]}
    assert shares == {("proved", None, ""): 9, ("proved", "4/3", "{c0}"): 18, ("proved", "2", "{c1}"): 9}
    assert {law["monomial"]: law["terms"] for law in result["laws"]} == {"c0": {"1,0": "1"}, "c1": {"0,1": "1"}}
    channel = MAP_PRESETS["signed-channel"]
    curved = phase_map(channel["system"], channel["base"], channel["perturbation"], resolution=4)
    assert {(o["verdict"], o["gamma"]) for o in curved["outcomes"]} == {("proved", None), ("proved-v22", "3"), ("proved", "6")}
    out = io.StringIO()
    with redirect_stdout(out):
        assert main(["map", "--preset", "two-edges", "--resolution", "4"]) == 0
    assert "A  Δ(s) = 0 for small s (proved)" in out.getvalue() and "a(t, u) = t" in out.getvalue()


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_browser_phase_map_matches_python_cell_for_cell():
    from gitcalculator.modes import phase_map
    from gitcalculator.presets import MAP_PRESETS
    names = sorted(MAP_PRESETS)
    requests = [dict(system=MAP_PRESETS[n]["system"], base=MAP_PRESETS[n]["base"], perturbation=MAP_PRESETS[n]["perturbation"],
                     t_from="-1", t_to="1", u_from="-1", u_to="1", resolution=8) for n in names]
    for name, request, js in zip(names, requests, _browser([{"mode": "map", "request": r} for r in requests])):
        python = phase_map(request["system"], request["base"], request["perturbation"], resolution=8)
        cells = [[o["verdict"], o["gamma"], o["winners"]] for o in (python["outcomes"][k] for k in python["grid"])]
        assert js["cells"] == cells, name
        assert js["laws"] == {law["monomial"]: law["terms"] for law in python["laws"]}, name
