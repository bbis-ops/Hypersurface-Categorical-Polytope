"""
Candidate generation for domain two: prompt shape and untrusted-reply parsing.

Every test here runs offline. The parser is the component that decides what a
campaign's denominator will contain, so it is worth pinning against canned
replies before any budget is spent - including the replies a real run actually
produces: truncated arrays, null content, and prose refusals.
"""

from __future__ import annotations

import json

import pytest

from categorical_polytope.adjudication.codeprops import CodePropertyDomain
from categorical_polytope.adjudication.codeprops.prompts import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_TOKENS,
    MAX_ARGS_CHARS,
    MAX_NOTE_CHARS,
    focus_prompt,
    parse_input_proposals,
    proposal_prompt,
)
from categorical_polytope.adjudication.codeprops.targets import RULE_IDS


def _reply(*items: dict) -> str:
    return json.dumps({"candidates": list(items)})


# ---------------------------------------------------------------- prompts ---


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_every_rule_has_a_prompt_that_states_its_contract(rule_id):
    prompt = proposal_prompt(rule_id, 32)
    assert rule_id in prompt
    # In-scope yield is the whole game: the contract must be spelled out, and
    # the cost of ignoring it made explicit.
    assert "CONTRACT" in prompt and "OUT OF CONTRACT" in prompt
    assert "wasted proposals" in prompt
    assert "32" in prompt


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_every_prompt_forbids_non_literal_payloads(rule_id):
    prompt = proposal_prompt(rule_id, 8)
    for banned in ("NO function calls", "NO names", "NO imports"):
        assert banned in prompt


def test_prompt_json_template_survives_formatting():
    # The literal braces in the output example must not be eaten by .format.
    prompt = proposal_prompt("rle/roundtrip", 4)
    assert '{"candidates":[{"name":"slug","args":"(...)","why":' in prompt


def test_unknown_rule_has_no_prompt():
    with pytest.raises(KeyError):
        proposal_prompt("no/such_rule", 4)


def test_focus_prompt_quotes_the_live_counterexample():
    text = focus_prompt("rle/roundtrip", "('a3',)")
    assert "('a3',)" in text and "inside the contract" in text


def test_batch_and_token_defaults_are_consistent():
    # ~100 tokens per record with a substantive `why`; the batch must sit below
    # the cap or every request risks truncating.
    assert DEFAULT_BATCH_SIZE * 100 < DEFAULT_MAX_TOKENS * 1.25


# ----------------------------------------------------------------- parser ---


def test_parses_a_well_formed_reply():
    parse = parse_input_proposals("rle/roundtrip")
    seeds = parse(_reply(
        {"name": "digit_adj", "args": "('a3',)", "why": "digit beside a letter run"},
        {"name": "empty", "args": "('',)", "why": "boundary"},
    ))
    assert [s.args for s in seeds] == ["('a3',)", "('',)"]
    assert all(s.rule_id == "rle/roundtrip" for s in seeds)
    assert seeds[0].note == "digit beside a letter run"


def test_salvages_a_reply_truncated_at_the_token_cap():
    # The failure mode a 20k-token request actually hits: finish_reason
    # "length" leaves the array open and the final record half written.
    parse = parse_input_proposals("rle/roundtrip")
    truncated = (
        '{"candidates":[{"name":"a","args":"(\'a3\',)","why":"x"},'
        '{"name":"b","args":"(\'b7\',)","why":"y"},{"name":"c","args":"(\'c'
    )
    seeds = parse(truncated)
    assert [s.name for s in seeds] == ["a", "b"], "complete records must survive"


def test_extracts_from_a_reply_wrapped_in_prose():
    parse = parse_input_proposals("rle/roundtrip")
    wrapped = "Here you go:\n" + _reply({"name": "n", "args": "('a3',)"}) + "\nHope that helps."
    assert len(parse(wrapped)) == 1


def test_null_content_is_not_an_error():
    # Some providers return content=None; that is zero candidates, not a crash.
    parse = parse_input_proposals("rle/roundtrip")
    for reply in (None, "", "   ", 42, {"candidates": []}):
        assert parse(reply) == []


def test_prose_refusal_yields_nothing():
    parse = parse_input_proposals("rle/roundtrip")
    assert parse("I'm sorry, I can't help with that.") == []


def test_duplicates_within_a_batch_are_collapsed():
    parse = parse_input_proposals("rle/roundtrip")
    seeds = parse(_reply(
        {"name": "one", "args": "('a3',)"},
        {"name": "two", "args": "('a3',)"},
        {"name": "three", "args": "('b7',)"},
    ))
    assert [s.args for s in seeds] == ["('a3',)", "('b7',)"]


def test_oversized_payloads_are_dropped():
    parse = parse_input_proposals("rle/roundtrip")
    assert parse(_reply({"name": "huge", "args": "('" + "a" * MAX_ARGS_CHARS + "',)"})) == []


def test_names_are_slugified_and_bounded():
    parse = parse_input_proposals("rle/roundtrip")
    seed = parse(_reply({"name": "bad name/with*chars!" + "x" * 60, "args": "('a',)"}))[0]
    assert len(seed.name) <= 32
    assert all(c.isalnum() or c == "_" for c in seed.name)


def test_missing_name_still_yields_a_candidate():
    parse = parse_input_proposals("rle/roundtrip")
    seeds = parse(_reply({"args": "('a3',)"}))
    assert len(seeds) == 1 and seeds[0].name


def test_notes_are_truncated_not_dropped():
    parse = parse_input_proposals("rle/roundtrip")
    seed = parse(_reply({"name": "n", "args": "('a',)", "why": "w" * 900}))[0]
    assert len(seed.note) == MAX_NOTE_CHARS


def test_non_literal_payloads_reach_the_adjudicator_rather_than_being_dropped():
    """
    A hostile or malformed payload must be counted, not silently filtered.

    Dropping it in the parser would remove it from the denominator and make the
    generator look more accurate than it was. It is kept, and the adjudicator
    records it as `rejected`.
    """
    parse = parse_input_proposals("rle/roundtrip")
    seeds = parse(_reply(
        {"name": "injection", "args": "__import__('os').system('echo pwned')"},
        {"name": "name_ref", "args": "(undefined_name,)"},
    ))
    assert len(seeds) == 2

    domain = CodePropertyDomain(timeout=5.0)
    for seed in seeds:
        assert domain.adjudicate(seed.rule_id, seed.args).status == "rejected"
