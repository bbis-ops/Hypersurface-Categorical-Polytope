#!/usr/bin/env python3
"""Run automated discovery sweeps and write artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.discoveries import (
    print_discovery_summary,
    write_discovery_artifacts,
)


def main() -> None:
    json_path, md_path, formal_path = write_discovery_artifacts(ROOT)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {formal_path}")
    from categorical_polytope.formal_proofs import verify_all_proofs

    checks = verify_all_proofs()
    failed = [c for c in checks if not c[2]]
    print(f"Proof checks: {len(checks) - len(failed)}/{len(checks)} passed")
    for pid, lab, ok, msg in failed:
        print(f"  FAIL {lab} ({pid}): {msg}")
    print()
    from categorical_polytope.discoveries import run_all_discoveries

    print_discovery_summary(run_all_discoveries())


if __name__ == "__main__":
    main()
