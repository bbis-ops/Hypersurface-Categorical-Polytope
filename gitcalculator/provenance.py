"""Git-native provenance: which exact bytes produced a calculation.

Every source file is identified by its git blob id, computed here directly
(``sha1("blob <size>\\0" + content)``), so a receipt can be checked with
``git cat-file -p <blob>`` without trusting this module or having git
installed. The browser build uses the same function under Pyodide.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("categorical_polytope", "gitcalculator")


def blob_id(data: bytes) -> str:
    """The git object id of ``data`` stored as a blob.

    Text files are normalized from CRLF to LF first, matching the repository's
    ``* text=auto`` attribute, so a Windows checkout reports the same ids.
    """
    if b"\0" not in data:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fingerprint(files: Mapping[str, str], prefix: str) -> str:
    """A short identity for a set of ``path -> blob`` entries (order-free)."""
    lines = "".join(f"{path} {blob}\n" for path, blob in sorted(files.items()))
    return f"{prefix}-" + hashlib.sha1(lines.encode()).hexdigest()[:12]


def python_files(package: str, root: Path = ROOT) -> dict[str, str]:
    """``path -> blob id`` for every ``.py`` file of a package on disk."""
    base = root / package
    return {
        path.relative_to(root).as_posix(): blob_id(path.read_bytes())
        for path in sorted(base.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def code_id(files: Mapping[str, str]) -> str:
    """Identity of a ``categorical_polytope`` code state (python files only)."""
    return fingerprint({p: b for p, b in files.items() if p.startswith("categorical_polytope/")}, "code")


def loaded_sources(root: Path = ROOT, packages: Iterable[str] = PACKAGES) -> dict[str, str]:
    """Blob ids of the modules this process actually imported from ``root``."""
    records: dict[str, str] = {}
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] not in packages:
            continue
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.exists():
            records[relative] = blob_id(path.read_bytes())
    return dict(sorted(records.items()))


def document_ids(paths: Iterable[str], root: Path = ROOT) -> dict[str, str | None]:
    """Blob ids of cited documents, so a cited statement is pinned too."""
    result = {}
    for relative in sorted(set(paths)):
        path = root / relative.split("#", 1)[0]
        result[relative.split("#", 1)[0]] = blob_id(path.read_bytes()) if path.is_file() else None
    return result


def _git(args: list[str], root: Path = ROOT) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def git_available(root: Path = ROOT) -> bool:
    return sys.platform != "emscripten" and _git(["rev-parse", "--git-dir"], root) is not None


def git_state(root: Path = ROOT) -> dict:
    """Commit, branch and working-tree state, or the bundled state in a browser."""
    bundled = BUNDLED_STATE.get("git")
    if bundled is not None:
        return dict(bundled)
    if not git_available(root):
        return {"commit": None, "short": None, "branch": None, "dirty": None,
                "dirty_paths": [], "remote": None, "source": "unavailable"}
    status = _git(["status", "--porcelain", "--", *PACKAGES], root) or ""
    dirty_paths = sorted({line[3:].strip() for line in status.splitlines() if line.strip()})
    remote = _git(["remote", "get-url", "origin"], root)
    return {
        "commit": _git(["rev-parse", "HEAD"], root),
        "short": _git(["rev-parse", "--short", "HEAD"], root),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], root),
        "date": _git(["log", "-1", "--format=%cI"], root),
        "dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
        "remote": remote,
        "source": "git",
    }


def runtime() -> dict:
    engine = "pyodide" if sys.platform == "emscripten" else platform.python_implementation().lower()
    return {"engine": engine, "python": platform.python_version()}


# A browser build records the commit it was built from here; see ``site.py``.
BUNDLED_STATE: dict = {}


def provenance(cited_documents: Iterable[str] = ()) -> dict:
    """The full provenance block of a receipt."""
    sources = loaded_sources()
    package_files = python_files("categorical_polytope")
    calculator_files = python_files("gitcalculator")
    return {
        "git": git_state(),
        "code_id": code_id(package_files),
        "calculator_id": fingerprint(calculator_files, "calc"),
        "sources": sources,
        "documents": document_ids(cited_documents),
        "runtime": runtime(),
        "verify": "git cat-file -p <blob> prints the exact bytes of any listed file",
    }
