"""Build the static web calculator.

The site is three files. ``index.html`` is the calculator. ``ledger.json``
holds recorded receipts and histories for the presets, so the page is complete
before any Python starts. ``bundle.json`` is a deduplicated store of git blobs:
every code state of ``categorical_polytope`` that had the backend, the
gitcalculator itself, and the documents it cites. In a browser that allows
WebAssembly, the page loads Pyodide, writes those blobs into its file system,
checks each against its git id, and runs the same Python as the command line.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .certify import LINKS
from .counter import REGISTRY, check_witnesses
from .history import export_bundle, replay
from .presets import PRESETS, preset_request
from .provenance import ROOT, blob_id, code_id, python_files
from .receipt import backend, calculate, counter_catalogue

WEB = Path(__file__).resolve().parent / "web"
PYODIDE_VERSION = "0.26.4"
PYODIDE_FILES = ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
</head>
<body>
{fragment}
</body>
</html>
"""


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def link_target(head: dict) -> tuple[str | None, list[str]]:
    """A ref the remote has, for links, and the paths that exist there.

    The built commit is used when a remote branch contains it; otherwise links
    fall back to its merge base with ``origin/main`` so they never 404.
    """
    commit = head.get("commit")
    if not commit:
        return None, []
    ref = commit if _git("branch", "-r", "--contains", commit) else _git("merge-base", commit, "origin/main")
    listing = _git("ls-tree", "-r", "--name-only", ref) if ref else None
    return ref, (listing.splitlines() if listing else [])


def cited_documents() -> list[str]:
    paths = {doc.split("#", 1)[0] for _, doc, _ in LINKS.values()}
    paths |= {src.split("#", 1)[0] for argument in REGISTRY for src in argument.sources}
    return sorted(p for p in paths if (ROOT / p).is_file())


def build(out: Path, *, pyodide: Path | None = None, fragment: bool = False, live: bool = True) -> Path:
    """Write the site to ``out``.

    ``pyodide`` vendors a local runtime instead of the CDN; ``fragment`` writes
    the page without its document skeleton, as a Claude artifact expects;
    ``live=False`` ships recorded receipts only, without the blob bundle.
    """
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    bundle = export_bundle()
    bundle["head_state"] = code_id(python_files("categorical_polytope"))
    bundle["documents"] = {}
    for path in cited_documents():
        data = (ROOT / path).read_bytes()
        blob = blob_id(data)
        bundle["documents"][path] = blob
        bundle["blobs"].setdefault(blob, data.decode("utf-8"))
    bundle["pyodide"] = {"version": PYODIDE_VERSION,
                         "index": "./pyodide/" if pyodide else f"https://cdn.jsdelivr.net/npm/pyodide@{PYODIDE_VERSION}/"}
    ref, linkable = link_target(bundle["head"])
    bundle["head"]["link_ref"] = ref
    if live:
        (out / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    remote_commits = (_git("rev-list", "--remotes") or "").split()
    ledger = {"schema": "gitcalculator.ledger.v1", "head": bundle["head"], "linkable": linkable,
              "remote_commits": remote_commits, "live_engine": live, "presets": {},
              "counterarguments": counter_catalogue(), "witnesses": check_witnesses(backend().handle)}
    for name, preset in PRESETS.items():
        receipt = calculate(preset_request(name))
        ledger["presets"][name] = {"title": preset["title"], "note": preset["note"], "request": preset["request"],
                                   "receipt": receipt, "history": replay(receipt["input"])}
    (out / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    page = (WEB / "index.html").read_text(encoding="utf-8")
    (out / "index.html").write_text(page if fragment else PAGE.format(fragment=page), encoding="utf-8")
    if pyodide and live:
        target = out / "pyodide"
        target.mkdir(exist_ok=True)
        for name in PYODIDE_FILES:
            shutil.copyfile(pyodide / name, target / name)
    return out
