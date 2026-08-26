import copy
import json
from pathlib import Path

from categorical_polytope.eval_checklist import evaluate_checklist


def complete_card():
    path = Path(__file__).resolve().parents[1] / "experiments" / "eval_checklist_example.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_complete_card_passes():
    report = evaluate_checklist(complete_card())
    assert report.releasable
    assert len(report.checks) == 6


def test_missing_evidence_blocks_instead_of_defaulting_to_pass():
    report = evaluate_checklist({})
    assert not report.releasable
    assert all(item.status == "block" for item in report.checks)


def test_radius_safety_factor_is_enforced():
    card = copy.deepcopy(complete_card())
    card["coverage"]["measured_covering_radius"] = 0.046
    report = evaluate_checklist(card)
    assert next(x for x in report.checks if x.id == "finite_coverage").status == "block"


def test_uncovered_combination_blocks():
    card = copy.deepcopy(complete_card())
    card["coupled_constraints"]["declared_groups"].append(["persuasion", "privacy"])
    report = evaluate_checklist(card)
    assert next(x for x in report.checks if x.id == "coupled_constraints").status == "block"


def test_positive_raw_gap_blocks_even_when_small():
    card = copy.deepcopy(complete_card())
    card["tolerance"]["maximum_raw_gap"] = 1e-12
    report = evaluate_checklist(card)
    assert next(x for x in report.checks if x.id == "tolerance").status == "block"


def test_nonsmooth_budget_is_computed():
    card = copy.deepcopy(complete_card())
    card["nonsmooth_attacks"]["classes"][0]["discrete_search_trials"] = 298
    report = evaluate_checklist(card)
    assert next(x for x in report.checks if x.id == "nonsmooth_attacks").status == "block"
