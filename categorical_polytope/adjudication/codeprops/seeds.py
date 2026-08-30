"""
Hand-written seed candidates for domain two.

The equivalent of domain one's `BUILTIN_CANDIDATES`: enough inputs to exercise
every path in the adjudicator without spending a single API call. A model is
useful here only for volume and adversarial variety, and only once the seam
below is known to hold.

The bank is deliberately unflattering. Roughly half the entries are inputs the
functions never claimed to accept, because a seed bank of only valid inputs
would never exercise the contract guard - and the contract guard is the part
that decides whether this domain's denominator means anything.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Seed:
    """One hand-written candidate input."""

    rule_id: str
    name: str
    #: Python literal for the argument tuple. Never evaluated as code.
    args: str
    note: str = ""


SEEDS: tuple[Seed, ...] = (
    # -- in contract, property should hold ---------------------------------
    Seed("merge_intervals/disjoint_and_ordered", "overlapping_pair",
         "([[1, 3], [2, 6], [8, 10]],)", "classic merge"),
    Seed("merge_intervals/disjoint_and_ordered", "already_disjoint",
         "([[1, 2], [5, 6]],)", "nothing to merge"),
    Seed("merge_intervals/disjoint_and_ordered", "empty",
         "([],)", "boundary: no intervals"),
    Seed("merge_intervals/covers_input", "fully_nested",
         "([[1, 10], [2, 3]],)", "containment, not overlap"),
    Seed("merge_intervals/covers_input", "touching_endpoints",
         "([[1, 2], [2, 3]],)", "closed intervals share an endpoint"),
    Seed("merge_intervals/covers_input", "unsorted_input",
         "([[8, 10], [1, 3], [2, 6]],)", "order must not matter"),
    Seed("rle/roundtrip", "simple_runs", "('aaabbc',)", "no digits, should hold"),
    Seed("rle/roundtrip", "empty_string", "('',)", "boundary: empty"),
    Seed("rle/roundtrip", "single_char", "('a',)", "boundary: one run"),
    Seed("nth_prime/matches_sieve", "first", "(1,)", "boundary: n = 1"),
    Seed("nth_prime/matches_sieve", "small", "(50,)", "cheap agreement check"),

    # -- in contract, property should fail (real defect) --------------------
    Seed("rle/roundtrip", "digit_in_source", "('a3',)",
         "count absorbs the literal digit; genuine encoder defect"),
    # Survives: "11" is one run, encoding to "12", which decodes cleanly. Kept
    # because it bounds the defect - a digit in the source is not sufficient to
    # break the round trip, so a fix must not be judged by digit-presence alone.
    Seed("rle/roundtrip", "digits_only_single_run", "('11',)",
         "digit-bearing but round-trips; bounds the defect"),
    Seed("rle/roundtrip", "digit_after_run", "('aab7',)",
         "defect survives a preceding multi-char run"),

    # -- out of contract: must be excused, and only before the run ----------
    Seed("merge_intervals/disjoint_and_ordered", "reversed_bounds",
         "([[5, 1]],)", "start > end: never supported"),
    Seed("merge_intervals/covers_input", "triple_not_pair",
         "([[1, 2, 3]],)", "not a [start, end] pair"),
    Seed("merge_intervals/covers_input", "string_bounds",
         "([['a', 'b']],)", "bounds are not numbers"),
    Seed("rle/roundtrip", "not_a_string", "(123,)", "wrong argument type"),
    Seed("nth_prime/matches_sieve", "zero_index", "(0,)", "index below 1"),
    Seed("nth_prime/matches_sieve", "negative_index", "(-5,)", "index below 1"),

    # -- in contract, but the verifier cannot decide ------------------------
    Seed("nth_prime/matches_sieve", "beyond_budget", "(400000,)",
         "trial division exceeds the wall clock; undecided, not passing"),

    # -- refused at the sandbox boundary ------------------------------------
    Seed("rle/roundtrip", "import_injection",
         "__import__('os').system('echo pwned')",
         "hostile payload: literal_eval refuses to build it"),
    Seed("rle/roundtrip", "name_reference", "(undefined_name,)",
         "not a literal"),
    Seed("merge_intervals/covers_input", "call_expression", "(list(range(3)),)",
         "calls are not literals"),

    # -- the three newer targets: in contract, and each defect is reachable --
    Seed("chunk/covers", "exact_multiple", "([1, 2, 3, 4], 2)", "no remainder; should hold"),
    Seed("chunk/covers", "leaves_remainder", "([1, 2, 3], 2)", "trailing partial chunk is dropped"),
    Seed("chunk/covers", "size_one", "([1, 2, 3], 1)", "boundary: size 1"),
    Seed("chunk/covers", "size_exceeds_list", "([1, 2], 5)", "whole list is the remainder"),
    Seed("chunk/covers", "empty_list", "([], 3)", "boundary: nothing to chunk"),
    Seed("chunk/covers", "zero_size", "([1, 2], 0)", "size < 1: out of contract"),
    Seed("binary_search/finds_present", "target_first", "([1, 2, 3, 4], 1)", "first position"),
    Seed("binary_search/finds_present", "target_last", "([1, 2, 3, 4], 4)", "last position; the off-by-one"),
    Seed("binary_search/finds_present", "target_middle", "([1, 2, 3, 4, 5], 3)", "midpoint hit"),
    Seed("binary_search/finds_present", "single_item", "([7], 7)", "boundary: one element"),
    Seed("binary_search/finds_present", "absent_in_range", "([1, 3, 5], 4)", "absent; must report -1"),
    Seed("binary_search/finds_present", "unsorted", "([3, 1, 2], 2)", "unsorted: out of contract"),
    Seed("truncate/respects_limit", "under_limit", "('abc', 10)", "no truncation needed"),
    Seed("truncate/respects_limit", "exactly_limit", "('abcde', 5)", "boundary: exact fit"),
    Seed("truncate/respects_limit", "one_over", "('abcdef', 5)", "ellipsis pushes past the limit"),
    Seed("truncate/respects_limit", "far_over", "('abcdefghijklmnop', 4)", "same defect, longer input"),
    Seed("truncate/respects_limit", "zero_limit", "('abc', 0)", "limit < 1: out of contract"),
)
