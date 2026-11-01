"""Proof sheets: one calculation as GitHub Markdown.

A sheet states the answer and its formula, the input, the exact certificate
clause by clause with each clause linked to its theorem at a fixed commit, the
alternatives and the measurement, the counter-arguments that bear on the
input, and how to open or reproduce the calculation. The mathematics follows
the rules of ``experiments/ghmath.py``, so a sheet pasted into an issue, a pull
request or a discussion renders as written.

``gitcalculator/web/modes.js`` renders the same sheet in the browser; given the
same receipt, the two produce the same text (tests/test_gitcalculator.py).
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

VERDICTS = {"proved": "proved", "proved-v22": "proved by V.22", "licensed": "licensed",
            "unlicensed": "not licensed", "refused": "refused", "contradicted": "contradicted"}
# Brackets stay bare: a backslash before a bracket reads as a LaTeX display
# delimiter, and no sheet defines link references for "[...]" to resolve to.
_SPECIAL = re.compile(r"([\\`*_<>|$~])")
_GITHUB = re.compile(r"^(?:https://github\.com/|git@github\.com:)([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")
_FORM_SAFE = frozenset(b"*-._0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


def text(value: Any) -> str:
    """Plain text with Markdown's special characters escaped."""
    return _SPECIAL.sub(r"\\\1", " ".join(str(value).split()))


def code(value: Any) -> str:
    """An inline code span, safe inside a table cell."""
    body = str(value).replace("|", "\\|")
    fence = "`" * (max((len(run) for run in re.findall(r"`+", body)), default=0) + 1)
    pad = " " if body.startswith("`") or body.endswith("`") else ""
    return f"{fence}{pad}{body}{pad}{fence}"


def tex(value: Any) -> str:
    """A rational such as ``4/3`` or ``-1/2`` as TeX."""
    body = str(value).strip()
    sign, body = ("-", body[1:]) if body.startswith("-") else ("", body)
    if "/" in body:
        p, q = body.split("/", 1)
        return f"{sign}\\tfrac{{{p}}}{{{q}}}"
    return sign + body


def form_encode(pairs: Iterable[tuple[str, str]]) -> str:
    """``application/x-www-form-urlencoded``, byte for byte as a browser's URLSearchParams writes it."""
    def one(value: str) -> str:
        return "".join(chr(b) if b in _FORM_SAFE else "+" if b == 0x20 else f"%{b:02X}" for b in value.encode("utf-8"))
    return "&".join(f"{one(k)}={one(v)}" for k, v in pairs)


def shell(value: Any) -> str:
    return "'" + str(value).replace("'", "'\\''") + "'"


def number(value: Any) -> str:
    """A float the way JavaScript's String() writes it, for the common cases."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def github_repository(remote: str | None) -> str | None:
    found = _GITHUB.match(remote or "")
    return f"https://github.com/{found.group(1)}/{found.group(2)}" if found else None


def pages_url(repository: str | None) -> str | None:
    found = _GITHUB.match(repository or "")
    return f"https://{found.group(1).lower()}.github.io/{found.group(2)}/" if found else None


def formula(answer: Mapping[str, Any]) -> str | None:
    """The answer as one line of display mathematics, when it has one."""
    gamma, q = answer.get("gamma"), answer.get("q_star")
    coefficient = (answer.get("coefficient") or {}).get("exact")
    if answer.get("certificate_status") == "zero_response":
        return "\\Delta(s) = 0 \\quad \\text{for all sufficiently small } s \\gt 0"
    if answer.get("verdict") == "proved-v22" and gamma:
        return f"\\Delta(s) \\sim {tex(coefficient) if coefficient else 'C'}\\, s^{{{gamma}}}"
    if gamma and q:
        return (f"\\Delta(s) = \\Theta\\big(s^{{\\gamma}}\\big), \\quad \\gamma = \\frac{{1}}{{1 - q^\\ast}}"
                f" = \\frac{{1}}{{1 - {tex(q)}}} = {tex(gamma)}")
    return None


def _calculation(request: Mapping[str, Any]) -> list[tuple[str, str]]:
    pairs = [(key, str(request[key])) for key in ("system", "base", "perturbation") if request.get(key)]
    if request.get("observed_exponent") is not None:
        pairs.append(("observed", number(request["observed_exponent"])))
    return pairs


def command(request: Mapping[str, Any]) -> str:
    """The command line that reproduces the calculation."""
    flags = {"system": "--system", "base": "--base", "perturbation": "--perturbation", "observed": "--observed"}
    return "python -m gitcalculator calc " + " ".join(f"{flags[k]} {shell(v)}" for k, v in _calculation(request))


def link(request: Mapping[str, Any], calculator: str) -> str:
    """A link that opens the calculation in the web calculator at ``calculator``."""
    return f"{calculator}?{form_encode(_calculation(request))}#solve"


def sheet(receipt: Mapping[str, Any], *, repository: str | None = None, ref: str | None = None,
          calculator: str | None = None, linkable: Iterable[str] | None = None) -> str:
    """The receipt as GitHub Markdown.

    ``repository`` (an ``https://github.com/OWNER/REPO`` URL) and ``ref`` pin the
    links to the theorem documents; only paths in ``linkable`` are linked when it
    is given. ``calculator`` is the web calculator's address.
    """
    answer, request = receipt["answer"], receipt["input"]
    git = (receipt.get("provenance") or {}).get("git") or {}
    repository = repository or github_repository(git.get("remote"))
    ref = ref or git.get("commit")
    calculator = calculator or pages_url(repository)
    files = None if linkable is None else set(linkable)

    def doc(label: str, path: str) -> str:
        file, _, anchor = path.partition("#")
        if not repository or not ref or (files is not None and file not in files):
            return text(label)
        label = text(label).replace("[", "(").replace("]", ")")
        return f"[{label}]({repository}/blob/{ref}/{file}{'#' + anchor if anchor else ''})"

    out = [f"### {text(answer['headline'])} · {VERDICTS.get(answer['verdict'], text(answer['verdict']))}", ""]
    if (math := formula(answer)) is not None:
        out += ["```math", math, "```", ""]
    out += [text(answer["meaning"]), ""]

    out += ["| Input | |", "| :--- | :--- |",
            f"| Polyhedron $Ax \\le b$ | {code(request['system'])} |",
            f"| Base objective $F$ | {code(request['base'])} |",
            f"| Perturbation $G$ | {code(request['perturbation'])} |"]
    if request.get("observed_exponent") is not None:
        out.append(f"| Observed exponent | {code(number(request['observed_exponent']))} |")
    out.append("")

    certificate = receipt.get("certificate") or {}
    out += [f"#### Exact certificate: {text(str(certificate.get('status', '—')).replace('_', ' '))}", "",
            "| Clause | Status | What was checked |", "| :--- | :--- | :--- |"]
    out += [f"| {doc(l['clause'], l['doc'])} | {text(l['status'].replace('_', ' '))} | {text(l.get('detail') or '')} |"
            for l in certificate.get("links") or []]
    out.append("")

    alternatives = receipt.get("alternatives") or {}
    curved, ambient = alternatives.get("curved_reduction"), alternatives.get("ambient_axes")
    rows = []
    if curved:
        if curved.get("status") == "licensed":
            found = f"licensed: $\\gamma = {tex(curved['gamma'])}$" + (f", $C = {tex(curved['coefficient'])}$"
                                                                      if curved.get("coefficient") else "")
        else:
            found = text(str(curved.get("status", "")).replace("_", " ")) + (
                f": {text(curved['blockers'][0])}" if curved.get("blockers") else "")
        rows.append(f"| V.22 curved reduction | {found} |")
    if ambient:
        guess = f"$\\gamma = {tex(ambient['gamma'])}$" if ambient.get("gamma") else "no exponent"
        rows.append(f"| Ambient axes, ignoring the edge chart | {guess} |")
    if rows:
        out += ["#### Alternatives", "", "| Reading | Result |", "| :--- | :--- |", *rows, ""]

    measurement = receipt.get("measurement") or {}
    verdicts = measurement.get("verdicts") or []
    if measurement.get("status") == "complete" and (verdicts or measurement.get("measured_exponent") is not None):
        exponent, scales = measurement.get("measured_exponent"), measurement.get("series_length")
        scales = len(measurement.get("rows") or []) if scales is None else scales
        out += ["#### Measurement", "",
                f"Certified lower bounds $\\Delta(s) \\ge L(s)$ at {scales} "
                f"scales, each witnessed by a point of $P$ checked in exact arithmetic"
                + (f"; measured exponent {text(number(exponent))}." if exponent is not None else "."), ""]
        if verdicts:
            out += ["| Prediction | $\\gamma$ | Verdict |", "| :--- | :--- | :--- |"]
            for v in verdicts:
                predicted = f"${tex(v['gamma'])}$" if v.get("gamma") else "—"
                out.append(f"| {text(v['label'])} | {predicted} | {text(v['verdict'])} |")
            out.append("")

    counters = receipt.get("counterarguments") or []
    bearing = [c for c in counters if c.get("effect") != "clear"]
    if counters:
        out += ["#### Counter-arguments", ""]
        if bearing:
            out += ["| Counter-argument | Effect | Here |", "| :--- | :--- | :--- |"]
            out += [f"| {text(c['title'])} | {text(c['effect'])} | {text(c.get('detail') or '')} |" for c in bearing]
            out.append("")
        clear = len(counters) - len(bearing)
        if clear:
            out += [f"{clear} other counter-argument{'s' if clear != 1 else ''} do{'es' if clear == 1 else ''} not apply to this input.", ""]

    provenance = receipt.get("provenance") or {}
    engine = (f"exact JS engine {code(receipt['engine'])}" if receipt.get("engine") else
              f"Python {code(provenance.get('code_id') or '—')} · {code(provenance.get('calculator_id') or '—')}")
    commit = git.get("commit")
    short = git.get("short") or (commit[:7] if commit else "—")
    # The commit is linked only where the documents are pinned to it, so the link resolves.
    pinned = f"[{code(short)}]({repository}/commit/{commit})" if repository and commit and ref == commit else code(short)
    out += [f"<sub>Receipt {code(receipt.get('id') or '—')} · {engine} · commit {pinned}</sub>", ""]
    if calculator:
        out += [f"[Open this calculation in the gitcalculator]({link(request, calculator)}). Reproduce it:", ""]
    else:
        out += ["Reproduce it:", ""]
    out += ["```bash", command(request), "```", ""]
    return "\n".join(out)
