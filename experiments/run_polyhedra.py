#!/usr/bin/env python3
"""
Domain three: drive the polyhedral exponent-law seeds through the shared ledger.

Runs offline and costs nothing. The multi-domain runner (`run_campaign.py`)
handles the API side; this exists to seed the corpus and regenerate the report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.adjudication import Ledger, Status  # noqa: E402
from categorical_polytope.adjudication.screening import (  # noqa: E402
    DECISIVE,
    VALUE_ORDER,
)
from categorical_polytope.adjudication.polyhedra import PolyhedronDomain  # noqa: E402
from categorical_polytope.adjudication.polyhedra.domain import (  # noqa: E402
    SELECTION_SPREAD,
)
from categorical_polytope.adjudication.polyhedra.seeds import SEEDS  # noqa: E402

STATE = ROOT / "experiments" / "polyhedra.json"
REPORT = ROOT / "docs" / "POLYHEDRA.md"


def _write_report(ledger: Ledger, domain: PolyhedronDomain) -> None:
    total = ledger.counts(domain)
    lines = [
        "# Domain three: exponent laws on a general polyhedron", "",
        "Domain one runs on a box, where a vertex's edges *are* the coordinate axes,",
        "so \"measure along each axis\" and \"measure along each edge\" are the same",
        "instruction. On any other polytope they differ. This domain asks the same law",
        "both ways and records which coordinate system it lives in.", "",
        f"Local adjudicator version: **{ledger.verifier_version}**. Adjudicator is stdlib",
        "arithmetic; no model decides any verdict.", "",
        "| Rule | corpus | verified | counterexamples | outside scope | rejected/inconclusive |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for rule_id in domain.rule_ids:
        c = ledger.counts(domain, rule_id)
        lines.append(f"| `{rule_id}` | {sum(c.values())} | {c['verified']} "
                     f"| {c['counterexample']} | {c['outside_scope']} "
                     f"| {c['rejected'] + c['inconclusive']} |")
    lines += ["", "## Denominator", "",
              f"- Retained corpus: **{len(ledger)}**",
              f"- In-scope: **{ledger.in_scope_total(domain)}**",
              f"- Out of scope: **{total['outside_scope']}**",
              f"- Undecided: **{total['inconclusive']}**",
              f"- Refused at the parse boundary: **{total['rejected']}**", ""]

    # V.16 has two clauses and they are not equally tested. A row whose
    # admissible faces all agree on q tests the dilation and the admissibility
    # filter; minimum, maximum and "pick any" would all return the same answer
    # there. Only a row whose faces DISAGREE puts the selection itself at risk.
    # Counting them separately stops corpus size from implying coverage it does
    # not have.
    def faces_of(row):
        return (row.get("metrics") or {}).get("admissible_faces") or []

    multi = [r for r in ledger.records if any(len(f) > 1 for f, _ in faces_of(r))]
    product_only = [r for r in multi if all(len(f) > 1 for f, _ in faces_of(r))]
    spread = [r for r in ledger.records
              if faces_of(r)
              and max(q for _, q in faces_of(r)) - min(q for _, q in faces_of(r))
              > SELECTION_SPREAD]
    carries = [r for r in ledger.records
               if "base_homogeneity" in (r.get("metrics") or {})]
    licensed = sum(1 for r in carries
                   if r["metrics"]["base_homogeneity"] is not None
                   and abs(r["metrics"]["base_homogeneity"] - 1.0) < 1e-3)
    # A discriminating row only tests the theorem where the theorem applies:
    # FORMAL_FACE_SELECTION hypothesis 2 wants every beta_i > 1, and the
    # transport wants homogeneity 1. `case4` discriminates min from max with
    # both predictions finite, but carries a beta of 0 and unresolved
    # homogeneity, so it sits outside those hypotheses. That overlap is the
    # number to move, and it is not the same as the disagreement count.
    #
    # Both tests are read off the row rather than recomputed here. A report
    # that derives its own coverage can disagree with the corpus it summarises;
    # since v8 the adjudicator records what each row is evidence for, and this
    # function only counts.
    def covered(row):
        return bool((row.get("metrics") or {}).get("hypotheses_licensed"))

    def finite_rival(row):
        """The max rule also predicts a finite exponent, so both are testable."""
        return bool((row.get("metrics") or {}).get("selection_discriminates"))

    covered_rows = [r for r in spread if covered(r)]
    # The strongest possible evidence: faces disagree, the rival rule predicts
    # a finite exponent too (so measurement can choose between two real
    # numbers rather than merely rejecting a divergence), AND the row sits
    # inside the hypotheses. This is the count that would settle the selection
    # clause, and it is not implied by any of the others.
    decisive = [r for r in covered_rows if finite_rival(r)]
    lines += ["## Coverage of the selection rule", "",
              "Theorem V.16 selects `q* = min_j q_j` over the admissible faces of the",
              "tangent cone. A row whose faces all agree on `q` tests the dilation and",
              "the admissibility filter; only a row whose faces *disagree* tests the",
              "selection.", "",
              f"- Rows with a multi-ray admissible face: **{len(multi)}**",
              f"- Rows admissible ONLY on a multi-ray face (product monomials): "
              f"**{len(product_only)}**",
              f"- Rows whose faces disagree about `q` by more than 0.05: **{len(spread)}**",
              f"- Transport licensed (`base_homogeneity` = 1): **{licensed}/{len(carries)}**",
              f"- Inside hypothesis 2 in full, every `beta_i` > 1 as well "
              f"(`hypotheses_licensed`): **{sum(1 for r in carries if covered(r))}"
              f"/{len(carries)}**",
              f"- Rows that separate the minimum rule from the maximum rule "
              f"(`selection_discriminates`): **{sum(1 for r in ledger.records if finite_rival(r))}**",
              f"- Disagreeing AND inside the theorem's hypotheses "
              f"(every `beta_i` > 1, homogeneity 1): **{len(covered_rows)}**",
              f"- Of those, ones where the rival maximum rule is also FINITE "
              f"(so measurement chooses between two numbers rather than "
              f"rejecting a divergence): **{len(decisive)}**", ""]
    if spread:
        lines.append("The disagreeing rows, which are the ones carrying the selection:")
        lines += [f"- `{r['name']}` ({r['rule_id'].split('/')[1]}): "
                  f"q in {sorted(round(q, 4) for _, q in faces_of(r))} -> "
                  f"q* = {r['metrics']['weighted_degree']:.4f}, {r['status']}"
                  for r in spread]
        lines.append("")

    # Lemma 1 is the hypothesis every other section silently stands on: the
    # face argument describes a neighbourhood of the vertex, and that is the
    # global asymptotic only if the vertex is the unperturbed maximiser and
    # isolated. `scope` only ever checked that it is a local maximum along its
    # own edges, which a second, higher vertex does not contradict.
    margins = [(r, (r.get("metrics") or {}).get("rival_margin"))
               for r in ledger.records
               if "rival_margin" in (r.get("metrics") or {})]
    measured = [(r, m) for r, m in margins if m is not None]
    rivalled = [(r, m) for r, m in measured if m <= 0.0]
    lines += ["## Localisation (Lemma 1)", "",
              "The face analysis runs inside a neighbourhood of the vertex, so it is",
              "the global asymptotic only where the vertex is the unperturbed",
              "maximiser and isolated. `rival_margin` measures that `eta` against a",
              "ball of radius 0.25: it is the amount by which the vertex outranks the",
              "best competing maximum the probe found outside that ball. Positive is a",
              "margin; zero or less is a genuine rival, and the localisation does not",
              "hold for that row. The probe is finite - it can find a rival, it cannot",
              "prove there is none - so nothing is gated on it.", "",
              f"- Rows carrying a margin: **{len(measured)}/{len(margins)}**",
              f"- No rival found outside the ball: **{len(measured) - len(rivalled)}**",
              f"- Rival at least as high as the vertex: **{len(rivalled)}**"]
    if measured:
        tightest = min(measured, key=lambda pair: pair[1])
        lines.append(f"- Smallest margin: **{tightest[1]:.3g}** on "
                     f"`{tightest[0]['name']}` ({tightest[0]['status']})")
    lines.append("")
    if rivalled:
        lines.append("Rows where the unperturbed maximiser is not isolated:")
        lines += [f"- `{r['name']}` ({r['rule_id'].split('/')[1]}): "
                  f"margin {m:.3g}, {r['status']}" for r, m in rivalled]
        lines.append("")

    # What the corpus is worth, as opposed to how large it is. Read off the
    # recorded metrics - `screen_row` re-measures nothing - so this costs a
    # pass over the rows and can be regenerated as often as the campaign runs.
    from categorical_polytope.adjudication.polyhedra.screening import screen_row

    edge_rows = [r for r in ledger.records
                 if r["rule_id"] == "polyhedron/edge_exponent_law"]
    screened = [(r, screen_row(r)) for r in edge_rows]
    counts = {value: 0 for value in VALUE_ORDER}
    for _row, screening in screened:
        counts[screening.value] += 1
    useful = sum(1 for _r, s in screened if s.informative)
    share = (100.0 * useful / len(screened)) if screened else 0.0
    lines += ["## Candidate value", "",
              "Corpus size is not evidence. A row whose admissible faces all",
              "agree about `q` exercises the transport and the admissibility",
              "filter, and would have looked identical under a maximum rule, so",
              "it cannot move the selection clause however many of it there is.",
              "Screening classifies what each row would be evidence FOR, from",
              "the metrics already recorded - no re-measurement.", "",
              "| class | rows | what it would establish |",
              "|---|---:|---|",
              f"| `decisive` | {counts['decisive']} | separates the minimum "
              "rule from a rival that also gives a finite answer |",
              f"| `selective` | {counts['selective']} | separates it from a "
              "rival that only diverges - any rule survives that |",
              f"| `confirming` | {counts['confirming']} | in scope and "
              "licensed, but consistent with the rivals too |",
              f"| `unlicensed` | {counts['unlicensed']} | adjudicated, but a "
              "hypothesis is unmet, so a pass licenses nothing |",
              f"| `refused` | {counts['refused']} | scope declines it; the "
              "proposal was spent for nothing |", "",
              f"Of {len(screened)} `edge_exponent_law` rows, **{useful}** "
              f"({share:.0f}%) distinguish the rule from a rival.", ""]
    if counts[DECISIVE]:
        lines.append("Decisive rows, the ones that carry the selection clause:")
        lines += [f"- `{r['name']}`: {s.reason} ({r['status']})"
                  for r, s in screened if s.value == DECISIVE]
    else:
        lines.append("**No decisive row yet.** `propose(steer=True)` asks for "
                     "this shape; `focus_for_gap` is the description it sends.")
    lines.append("")

    lines += ["## Disagreements between coordinate systems", ""]
    cx = [r for r in ledger.records if r["status"] == "counterexample"]
    if cx:
        for r in cx:
            m = r.get("metrics") or {}
            lines += [f"### `{r['rule_id']}` / {r['name']}", "",
                      f"- System: `{r['payload']['system']}`",
                      f"- Base: `{r['payload']['base']}`  Pert: `{r['payload']['pert']}`",
                      f"- Vertex: `{m.get('vertex')}` axis-aligned: `{m.get('axis_aligned')}`",
                      f"- Predicted {m.get('predicted_exponent')}, measured {m.get('measured_exponent')}",
                      f"- {r['reason']}", ""]
    else:
        lines.append("None recorded.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report without writing")
    args = ap.parse_args()

    domain = PolyhedronDomain()
    ledger = Ledger.load(STATE)
    ledger.sync_verifier(domain)
    rows = [domain.to_row(s.rule_id, s.name, s.system, s.base, s.pert, s.note)
            for s in SEEDS]
    fresh = ledger.admit(domain, rows)
    ledger.validate()

    counts = ledger.counts(domain)
    print(f"seeds {len(SEEDS)}, newly admitted {len(fresh)}, corpus {len(ledger)}")
    for status in Status:
        print(f"  {str(status):15} {counts[str(status)]}")
    print(f"  in-scope denominator: {ledger.in_scope_total(domain)}/{len(ledger)}")
    missing = [str(s) for s in Status if not counts[str(s)]]
    if missing:
        print(f"WARNING: never produced: {', '.join(missing)}", file=sys.stderr)
    if args.check:
        print("--check: nothing written")
        return 0
    ledger.save(STATE)
    _write_report(ledger, domain)
    print(f"wrote {STATE}\nwrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
