"""Executable release gates for the six conditional evaluation warnings."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Mapping
from .eval_design import distributional_samples

@dataclass(frozen=True)
class CheckResult:
    id: str
    status: str
    evidence: str
    action: str

@dataclass(frozen=True)
class ChecklistReport:
    checks: tuple[CheckResult, ...]
    @property
    def releasable(self) -> bool:
        return all(x.status == "pass" for x in self.checks)
    def as_dict(self) -> dict[str, Any]:
        return {"releasable": self.releasable, "checks": [asdict(x) for x in self.checks]}

def _yes(value: Any) -> bool:
    return value is True

def _pair(value: Any) -> frozenset[str] | None:
    return frozenset(str(x) for x in value) if isinstance(value, list) and len(value) >= 2 else None

def _pairs(values: Any) -> set[frozenset[str]]:
    return {p for p in (_pair(x) for x in values) if p is not None} if isinstance(values, list) else set()

def _result(check_id: str, passed: bool, evidence: str, action: str) -> CheckResult:
    return CheckResult(check_id, "pass" if passed else "block", evidence, action)

def evaluate_checklist(card: Mapping[str, Any]) -> ChecklistReport:
    """Evaluate all six gates. Missing or malformed evidence blocks release."""
    joint, boundary = card.get("separability", {}), card.get("boundary_margin", {})
    coverage, coupling = card.get("coverage", {}), card.get("coupled_constraints", {})
    nonsmooth, tolerance = card.get("nonsmooth_attacks", {}), card.get("tolerance", {})

    axes = joint.get("risk_axes") if isinstance(joint, Mapping) else None
    expected = ({frozenset(p) for p in combinations((str(x) for x in axes), 2)}
                if isinstance(axes, list) and len(axes) >= 2 else set())
    tested = _pairs(joint.get("tested_pairs")) if isinstance(joint, Mapping) else set()
    joint_pass = (bool(expected) and expected.issubset(tested) and _yes(joint.get("joint_score_tested"))
                  and bool(joint.get("preregistered_score_formula")) and bool(joint.get("preregistered_config_hash")))

    margins = boundary.get("certified_margin_lower_bounds") if isinstance(boundary, Mapping) else None
    required = boundary.get("required_margin") if isinstance(boundary, Mapping) else None
    boundary_rho = boundary.get("boundary_covering_radius") if isinstance(boundary, Mapping) else None
    boundary_resolution = boundary.get("maximum_boundary_resolution") if isinstance(boundary, Mapping) else None
    margin_pass = (isinstance(margins, list) and bool(margins) and isinstance(required, (int, float)) and required > 0
                   and all(isinstance(x, (int, float)) and x >= required for x in margins)
                   and isinstance(boundary_rho, (int, float)) and isinstance(boundary_resolution, (int, float))
                   and 0 <= boundary_rho <= boundary_resolution and _yes(boundary.get("adversarial_inward_search"))
                   and bool(boundary.get("search_trace_hash")))

    rho = coverage.get("measured_covering_radius") if isinstance(coverage, Mapping) else None
    delta = coverage.get("minimum_failure_radius") if isinstance(coverage, Mapping) else None
    eta = coverage.get("safety_factor") if isinstance(coverage, Mapping) else None
    coverage_pass = (isinstance(rho, (int, float)) and isinstance(delta, (int, float)) and isinstance(eta, (int, float))
                     and rho >= 0 and delta > 0 and 0 < eta < 1 and rho <= (1 - eta) * delta
                     and bool(coverage.get("metric")) and _yes(coverage.get("metric_semantically_validated"))
                     and int(coverage.get("heldout_adversarial_contrast_pairs", 0)) > 0
                     and bool(coverage.get("metric_validation_hash")) and bool(coverage.get("eval_dataset_hash"))
                     and coverage.get("metric_validation_hash") != coverage.get("eval_dataset_hash"))

    declared = _pairs(coupling.get("declared_groups")) if isinstance(coupling, Mapping) else set()
    tested_groups = _pairs(coupling.get("tested_groups")) if isinstance(coupling, Mapping) else set()
    starts = coupling.get("initializations") if isinstance(coupling, Mapping) else None
    min_starts = coupling.get("preregistered_minimum_initializations") if isinstance(coupling, Mapping) else None
    coupling_pass = (bool(declared) and declared.issubset(tested_groups) and _yes(coupling.get("joint_search_used"))
                     and isinstance(starts, int) and isinstance(min_starts, int) and starts >= min_starts > 0
                     and _yes(coupling.get("domain_spanning_initializations")) and _yes(coupling.get("historical_failures_seeded"))
                     and bool(coupling.get("search_trace_hash")))

    classes = nonsmooth.get("classes") if isinstance(nonsmooth, Mapping) else None
    nonsmooth_pass = isinstance(classes, list) and bool(classes)
    if nonsmooth_pass:
        for item in classes:
            try:
                needed = distributional_samples(float(item["minimum_success_probability"]), float(item["miss_probability"]))
                if (item.get("regularity") != "nonsmooth" or int(item["discrete_search_trials"]) < needed
                        or not item.get("search_trace_hash")):
                    nonsmooth_pass = False
                    break
            except (AttributeError, KeyError, TypeError, ValueError):
                nonsmooth_pass = False
                break

    raw_gap = tolerance.get("maximum_raw_gap") if isinstance(tolerance, Mapping) else None
    tolerance_pass = (isinstance(tolerance, Mapping) and _yes(tolerance.get("raw_scores_published"))
                      and _yes(tolerance.get("release_decision_uses_raw_scores"))
                      and isinstance(raw_gap, (int, float)) and raw_gap <= 0
                      and bool(tolerance.get("immutable_results_hash")) and bool(tolerance.get("decision_rule")))

    return ChecklistReport((
        _result("separability", joint_pass, f"{len(tested)} of {len(expected)} pairs tested with a frozen score", "Test the complete pair map and hash the preregistered joint-score formula."),
        _result("boundary_margin", margin_pass, f"certified lower bounds; boundary rho={boundary_rho!r}", "Cover the boundary and certify a positive lower margin using adversarial inward search."),
        _result("finite_coverage", coverage_pass, f"rho={rho!r}, delta={delta!r}, eta={eta!r}", "Validate the metric on a disjoint adversarial holdout and achieve rho <= (1-eta)*delta."),
        _result("coupled_constraints", coupling_pass, f"{len(tested_groups)} groups; {starts!r} starts", "Test every multi-axis group with domain-spanning and historical-failure seeds."),
        _result("nonsmooth_attacks", nonsmooth_pass, "per-class trials checked against declared detection mass", "Meet the computed per-class budget and retain each search trace."),
        _result("tolerance", tolerance_pass, f"maximum raw gap={raw_gap!r}", "Make the immutable raw gap—not a rounded display value—the release input."),
    ))
