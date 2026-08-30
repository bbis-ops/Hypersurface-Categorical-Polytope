"""
Candidate generation for domain two: prompts and an untrusted-reply parser.

The model proposes *inputs*; nothing it returns is trusted. Every payload is a
string until `CodePropertyDomain.parse` puts it through `literal_eval`, and no
verdict here depends on which model produced it. This module only decides what
to ask for and how to read the answer.

Sizing a batch
--------------
Tokens per record depend on the model and on how much rationale it writes, so
the defaults below are a starting point to be measured, not a prediction:
`run_code_properties.py --calibrate` reports the real figure after one batch.

Two forces set the batch size. A completion budget only buys candidates if the
batch is large enough to spend it, but a model that cannot hold a long
structured reply together will truncate - and a small-active-parameter MoE
truncates sooner than its context window suggests. A truncated reply returns
`finish_reason="length"` and an unclosed array, so the salvage path in
`parse_input_proposals` is what keeps an oversized batch from costing the whole
request.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .seeds import Seed
from .targets import RULES

#: Longest `why` retained. Rationale lands in the record's `note`, so it is
#: worth keeping far more of than domain one's 80-character cap.
MAX_NOTE_CHARS = 240

#: Guard against a runaway payload consuming the corpus.
MAX_ARGS_CHARS = 4000

#: Batch size that fills a ~20k completion without courting truncation.
DEFAULT_BATCH_SIZE = 128

#: Completion cap paired with the batch size above.
DEFAULT_MAX_TOKENS = 20000


# ----------------------------------------------------------------- prompts ---

_CONTRACTS: dict[str, str] = {
    "merge_intervals/disjoint_and_ordered": (
        "args is a 1-tuple holding a list of [start, end] pairs. Every pair must have "
        "exactly two numeric bounds (int or float, never bool, never a string), and "
        "start <= end for EVERY pair. A pair with start > end, a non-numeric bound, or "
        "a length other than two is OUT OF CONTRACT and will be discarded."
    ),
    "merge_intervals/covers_input": (
        "args is a 1-tuple holding a list of [start, end] pairs. Every pair must have "
        "exactly two numeric bounds (int or float, never bool, never a string), and "
        "start <= end for EVERY pair. A pair with start > end, a non-numeric bound, or "
        "a length other than two is OUT OF CONTRACT and will be discarded."
    ),
    "rle/roundtrip": (
        "args is a 1-tuple holding a single Python string. Any string is in contract, "
        "including empty, unicode, whitespace, and strings containing digits. A "
        "non-string argument is OUT OF CONTRACT and will be discarded."
    ),
    "chunk/covers": (
        "args is a 2-tuple (items, size). `items` must be a list of any literal values; "
        "`size` must be an integer >= 1 and never a bool. A non-list first argument, a "
        "non-integer size, or size < 1 is OUT OF CONTRACT and will be discarded."
    ),
    "binary_search/finds_present": (
        "args is a 2-tuple (items, target). `items` must be a list of numbers sorted "
        "ascending, and `target` must be a number. An unsorted list, non-numeric "
        "entries, or a non-numeric target is OUT OF CONTRACT and will be discarded - "
        "the function only ever claimed to search sorted numeric input."
    ),
    "truncate/respects_limit": (
        "args is a 2-tuple (text, limit). `text` must be a string; `limit` must be an "
        "integer >= 1 and never a bool. A non-string text, non-integer limit, or "
        "limit < 1 is OUT OF CONTRACT and will be discarded."
    ),
    "nth_prime/matches_sieve": (
        "args is a 1-tuple holding a single integer n with n >= 1. A non-integer, a "
        "bool, or n < 1 is OUT OF CONTRACT and will be discarded. Very large n is IN "
        "contract but may exceed the wall-clock budget and be recorded as undecided "
        "rather than as a failure."
    ),
}

_ATTACKS: dict[str, str] = {
    "merge_intervals/disjoint_and_ordered": (
        "Attack the claim that merged output is strictly increasing and non-overlapping. "
        "Cover, as separate families: intervals touching exactly at an endpoint; "
        "zero-width intervals where start == end; duplicated pairs; one interval "
        "containing many others; long chains where each overlaps only its neighbour; "
        "float bounds that collide under rounding; very large and very small "
        "magnitudes; negative bounds; input already sorted, reverse sorted, and "
        "shuffled; and the empty list."
    ),
    "merge_intervals/covers_input": (
        "Attack the claim that every input interval lies inside some merged interval. "
        "Cover, as separate families: full containment; chains merging transitively; "
        "endpoint-only contact; zero-width intervals at the boundary of a merge; "
        "duplicates; float bounds whose sum or comparison is inexact; mixed int and "
        "float bounds for the same interval; and large magnitude gaps."
    ),
    "rle/roundtrip": (
        "Attack the claim that decode(encode(s)) == s. The decoder reads a run count "
        "as a greedy digit sequence, so digits in the source are the obvious lead - but "
        "do not stop there. Cover, as separate families: digits adjacent to a letter "
        "run; digits adjacent to other digits; digit runs of length 10 or more so the "
        "count itself is multi-digit; strings that are only digits; digits at the very "
        "start and very end; unicode digits; whitespace and newlines; the empty string; "
        "single characters; and very long uniform runs."
    ),
    "chunk/covers": (
        "Attack the claim that concatenating the chunks reproduces the input. Cover, as "
        "separate families: lengths that are exact multiples of size; lengths leaving a "
        "remainder of one, of size-1, and everything between; size == 1; size larger "
        "than the whole list; the empty list; single-element lists; and lists whose "
        "elements are themselves lists or strings."
    ),
    "binary_search/finds_present": (
        "Attack the claim that a present target is found. Cover, as separate families: "
        "the target at the very first and very last positions; two-element and "
        "one-element lists; duplicated values; targets absent but within range; targets "
        "outside the range on both sides; negative and float values; and long lists "
        "where the target sits at an index the midpoint sequence never visits."
    ),
    "truncate/respects_limit": (
        "Attack the claim that the result never exceeds the limit. Cover, as separate "
        "families: text exactly at the limit; text one character over; text far over; "
        "limit == 1 and other small limits; unicode and multi-byte characters; "
        "whitespace-only text; and the empty string."
    ),
    "nth_prime/matches_sieve": (
        "Attack the claim that trial division agrees with an independent sieve. Cover, "
        "as separate families: n = 1 and other small boundaries; n just below and above "
        "powers of two; n where the n-th prime is just above a perfect square (the "
        "divisor*divisor <= candidate loop boundary); n around the sieve's internal "
        "limit doubling; and a few large n that probe the wall-clock budget."
    ),
}

_TEMPLATE = """You are a hostile property-based testing engineer. Propose {n} distinct INPUTS \
designed to falsify a stated property of a Python function.

RULE: {rule_id}
PROPERTY: {description}

CONTRACT (read carefully - this decides whether your input counts):
{contract}

Inputs that violate the contract are recorded as out-of-contract and are NOT counted \
as findings. They are wasted proposals. Stay strictly inside the contract; the goal is \
to break the property using input the function genuinely claims to handle.

{attacks}

SYNTAX RULES (violations are discarded):
- "args" must be a Python literal for the argument TUPLE, e.g. "([[1, 3], [2, 6]],)" \
or "('a3',)" or "(50,)".
- A one-argument tuple needs its trailing comma.
- Literals only: numbers, strings, True, False, None, lists, tuples, dicts, sets. \
NO function calls, NO names, NO imports, NO operators, NO comprehensions.
- Keep each "args" under 300 characters.
- Every "args" in this batch must be distinct.

Give each candidate a distinct short snake_case "name" and a "why" of AT MOST 10 \
WORDS naming the attack family. Do not explain your reasoning: a long "why" is \
truncated and wastes budget that would have bought more candidates. Vary the \
families; {n} near-identical inputs are worth far less than {n} spread across them.

Output the JSON object and nothing else. No preamble, no plan, no commentary.

Reply with JSON only, no prose before or after:
{{"candidates":[{{"name":"slug","args":"(...)","why":"attack family and expectation"}}]}}
"""


def proposal_prompt(rule_id: str, n: int) -> str:
    """The generation prompt for one rule."""
    if rule_id not in RULES:
        raise KeyError(f"unknown rule: {rule_id}")
    return _TEMPLATE.format(
        n=n,
        rule_id=rule_id,
        description=RULES[rule_id].description,
        contract=_CONTRACTS[rule_id],
        attacks=_ATTACKS[rule_id],
    )


def focus_prompt(rule_id: str, args_literal: str) -> str:
    """Ask for mutations of a candidate that already broke the property."""
    return (
        f"\n\nA current counterexample for {rule_id} is args={args_literal}. Generate "
        "structural, length, coefficient, and encoding variants of it that stay inside "
        "the contract, and probe whether the same defect survives each variation."
    )


# ------------------------------------------------------------------ parser ---

_ITEM = re.compile(r"\{[^{}]*\"args\"[^{}]*\}", re.DOTALL)
_SLUG = re.compile(r"[^A-Za-z0-9_]")


def _items(text: str) -> list[dict[str, Any]]:
    """
    Pull candidate objects out of a reply, salvaging a truncated one.

    A large batch that hits the completion cap comes back as a partial JSON
    array. Parsing it strictly would throw away every complete record it does
    contain - the whole point of a big token budget - so on failure we fall
    back to extracting the individual objects that did close.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None

    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return [item for item in payload["candidates"] if isinstance(item, dict)]

    salvaged: list[dict[str, Any]] = []
    for chunk in _ITEM.findall(text):
        try:
            item = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            salvaged.append(item)
    return salvaged


def parse_input_proposals(rule_id: str) -> Callable[[Any], list[Seed]]:
    """
    Build a parser for one rule, matching `propose_candidates(parser=...)`.

    Deliberately does no content filtering. A payload that is not a valid
    literal is kept and allowed to reach the adjudicator, which records it as
    `rejected`. Dropping it here instead would erase it from the denominator
    and make the generator look more accurate than it was - the same
    bookkeeping failure the harness exists to prevent. Only structural
    nonsense (a missing or oversized `args`) is discarded.
    """

    def parse(text: Any) -> list[Seed]:
        # A reply can be non-string when a provider returns null content.
        if not isinstance(text, str) or not text.strip():
            return []

        out: list[Seed] = []
        seen: set[str] = set()
        for item in _items(text):
            args = str(item.get("args", "")).strip()
            if not args or len(args) > MAX_ARGS_CHARS or args in seen:
                continue
            seen.add(args)
            name = _SLUG.sub("_", str(item.get("name", "")).strip())[:32]
            out.append(Seed(
                rule_id=rule_id,
                name=name or f"proposed_{len(out)}",
                args=args,
                note=str(item.get("why", "")).strip()[:MAX_NOTE_CHARS],
            ))
        return out

    return parse
