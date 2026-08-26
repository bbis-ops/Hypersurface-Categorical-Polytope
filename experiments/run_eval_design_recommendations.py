#!/usr/bin/env python3
"""Generate a concrete eval-design standard, optionally with an API red-team review."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_MD = ROOT / "docs" / "EVAL_DESIGN_RECOMMENDATIONS.md"
OUT_JSON = ROOT / "experiments" / "eval_design_recommendations.json"

REVIEW_PROMPT = r"""Act as a hostile safety-evaluation methodologist. Review this
proposed standard:

1. Every finite eval reports its input metric, domain normalization, tested-set
covering radius, and effective dimension. A pass is pointwise unless extended.
2. Worst-case geometric claim: failures are guaranteed detected only when they
contain a closed ball at least the covering radius (or open ball strictly larger).
3. Distributional claim: n IID draws miss any failure region of probability mass
mu with probability (1-mu)^n.
4. Lipschitz claim: if H is L-Lipschitz, tested max is M, and covering radius is
rho, then sup H <= M+L*rho.
5. Mixed categorical/continuous spaces cover every safety-relevant stratum; an
uncovered stratum receives no worst-case claim.
6. High-dimensional brute-force grids are reported as infeasible rather than
quietly replaced by a pointwise benchmark claim.

Return the strongest distinct flaws or missing operational requirements. Focus on
distribution shift, metric validity, estimating L, randomized/adaptive sampling,
intrinsic dimension, correlated samples, and confidence calibration. JSON only:
{"reviews":[{"id":"slug","issue":"...","repair":"...","severity":"major|minor"}]}
"""


def parse_reviews(text: Any) -> list[dict[str, str]]:
    if not isinstance(text, str):
        return []
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict) or not isinstance(payload.get("reviews"), list):
        return []
    rows = []
    for index, item in enumerate(payload["reviews"]):
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "major")).lower()
        rows.append(
            {
                "id": re.sub(r"[^a-z0-9_]+", "_", str(item.get("id", f"review_{index}")).lower())[:60],
                "issue": str(item.get("issue", ""))[:2000],
                "repair": str(item.get("repair", ""))[:2000],
                "severity": severity if severity in {"major", "minor"} else "major",
                "local_status": "pending adjudication",
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-review", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    from categorical_polytope.eval_design import (
        anisotropic_grid,
        distributional_samples,
        lipschitz_certificate,
        mixed_space_grid_samples,
        shift_robust_distributional_samples,
    )
    from categorical_polytope.eval_escape import samples_to_catch

    grid_20 = samples_to_catch(0.05, 20)
    distributional = distributional_samples(0.01, 0.05)
    shifted_distributional = shift_robust_distributional_samples(
        0.01, 0.05, 5.0, detection_sensitivity=0.9
    )
    anisotropic = anisotropic_grid((0.02, 0.05, 0.10), norm="linf")
    certificate = lipschitz_certificate(-0.2, 2.0, 0.05)
    mixed = mixed_space_grid_samples(12, 3, 0.10)

    reviews: list[dict[str, str]] = []
    backend = "not requested"
    previous_by_id: dict[str, dict[str, str]] = {}
    if OUT_JSON.exists():
        try:
            previous = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            previous_review = previous.get("api_review", {})
            backend = str(previous_review.get("backend", backend))
            reviews = [
                item for item in previous_review.get("items", []) if isinstance(item, dict)
            ]
            previous_by_id = {
                str(item.get("id", "")): item for item in reviews if item.get("id")
            }
        except (json.JSONDecodeError, OSError):
            reviews = []
    if args.api_review:
        from categorical_polytope.interaction_search import propose_candidates

        reviews, backend = propose_candidates(
            1,
            model=args.model,
            base_url=args.base_url,
            prompt=REVIEW_PROMPT,
            parser=parse_reviews,
        )
        for item in reviews:
            prior = previous_by_id.get(item["id"])
            if prior:
                item["local_status"] = str(prior.get("local_status", item["local_status"]))
                item["local_reason"] = str(prior.get("local_reason", ""))
            else:
                item["local_reason"] = ""
        print(f"  API design review: {len(reviews)} items ({backend})", flush=True)

    payload = {
        "rules": {
            "grid_20d_delta_005": grid_20,
            "iid_mu_001_alpha_005": distributional,
            "shifted_mu_001_alpha_005_W_5_sensitivity_09": shifted_distributional,
            "anisotropic_linf": {
                "radii": anisotropic.target_radii,
                "points_per_axis": anisotropic.points_per_axis,
                "total": anisotropic.total_points,
            },
            "lipschitz_example": {
                "sampled_max": certificate.sampled_max,
                "L": certificate.lipschitz_constant,
                "rho": certificate.covering_radius,
                "global_upper_bound": certificate.global_upper_bound,
                "certified": certificate.certified,
            },
            "mixed_12_strata_3d_delta_01": mixed,
        },
        "api_review": {"backend": backend, "items": reviews},
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    review_lines = ["_API review not requested._"]
    if reviews:
        review_lines = []
        for item in reviews:
            review_lines += [
                f"### {item['id']} ({item['severity']})",
                "",
                f"- Issue: {item['issue']}",
                f"- Proposed repair: {item['repair']}",
                f"- Local status: **{item['local_status']}**",
                f"- Local reason: {item.get('local_reason', '')}",
                "",
            ]

    body = f"""# Concrete safety-evaluation design recommendations

## Required claim types

Every result must label itself as one of these non-interchangeable claims:

1. **Pointwise:** the listed test inputs passed. No neighborhood claim.
2. **Distributional:** under a named sampling distribution, a failure region of
   probability mass at least `mu` is missed with probability at most `alpha`.
3. **Geometric worst-case:** every failure containing a specified metric ball is
   hit because the tested set has a measured covering radius.
4. **Margin-certified:** a regularity bound extends sampled scores globally.

## Mandatory eval card

Publish: domain and exclusions; metric and normalization and its semantic
validation; discrete strata;
sample-selection rule; number of unique samples; empirical covering radius or an
explicit statement that it is unknown; effective-dimension justification;
failure-width or regularity assumption; raw score margin; scorer false-negative
rate; sample dependence/cluster provenance; distribution-shift assumption; and
the exact claim type above.

## Design rules

### High-dimensional geometry

Do not imply worst-case coverage from a large test count alone. In 20 normalized
Euclidean dimensions, a radius-0.05 Cartesian guarantee needs
`{grid_20:,}` points. When this is infeasible, reduce the justified intrinsic
dimension, prove structure/regularity, or downgrade the claim to pointwise or
distributional. Never silently substitute one claim type for another.
An intrinsic-dimension claim must define the restricted deployment domain and
validate that inputs remain on it; an estimator alone cannot erase ambient
off-manifold regions from a worst-case claim.

### Anisotropic inputs

Use domain-specific radii instead of pretending every coordinate has equal
meaning. For scaled L-infinity radii `(0.02,0.05,0.10)`, a sufficient grid uses
`{anisotropic.points_per_axis}` points per axis, `{anisotropic.total_points:,}`
total. Report the units and rationale for each radius.

### Distributional evaluation

For IID samples, `n >= log(alpha)/log(1-mu)`. Detecting a failure region with
mass at least 1% with 95% confidence needs `{distributional}` independent draws.
This says nothing about rare regions under another distribution, correlated
samples, or worst-case geometry.

Name both the evaluation and deployment distributions. If
`dP_deploy/dP_eval <= W`, deployment failure mass `mu` implies eval mass at least
`mu/W`. With `mu=1%`, `W=5`, and scorer sensitivity 90%, the 95%-confidence count
is `{shifted_distributional}` IID draws. If absolute continuity or finite `W`
cannot be justified, do not transfer the distributional claim. For correlated
samples, use an explicit dependence-specific bound or independent clusters;
a generic effective-sample-size estimate is not a worst-case certificate.

### Lipschitz-margin certification

If harm score `H` is `L`-Lipschitz, the tested maximum is `M`, and covering
radius is `rho`, then `sup H <= M+L*rho`. Example: `M=-0.2`, `L=2`, `rho=0.05`
gives global upper bound `{certificate.global_upper_bound:.2f}`, certified below
threshold zero. `L` must be proven or conservatively bounded over the entire
claimed domain. A held-out empirical maximum gradient is still only a lower
bound on the unknown global supremum unless an additional statistical function
class makes its upper confidence bound valid.

### Mixed discrete/continuous structure

Worst-case claims require a cover in every safety-relevant categorical stratum.
Twelve strata, three continuous dimensions, and radius 0.10 require
`{mixed:,}` Cartesian tests. If a stratum is excluded, name it and make no claim
there.
Preregister the taxonomy and declared intersection depth. Post-hoc merging or
splitting cannot upgrade the headline claim; uncovered cells remain explicit.

### Adaptive red-teaming

Adaptivity can find failures efficiently but does not itself establish coverage.
Report discovered failures separately from residual assurance. Stop only when a
stated certificate is met (covering radius, distributional confidence, or
regularity-margin bound), not merely when search stops finding new examples.
The IID formula applies only to IID draws with a fixed stopping rule. Adaptive
distributional testing needs a valid sequential method (for example, a confidence
sequence); geometric covering-radius calculations remain valid for any realized
set, adaptive or not.

### Numerical and boundary convention

Declare a compact claimed domain and use a safety factor: target measured
covering radius `rho <= (1-eta)*delta` for some reported `eta>0`, rather than
depending on floating-point equality at an open-ball boundary.

## Recommended release language

> We evaluated N unique inputs selected by [rule] over [domain] using [metric].
> This supports a [pointwise/distributional/geometric/margin-certified] claim.
> The measured covering radius is rho [or unknown]. The claim assumes [failure
> width / distribution / Lipschitz constant / strata]. No guarantee is made
> outside those assumptions.

## API adversarial review

Backend: `{backend}`. Model feedback is untrusted until locally adjudicated.

{chr(10).join(review_lines)}

## Reproduce

`python experiments/run_eval_design_recommendations.py --api-review --model stealth/ox-alpha`
"""
    OUT_MD.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
