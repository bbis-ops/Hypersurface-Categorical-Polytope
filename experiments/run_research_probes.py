#!/usr/bin/env python3
"""Weekend research discovery probes."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.discoveries import discoveries_to_markdown
from categorical_polytope.discoveries_research import run_research_discoveries


def main() -> None:
    items = run_research_discoveries()
    out_json = ROOT / "experiments" / "research_discoveries.json"
    out_md = ROOT / "docs" / "RESEARCH_DISCOVERIES.md"
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "discoveries": [d.to_dict() for d in items],
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = discoveries_to_markdown(items).replace(
        "# Discoveries (automated)",
        "# Research discoveries (automated)",
    )
    out_md.write_text(md, encoding="utf-8")
    formal = ROOT / "docs" / "FORMAL_RESEARCH_PROOFS.md"
    from categorical_polytope.formal_proofs_research import research_formal_markdown

    formal.write_text(research_formal_markdown(), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {formal}")
    print(f"\nResearch discoveries: {len(items)}")
    sample = ROOT / "experiments" / "sample_learner_log.json"
    from categorical_polytope.learner_diagram import LearnerTrajectoryLog

    LearnerTrajectoryLog.simulate_random_walk(seed=11).save_json(sample)
    print(f"Wrote sample trajectory {sample}")

    for d in items:
        print(f"  [{d.category}] {d.id}: {d.summary}")


if __name__ == "__main__":
    main()
