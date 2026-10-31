"""Command line for the gitcalculator. Run ``python -m gitcalculator --help``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .presets import PRESETS, preset_request


def _request(args: argparse.Namespace) -> dict:
    if args.preset:
        request = preset_request(args.preset)
    else:
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

    design = sub.add_parser("design", help="the exponent spectrum of a vertex, and perturbations that reach a target")
    design.add_argument("--preset", choices=sorted(PRESETS), help="take P and F from a preset")
    design.add_argument("--system")
    design.add_argument("--base")
    design.add_argument("--target", help="a response exponent to synthesize, such as 3/2")
    design.add_argument("--json", action="store_true")

    sweep = sub.add_parser("sweep", help="the exact phase fan of a family G(t)")
    _inputs(sweep)
    sweep.add_argument("--from", dest="low", default="-1")
    sweep.add_argument("--to", dest="high", default="1")

    attack = sub.add_parser("attack", help="generate counterexamples to one answer")
    _inputs(attack)

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
    site.add_argument("--recorded-only", action="store_true", help="ship recorded receipts without the live engine")

    # An expression such as -(x0**4+x1**4) starts like an option; bind it to its flag.
    raw = list(sys.argv[1:] if argv is None else argv)
    valued = {"--system", "--base", "--perturbation", "--target", "--from", "--to", "--observed"}
    bound: list[str] = []
    while raw:
        token = raw.pop(0)
        bound.append(f"{token}={raw.pop(0)}" if token in valued and raw else token)
    args = parser.parse_args(bound)

    if args.command == "design":
        from .modes import design as run_design
        system, base = args.system, args.base
        if args.preset:
            preset = preset_request(args.preset)
            system, base = system or preset["system"], base or preset["base"]
        if not (system and base):
            raise SystemExit("give --preset, or both --system and --base")
        result = run_design(system, base, args.target)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if result["status"] != "complete":
            print(f"not applicable: {result['reason']}")
            return 1
        print(f"vertex ({', '.join(result['vertex'])}) · edge weights {', '.join(result['weights'])} · "
              f"base {'proved' if result['base_proved'] else 'not proved'} (H0–H2)")
        print("edge coordinates are the active constraints' slacks: "
              + ", ".join(f"{s['axis']} = {s['expression']}" for s in result["slacks"]))
        print("\nexponent spectrum (γ = 1/(1 − q))")
        for entry in result["spectrum"]:
            examples = ", ".join(m["perturbation"] for m in entry["mechanisms"][:3])
            print(f"  γ = {entry['gamma']:<6} q = {entry['q']:<6} {entry['mechanism_count']} mechanism(s), e.g. G = {examples}")
        target = result.get("target")
        if target:
            if "error" in target:
                print(f"\ntarget: {target['error']}")
            elif target["achievable"]:
                print(f"\ntarget γ = {target['gamma']} is reachable:")
                for c in target["candidates"]:
                    print(f"  G = {c['perturbation']:<28} → {c['check']['verdict']} γ = {c['check']['gamma']}")
            else:
                print(f"\ntarget γ = {target['gamma']} is not reachable by any qualified face or V.22 channel here; "
                      f"nearest: {target['nearest_below']} below, {target['nearest_above']} above")
        return 0

    if args.command == "sweep":
        from .modes import sweep as run_sweep
        request = _request(args)
        result = run_sweep(request["system"], request["base"], request["perturbation"], args.low, args.high)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if result["status"] != "complete":
            print(f"not applicable: {result['reason']}")
            return 1
        print("transported coefficient laws: " + "; ".join(f"{law['monomial']}: {law['law']}" for law in result["coefficient_laws"]))
        for wall in result["walls"]:
            where = wall["at"] or f"[{wall['lo']}, {wall['hi']}]"
            print(f"  wall t = {where}  ({wall['kind']}{', ' + wall['monomial'] if wall['monomial'] else ''})")
        for chamber in result["chambers"]:
            o = chamber["outcome"]
            print(f"  t in ({chamber['from']}, {chamber['to']}): {o['verdict']} γ = {o['gamma']} {o['winners']}")
        return 0

    if args.command == "attack":
        from .modes import attack as run_attack
        request = _request(args)
        result = run_attack(request["system"], request["base"], request["perturbation"])
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if result["status"] != "complete":
            print(f"not applicable: {result['reason']}")
            return 1
        b = result["base"]
        print(f"answer under attack: {b['verdict']} γ = {b['gamma']} {b['winners']}")
        for m in result["mutations"]:
            o = m["outcome"]
            print(f"  {'BREAKS' if m['changed'] else 'holds '}  {m['kind']:<16} {m['description']}  → {o['verdict']} γ = {o['gamma']}")
        s = result["summary"]
        print(f"{s['changed']} of {s['total']} mutations change the answer")
        return 0

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
        out = build(args.out, pyodide=args.pyodide, fragment=args.fragment, live=not args.recorded_only)
        print(f"web calculator written to {out}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
