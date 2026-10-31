"""Replay a calculation across the repository's history.

The answer to a question is a function of the input and of the code. Git
records every code state the repository has had, so the calculator can ask
each one. Commits are grouped by *code identity* (the blob ids of the package's
Python files): docs-only commits share a state and never need recomputing.

Each state is run in this process with its own copy of ``categorical_polytope``
swapped into ``sys.modules``. Three probes are recorded per state:

* ``backend`` - the public face-selection operation, as it answered then;
* ``curved``  - the V.22 operation, where it existed;
* ``core``    - the exact selection core judging the *same* exact edge data
  (computed once, at HEAD), so changes in the law itself are visible even
  where the numerical front end would have stopped earlier.

States come from ``git`` on a workstation or from a bundled blob store in the
browser, where the same code runs under Pyodide.
"""

from __future__ import annotations

import importlib
import io
import json
import subprocess
import sys
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from . import exact as X
from .certify import certify
from .provenance import ROOT, blob_id, code_id, git_available, git_state, python_files
from .receipt import backend, backend_signature, normalize

SCHEMA = "gitcalculator.history.v1"
BUNDLE_SCHEMA = "gitcalculator.snapshots.v1"
BACKEND_PATH = "categorical_polytope/adjudication/polyhedra/backend.py"
CORE_PATH = "categorical_polytope/face_selection.py"
PACKAGE = "categorical_polytope"


@dataclass
class CodeState:
    id: str
    files: dict[str, str]
    commits: list[dict[str, str]] = field(default_factory=list)

    @property
    def has_backend(self) -> bool:
        return BACKEND_PATH in self.files

    @property
    def has_core(self) -> bool:
        return CORE_PATH in self.files

    def describe(self) -> dict[str, Any]:
        return {"code_id": self.id, "first_commit": self.commits[0], "last_commit": self.commits[-1],
                "commit_count": len(self.commits), "has_backend": self.has_backend}


def _git(args: Sequence[str], root: Path, *, binary: bool = False):
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=60)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return completed.stdout if binary else completed.stdout.decode()


class GitSource:
    """Code states read from the local repository's history."""

    kind = "git"

    def __init__(self, root: Path = ROOT, rev: str = "HEAD", cache: Path | None = None):
        if not git_available(root):
            raise RuntimeError("git history is not available here")
        self.root, self.rev = root, rev
        self.cache = cache or root / "tmp" / "gitcalculator" / "snapshots"

    def states(self) -> list[CodeState]:
        log = _git(["log", "--reverse", "--format=%H%x09%h%x09%cI%x09%s", self.rev], self.root)
        states: dict[str, CodeState] = {}
        for line in log.splitlines():
            full, short, date, subject = line.split("\t", 3)
            listing = _git(["ls-tree", "-r", full, "--", PACKAGE], self.root)
            files = {}
            for entry in listing.splitlines():
                meta, path = entry.split("\t", 1)
                if path.endswith(".py"):
                    files[path] = meta.split()[2]
            identity = code_id(files)
            state = states.setdefault(identity, CodeState(identity, files))
            state.commits.append({"commit": full, "short": short, "date": date, "subject": subject})
        working = python_files(PACKAGE, self.root)
        if code_id(working) not in states:
            state = CodeState(code_id(working), working)
            state.commits.append({"commit": "working-tree", "short": "worktree", "date": "",
                                  "subject": "uncommitted changes in this checkout"})
            states[state.id] = state
        return list(states.values())

    def materialize(self, state: CodeState) -> Path:
        target = self.cache / state.id
        marker = target / ".complete"
        if marker.exists():
            return target
        target.mkdir(parents=True, exist_ok=True)
        commit = state.commits[0]["commit"]
        if commit == "working-tree":
            for path in state.files:
                destination = target / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((self.root / path).read_bytes())
        else:
            archive = _git(["archive", "--format=tar", commit, PACKAGE], self.root, binary=True)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                members = [m for m in tar.getmembers() if m.isfile() and m.name.endswith(".py")]
                for member in members:
                    destination = target / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(tar.extractfile(member).read())
        marker.write_text(state.id)
        return target

    def blob(self, blob: str) -> bytes:
        return _git(["cat-file", "-p", blob], self.root, binary=True)


class BundleSource:
    """Code states read from a bundled, deduplicated blob store (browser builds)."""

    kind = "bundle"

    def __init__(self, bundle: Mapping[str, Any], base: Path):
        if bundle.get("schema") != BUNDLE_SCHEMA:
            raise ValueError("not a gitcalculator snapshot bundle")
        self.bundle, self.base = bundle, base

    def states(self) -> list[CodeState]:
        return [CodeState(s["code_id"], dict(s["files"]), list(s["commits"])) for s in self.bundle["states"]]

    def materialize(self, state: CodeState) -> Path:
        target = self.base / state.id
        if (target / ".complete").exists():
            return target
        for path, blob in state.files.items():
            data = self.bundle["blobs"][blob].encode()
            if blob_id(data) != blob:
                raise ValueError(f"bundled blob {blob} does not hash to its id")
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (target / ".complete").write_text(state.id)
        return target


@contextmanager
def code_state(path: Path) -> Iterator[None]:
    """Import ``categorical_polytope`` from ``path`` for the duration of the block."""
    def ours(name: str) -> bool:
        return name == PACKAGE or name.startswith(PACKAGE + ".")

    saved = {name: module for name, module in sys.modules.items() if ours(name)}
    for name in saved:
        del sys.modules[name]
    sys.path.insert(0, str(path))
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in [n for n in sys.modules if ours(n)]:
            del sys.modules[name]
        sys.modules.update(saved)
        sys.path.remove(str(path))
        importlib.invalidate_caches()


def _edge_data(inputs: Mapping[str, Any]):
    """HEAD's exact local model, handed unchanged to every historical core."""
    response = backend().handle(dict(inputs))
    certificate, model = certify(inputs, response)
    statuses = {link["id"]: link["status"] for link in certificate.get("links", [])}
    assumptions_hold = all(statuses.get(key) == "exact" for key in ("H0", "H1", "H2"))
    if model is None or not model.principal or not model.gain:
        return None, model, assumptions_hold
    return {
        "vertex": [float(v) for v in model.vertex],
        "generators": {a: [float(u) for u in model.generators[a]] for a in model.axes},
        "principal": {a: (beta, coefficient) for a, (beta, coefficient) in model.principal.items()},
        "gain": [(coefficient, dict(zip(model.axes, signature))) for signature, coefficient in sorted(model.gain.items())],
    }, model, assumptions_hold


def _claims(answer: Mapping[str, Any], assumptions_hold: bool) -> list[tuple[str, str]]:
    """Licensed exponents a state asserted, as ``(probe, gamma)`` pairs.

    The core runs with the analytic hypotheses assumed, so its license is a
    claim only when HEAD's certificate shows those assumptions hold.
    """
    claims = []
    if (answer.get("backend") or {}).get("licensed") and answer["backend"].get("gamma"):
        claims.append(("backend", answer["backend"]["gamma"]))
    if (answer.get("curved") or {}).get("status") == "licensed" and answer["curved"].get("gamma"):
        claims.append(("curved", answer["curved"]["gamma"]))
    if assumptions_hold and (answer.get("core") or {}).get("licensed") and answer["core"].get("gamma"):
        claims.append(("core", answer["core"]["gamma"]))
    return claims


def _probe(inputs: Mapping[str, Any], edge: Mapping[str, Any] | None, state: CodeState) -> dict[str, Any]:
    answer: dict[str, Any] = {}
    if state.has_backend:
        try:
            module = importlib.import_module("categorical_polytope.adjudication.polyhedra.backend")
            engine = module.FaceSelectionBackend()
            answer["backend"] = backend_signature(engine.handle(dict(inputs)))
            curved = engine.handle({"operation": "curved_reduction", **{k: inputs[k] for k in ("system", "base", "perturbation")}})
            if curved.get("schema_version", "").startswith("curved-reduction"):
                scaling = curved.get("scaling") or {}
                answer["curved"] = {"status": curved.get("status"), "gamma": scaling.get("response_exponent_exact"),
                                    "coefficient": (scaling.get("leading_coefficient") or {}).get("exact")}
            else:
                answer["curved"] = {"status": "unavailable"}
        except Exception as exc:  # an old state may simply fail; that is a recorded answer too
            answer["backend"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    else:
        answer["backend"] = {"status": "unavailable"}
    if state.has_core and edge is not None:
        try:
            fs = importlib.import_module("categorical_polytope.face_selection")
            assumed = fs.HypothesisStatus.ASSUMED
            problem = fs.FaceSelectionProblem(
                chart=fs.EdgeCoordinateChart(vertex=tuple(edge["vertex"]),
                                             generators={a: tuple(u) for a, u in edge["generators"].items()}),
                principal=fs.WeightedPrincipalPart({a: fs.BasePower(float(c), b) for a, (b, c) in edge["principal"].items()}),
                perturbation=fs.PolynomialPerturbation(tuple(fs.PerturbationMonomial(c, p) for c, p in edge["gain"])),
                hypotheses=fs.LawHypotheses(assumed, assumed, assumed),
            )
            result = problem.select()
            answer["core"] = {
                "q_star": X.label(result.q_star), "gamma": X.label(result.response_exponent),
                "licensed": result.theorem_licensed,
                "blockers": sorted({b.split(" on face")[0] for b in result.scope_blockers}),
            }
        except Exception as exc:
            answer["core"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    return answer


def _summary(answer: Mapping[str, Any], assumptions_hold: bool = True) -> str:
    b, c, k = answer.get("backend") or {}, answer.get("curved") or {}, answer.get("core") or {}
    if b.get("status") == "unavailable":
        return "no face-selection backend yet"
    parts = [f"backend {b.get('status')}" + (f" γ={b['gamma']}" if b.get("gamma") else "")
             + (f" blocked by {', '.join(b['blockers'])}" if b.get("blockers") else "")]
    if c.get("status") not in (None, "unavailable"):
        parts.append(f"V.22 {c['status']}" + (f" γ={c['gamma']}" if c.get("gamma") else ""))
    if "licensed" in k:
        parts.append(f"core γ={k.get('gamma')} " + ("licensed" if k["licensed"] else "withheld")
                     + ("" if assumptions_hold else " (on assumed hypotheses that fail here)"))
    return " · ".join(parts)


def _changes(before: Mapping[str, Any], after: Mapping[str, Any], assumptions_hold: bool) -> list[str]:
    if (before.get("backend") or {}).get("status") == "unavailable":
        if (after.get("backend") or {}).get("status") == "unavailable":
            return []
        return [f"first answer: {_summary(after, assumptions_hold)}"]
    lines = []
    for probe in ("backend", "curved", "core"):
        old, new = before.get(probe) or {}, after.get(probe) or {}
        for key in sorted(set(old) | set(new)):
            if old.get(key) != new.get(key):
                lines.append(f"{probe}.{key}: {json.dumps(old.get(key))} → {json.dumps(new.get(key))}")
    return lines


def replay(request: Mapping[str, Any], source=None, *, audit: bool = True) -> dict[str, Any]:
    """Answer ``request`` at every code state and report where the answer changed.

    With ``audit``, every exponent a state *licensed* is checked against HEAD's
    certified lower bounds, so the timeline shows which past answers were wrong.
    """
    from .measure import measure  # local: measure imports certify, which this module imports

    inputs = normalize(request)
    source = source or GitSource()
    states = source.states()
    edge, model, assumptions_hold = _edge_data(inputs)
    runs = []
    for state in states:
        if not (state.has_backend or state.has_core):
            answer = {"backend": {"status": "unavailable"}}
        else:
            with code_state(source.materialize(state)):
                answer = _probe(inputs, edge, state)
        runs.append({**state.describe(), "answer": answer, "summary": _summary(answer, assumptions_hold)})
    changes = []
    for previous, current in zip(runs, runs[1:]):
        lines = _changes(previous["answer"], current["answer"], assumptions_hold)
        if lines:
            changes.append({"code_id": current["code_id"], "at": current["first_commit"], "lines": lines})
    if audit:
        claimed = sorted({gamma for run in runs for _, gamma in _claims(run["answer"], assumptions_hold)},
                         key=Fraction)
        evidence = measure(model, [{"id": f"claim:{g}", "gamma": Fraction(g)} for g in claimed], budget="quick")
        verdicts = {v["id"]: v for v in evidence.get("verdicts", [])}
        for run in runs:
            run["audit"] = [{"probe": probe, "gamma": gamma, "verdict": verdicts.get(f"claim:{gamma}", {}).get("verdict"),
                             "detail": verdicts.get(f"claim:{gamma}", {}).get("detail")}
                            for probe, gamma in _claims(run["answer"], assumptions_hold)]
    answered = [r for r in runs if r["answer"].get("backend", {}).get("status") not in {"unavailable", None}]
    return {
        "schema": SCHEMA,
        "input": inputs,
        "source": source.kind,
        "head": git_state() if source.kind == "git" else source.bundle.get("head"),
        "state_count": len(runs),
        "answered_state_count": len(answered),
        "commit_count": sum(r["commit_count"] for r in runs),
        "assumptions_hold": assumptions_hold,
        "states": runs,
        "changes": changes,
    }


def render_history(history: Mapping[str, Any]) -> str:
    lines = [f"history of {json.dumps(history['input'], ensure_ascii=False)}",
             f"{history['commit_count']} commits, {history['state_count']} code states "
             f"({history['answered_state_count']} with the backend), source: {history['source']}", ""]
    for run in history["states"]:
        first, last = run["first_commit"], run["last_commit"]
        span = first["short"] if run["commit_count"] == 1 else f"{first['short']}..{last['short']}"
        wrong = [a for a in run.get("audit", []) if a["verdict"] == "contradicted"]
        flag = ("   ✗ licensed γ=" + ", ".join(a["gamma"] for a in wrong) + " is contradicted") if wrong else ""
        lines.append(f"  {run['code_id']}  {span:<17} {first['date'][:10]}  {run['summary']}{flag}")
    if history["changes"]:
        lines.append("")
        lines.append("where the answer changed")
        for change in history["changes"]:
            lines.append(f"  {change['at']['short']} {change['at']['date'][:10]}  {change['at']['subject'][:70]}")
            lines.extend(f"      {line}" for line in change["lines"])
    else:
        lines.append("\nthe answer never changed")
    return "\n".join(lines)


def export_bundle(source: GitSource | None = None) -> dict[str, Any]:
    """A deduplicated blob store of every code state that has the backend."""
    source = source or GitSource()
    states = [s for s in source.states() if s.has_backend]
    blobs: dict[str, str] = {}
    for state in states:
        for path, blob in state.files.items():
            if blob not in blobs:
                data = (source.root / path).read_bytes() if state.commits[0]["commit"] == "working-tree" else source.blob(blob)
                blobs[blob] = data.decode("utf-8")
    calculator = python_files("gitcalculator", source.root)
    for path, blob in calculator.items():
        blobs.setdefault(blob, (source.root / path).read_text(encoding="utf-8"))
    return {
        "schema": BUNDLE_SCHEMA,
        "head": git_state(source.root),
        "states": [{"code_id": s.id, "files": s.files, "commits": s.commits} for s in states],
        "calculator": {"files": calculator},
        "blobs": blobs,
    }
