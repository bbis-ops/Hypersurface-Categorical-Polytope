# Multi-domain adversarial campaign

Every domain below is adjudicated by a machine that is ground truth for its
own rules - stdlib arithmetic, or CPython running a reference implementation.
No verdict anywhere in this table came from a model's opinion.

Only `verified` is a pass. Candidates the adjudicator could not decide stay in
the corpus and stay counted, so the denominator cannot be improved by dropping
the hard cases.

| Domain | verifier | corpus | verified | counterexamples | outside scope | undecided | refused | in-scope denominator |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `polytope` | v17 | 1907 | 1184 | 0 | 327 | 287 | 109 | 1184 |
| `codeprops` | v1 | 496 | 283 | 181 | 11 | 8 | 13 | 464 |
| `polyhedra` | v11 | 386 | 213 | 2 | 119 | 11 | 41 | 215 |
| **total** | | **2789** | **1680** | **183** | **457** | **306** | **163** | **1863** |

## Domains

### `polytope`

- V.7-V.14 vertex-localization laws; adjudicator is stdlib arithmetic
- Rules: 8
- Reversals retained: 216
- Report: [`docs/VERIFICATION_CERTIFICATE.md`](VERIFICATION_CERTIFICATE.md)

### `codeprops`

- reference-implementation property violation; adjudicator is CPython
- Rules: 7
- Reversals retained: 0
- Report: [`docs/CODE_PROPERTIES.md`](CODE_PROPERTIES.md)

### `polyhedra`

- exponent laws on a general polytope, measured in edge vs ambient coordinates; adjudicator is stdlib arithmetic
- Rules: 3
- Reversals retained: 17
- Report: [`docs/POLYHEDRA.md`](POLYHEDRA.md)

## Campaign accounting

- Requests logged: **261**
- Parse-valid items before deduplication: **3065**
- Provider-reported total tokens: **1,558,595**
- Mean tokens per request: **5,972**

## Counterexamples across all domains

- `codeprops` / `rle/roundtrip` / digit_in_source: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_after_run: property failed on an in-contract input
- `codeprops` / `chunk/covers` / leaves_remainder: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_exceeds_list: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / target_first: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / target_last: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / single_item: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / adj_letter_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / adj_digits: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / only_digits: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / end_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / whitespace_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_ascii_adjacent: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_size_minus_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_between: property failed on an in-contract input
- `codeprops` / `chunk/covers` / nested_list_elems: property failed on an in-contract input
- `codeprops` / `chunk/covers` / string_elems: property failed on an in-contract input
- `codeprops` / `chunk/covers` / mixed_literal_types: property failed on an in-contract input
- `codeprops` / `chunk/covers` / tuple_elems: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_pos: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / one_elem: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_float: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_multi: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_only: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / newline_inside: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / tab_char: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / mixed_ascii_unicode: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / adj_letter_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / long_digit_run: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / only_digits: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / start_end_digits: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_adj_ascii_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / letter_run_adj_digits: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_pos: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_last: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_two_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_two_whitespace: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digits_adj_letter: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_at_end: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / multiple_digit_runs: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_size_minus_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_between: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_greater_than_list: property failed on an in-contract input
- `codeprops` / `chunk/covers` / single_element: property failed on an in-contract input
- `codeprops` / `chunk/covers` / nested_lists: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_second: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_float: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over_limit: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over_limit: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_two: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_emoji: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / newline_chars: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / astral_char: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digits_start_end: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / ascii_unicode_adjacent1: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_ascii_adjacent2: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / space_space_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / tab_before_digit: property failed on an in-contract input
- `codeprops` / `chunk/covers` / other_remainder: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_greater_than_list: property failed on an in-contract input
- `codeprops` / `chunk/covers` / elements_are_lists: property failed on an in-contract input
- `codeprops` / `chunk/covers` / elements_are_strings: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_pos: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / one_elem: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_float: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_float: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_between_letters: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_start_end: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / whitespace_with_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / alternating_digit_letter: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digits_with_newline_internal: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / negative: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / tab_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / combining_char: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / ascii_unicode_mix_over: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_digit_adjacent: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_digit_adjacent: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / whitespace_digit_adjacent: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_with_newline: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / mixed_whitespace_digits: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / middle_remainder: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_exceeds_list: property failed on an in-contract input
- `codeprops` / `chunk/covers` / nested_list_elements: property failed on an in-contract input
- `codeprops` / `chunk/covers` / string_elements: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_last: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / three_elem_first: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / three_elem_last: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_vals: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_first: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_last: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_mid_miss: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / digit_after_letter: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / long_digit_run: raised on an in-contract input: OverflowError: cannot fit 'int' into an index-sized integer
- `codeprops` / `rle/roundtrip` / unicode_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / whitespace_adjacent: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / newline_adjacent: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / long_uniform_with_digit_inside: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_size_minus_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / remainder_middle: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_greater_than_list: property failed on an in-contract input
- `codeprops` / `chunk/covers` / single_element: property failed on an in-contract input
- `codeprops` / `chunk/covers` / nested_lists: property failed on an in-contract input
- `codeprops` / `chunk/covers` / string_elements: property failed on an in-contract input
- `codeprops` / `chunk/covers` / mixed_literals: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / negative_numbers: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_list_midpoint: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / mixed_neg_float: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over_ascii: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over_unicode: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one_unicode: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_over: property failed on an in-contract input
- `codeprops` / `chunk/covers` / rem_size_minus_one: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_big: property failed on an in-contract input
- `codeprops` / `chunk/covers` / elem_lists: property failed on an in-contract input
- `codeprops` / `chunk/covers` / elem_none: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_elem: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_second: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_value: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_float_mix: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over_limit: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over_limit: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / small_limit_two: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_emoji: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_only: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one_char_over_unicode: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / whitespace_limit_one: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / unicode_digit: property failed on an in-contract input
- `codeprops` / `chunk/covers` / singleton_oversize: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_exceeds: property failed on an in-contract input
- `codeprops` / `chunk/covers` / string_elements: property failed on an in-contract input
- `codeprops` / `chunk/covers` / mixed_types: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / last_elem: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_last: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / neg_float: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_mid_miss: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_one_unicode: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / limit_two: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / mixed_whitespace: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / only_digits_large: raised on an in-contract input: OverflowError: cannot fit 'int' into an index-sized integer
- `codeprops` / `rle/roundtrip` / unicode_digits: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / alternating_letter_digit: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / multiple_digit_runs: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / leading_zeros_string: property failed on an in-contract input
- `codeprops` / `rle/roundtrip` / ends_with_digit_run: property failed on an in-contract input
- `codeprops` / `chunk/covers` / test_size_larger: property failed on an in-contract input
- `codeprops` / `chunk/covers` / test_nested_lists: property failed on an in-contract input
- `codeprops` / `chunk/covers` / test_mixed_types: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / negative_float: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / long_list_missed_mid: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / two_elem_last: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / far_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / combining_accent: property failed on an in-contract input
- `codeprops` / `chunk/covers` / size_greater_than_list: property failed on an in-contract input
- `codeprops` / `chunk/covers` / list_of_strings: property failed on an in-contract input
- `codeprops` / `binary_search/finds_present` / negative_vals: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / one_over: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / unicode_mb: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / newline_text: property failed on an in-contract input
- `codeprops` / `truncate/respects_limit` / combining_chars: property failed on an in-contract input
- `polyhedra` / `polyhedron/ambient_exponent_law` / simplex_quartic_ambient: exponent mismatch (|1.333 - 2.000| >= 0.200)
- `polyhedra` / `polyhedron/ambient_exponent_law` / sheared_quartic_ambient: exponent mismatch (|1.333 - 2.000| >= 0.200)
