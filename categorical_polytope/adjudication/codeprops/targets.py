"""
Functions under test, their contracts, and the properties claimed about them.

A rule in this domain is `target/property`, and a candidate is an *input*
claimed to violate it. Three pieces have to be written per target, and only the
middle one is easy to get wrong in a way that flatters the numbers:

  func      the implementation
  contract  the precondition: which inputs the function claims to handle
  property  what must hold for every input satisfying the contract

The contract is load-bearing. Narrowing it after seeing a failure is how a
property-test suite quietly reaches 100%, so contracts here are written to match
what each function actually advertises, not what it happens to survive. The
run-length coder below is the live example: it claims to encode *any* string, so
digit-bearing inputs stay in contract and its failures on them are recorded as
counterexamples rather than excused as unsupported input.

Everything is stdlib and deterministic. Nothing here consults a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

# ---------------------------------------------------------------- targets ---


def merge_intervals(intervals: Sequence[Sequence[float]]) -> list[list[float]]:
    """Merge overlapping closed intervals. Contract: each is [start, end], start <= end."""
    if not intervals:
        return []
    ordered = sorted([list(pair) for pair in intervals], key=lambda p: (p[0], p[1]))
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged


def rle_encode(text: str) -> str:
    """Run-length encode as <char><count> per run. Contract: any string."""
    if not text:
        return ""
    out: list[str] = []
    run_char, run_len = text[0], 1
    for char in text[1:]:
        if char == run_char:
            run_len += 1
        else:
            out.append(f"{run_char}{run_len}")
            run_char, run_len = char, 1
    out.append(f"{run_char}{run_len}")
    return "".join(out)


def rle_decode(encoded: str) -> str:
    """
    Inverse of `rle_encode`.

    Seeded defect, kept deliberately: the count is read as a greedy digit run,
    so any literal digit in the source text is absorbed into the preceding
    count. `rle_encode("a3")` is `"a131"`, which decodes to 131 a's. This is a
    real, common encoder bug, not a contrived one, and it is what gives this
    domain genuine counterexamples to find.
    """
    out: list[str] = []
    index = 0
    while index < len(encoded):
        char = encoded[index]
        index += 1
        digits = ""
        while index < len(encoded) and encoded[index].isdigit():
            digits += encoded[index]
            index += 1
        out.append(char * (int(digits) if digits else 1))
    return "".join(out)



def chunk(items: list, size: int) -> list[list]:
    """
    Split a list into consecutive chunks of `size`. Contract: size >= 1.

    Seeded defect: the range stops at `len(items) - size + 1`, so a trailing
    partial chunk is silently dropped. `chunk([1,2,3], 2)` loses the 3. This is
    the most common off-by-one in hand-rolled batching code.
    """
    return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]


def binary_search(items: list, target) -> int:
    """
    Index of `target` in a sorted list, or -1. Contract: items sorted ascending.

    Seeded defect: the loop condition is `lo < hi` where the inclusive bounds
    need `lo <= hi`, so the position the search converges on is never compared
    and reports as absent.

    Corrected 2026-08-26 after the campaign: this note originally said "the
    final position", which is too narrow. The generated witnesses showed
    `([1,2,3,4], 1)` failing at index 0 and `([7], 7)` failing on a
    single-element list, because the loop exits whenever lo and hi meet -
    wherever that is. The harness found a wider defect than the one seeded.
    """
    lo, hi = 0, len(items) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def truncate(text: str, limit: int) -> str:
    """
    Shorten `text` to at most `limit` characters. Contract: limit >= 1.

    Seeded defect: the ellipsis is appended *after* slicing to `limit`, so the
    result is `limit + 3` characters - the function violates the one bound it
    exists to enforce.
    """
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def nth_prime(n: int) -> int:
    """The n-th prime, 1-indexed, by trial division. Contract: n >= 1."""
    count, candidate = 0, 1
    while count < n:
        candidate += 1
        divisor, is_prime = 2, True
        while divisor * divisor <= candidate:
            if candidate % divisor == 0:
                is_prime = False
                break
            divisor += 1
        if is_prime:
            count += 1
    return candidate


def _sieve_nth_prime(n: int) -> int:
    """Independent reference for `nth_prime`, by sieve rather than division."""
    limit = 32
    while True:
        flags = bytearray([1]) * (limit + 1)
        flags[0] = flags[1] = 0
        for value in range(2, int(limit**0.5) + 1):
            if flags[value]:
                flags[value * value :: value] = bytearray(len(flags[value * value :: value]))
        primes = [i for i, flag in enumerate(flags) if flag]
        if len(primes) >= n:
            return primes[n - 1]
        limit *= 2


# -------------------------------------------------------------- contracts ---


def _contract_intervals(args: tuple) -> str | None:
    if len(args) != 1:
        return "expected exactly one argument"
    intervals = args[0]
    if not isinstance(intervals, (list, tuple)):
        return "argument must be a sequence of intervals"
    for pair in intervals:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return "each interval must be a [start, end] pair"
        start, end = pair
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (start, end)):
            return "interval bounds must be numbers"
        if start > end:
            # The single most common false positive in property testing: a
            # "failure" on input the function never claimed to accept.
            return "interval start must not exceed end"
    return None


def _contract_text(args: tuple) -> str | None:
    if len(args) != 1:
        return "expected exactly one argument"
    if not isinstance(args[0], str):
        return "argument must be a string"
    return None


def _contract_index(args: tuple) -> str | None:
    if len(args) != 1:
        return "expected exactly one argument"
    n = args[0]
    if not isinstance(n, int) or isinstance(n, bool):
        return "argument must be an integer"
    if n < 1:
        return "index must be >= 1"
    return None



def _contract_chunk(args: tuple) -> str | None:
    if len(args) != 2:
        return "expected exactly two arguments"
    items, size = args
    if not isinstance(items, list):
        return "first argument must be a list"
    if not isinstance(size, int) or isinstance(size, bool):
        return "size must be an integer"
    if size < 1:
        return "size must be >= 1"
    return None


def _contract_sorted_search(args: tuple) -> str | None:
    if len(args) != 2:
        return "expected exactly two arguments"
    items, target = args
    if not isinstance(items, list):
        return "first argument must be a list"
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in items)
    if not numeric:
        return "list items must be numbers"
    if not isinstance(target, (int, float)) or isinstance(target, bool):
        return "target must be a number"
    if any(a > b for a, b in zip(items, items[1:])):
        # The function advertises sorted input only; an unsorted list is a
        # false positive waiting to happen, not a defect.
        return "list must be sorted ascending"
    return None


def _contract_truncate(args: tuple) -> str | None:
    if len(args) != 2:
        return "expected exactly two arguments"
    text, limit = args
    if not isinstance(text, str):
        return "first argument must be a string"
    if not isinstance(limit, int) or isinstance(limit, bool):
        return "limit must be an integer"
    if limit < 1:
        return "limit must be >= 1"
    return None


# ------------------------------------------------------------- properties ---


def _prop_disjoint_and_ordered(args: tuple) -> bool:
    merged = merge_intervals(*args)
    for earlier, later in zip(merged, merged[1:]):
        if earlier[1] >= later[0]:
            return False
    return all(pair[0] <= pair[1] for pair in merged)


def _prop_covers_input(args: tuple) -> bool:
    merged = merge_intervals(*args)
    for start, end in args[0]:
        if not any(m[0] <= start and end <= m[1] for m in merged):
            return False
    return True


def _prop_rle_roundtrip(args: tuple) -> bool:
    return rle_decode(rle_encode(*args)) == args[0]


def _prop_nth_prime_matches_sieve(args: tuple) -> bool:
    return nth_prime(*args) == _sieve_nth_prime(*args)



def _prop_chunk_covers(args: tuple) -> bool:
    merged: list = []
    for piece in chunk(*args):
        merged.extend(piece)
    return merged == args[0]


def _prop_binary_search_finds_present(args: tuple) -> bool:
    items, target = args
    index = binary_search(items, target)
    if target in items:
        return index >= 0 and items[index] == target
    return index == -1


def _prop_truncate_respects_limit(args: tuple) -> bool:
    return len(truncate(*args)) <= args[1]


# -------------------------------------------------------------- registry ----


@dataclass(frozen=True)
class Rule:
    """One checkable claim about one function."""

    rule_id: str
    description: str
    contract: Callable[[tuple], str | None]
    check: Callable[[tuple], bool]


RULES: dict[str, Rule] = {
    rule.rule_id: rule
    for rule in (
        Rule(
            "merge_intervals/disjoint_and_ordered",
            "merged intervals are strictly increasing and non-overlapping",
            _contract_intervals,
            _prop_disjoint_and_ordered,
        ),
        Rule(
            "merge_intervals/covers_input",
            "every input interval lies inside some merged interval",
            _contract_intervals,
            _prop_covers_input,
        ),
        Rule(
            "rle/roundtrip",
            "decode(encode(s)) == s for any string s",
            _contract_text,
            _prop_rle_roundtrip,
        ),
        Rule(
            "chunk/covers",
            "concatenating the chunks reproduces the input list",
            _contract_chunk,
            _prop_chunk_covers,
        ),
        Rule(
            "binary_search/finds_present",
            "a target present in the sorted list is found at a matching index",
            _contract_sorted_search,
            _prop_binary_search_finds_present,
        ),
        Rule(
            "truncate/respects_limit",
            "the result never exceeds the requested character limit",
            _contract_truncate,
            _prop_truncate_respects_limit,
        ),
        Rule(
            "nth_prime/matches_sieve",
            "trial division agrees with an independent sieve",
            _contract_index,
            _prop_nth_prime_matches_sieve,
        ),
    )
}

RULE_IDS: tuple[str, ...] = tuple(RULES)


def check_contract(rule_id: str, args: tuple) -> str | None:
    """None when the input is in contract, else why it is not."""
    return RULES[rule_id].contract(tuple(args))


def check_property(rule_id: str, args: tuple) -> bool:
    """Run the property. Raises whatever the function under test raises."""
    return RULES[rule_id].check(tuple(args))
