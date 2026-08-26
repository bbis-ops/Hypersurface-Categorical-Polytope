#!/usr/bin/env python3
"""Correlate model-generated escape searches with the geometric coverage theorem."""

from __future__ import annotations

import json
import re
import sys
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COMBINED_JSON = ROOT / "experiments" / "combined_law.json"
SAFETY_MD = ROOT / "experiments" / "SAFETY_INSTANCES.md"
OUT_MD = ROOT / "docs" / "COVERAGE_CORRELATION.md"
OUT_TXT = ROOT / "docs" / "COVERAGE_CORRELATION.txt"
OUT_JSON = ROOT / "experiments" / "coverage_correlation.json"
REGISTERED_JSON = ROOT / "experiments" / "candidate_coverage_certificate.json"


def _match_int(pattern: str, text: str, default: int = 0) -> int:
    match = re.search(pattern, text, re.MULTILINE)
    return int(match.group(1)) if match else default


def _load_combined() -> list[dict]:
    if not COMBINED_JSON.exists():
        return []
    payload = json.loads(COMBINED_JSON.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _load_safety() -> tuple[str, dict[str, int]]:
    text = SAFETY_MD.read_text(encoding="utf-8") if SAFETY_MD.exists() else ""
    regimes = {
        name: _match_int(rf"^- {re.escape(name)}: (\d+)$", text)
        for name in ("quadratic", "coupled", "fractional", "saturating", "finite-scale", "safe")
    }
    return text, regimes


def _load_registered() -> dict:
    if not REGISTERED_JSON.exists():
        return {}
    payload = json.loads(REGISTERED_JSON.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> None:
    from categorical_polytope.eval_escape import samples_to_catch, unit_ball_volume

    combined = _load_combined()
    safety_text, regimes = _load_safety()
    registered = _load_registered()
    combined_breaks = [
        row for row in combined
        if row.get("ok") and row.get("breaks") and not row.get("base_self_fails")
    ]
    combined_violations = [
        row for row in combined_breaks
        if abs(row.get("measured_exponent", 0.0) - row.get("predicted_exponent", 0.0)) >= 0.08
    ]
    combined_self_fail = sum(bool(row.get("base_self_fails")) for row in combined)
    combined_has_provenance = bool(combined) and all(
        "base_expr" in row and "pert_expr" in row for row in combined
    )

    safety_screened = _match_int(r"\((\d+) screened:", safety_text)
    safety_violations = _match_int(r"Law violations \(counterexamples\): (\d+)", safety_text)

    delta = 0.05
    dimensions = (1, 2, 3, 5, 10, 20)
    table_rows = []
    for d in dimensions:
        grid_sufficient = samples_to_catch(delta, d)
        arbitrary_necessary = ceil(1.0 / (unit_ball_volume(d) * delta**d))
        table_rows.append(
            {
                "dimension": d,
                "arbitrary_volume_lower_bound": arbitrary_necessary,
                "cartesian_grid_sufficient": grid_sufficient,
            }
        )

    payload = {
        "theorem": {
            "space": "[0,1]^d with Euclidean metric",
            "arbitrary_sample_radius_lower_bound": "(1/(n*v_d))^(1/d)",
            "cartesian_grid_radius": "sqrt(d)/(2*(m-1)), n=m^d",
            "delta": delta,
            "sample_table": table_rows,
        },
        "combined_law": {
            "screened_rows": len(combined),
            "breaking_pairs": len(combined_breaks),
            "base_self_fail": combined_self_fail,
            "flagged_exponent_mismatches": len(combined_violations),
            "source_expression_provenance_available": combined_has_provenance,
        },
        "safety_instances": {
            "screened": safety_screened,
            "regimes": regimes,
            "asymptotic_law_violations": safety_violations,
        },
        "registered_candidate_coverage": {
            "registry_version": registered.get("registry_version"),
            "phase": registered.get("phase"),
            "families": [
                {key: row.get(key) for key in (
                    "law", "family", "dimension", "grid_points", "covering_radius",
                    "certificate_status", "unresolved"
                )}
                for row in registered.get("families", [])
            ],
        },
    }

    rows_md = []
    for row in table_rows:
        rows_md.append(
            f"| {row['dimension']} | {row['arbitrary_volume_lower_bound']:,} | "
            f"{row['cartesian_grid_sufficient']:,} |"
        )

    provenance_note = (
        "The current combined-law JSON predates expression provenance, so its four "
        "flags are leads, not auditable counterexamples. The runner now persists both "
        "expressions and sources for future runs."
        if not combined_has_provenance
        else "The combined-law rows include their source expressions and are auditable."
    )

    body = f"""# Coverage theorem × model-generated escape searches

This report connects the finite-sample coverage theorem to the completed
`COMBINED_LAW` and `SAFETY_INSTANCES` searches. The theorem is geometric; the
model-generated searches are finite empirical probes. The latter illustrate the
blind spots but cannot validate exhaustive coverage.

## The rigorous statement

Let `X=[0,1]^d` with Euclidean distance and let `S={{x_1,...,x_n}}` be the inputs
actually tested. Define the covering radius

`rho(S) = max_(x in X) min_(s in S) ||x-s||_2`.

Because `X` is compact, a maximizer `x*` exists. The open metric ball
`B_X(x*,rho(S))` contains no tested point. Therefore an all-safe behavior and a
behavior that fails only inside this ball give exactly the same `n` test results.
This remains true for a deterministic adaptive evaluator on its all-pass
transcript: construct one fixed failing behavior after deriving that finite path;
it returns the same pass observations and therefore induces the same path.

The radius has the volume lower bound

`rho(S) >= (1/(n*v_d))^(1/d)`, where `v_d=pi^(d/2)/Gamma(d/2+1)`.

Proof: if radius-`r` balls around the samples cover the unit-volume cube, their
union has volume at most `n*v_d*r^d`, hence `1 <= n*v_d*r^d`.

For an endpoint-including Cartesian grid with `m` points per axis (`n=m^d`), the
covering radius is exactly half a cell diagonal:

`rho_grid = sqrt(d)/(2(m-1))`.

Thus a grid with `rho_grid <= delta` is sufficient to hit every **open failure
ball of radius greater than `delta`** (and every closed ball of radius at least
`delta`). At `delta=0.05`:

| dimension | necessary for any placement (volume bound) | sufficient Cartesian grid |
|-----------|--------------------------------------------|-----------------------------|
{chr(10).join(rows_md)}

The headline `46^20 = 1,799,519,816,997,495,209,117,766,334,283,776 ≈ 1.80×10^33`
is therefore a **Cartesian-grid sufficient count**, not a lower bound for every
possible sampling design. Even the assumption-light volume lower bound in 20-D
is about `4.06×10^27` samples.

## What “passed N tests” licenses

Without a regularity assumption, it licenses only: “the tested points passed.”
To extend that observation to neighborhoods, report all of:

1. the metric and normalization on the input space;
2. the empirical covering radius of the tested set;
3. the effective/intrinsic dimension used in any dimension-only bound; and
4. a minimum failure width or a Lipschitz/margin condition connecting sampled
   outcomes to nearby inputs.

If every relevant failure set contains a **closed** relative ball of radius
`delta`, a cover with radius at most `delta` detects every such failure. For open
failure balls, require their radius to be strictly greater than the covering
radius. This is the precise version of “safe down to radius `r(N,d)`.”

## Correlation with the completed searches

### Safety instances

- Screened: **{safety_screened}**.
- Regimes: {', '.join(f'{name}={count}' for name, count in regimes.items())}.
- Asymptotic-law violations after scale classification: **{safety_violations}**.

The model generated thin interior spikes, coupled surfaces, fractional ridges,
and steep gates. Those are constructive examples of failure sets that a fixed
axis/grid/local evaluator can miss. The `tolerance_cliff` initially looked like a
quadratic-law violation at `s=0.01`; a strength sweep showed its exponent returning
to `2` and measured/predicted ratio returning to `1` as `s` decreased. It is a
finite-scale remote-gate transition—exactly the kind of nonlocal feature for which
coverage, rather than a local Taylor law, is the relevant diagnostic.

### Combined law

- Rows recorded: **{len(combined)}**.
- Breaking pairs: **{len(combined_breaks)}**; base-self-fail: **{combined_self_fail}**.
- Exponent mismatches flagged for follow-up: **{len(combined_violations)}**.

{provenance_note}

These probes broaden adversarial search. Their observed attack yield is directly
reportable, but their candidate count is not a covering design: arbitrary
expressions have no declared finite-dimensional metric here.

## The registered candidate-space bridge

The separate [`CANDIDATE_COVERAGE_CERTIFICATE.md`](CANDIDATE_COVERAGE_CERTIFICATE.md)
implements the missing bridge without pretending that arbitrary expression text
is Cartesian. Registry v1 defines one bounded normal-form parameter family per
law, maps its coordinates independently to `[0,1]`, uses normalized Euclidean
distance, and evaluates an endpoint-including Cartesian grid. Its exact radius is
`sqrt(d)/(2(m-1))`.

The positive detection statement is explicitly conditional on minimum-width
assumption `R(rho)`: every relevant counterexample set in the registered family
contains a closed relative ball of radius at least `rho`. Numerical survivors or
unresolved grid points withhold the corresponding certificate. Registry v1 was
designed after the open campaign and calibrated with boundary probes, so its
current run is exploratory; the frozen registry supports later confirmatory use.

This yields two non-conflicting outputs: the open API campaign measures observed
adversarial-search behavior, while the registered layer makes a restricted,
metric coverage claim. Neither is automatically a coverage claim over all
candidate functions, prompt space, or deployed-model behavior.

## Scope and citations

This is a theorem about finite point evaluation on a metric space, not evidence
about any deployed model. “Dimension” means the dimension of the chosen metric
model, ideally effective/intrinsic dimension—not token count or embedding width.

Covering numbers and metric entropy are standard notions originating with
[Kolmogorov and Tikhomirov (1959/1961)](https://www.mathnet.ru/eng/rm7289).
A modern worst-case global-optimization result likewise constructs adversarial
functions that agree on the sampled trajectory while differing at an unsampled
point: [Xu et al., 2024, JOTA](https://doi.org/10.1007/s10957-024-02399-1).
Classical high-dimensional sphere-covering context appears in
[Rogers, 1963](https://doi.org/10.1112/S0025579300004083).

## Reproduce

`python experiments/run_coverage_correlation.py`
"""

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(body, encoding="utf-8")
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    plain = re.sub(r"^#+\s*", "", plain, flags=re.MULTILINE).replace("**", "").replace("`", "")
    OUT_TXT.write_text(plain, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_TXT}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
