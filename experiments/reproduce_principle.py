"""Reproduce the runbook's canonical results through the public JSON process.

Standard library only. Each run preserves its requests, full outputs, explicit
checks, and source hashes in a new directory. No tracked reports are regenerated.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
BACKEND = "categorical_polytope.adjudication.polyhedra.backend"
FIXTURES = {
    "transport": "face_selection_ambient_v20_request.json",
    "binomial": "face_selection_binomial_v19_request.json",
    "phase": "face_selection_phase_v17_request.json",
    "qualification": "face_selection_qualified_v18_request.json",
    "discovery": "face_selection_discovery_v21_request.json",
    "curved": "curved_reduction_request.json",
    "finite-scale": "curved_finite_scale_requests.json",
}
SCRIPTS = {
    "activation": "activation_contact_check.py",
    "corrected-note": "note_publication_check.py",
    # A value may carry arguments. The publication control gates document
    # rendering, so a formula that would print as literal text on GitHub fails
    # this suite alongside a mathematical regression.
    "docs-rendering": ("ghmath.py", "README.md", "docs", "categorical_polytope",
                       "experiments"),
}
DERIVED = ("selector-limit", "curved-cancellation", "inverse", "phase-unlicensed")
RUNS = tuple(FIXTURES) + DERIVED + tuple(SCRIPTS)


def read_fixture(name: str):
    path = ROOT / "experiments" / FIXTURES[name]
    return json.loads(path.read_text(encoding="utf-8"))


def request_for(name: str):
    if name in FIXTURES:
        return read_fixture(name), "experiments/" + FIXTURES[name]
    if name == "selector-limit":
        payload = read_fixture("curved")
        payload.pop("operation")
        payload["request_id"] = name
        return payload, "curved fixture with operation omitted"
    if name == "curved-cancellation":
        payload = read_fixture("curved")
        payload["perturbation"] += "-x1**4/4+x1**5"
        payload["request_id"] = name
        return payload, "curved fixture with quartic cancellation and a quintic term"
    if name == "inverse":
        base = read_fixture("transport")["cases"][0]
        return [dict(base, request_id="inverse-match", observed_exponent=4 / 3),
                dict(base, request_id="inverse-mismatch", observed_exponent=2)], (
                    "simplex transport fixture with two observed exponents")
    if name == "phase-unlicensed":
        payload = read_fixture("phase")
        payload.pop("assumptions")
        payload["request_id"] = name
        return payload, "phase fixture with assumption attestations omitted"
    raise ValueError(f"No request for {name}")


def inspect_result(name: str, data) -> list[dict]:
    checks = []

    def equal(label, actual, expected):
        checks.append(dict(check=label, actual=actual, expected=expected,
                           passed=actual == expected))

    def field(path, expected):
        value = data
        for part in path.split("/"):
            value = value[int(part)] if isinstance(value, list) else value[part]
        equal(path, value, expected)

    if name == "transport":
        field("status", "complete")
        field("case_count", 2)
        for i in range(2):
            field(f"cases/{i}/status", "licensed")
            field(f"cases/{i}/universality_class/id", "face-weight:1/4|response:4/3")
            field(f"cases/{i}/ambient_hierarchy/weight_layer/exact_pullback_axial_orders",
                  {"c0": 4, "c1": 2})
            field(f"cases/{i}/selection/winning_faces", [[0]])
        field("transitions/0/kind", "same_universality_class")
        field("transitions/0/ambient_transport_change/changed", True)
    elif name == "binomial":
        field("status", "licensed")
        field("universality_class/id", "face-weight:1/2|response:2")
        witnesses = data["exact_refinement"]["positivity_certificates"]
        witness = next(w for w in witnesses if w["face"] == [0, 1])
        x, y = (Fraction(str(witness["coordinates"][axis])) for axis in ("c0", "c1"))
        equal("binomial witness is in the relative interior", x > 0 and y > 0, True)
        equal("exact binomial gain at returned witness", str(-2 * x + y * y), "3/4")
        equal("constructive provenance", witness["provenance"],
              "mixed-sign binomial ratio certificate")
    elif name in ("phase", "phase-unlicensed"):
        field("status", "licensed" if name == "phase" else "unlicensed")
        field("phase_diagram/transitions/0/parameter/exact", "1/4")
        field("evaluations/2/response_exponent/exact", "8/5")
        field("evaluations/2/winning_mechanisms", ["face-a", "face-b"])
        field("evaluations/2/robustness/parameter_distance/exact", "0")
        if name == "phase-unlicensed":
            field("licensed", False)
            equal("missing hypotheses remain explicit", bool(data["scope"]["blockers"]), True)
    elif name == "qualification":
        field("status", "licensed")
        field("phase_diagram/transitions/0/parameter/exact", "1/3")
        for i, exponent in enumerate(("2", "2", "4/3")):
            field(f"evaluations/{i}/response_exponent/exact", exponent)
        field("evaluations/1/qualified_selection/mechanisms/0/status", "cancelled")
        field("evaluations/2/winning_mechanisms", ["emerging-low-face"])
    elif name == "discovery":
        field("status", "complete")
        field("candidate_count", 6)
        field("screening/counts", {"relevant": 5, "critical": 1})
        equal("exact universality classes", [g["id"] for g in data["universality_classes"]],
              ["face-weight:1/4|response:4/3", "face-weight:1/2|response:2",
               "face-weight:3/4|response:4"])
        field("summary/law_candidate_count", 2)
        field("universality_classes/0/registry_status", "known")
        cancelled = next(x for x in data["case_summaries"] if x["id"] == "cancelled-linear")
        equal("cancelled ambient monomial retained", cancelled["cancelled_edge_monomial_count"], 1)
    elif name in ("curved", "curved-cancellation"):
        field("status", "licensed")
        field("scaling/response_exponent_exact", "3" if name == "curved" else "6")
        field("scaling/leading_coefficient/exact", "1/432" if name == "curved" else "3125/46656")
        field("scaling/uniform_in_coefficients", False)
    elif name == "finite-scale":
        equal("two finite-scale responses", len(data), 2)
        for i, status in enumerate(("outside_tolerance", "within_tolerance")):
            field(f"{i}/status", "licensed")
            field(f"{i}/scaling/response_exponent_exact", "3")
            field(f"{i}/finite_scale/status", status)
            field(f"{i}/finite_scale/bounds_certified", True)
            field(f"{i}/finite_scale/witness/feasible", True)
            ratio = data[i]["finite_scale"]["gap_to_prediction_ratio"]
            lower, upper = (Fraction(ratio[k]["exact"]) for k in ("lower", "upper"))
            equal(f"case {i}: ordered ratio enclosure", 0 <= lower <= upper, True)
            inside = Fraction(9, 10) <= lower <= upper <= Fraction(11, 10)
            outside = lower > Fraction(11, 10) or upper < Fraction(9, 10)
            equal(f"case {i}: rational tolerance decision", outside if i == 0 else inside, True)
    elif name == "selector-limit":
        field("status", "refused")
        field("licensed", False)
        field("exact_refinement/unresolved_faces", [[0, 1]])
        equal("higher-layer blocker retained", any("higher_order_unresolved" in x
              for x in data["scope"]["blockers"]), True)
    elif name == "inverse":
        for i in range(2):
            field(f"{i}/status", "licensed")
            field(f"{i}/universality_class/id", "face-weight:1/4|response:4/3")
        field("0/inverse/status", "matched")
        field("0/inverse/minimal_consistent_faces", [[0]])
        field("1/inverse/status", "no_face_match")
    else:
        raise ValueError(f"No checks for {name}")
    return checks


def script_parts(entry) -> tuple[str, list[str]]:
    """A SCRIPTS value is a filename, optionally followed by arguments."""
    if isinstance(entry, str):
        return entry, []
    return entry[0], list(entry[1:])


def source_record() -> dict:
    paths = set((ROOT / "categorical_polytope").rglob("*.py"))
    paths.update(ROOT / "experiments" / name for name in FIXTURES.values())
    paths.update(ROOT / "experiments" / script_parts(entry)[0]
                 for entry in SCRIPTS.values())
    paths.update((Path(__file__).resolve(), ROOT / "docs" / "RUNBOOK.md", ROOT / "pyproject.toml"))
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(paths)}
    git = {}
    for key, args in (("commit", ["rev-parse", "HEAD"]),
                      ("working_tree", ["status", "--porcelain", "--untracked-files=all"])):
        try:
            result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                    text=True, encoding="utf-8", timeout=10)
            git[key] = result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            git[key] = None
    return dict(python=sys.version, platform=platform.platform(), git=git, sha256=hashes)


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reproduce(name: str, directory: Path) -> dict:
    case_dir = directory / name
    case_dir.mkdir()
    record = {"id": name, "checks": [], "artifacts": {}}
    started = time.monotonic()
    try:
        if name in SCRIPTS:
            script, extra = script_parts(SCRIPTS[name])
            record["source"] = "experiments/" + script
            command = [sys.executable, str(ROOT / record["source"]), *extra]
            output_name = "output.txt"
        else:
            request, source = request_for(name)
            record["source"] = source
            write_json(case_dir / "request.json", request)
            record["artifacts"]["request"] = f"{name}/request.json"
            command = [sys.executable, "-m", BACKEND, "--input",
                       str(case_dir / "request.json"), "--pretty"]
            output_name = "response.json"
        # The two algebra scripts use assertions as executable proof checks.
        env = dict(os.environ, PYTHONOPTIMIZE="0")
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", env=env, timeout=120)
        (case_dir / output_name).write_text(result.stdout, encoding="utf-8")
        (case_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")
        record["command"] = command
        record["artifacts"].update(output=f"{name}/{output_name}", stderr=f"{name}/stderr.txt")
        expected_exit = 1 if name == "selector-limit" else 0
        record["checks"].append(dict(check="process exit", actual=result.returncode,
                                     expected=expected_exit, passed=result.returncode == expected_exit))
        if name == "activation":
            marker = "Exact coexistence, zero value, and stationarity verified through degree 20."
            record["checks"].append(dict(check="degree-20 algebra verified",
                                         passed=marker in result.stdout))
        elif name == "corrected-note":
            # Successful execution means every exact assertion in the script passed.
            data = json.loads(result.stdout)
            record["checks"].append(dict(check="exact note report produced", passed=bool(data)))
        elif name == "docs-rendering":
            # Errors are known to render wrongly on GitHub; warnings are advisory
            # and deliberately do not fail the control.
            record["checks"].append(dict(check="no GitHub math rendering errors",
                                         passed="; 0 error," in result.stdout))
        else:
            record["checks"].extend(inspect_result(name, json.loads(result.stdout)))
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError,
            TypeError, StopIteration) as error:
        record["checks"].append(dict(check="execution and response contract", passed=False,
                                     error=f"{type(error).__name__}: {error}"))
    record["seconds"] = round(time.monotonic() - started, 3)
    record["passed"] = all(check["passed"] for check in record["checks"])
    write_json(case_dir / "checks.json", record)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=RUNS, help="run selected evidence cases")
    parser.add_argument("--output-dir", type=Path, help="new output directory; must not already exist")
    args = parser.parse_args(argv)
    if args.output_dir:
        directory = args.output_dir.resolve()
        try:
            directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            parser.error("--output-dir already exists; choose a new directory")
    else:
        parent = ROOT / "tmp" / "principle-reproduction"
        parent.mkdir(parents=True, exist_ok=True)
        # Inherit repository access permissions so reviewers can reopen evidence
        # from Windows sandboxed tools as well as from the shell that ran it.
        directory = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex)
        directory.mkdir()
    selected = list(dict.fromkeys(args.only or RUNS))
    manifest = dict(schema_version="principle-reproduction.v1", status="running",
                    started_utc=datetime.now(timezone.utc).isoformat(),
                    source=source_record(), selected=selected, results=[])
    write_json(directory / "manifest.json", manifest)
    print(f"Evidence directory: {directory}", flush=True)
    for name in selected:
        record = reproduce(name, directory)
        manifest["results"].append(record)
        write_json(directory / "manifest.json", manifest)
        print(f"{'PASS' if record['passed'] else 'FAIL'} {name} ({record['seconds']:.3f}s)", flush=True)
        for check in record["checks"]:
            if not check["passed"]:
                print("  " + json.dumps(check, sort_keys=True), flush=True)
    passed = sum(result["passed"] for result in manifest["results"])
    manifest.update(status="passed" if passed == len(selected) else "failed",
                    finished_utc=datetime.now(timezone.utc).isoformat(),
                    passed_count=passed, failed_count=len(selected) - passed)
    write_json(directory / "manifest.json", manifest)
    print(f"{passed}/{len(selected)} reproductions passed. Manifest: {directory / 'manifest.json'}")
    return 0 if manifest["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
