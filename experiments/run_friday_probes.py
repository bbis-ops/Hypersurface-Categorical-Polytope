#!/usr/bin/env python3
"""Friday–Saturday immediate discovery batch."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.category_learning_session import run_default_session
from categorical_polytope.category_tutor import run_default_tutor_session
from categorical_polytope.discoveries import discoveries_to_markdown
from categorical_polytope.discoveries_friday import run_friday_discoveries
from categorical_polytope.formal_proofs_friday import (
    FRIDAY_PROOF_REGISTRY,
    all_research_formal_markdown,
    friday_formal_markdown,
    verify_friday_evidence,
)


def main() -> None:
    run_default_session(ROOT / "experiments")
    run_default_tutor_session(ROOT / "experiments")
    from categorical_polytope.loop_closure import run_loop_closure

    run_loop_closure(ROOT / "experiments", use_api=False)
    plot_lc = ROOT / "experiments" / "plot_loop_closure.py"
    if plot_lc.exists():
        import subprocess

        subprocess.run([sys.executable, str(plot_lc)], cwd=str(ROOT))
    items = run_friday_discoveries()
    out_json = ROOT / "experiments" / "friday_discoveries.json"
    out_md = ROOT / "docs" / "FRIDAY_DISCOVERIES.md"
    formal_fri = ROOT / "docs" / "FORMAL_FRIDAY_PROOFS.md"
    formal_all = ROOT / "docs" / "FORMAL_RESEARCH_ALL.md"
    by_id = {d.id: d.evidence for d in items}
    proof_checks = [
        {
            "id": s.discovery_id,
            "label": s.label,
            "ok": verify_friday_evidence(s.discovery_id, by_id.get(s.discovery_id, {}))[0],
        }
        for s in FRIDAY_PROOF_REGISTRY
    ]
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "discoveries": [d.to_dict() for d in items],
        "formal_proofs": [
            {
                "discovery_id": s.discovery_id,
                "label": s.label,
                "title": s.title,
            }
            for s in FRIDAY_PROOF_REGISTRY
        ],
        "proof_verification": proof_checks,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = discoveries_to_markdown(items).replace(
        "# Discoveries (automated)",
        "# Friday–Saturday discoveries",
    )
    out_md.write_text(md, encoding="utf-8")
    formal_fri.write_text(friday_formal_markdown(), encoding="utf-8")
    formal_all.write_text(all_research_formal_markdown(), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {formal_fri}")
    print(f"Wrote {formal_all}")
    ok = sum(1 for c in proof_checks if c["ok"])
    print(f"Proof checks: {ok}/{len(proof_checks)}")
    print(f"\nFriday probes: {len(items)}")
    for d in items:
        print(f"  [{d.category}] {d.id}: {d.summary}")


if __name__ == "__main__":
    main()
