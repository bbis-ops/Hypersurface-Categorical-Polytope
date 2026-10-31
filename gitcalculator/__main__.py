"""Command line for the gitcalculator. Run ``python -m gitcalculator --help``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .presets import PRESETS, preset_request


def _request(args: argparse.Namespace) -> dict:
    if args.preset:
        return preset_request(args.preset)
    missing = [name for name in ("system", "base", "perturbation") if not getattr(args, name)]
    if missing:
        raise SystemExit(f"give --preset, or all of --system --base --perturbation (missing: {', '.join(missing)})")
    request = {"system": args.system, "base": args.base, "perturbation": args.perturbation}
    if getattr(args, "observed", None):
        from fractions import Fraction
        request["observed_exponent"] = float(Fraction(args.observed))
    return request


def _inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preset", choices=sorted(PRESETS), help="a canonical example or counterexample")
    parser.add_argument("--system", help='the polyhedron A·x <= b as "([[...]], [...])"')
    parser.add_argument("--base", help="the base objective F in x0, x1, ...")
    parser.add_argument("--perturbation", help="the perturbation G")
    parser.add_argument("--json", action="store_true", help="print JSON instead of the tape")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m gitcalculator", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    calc = sub.add_parser("calc", help="compute, certify, attack, and pin one calculation")
    _inputs(calc)
    calc.add_argument("--observed", help="an observed exponent, such as 4/3, for the inverse check")
    calc.add_argument("--budget", choices=("quick", "standard"), default="standard")
    calc.add_argument("--full", action="store_true", help="include the complete backend response")
    calc.add_argument("--history", action="store_true", help="also replay the input across git history")

    sub.add_parser("presets", help="list the canonical calculations")

    counter = sub.add_parser("counter", help="list the counter-arguments and run their witnesses")
    counter.add_argument("--json", action="store_true")

    history = sub.add_parser("history", help="replay one input across every code state in git")
    _inputs(history)

    tape = sub.add_parser("tape", help="record or verify calculations kept in calculations/")
    tape.add_argument("action", choices=("record", "verify"))
    tape.add_argument("names", nargs="*", help="presets to record (default: all)")

    site = sub.add_parser("site", help="build the static web calculator")
    site.add_argument("--out", type=Path, default=Path("tmp/gitcalculator/site"))
    site.add_argument("--pyodide", type=Path, help="a local Pyodide directory to vendor instead of the CDN")
    site.add_argument("--fragment", action="store_true", help="omit the document skeleton (for a Claude artifact)")

    args = parser.parse_args(argv)

    if args.command == "presets":
        for name, preset in PRESETS.items():
            print(f"{name:<22} {preset['title']}: {preset['note']}")
        return 0

    if args.command == "calc":
        from .receipt import calculate, render_text
        receipt = calculate(_request(args), budget=args.budget, include_backend=args.full)
        if args.history:
            from .history import replay
            receipt["history"] = replay(receipt["input"])
        if args.json:
            print(json.dumps(receipt, indent=2, ensure_ascii=False))
        else:
            print(render_text(receipt))
            if args.history:
                from .history import render_history
                print("\n" + render_history(receipt["history"]))
        return 2 if receipt["answer"]["verdict"] == "contradicted" else 0

    if args.command == "counter":
        from .counter import check_witnesses
        from .receipt import backend, counter_catalogue
        report = check_witnesses(backend().handle)
        if args.json:
            print(json.dumps({"counterarguments": counter_catalogue(), "witnesses": report}, indent=2, ensure_ascii=False))
        else:
            catalogue = {c["id"]: c for c in counter_catalogue()}
            for row in report:
                c = catalogue[row["id"]]
                print(f"{'PASS' if row['passed'] else 'FAIL'}  {row['id']:<18} {c['title']}")
                print(f"      claim      {c['claim']}")
                print(f"      refutation {c['refutation']}")
                print(f"      witness    expects {row['expect']}; got {row['status']}")
        return 0 if all(r["passed"] for r in report) else 1

    if args.command == "history":
        from .history import render_history, replay
        result = replay(_request(args))
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else render_history(result))
        return 0

    if args.command == "tape":
        from . import tape
        if args.action == "record":
            for name in args.names or list(PRESETS):
                print(f"recorded {tape.record(name, preset_request(name)).relative_to(tape.ROOT)}")
            return 0
        report = tape.verify()
        for row in report:
            print(f"{'same ' if row['unchanged'] else 'DRIFT'}  {row['name']:<22} {row['current_receipt']}")
            for line in row["drift"]:
                print(f"         {line}")
        print(f"{sum(r['unchanged'] for r in report)}/{len(report)} recorded calculations unchanged")
        return 0 if all(r["unchanged"] for r in report) else 1

    if args.command == "site":
        from .site import build
        out = build(args.out, pyodide=args.pyodide, fragment=args.fragment)
        print(f"web calculator written to {out}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
