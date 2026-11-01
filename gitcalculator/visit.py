"""Visit a published web calculator the way a browser does, and check it.

``visit`` loads the page, the ledger, the blob bundle and a vendored Pyodide
from an address such as the GitHub Pages site, and checks that

- the page is a gitcalculator build, and the engine inlined in it hashes to
  the blob ids stamped beside it;
- the ledger and the bundle come from the same build as the page;
- every bundled blob hashes to its git id;
- a vendored Pyodide arrives whole, with its WebAssembly module served as
  ``application/wasm``.

When this clone has the commit the page was built from, the served engine is
compared with that commit's files and every bundled blob is looked up in the
clone's git objects, so a clean build is shown to be the repository, byte for
byte. With ``commit`` the page must be that build. A fresh deployment can take
minutes to reach every server, so ``visit_until`` retries.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable

from .history import BUNDLE_SCHEMA
from .provenance import ROOT, blob_id
from .site import LEDGER_SCHEMA, PYODIDE_FILES, PYODIDE_VERSION

STAMP = re.compile(r"window\.GITCALC_BUILD = (\{[^\n]*?\});</script>")
INLINE = re.compile(r"<script>\n(.*?)</script>", re.S)
MAGIC = {".wasm": (b"\0asm", "a WebAssembly module"), ".zip": (b"PK\x03\x04", "a zip archive")}
ENGINE = {"engine": "gitcalculator/web/engine.js", "modes": "gitcalculator/web/modes.js"}


def fetch(url: str, timeout: float = 60) -> tuple[int | None, str, bytes, str]:
    """``(status, media type, body, error)`` for one GET; never raises."""
    request = urllib.request.Request(url, headers={"User-Agent": "gitcalculator-visit", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers.get_content_type(), response.read(), ""
    except urllib.error.HTTPError as error:
        return error.code, "", b"", f"HTTP {error.code}"
    except (urllib.error.URLError, OSError) as error:
        return None, "", b"", str(getattr(error, "reason", error))


def _git(args: list[str], stdin: str | None = None) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=ROOT, input=stdin, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _commit(ref: str) -> str | None:
    """The full id of ``ref`` when this clone has it."""
    found = _git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    return found.strip() if found else None


def _git_blobs(ids: list[str]) -> set[str]:
    """The ids among ``ids`` that are blobs in this clone's object store."""
    listing = _git(["cat-file", "--batch-check"], "".join(f"{i}\n" for i in ids)) or ""
    return {fields[0] for fields in (line.split() for line in listing.splitlines()) if fields[1:2] == ["blob"]}


def _json(body: bytes | None, name: str, problems: list[str]) -> Any:
    if body is None:
        return None
    try:
        return json.loads(body)
    except ValueError as error:
        problems.append(f"{name}: not JSON ({error})")
        return None


def visit(url: str, *, commit: str | None = None) -> dict[str, Any]:
    """Load the calculator at ``url`` and check every file it loads."""
    base = url if url.endswith("/") else url + "/"
    nonce = uuid.uuid4().hex[:12]  # a query string no cache has seen, so the server itself answers
    files: list[dict[str, Any]] = []
    problems: list[str] = []

    def load(path: str, media: str | None = None) -> tuple[dict[str, Any], bytes | None]:
        name = path or "index.html"
        status, kind, body, error = fetch(f"{base}{path}?visit={nonce}")
        row = {"path": name, "status": status, "type": kind, "bytes": len(body), "notes": []}
        files.append(row)
        if status != 200:
            problems.append(f"{name}: {error or f'HTTP {status}'}")
            return row, None
        if media and kind != media:
            problems.append(f"{name}: served as {kind}, not {media}")
        return row, body

    def same_build(name: str, document: dict) -> None:
        theirs = (document.get("head") or {}).get("commit")
        if built and theirs != built:
            problems.append(f"{name}: from build {str(theirs)[:7]}, but the page is build {built[:7]}")

    page_row, page = load("", "text/html")
    stamp: dict[str, Any] = {}
    if page is not None:
        text = page.decode("utf-8", "replace")
        found = STAMP.search(text)
        try:
            stamp = json.loads(found.group(1)) if found else {}
        except ValueError:
            stamp = {}
        if not stamp:
            problems.append("index.html: no build stamp, so this is not a gitcalculator page")
        else:
            inlined = {blob_id(body.encode("utf-8")) for body in INLINE.findall(text)}
            wrong = [name for name in ENGINE if stamp.get(f"{name}_blob") not in inlined]
            problems += [f"index.html: the inlined {name}.js does not hash to its stamped blob id" for name in wrong]
            page_row["notes"].append(f"build {stamp.get('short')}"
                                     + ("" if wrong else "; engine.js and modes.js match their blob ids"))
    built = stamp.get("commit")
    if commit and stamp:
        wanted = _commit(commit) or commit
        if built != wanted and not (len(commit) >= 7 and str(built).startswith(commit)):
            problems.append(f"index.html: serving build {stamp.get('short')}, not {commit[:7]}")

    ledger_row, raw = load("ledger.json", "application/json")
    ledger = _json(raw, "ledger.json", problems)
    head: dict[str, Any] = {}
    if isinstance(ledger, dict) and ledger.get("schema") != LEDGER_SCHEMA:
        problems.append(f"ledger.json: schema {ledger.get('schema')!r}, not {LEDGER_SCHEMA}")
    elif isinstance(ledger, dict):
        same_build("ledger.json", ledger)
        head = ledger.get("head") or {}
        presets = ledger.get("presets") or {}
        recorded = [name for name, p in presets.items() if (p.get("receipt") or {}).get("id") and p.get("history")]
        if not presets or len(recorded) < len(presets):
            problems.append(f"ledger.json: {len(presets) - len(recorded)} of {len(presets)} presets lack a recorded "
                            "receipt or history")
        ledger_row["notes"].append(f"{len(recorded)} presets with recorded receipts and histories")

    blobs: dict[str, str] = {}
    bundle_row: dict[str, Any] = {}
    if isinstance(ledger, dict) and ledger.get("live_engine"):
        bundle_row, raw = load("bundle.json", "application/json")
        bundle = _json(raw, "bundle.json", problems)
        if isinstance(bundle, dict) and bundle.get("schema") != BUNDLE_SCHEMA:
            problems.append(f"bundle.json: schema {bundle.get('schema')!r}, not {BUNDLE_SCHEMA}")
        elif isinstance(bundle, dict):
            same_build("bundle.json", bundle)
            blobs = bundle.get("blobs") or {}
            forged = sorted(key for key, body in blobs.items() if blob_id(body.encode("utf-8")) != key)
            referenced = {b for state in bundle.get("states") or [] for b in (state.get("files") or {}).values()}
            referenced |= set(((bundle.get("calculator") or {}).get("files") or {}).values())
            referenced |= set((bundle.get("documents") or {}).values())
            missing = sorted(referenced - set(blobs))
            problems += [f"bundle.json: blob {key} does not hash to its id" for key in forged[:5]]
            if len(forged) > 5:
                problems.append(f"bundle.json: {len(forged) - 5} more blobs do not hash to their ids")
            if missing:
                problems.append(f"bundle.json: {len(missing)} referenced blobs are missing, such as {missing[0]}")
            bundle_row["notes"].append(f"{len(blobs) - len(forged)}/{len(blobs)} blobs hash to their git ids; "
                                       f"{len(bundle.get('states') or [])} code states, "
                                       f"{len(bundle.get('documents') or {})} documents")
            runtime = bundle.get("pyodide") or {}
            if runtime.get("index") == "./pyodide/":
                for name in PYODIDE_FILES:
                    row, body = load(f"pyodide/{name}", "application/wasm" if name.endswith(".wasm") else None)
                    suffix = name[name.rfind("."):]
                    if body is None:
                        continue
                    if not body:
                        problems.append(f"pyodide/{name}: empty")
                    elif suffix in MAGIC:
                        magic, kind = MAGIC[suffix]
                        if body.startswith(magic):
                            row["notes"].append(kind)
                        else:
                            problems.append(f"pyodide/{name}: not {kind}")
                    elif name == "pyodide-lock.json":
                        lock = _json(body, f"pyodide/{name}", problems)
                        version = ((lock if isinstance(lock, dict) else {}).get("info") or {}).get("version")
                        if version == PYODIDE_VERSION:
                            row["notes"].append(f"Pyodide {version}")
                        else:
                            problems.append(f"pyodide/{name}: Pyodide {version}, not {PYODIDE_VERSION}")
            elif runtime.get("index"):
                bundle_row["notes"].append(f"Pyodide {runtime.get('version')} loads from {runtime['index']}")

    # The build against git: a clean build's engine is its commit's, and its blobs are git objects.
    known = _commit(built) if built else None
    dirty = bool(head.get("dirty"))
    against_git = False
    if stamp and not known:
        page_row["notes"].append(f"commit {stamp.get('short')} is not in this clone, so the build was not compared with git")
    elif known:
        found = len(problems)
        if dirty:
            changed = len(head.get("dirty_paths") or [])
            text = f"built from {known[:7]} plus uncommitted changes to {changed} file(s)"
            if commit:
                problems.append(f"index.html: {text}")
            else:
                page_row["notes"].append(text)
        committed = {name: (_git(["rev-parse", f"{known}:{path}"]) or "").strip() for name, path in ENGINE.items()}
        differ = [name for name in ENGINE if committed[name] != stamp.get(f"{name}_blob")]
        if not differ:
            page_row["notes"].append(f"engine.js and modes.js are commit {known[:7]}'s")
        elif not dirty:
            problems += [f"index.html: the served {name}.js is not the one committed at {known[:7]}" for name in differ]
        if blobs:
            absent = sorted(set(blobs) - _git_blobs(sorted(blobs)))
            if not absent:
                bundle_row["notes"].append("every blob is an object in this repository")
            elif dirty:
                bundle_row["notes"].append(f"{len(absent)} blob(s) from the uncommitted changes are not in git")
            else:
                problems.append(f"bundle.json: {len(absent)} blob(s) are not objects in this repository, "
                                f"such as {absent[0]}")
        against_git = not dirty and len(problems) == found
    return {"url": base, "commit": built, "short": stamp.get("short"), "expected": commit,
            "checked_against_git": against_git and not problems, "files": files, "problems": problems,
            "ok": not problems}


def visit_until(url: str, *, commit: str | None = None, wait: float = 0.0, interval: float = 15.0,
                progress: Callable[[int, dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """``visit`` until every check passes or ``wait`` seconds run out."""
    deadline = time.monotonic() + max(wait, 0.0)
    attempts = 0
    while True:
        attempts += 1
        report = visit(url, commit=commit)
        report["attempts"] = attempts
        if report["ok"] or time.monotonic() + interval > deadline:
            return report
        if progress:
            progress(attempts, report)
        time.sleep(interval)


def _size(count: int) -> str:
    if count < 1024:
        return f"{count} B"
    return f"{count / 1024:.1f} KB" if count < 1024 ** 2 else f"{count / 1024 ** 2:.1f} MB"


def render(report: dict[str, Any]) -> str:
    attempts = report.get("attempts", 1)
    lines = [f"visited {report['url']}" + (f" ({attempts} attempts)" if attempts > 1 else "")]
    width = max([16] + [len(row["type"]) for row in report["files"]])
    for row in report["files"]:
        status = "---" if row["status"] is None else str(row["status"])
        lines.append(f"  {status:>3}  {row['path']:<26} {row['type']:<{width}} {_size(row['bytes']):>9}  "
                     f"{'; '.join(row['notes'])}".rstrip())
    lines += [f"  PROBLEM  {problem}" for problem in report["problems"]]
    if report["ok"]:
        lines.append(f"the calculator at this address is build {report['short']}, and every file it loads checks out"
                     + (", down to this repository's git objects" if report["checked_against_git"] else ""))
    else:
        lines.append(f"{len(report['problems'])} problem(s): the calculator at this address does not check out")
    return "\n".join(lines)
