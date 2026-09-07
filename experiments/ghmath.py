#!/usr/bin/env python3
"""ghmath - publication control for GitHub-rendered mathematics in Markdown.

GitHub does not render LaTeX the way a local KaTeX or pdflatex build does. Its
Markdown pass runs *before* the math renderer and rewrites some characters; its
KaTeX instance then refuses a set of macros outright. Both failures are silent
in local preview and visible only once the file is on github.com.

Every rule below was extracted from a real fix commit, not from documentation.
Run --list-rules to see the catalogue with provenance.

Scope: Markdown only. LaTeX sources (.tex) are compiled by pdflatex and follow
the opposite conventions -- notably `\\\\` is correct there and wrong here - so
this tool never touches them.

Usage:
    python ghmath.py                 # scan ./**/*.md, exit 1 on findings
    python ghmath.py docs README.md  # scan specific paths
    python ghmath.py --fix           # apply the auto-fixable rules in place
    python ghmath.py --list-rules    # print the bug catalogue
    python ghmath.py --json          # machine-readable findings

Stdlib only. Copy this single file into any repository.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

__version__ = "1.0.0"

ERROR = "error"   # known to render wrongly on GitHub
WARN = "warn"     # context-dependent; a human should look


class Rule:
    def __init__(self, rid, severity, since, why, detect, fix=None):
        self.id = rid
        self.severity = severity
        self.since = since
        self.why = why
        self._detect = detect
        self._fix = fix

    @property
    def fixable(self):
        return self._fix is not None

    def detect(self, body):
        return self._detect(body)

    def fix(self, body):
        return self._fix(body) if self._fix else body


def _find(pattern):
    rx = re.compile(pattern)
    return lambda body: [m.group(0) for m in rx.finditer(body)]


def _contains(*needles):
    return lambda body: [n for n in needles if n in body]


def _sub(pattern, repl):
    rx = re.compile(pattern)
    return lambda body: rx.sub(repl, body)


def _sub_macro(pattern, macro):
    """Replace pattern with a control word, guarding against name capture.

    A TeX control word runs to the next non-letter, so a naive `\\{` -> `\\lbrace`
    turns `\\{x` into `\\lbracex`, an undefined macro. Emit a separating space
    only when the following character is a letter, which keeps diffs minimal.
    """
    rx = re.compile(pattern)

    def repl(m):
        nxt = m.string[m.end():m.end() + 1]
        return macro + (" " if nxt.isalpha() else "")

    return lambda body: rx.sub(repl, body)


def _chain(*fixers):
    def run(body):
        for f in fixers:
            body = f(body)
        return body
    return run


def _angle_repl(m):
    return "\\lt " if m.group(1) == "<" else "\\gt "


# Order matters: operatorname is repaired before the literal-asterisk rule, so
# that \operatorname* does not first become \operatorname\ast.
RULES = [
    Rule(
        "banned-macro", ERROR, "2681481, d8813b4",
        "GitHub's KaTeX refuses these outright: 'The following macros are not "
        "allowed'. \\operatorname is rejected in both its plain and starred "
        "forms; \\mathrm is the supported replacement.",
        _contains("\\operatorname", "\\gdef", "\\newcommand", "\\htmlClass",
                  "\\htmlId", "\\htmlStyle", "\\includegraphics", "\\url"),
        _chain(_sub(r"\\operatorname\*\{", "\\\\mathrm{"),
               _sub(r"\\operatorname\{", "\\\\mathrm{")),
    ),
    Rule(
        "left-right-brace", ERROR, "f0085e9",
        "GitHub rejects \\left/\\right wrapped around \\lbrace/\\rbrace. Use "
        "the bare \\lbrace and \\rbrace.",
        _find(r"\\left\\lbrace|\\right\\rbrace|\\left\\\{|\\right\\\}"),
        _chain(_sub_macro(r"\\left\\lbrace", "\\lbrace"),
               _sub_macro(r"\\right\\rbrace", "\\rbrace"),
               _sub_macro(r"\\left\\\{", "\\lbrace"),
               _sub_macro(r"\\right\\\}", "\\rbrace")),
    ),
    Rule(
        "escaped-brace", ERROR, "602f9e1, f221a5f",
        "The Markdown pass eats the backslash in \\{ and \\}, leaving a bare "
        "brace that KaTeX then reads as a group delimiter. Use \\lbrace and "
        "\\rbrace.",
        _find(r"(?<!\\)\\\{|(?<!\\)\\\}"),
        _chain(_sub_macro(r"(?<!\\)\\\{", "\\lbrace"),
               _sub_macro(r"(?<!\\)\\\}", "\\rbrace")),
    ),
    Rule(
        "unknown-spacing", ERROR, "a0f5d89",
        "GitHub's KaTeX build does not know these spacing macros. \\quad and "
        "\\, are safe.",
        _contains("\\thickspace", "\\medspace", "\\thinspace", "\\negthinspace"),
        _chain(_sub_macro(r"\\thickspace", "\\quad"),
               _sub_macro(r"\\medspace", "\\quad"),
               _sub_macro(r"\\thinspace", "\\,"),
               _sub_macro(r"\\negthinspace", "\\!")),
    ),
    Rule(
        "literal-asterisk", ERROR, "8c4c08c, 7fb893b",
        "A literal * inside math is consumed by Markdown emphasis before the "
        "renderer sees it. Use \\ast.",
        _find(r"(?<!\\operatorname)\*"),
        _sub_macro(r"\*", "\\ast"),
    ),
    Rule(
        "raw-angle", ERROR, "5f19e14",
        "Bare < and > let GitHub inject alignment characters into the math. "
        "Inside a table cell this also breaks the row. Use \\lt and \\gt.",
        _find(r"(?<!\\)[<>]"),
        _sub(r"(?<!\\)([<>])", _angle_repl),
    ),
    Rule(
        "tag", ERROR, "d8813b4",
        "\\tag does not render. Number the equation in surrounding prose "
        "instead.",
        _contains("\\tag"),
        None,
    ),
    Rule(
        "double-backslash-newline", WARN, "7fb893b, f221a5f",
        "A \\\\ line break in display math can be swallowed by GitHub's "
        "backslash escaping, collapsing the rows. The hardened documents in "
        "this project use \\cr instead. Context-dependent, so review by hand.",
        _find(r"\\\\(\[[^\]]*\])?\s*(?=\n|$)"),
        None,
    ),
]

RULES_BY_ID = {r.id: r for r in RULES}

_FENCE = re.compile(r"^[ \t]*(```+|~~~+)[ \t]*([^\n`]*)\n(.*?)^[ \t]*\1[ \t]*$",
                    re.S | re.M)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE_MATH = re.compile(r"(?<![\$\\])\$([^\$\n]+?)(?<!\\)\$(?!\$)")
# GitHub does not treat these as math, but authors write them and the content
# inside still needs checking, so they are recognised as spans.
_LATEX_DISPLAY = re.compile(r"\\\[(.+?)\\\]", re.S)
_LATEX_INLINE = re.compile(r"\\\((.+?)\\\)", re.S)


def _blank(text, start, end):
    """Replace a slice with spaces, preserving newlines so offsets stay valid."""
    chunk = text[start:end]
    return "".join(c if c == "\n" else " " for c in chunk)


def math_spans(text):
    """Yield (start, end) of every math body GitHub will hand to KaTeX.

    ```math fences are math. All other fenced blocks and inline code spans are
    masked out first so their contents are never mistaken for math.
    """
    spans = []
    masked = list(text)

    def blank_range(a, b):
        for i in range(a, b):
            if masked[i] != "\n":
                masked[i] = " "

    for m in _FENCE.finditer(text):
        info = (m.group(2) or "").strip().lower()
        if info == "math":
            spans.append((m.start(3), m.end(3)))
        blank_range(m.start(), m.end())

    masked = "".join(masked)
    masked = _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), masked)

    for rx in (_LATEX_DISPLAY, _LATEX_INLINE, _DISPLAY):
        for m in rx.finditer(masked):
            spans.append((m.start(1), m.end(1)))
        masked = rx.sub(lambda m: _blank(m.group(0), 0, len(m.group(0))), masked)

    for m in _INLINE_MATH.finditer(masked):
        spans.append((m.start(1), m.end(1)))

    return sorted(spans)


def _outside_code(text):
    """The document with fenced blocks and inline code blanked out."""
    masked = _FENCE.sub(lambda m: _blank(m.group(0), 0, len(m.group(0))), text)
    return _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), masked)


_DELIMS = re.compile(r"\\[\[\]()]")

DOC_RULES = [
    Rule(
        "latex-delimiters", ERROR, "FORMAL_AMBIENT_FACE_TRANSPORT.md",
        "GitHub Markdown recognises only $...$, $$...$$ and ```math fences. "
        "The LaTeX delimiters \\[ \\] \\( \\) are not math to GitHub, so the "
        "formula renders as literal text rather than as mathematics. This is "
        "silent: no error appears, the page is simply wrong.",
        lambda text: _DELIMS.findall(_outside_code(text)),
        None,  # applied by fix_document, which must not touch code blocks
    ),
    Rule(
        "indented-display-math", ERROR, "FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md",
        "A $$ block whose delimiters are indented does not render - typically "
        "when the block is nested under a list item, and especially when the "
        "indentation is ragged. Left-align the block. This can lift it out of "
        "the list item, which is the intended trade: rendered mathematics "
        "beats nesting.",
        lambda text: _INDENTED_DD.findall(_outside_code(text)),
        None,  # applied by fix_indented_display
    ),
]


_FENCE_LINE = re.compile(r"^[ \t]*(```+|~~~+)")
_INDENTED_DD = re.compile(r"^[ \t]+\$\$[ \t]*$", re.M)


def _display_blocks(text):
    """Yield (open_index, close_index) line pairs for $$ blocks outside code."""
    lines = text.split("\n")
    in_fence, opened = False, None
    for i, line in enumerate(lines):
        if _FENCE_LINE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.strip() == "$$":
            if opened is None:
                opened = i
            else:
                yield opened, i
                opened = None


def fix_indented_display(text):
    """Left-align $$ blocks whose delimiters carry leading whitespace.

    GitHub does not render an indented display block. Only offending blocks are
    touched, and the block's *relative* indentation is preserved by removing the
    common prefix rather than stripping every line.
    """
    lines = text.split("\n")
    for a, b in list(_display_blocks(text)):
        block = lines[a:b + 1]
        if not any(ln[:1] in (" ", "\t") for ln in (lines[a], lines[b])):
            continue
        widths = [len(ln) - len(ln.lstrip()) for ln in block if ln.strip()]
        cut = min(widths) if widths else 0
        for i in range(a, b + 1):
            ln = lines[i]
            if ln.strip():
                lead = len(ln) - len(ln.lstrip())
                lines[i] = ln[min(cut, lead):]
        # the delimiters themselves must end up flush left
        lines[a], lines[b] = lines[a].strip(), lines[b].strip()
    return "\n".join(lines)


def fix_document(text):
    """Convert LaTeX delimiters to GitHub's, leaving code blocks alone."""
    masked = _outside_code(text)
    out, last = [], 0
    for m in _DELIMS.finditer(masked):
        repl = {"\\[": "$$", "\\]": "$$", "\\(": "$", "\\)": "$"}[m.group(0)]
        out.append(text[last:m.start()])
        out.append(repl)
        last = m.end()
    out.append(text[last:])
    return "".join(out)


ALL_RULES = RULES + DOC_RULES
RULES_BY_ID = {r.id: r for r in ALL_RULES}


def check_text(text, enabled=None):
    """Return a list of findings: dicts with line, rule, severity, sample."""
    findings = []
    masked = _outside_code(text)
    for rule in DOC_RULES:
        if enabled and rule.id not in enabled:
            continue
        hits = rule.detect(text)
        if not hits:
            continue
        probe = _DELIMS if rule.id == "latex-delimiters" else _INDENTED_DD
        first = probe.search(masked)
        note = ("%d LaTeX delimiter(s); GitHub needs $$ and $"
                if rule.id == "latex-delimiters"
                else "%d indented $$ delimiter line(s); must be flush left")
        findings.append({
            "line": text.count("\n", 0, first.start()) + 1 if first else 1,
            "rule": rule.id,
            "severity": rule.severity,
            "since": rule.since,
            "hits": sorted(set(h.strip() for h in hits)),
            "sample": note % len(hits),
        })
    for a, b in math_spans(text):
        body = text[a:b]
        line = text.count("\n", 0, a) + 1
        for rule in RULES:
            if enabled and rule.id not in enabled:
                continue
            hits = rule.detect(body)
            if hits:
                findings.append({
                    "line": line,
                    "rule": rule.id,
                    "severity": rule.severity,
                    "since": rule.since,
                    "hits": sorted(set(hits)),
                    "sample": " ".join(body.split())[:90],
                })
    return findings


def fix_text(text, enabled=None):
    """Apply every auto-fixable rule inside math spans. Returns (text, n)."""
    doc_changed = 0
    for rid, fixer in (("latex-delimiters", fix_document),
                       ("indented-display-math", fix_indented_display)):
        if enabled and rid not in enabled:
            continue
        converted = fixer(text)
        if converted != text:
            text, doc_changed = converted, doc_changed + 1

    pieces, last, changed = [], 0, doc_changed
    for a, b in math_spans(text):
        body = text[a:b]
        new = body
        for rule in RULES:
            if enabled and rule.id not in enabled:
                continue
            if rule.fixable:
                new = rule.fix(new)
        if new != body:
            changed += 1
        pieces.append(text[last:a])
        pieces.append(new)
        last = b
    pieces.append(text[last:])
    return "".join(pieces), changed


def iter_markdown(paths):
    for p in paths:
        if os.path.isfile(p):
            if p.lower().endswith(".md"):
                yield p
        else:
            for root, dirs, files in os.walk(p):
                # Skip dot-directories (.git, .claude worktrees, .venv, caches)
                # and vendored trees. Copies of the source would otherwise be
                # reported twice.
                dirs[:] = [d for d in dirs
                           if not d.startswith(".")
                           and d not in {"node_modules", "__pycache__", "vendor"}
                           and not d.startswith("pytest-cache-files-")]
                for f in sorted(files):
                    if f.lower().endswith(".md"):
                        yield os.path.join(root, f)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ghmath",
        description="Publication control for GitHub-rendered math in Markdown.")
    ap.add_argument("paths", nargs="*", default=["."],
                    help="files or directories to scan (default: .)")
    ap.add_argument("--fix", action="store_true",
                    help="rewrite files, applying the auto-fixable rules")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--list-rules", action="store_true",
                    help="print the bug catalogue and exit")
    ap.add_argument("--only", metavar="ID", action="append",
                    help="restrict to a rule id (repeatable)")
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    ap.add_argument("--strict", action="store_true",
                    help="also exit non-zero for advisory warnings")
    args = ap.parse_args(argv)

    if args.list_rules:
        for r in RULES:
            fixable = "auto-fix" if r.fixable else "manual"
            print("%-24s %-5s %-8s  first fixed in %s" %
                  (r.id, r.severity, fixable, r.since))
            for line in _wrap(r.why, 74):
                print("    " + line)
            print()
        return 0

    enabled = set(args.only) if args.only else None
    if enabled:
        unknown = enabled - set(RULES_BY_ID)
        if unknown:
            sys.stderr.write("unknown rule id(s): %s\n" % ", ".join(sorted(unknown)))
            return 2

    files = sorted(set(iter_markdown(args.paths)))
    report, total, fixed_files = {}, 0, 0

    for path in files:
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as exc:
            sys.stderr.write("skipped %s: %s\n" % (path, exc))
            continue

        if args.fix:
            new, n = fix_text(text, enabled)
            if n:
                open(path, "w", encoding="utf-8", newline="").write(new)
                fixed_files += 1
            text = new

        found = check_text(text, enabled)
        if found:
            report[path] = found
            total += len(found)

    errors = sum(1 for fs in report.values() for f in fs
                 if f["severity"] == ERROR)

    if args.json:
        print(json.dumps({"version": __version__, "files": report,
                          "findings": total, "errors": errors,
                          "warnings": total - errors}, indent=2))
    else:
        if not args.quiet:
            for path in sorted(report):
                print("%s" % path)
                for f in report[path]:
                    print("  L%-5d %-24s %-5s %s" %
                          (f["line"], f["rule"], f["severity"], f["sample"]))
                print()
        if args.fix:
            print("rewrote %d file(s)" % fixed_files)
        print("%d finding(s) in %d of %d file(s); %d error, %d warn"
              % (total, len(report), len(files), errors, total - errors))

    # Errors are known to render wrongly and fail the run. Warnings are
    # advisory and need a human, so they only fail under --strict.
    return 1 if (errors or (args.strict and total)) else 0


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
