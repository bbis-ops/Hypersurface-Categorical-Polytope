# Domain two: generated-code property violation

Backend: `HTTP 429`. Adjudicator: CPython running a reference implementation.
Model proposals are candidate *inputs* only; every payload passes `literal_eval`
and is adjudicated locally, so no verdict depends on which model produced it.

Local adjudicator version: **1**.

`outside_scope` is decided from the declared contract *before* the property is
run, so a failing input can never be retired as unsupported after the fact.

| Rule | corpus | verified | counterexamples | outside contract | rejected/inconclusive |
|---|---:|---:|---:|---:|---:|
| `merge_intervals/disjoint_and_ordered` | 62 | 61 | 0 | 1 | 0 |
| `merge_intervals/covers_input` | 46 | 43 | 0 | 2 | 1 |
| `rle/roundtrip` | 90 | 31 | 47 | 2 | 10 |
| `chunk/covers` | 78 | 28 | 45 | 1 | 4 |
| `binary_search/finds_present` | 94 | 55 | 37 | 1 | 1 |
| `truncate/respects_limit` | 95 | 41 | 52 | 2 | 0 |
| `nth_prime/matches_sieve` | 31 | 24 | 0 | 2 | 5 |

## Denominator

- Retained corpus: **496**
- In-scope (verified + counterexample): **464**
- Out of contract, never counted as a pass: **11**
- Undecided within budget: **8**
- Refused at the `literal_eval` boundary: **13**

## Campaign accounting

- Requests logged: **65**
- Parse-valid items returned before deduplication: **661**
- Provider-reported prompt tokens: **34,887**
- Provider-reported completion tokens: **338,281**
- Provider-reported total tokens: **373,168**
- Mean tokens per request: **5,741**

## Counterexamples

### `rle/roundtrip` / digit_in_source

- Input: `('a3',)`
- Reason: property failed on an in-contract input
- Note: count absorbs the literal digit; genuine encoder defect

### `rle/roundtrip` / digit_after_run

- Input: `('aab7',)`
- Reason: property failed on an in-contract input
- Note: defect survives a preceding multi-char run

### `chunk/covers` / leaves_remainder

- Input: `([1, 2, 3], 2)`
- Reason: property failed on an in-contract input
- Note: trailing partial chunk is dropped

### `chunk/covers` / size_exceeds_list

- Input: `([1, 2], 5)`
- Reason: property failed on an in-contract input
- Note: whole list is the remainder

### `binary_search/finds_present` / target_first

- Input: `([1, 2, 3, 4], 1)`
- Reason: property failed on an in-contract input
- Note: first position

### `binary_search/finds_present` / target_last

- Input: `([1, 2, 3, 4], 4)`
- Reason: property failed on an in-contract input
- Note: last position; the off-by-one

### `binary_search/finds_present` / single_item

- Input: `([7], 7)`
- Reason: property failed on an in-contract input
- Note: boundary: one element

### `truncate/respects_limit` / one_over

- Input: `('abcdef', 5)`
- Reason: property failed on an in-contract input
- Note: ellipsis pushes past the limit

### `truncate/respects_limit` / far_over

- Input: `('abcdefghijklmnop', 4)`
- Reason: property failed on an in-contract input
- Note: same defect, longer input

### `rle/roundtrip` / adj_letter_digit

- Input: `('a3b',)`
- Reason: property failed on an in-contract input
- Note: digit inside letter run causes count/char confusion

### `rle/roundtrip` / adj_digits

- Input: `('12',)`
- Reason: property failed on an in-contract input
- Note: adjacent digit runs produce ambiguous count parsing

### `rle/roundtrip` / only_digits

- Input: `('12345',)`
- Reason: property failed on an in-contract input
- Note: string of only digits yields no trailing character

### `rle/roundtrip` / end_digit

- Input: `('abc3',)`
- Reason: property failed on an in-contract input
- Note: trailing digit leaves no character after count in decoding

### `rle/roundtrip` / whitespace_digit

- Input: `(' 2',)`
- Reason: property failed on an in-contract input
- Note: whitespace before digit lets count swallow the digit

### `rle/roundtrip` / unicode_ascii_adjacent

- Input: `('5\u0660',)`
- Reason: property failed on an in-contract input
- Note: ascii digit before unicode digit blocks proper decoding

### `chunk/covers` / remainder_one

- Input: `([1, 2, 3, 4, 5], 4)`
- Reason: property failed on an in-contract input
- Note: remainder one

### `chunk/covers` / remainder_size_minus_one

- Input: `([1, 2, 3, 4, 5], 3)`
- Reason: property failed on an in-contract input
- Note: remainder size-1

### `chunk/covers` / remainder_between

- Input: `([1, 2, 3, 4, 5, 6, 7, 8], 5)`
- Reason: property failed on an in-contract input
- Note: remainder between

### `chunk/covers` / nested_list_elems

- Input: `([[1, 2], [3, 4], []], 2)`
- Reason: property failed on an in-contract input
- Note: nested list elements

### `chunk/covers` / string_elems

- Input: `(['a', 'bb', 'ccc'], 2)`
- Reason: property failed on an in-contract input
- Note: string elements

### `chunk/covers` / mixed_literal_types

- Input: `([None, True, False, 0, ''], 3)`
- Reason: property failed on an in-contract input
- Note: mixed literal types

### `chunk/covers` / tuple_elems

- Input: `([(1, 2), (3, 4), (5,)], 2)`
- Reason: property failed on an in-contract input
- Note: tuple elements

### `binary_search/finds_present` / last_pos

- Input: `([1, 2, 3, 4, 5], 5)`
- Reason: property failed on an in-contract input
- Note: last element

### `binary_search/finds_present` / one_elem

- Input: `([42], 42)`
- Reason: property failed on an in-contract input
- Note: single‑element list

### `binary_search/finds_present` / neg_float

- Input: `([-5.5, -2, 0, 3.2, 7], -2)`
- Reason: property failed on an in-contract input
- Note: negative and float values

### `truncate/respects_limit` / one_over

- Input: `("abcdefghijk", 10)`
- Reason: property failed on an in-contract input
- Note: off‑by‑one overflow returns extra char

### `truncate/respects_limit` / far_over

- Input: `("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 5)`
- Reason: property failed on an in-contract input
- Note: massive overflow returns unchanged input exceeding limit

### `truncate/respects_limit` / limit_one

- Input: `("hello", 1)`
- Reason: property failed on an in-contract input
- Note: single char limit returns longer string

### `truncate/respects_limit` / unicode_multi

- Input: `("🚀🚀🚀🚀🚀", 3)`
- Reason: property failed on an in-contract input
- Note: unicode grapheme cluster exceeds limit

### `truncate/respects_limit` / whitespace_only

- Input: `("   \t\n   ", 2)`
- Reason: property failed on an in-contract input
- Note: whitespace string not trimmed causing overflow

### `truncate/respects_limit` / newline_inside

- Input: `("line\nline2", 5)`
- Reason: property failed on an in-contract input
- Note: internal newline counted as one char but output duplicates

### `truncate/respects_limit` / tab_char

- Input: `("a\tb\tc", 3)`
- Reason: property failed on an in-contract input
- Note: tab treated as single char causing excess

### `truncate/respects_limit` / mixed_ascii_unicode

- Input: `("ab🚀cd", 4)`
- Reason: property failed on an in-contract input
- Note: mixed ascii‑unicode length miscalc leads overflow

### `rle/roundtrip` / adj_letter_digit

- Input: `('a12b',)`
- Reason: property failed on an in-contract input
- Note: digits adj letter run

### `rle/roundtrip` / long_digit_run

- Input: `('a1111111111b',)`
- Reason: property failed on an in-contract input
- Note: digit run length >=10 multi-digit count

### `rle/roundtrip` / only_digits

- Input: `('123',)`
- Reason: property failed on an in-contract input
- Note: string only digits

### `rle/roundtrip` / start_end_digits

- Input: `('1abc2',)`
- Reason: property failed on an in-contract input
- Note: digits at start and end

### `rle/roundtrip` / unicode_digit

- Input: `('a١b',)`
- Reason: property failed on an in-contract input
- Note: unicode digit interpreted as count

### `rle/roundtrip` / unicode_adj_ascii_digit

- Input: `('\u06612',)`
- Reason: property failed on an in-contract input
- Note: unicode digit adjacent ascii digit causes overrun

### `rle/roundtrip` / letter_run_adj_digits

- Input: `('aa12bb',)`
- Reason: property failed on an in-contract input
- Note: multi-digit letter run adjacent digits causes overrun

### `binary_search/finds_present` / last_pos

- Input: `([1,2,3,4,5], 5)`
- Reason: property failed on an in-contract input
- Note: target at last position

### `binary_search/finds_present` / two_elem_last

- Input: `([10,20], 20)`
- Reason: property failed on an in-contract input
- Note: two-element list, target last

### `truncate/respects_limit` / far_over

- Input: `('aaaaaaaaaa', 3)`
- Reason: property failed on an in-contract input
- Note: text far over limit

### `truncate/respects_limit` / limit_one

- Input: `('ab', 1)`
- Reason: property failed on an in-contract input
- Note: limit == 1 with longer text

### `truncate/respects_limit` / unicode_over

- Input: `('😀😀', 1)`
- Reason: property failed on an in-contract input
- Note: unicode multi-byte characters over limit

### `truncate/respects_limit` / whitespace_over

- Input: `('      ', 5)`
- Reason: property failed on an in-contract input
- Note: whitespace-only text over limit

### `truncate/respects_limit` / limit_two_over

- Input: `('abc', 2)`
- Reason: property failed on an in-contract input
- Note: limit == 2 text one character over

### `truncate/respects_limit` / limit_two_whitespace

- Input: `('   ', 2)`
- Reason: property failed on an in-contract input
- Note: limit == 2 whitespace-only text over limit

### `rle/roundtrip` / digits_adj_letter

- Input: `('a1b',)`
- Reason: property failed on an in-contract input
- Note: digits adjacent to letter run

### `rle/roundtrip` / digit_at_end

- Input: `('abc1',)`
- Reason: property failed on an in-contract input
- Note: digit at very end of string

### `rle/roundtrip` / unicode_digit

- Input: `('a٠b',)`
- Reason: property failed on an in-contract input
- Note: unicode digit interferes with decoding

### `rle/roundtrip` / multiple_digit_runs

- Input: `('a12b3c',)`
- Reason: property failed on an in-contract input
- Note: multiple digit runs interleaved with letters

### `chunk/covers` / remainder_one

- Input: `([1,2,3,4,5], 2)`
- Reason: property failed on an in-contract input
- Note: remainder one

### `chunk/covers` / remainder_size_minus_one

- Input: `([1,2,3,4,5], 3)`
- Reason: property failed on an in-contract input
- Note: remainder size-1

### `chunk/covers` / remainder_between

- Input: `([1,2,3,4,5,6,7,8], 3)`
- Reason: property failed on an in-contract input
- Note: remainder between 1 and size-1

### `chunk/covers` / size_greater_than_list

- Input: `([[1,2],[3,4]], 5)`
- Reason: property failed on an in-contract input
- Note: size larger than list length

### `chunk/covers` / single_element

- Input: `([42], 2)`
- Reason: property failed on an in-contract input
- Note: single-element list

### `chunk/covers` / nested_lists

- Input: `([[], [1], [2,3]], 2)`
- Reason: property failed on an in-contract input
- Note: elements are lists

### `binary_search/finds_present` / two_elem_second

- Input: `([10, 20], 20)`
- Reason: property failed on an in-contract input
- Note: two-element list, target second

### `binary_search/finds_present` / neg_float

- Input: `([-5.5, -2.0, 0, 1.5, 3.2], -2.0)`
- Reason: property failed on an in-contract input
- Note: negative and float values, target present

### `truncate/respects_limit` / one_over_limit

- Input: `("abcdefghijk",10)`
- Reason: property failed on an in-contract input
- Note: one char over limit may not truncate

### `truncate/respects_limit` / far_over_limit

- Input: `("aaaaaaaaaaaaaaaaaaaa",10)`
- Reason: property failed on an in-contract input
- Note: far over limit may return full text

### `truncate/respects_limit` / limit_one

- Input: `("ab",1)`
- Reason: property failed on an in-contract input
- Note: limit 1 with 2 chars may overflow

### `truncate/respects_limit` / limit_two

- Input: `("abc",2)`
- Reason: property failed on an in-contract input
- Note: limit 2 with 3 chars may overflow

### `truncate/respects_limit` / unicode_emoji

- Input: `("😀😀😀😀😀",3)`
- Reason: property failed on an in-contract input
- Note: emoji may cause byte count overflow

### `truncate/respects_limit` / whitespace_over

- Input: `("      ",5)`
- Reason: property failed on an in-contract input
- Note: whitespace over limit may exceed

### `truncate/respects_limit` / newline_chars

- Input: `("\n\n\n\n\n",3)`
- Reason: property failed on an in-contract input
- Note: newline only text may exceed limit

### `truncate/respects_limit` / astral_char

- Input: `("𝔘𝔘",1)`
- Reason: property failed on an in-contract input
- Note: astral char may exceed byte limit

### `rle/roundtrip` / digits_start_end

- Input: `('3abc3',)`
- Reason: property failed on an in-contract input
- Note: digits at very start and end

### `rle/roundtrip` / ascii_unicode_adjacent1

- Input: `('0٠',)`
- Reason: property failed on an in-contract input
- Note: ascii digit adjacent to unicode digit

### `rle/roundtrip` / unicode_ascii_adjacent2

- Input: `('٠0',)`
- Reason: property failed on an in-contract input
- Note: unicode digit adjacent to ascii digit

### `rle/roundtrip` / space_space_digit

- Input: `('  3',)`
- Reason: property failed on an in-contract input
- Note: spaces followed by digit

### `rle/roundtrip` / tab_before_digit

- Input: `('\t3',)`
- Reason: property failed on an in-contract input
- Note: tab before digit

### `chunk/covers` / other_remainder

- Input: `([1,2,3,4,5,6,7], 5)`
- Reason: property failed on an in-contract input
- Note: other remainder

### `chunk/covers` / size_greater_than_list

- Input: `([1,2,3], 5)`
- Reason: property failed on an in-contract input
- Note: size larger than list length

### `chunk/covers` / elements_are_lists

- Input: `([[1,2],[3,4],[5]], 2)`
- Reason: property failed on an in-contract input
- Note: elements are lists

### `chunk/covers` / elements_are_strings

- Input: `(['ab','cd','ef','g'], 3)`
- Reason: property failed on an in-contract input
- Note: elements are strings

### `binary_search/finds_present` / last_pos

- Input: `([0,1,2,3,4],4)`
- Reason: property failed on an in-contract input
- Note: target at last index

### `binary_search/finds_present` / one_elem

- Input: `([42],42)`
- Reason: property failed on an in-contract input
- Note: one-element list

### `binary_search/finds_present` / neg_float

- Input: `([-5.5,-2.0,0,2.5,5.0],-2.0)`
- Reason: property failed on an in-contract input
- Note: negative and float values

### `binary_search/finds_present` / last_float

- Input: `([1.1,2.2,3.3,4.4,5.5],5.5)`
- Reason: property failed on an in-contract input
- Note: target at last index with float values

### `rle/roundtrip` / digit_between_letters

- Input: `('a5b',)`
- Reason: property failed on an in-contract input
- Note: digit inside letter run causes parse error

### `rle/roundtrip` / digit_start_end

- Input: `('5abc5',)`
- Reason: property failed on an in-contract input
- Note: leading/trailing digits disrupt parsing boundaries

### `rle/roundtrip` / whitespace_with_digit

- Input: `(' \n5\t ',)`
- Reason: property failed on an in-contract input
- Note: whitespace does not prevent digit-induced misparse

### `rle/roundtrip` / alternating_digit_letter

- Input: `('a1b2c3',)`
- Reason: property failed on an in-contract input
- Note: alternating digits and letters cause repeated misparse

### `rle/roundtrip` / digits_with_newline_internal

- Input: `('12\n34',)`
- Reason: property failed on an in-contract input
- Note: internal newline does not stop digit misparse

### `binary_search/finds_present` / negative

- Input: `([-5,-3,0,2,4], -3)`
- Reason: property failed on an in-contract input
- Note: negative numbers, target present

### `truncate/respects_limit` / one_over

- Input: `('aaaaaa', 5)`
- Reason: property failed on an in-contract input
- Note: one char over limit

### `truncate/respects_limit` / far_over

- Input: `('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 5)`
- Reason: property failed on an in-contract input
- Note: far over limit

### `truncate/respects_limit` / tab_over

- Input: `('\t\t\t', 2)`
- Reason: property failed on an in-contract input
- Note: tab characters over limit

### `truncate/respects_limit` / combining_char

- Input: `('e\u0301', 1)`
- Reason: property failed on an in-contract input
- Note: combining character sequence

### `truncate/respects_limit` / ascii_unicode_mix_over

- Input: `('a🚀b🚀c', 4)`
- Reason: property failed on an in-contract input
- Note: mixed ascii-unicode over limit

### `rle/roundtrip` / digit_digit_adjacent

- Input: `('12a',)`
- Reason: property failed on an in-contract input
- Note: adjacent digit run creates multi-digit count confusion

### `rle/roundtrip` / unicode_digit_adjacent

- Input: `('a\u0661b',)`
- Reason: property failed on an in-contract input
- Note: unicode digit treated as digit, causing count greediness

### `rle/roundtrip` / whitespace_digit_adjacent

- Input: `(' 1',)`
- Reason: property failed on an in-contract input
- Note: whitespace before digit leads to misparsed count

### `rle/roundtrip` / digit_with_newline

- Input: `('\n1a',)`
- Reason: property failed on an in-contract input
- Note: newline before digit causes similar count misinterpretation

### `rle/roundtrip` / mixed_whitespace_digits

- Input: `(' \t 2',)`
- Reason: property failed on an in-contract input
- Note: mixed whitespace before digit disrupts count parsing

### `chunk/covers` / remainder_one

- Input: `([1, 2, 3, 4, 5], 2)`
- Reason: property failed on an in-contract input
- Note: remainder one

### `chunk/covers` / middle_remainder

- Input: `([1, 2, 3, 4, 5, 6], 4)`
- Reason: property failed on an in-contract input
- Note: middle remainder

### `chunk/covers` / size_exceeds_list

- Input: `([1, 2, 3], 5)`
- Reason: property failed on an in-contract input
- Note: size exceeds list length

### `chunk/covers` / nested_list_elements

- Input: `([[1, 2], [3, 4], [5, 6]], 2)`
- Reason: property failed on an in-contract input
- Note: nested list elements

### `chunk/covers` / string_elements

- Input: `(['a','bb','ccc'], 2)`
- Reason: property failed on an in-contract input
- Note: string elements

### `binary_search/finds_present` / two_elem_last

- Input: `([-5, 10], 10)`
- Reason: property failed on an in-contract input
- Note: two‑element list, target at last

### `binary_search/finds_present` / three_elem_first

- Input: `([0,1,2], 0)`
- Reason: property failed on an in-contract input
- Note: three‑element list, target at first

### `binary_search/finds_present` / three_elem_last

- Input: `([0,1,2], 2)`
- Reason: property failed on an in-contract input
- Note: three‑element list, target at last

### `binary_search/finds_present` / neg_vals

- Input: `([-20, -5, 0, 5, 20], -5)`
- Reason: property failed on an in-contract input
- Note: list with negative numbers

### `binary_search/finds_present` / long_first

- Input: `([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19], 0)`
- Reason: property failed on an in-contract input
- Note: long list, target at first index

### `binary_search/finds_present` / long_last

- Input: `([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19], 19)`
- Reason: property failed on an in-contract input
- Note: long list, target at last index

### `binary_search/finds_present` / long_mid_miss

- Input: `([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19], 10)`
- Reason: property failed on an in-contract input
- Note: long list, equality‑treated‑as‑greater bug

### `rle/roundtrip` / digit_after_letter

- Input: `('a1',)`
- Reason: property failed on an in-contract input
- Note: digit adjacent to letter run

### `rle/roundtrip` / long_digit_run

- Input: `('12345678901',)`
- Reason: raised on an in-contract input: OverflowError: cannot fit 'int' into an index-sized integer
- Note: digit run length >=10

### `rle/roundtrip` / unicode_digit

- Input: `('٢٣',)`
- Reason: property failed on an in-contract input
- Note: unicode digit adjacency

### `rle/roundtrip` / whitespace_adjacent

- Input: `('a 1',)`
- Reason: property failed on an in-contract input
- Note: digit adjacent to whitespace

### `rle/roundtrip` / newline_adjacent

- Input: `('a\n1',)`
- Reason: property failed on an in-contract input
- Note: digit after newline

### `rle/roundtrip` / long_uniform_with_digit_inside

- Input: `('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',)`
- Reason: property failed on an in-contract input
- Note: digit inside long uniform run

### `chunk/covers` / remainder_one

- Input: `([1,2,3,4],3)`
- Reason: property failed on an in-contract input
- Note: remainder of one

### `chunk/covers` / remainder_size_minus_one

- Input: `([1,2,3,4,5,6,7,8,9],5)`
- Reason: property failed on an in-contract input
- Note: remainder size minus one

### `chunk/covers` / remainder_middle

- Input: `([1,2,3,4,5,6],4)`
- Reason: property failed on an in-contract input
- Note: remainder middle range

### `chunk/covers` / size_greater_than_list

- Input: `([1,2,3],10)`
- Reason: property failed on an in-contract input
- Note: size larger than list

### `chunk/covers` / single_element

- Input: `([42],2)`
- Reason: property failed on an in-contract input
- Note: single element list

### `chunk/covers` / nested_lists

- Input: `([[1,2],[3,4],[5]],2)`
- Reason: property failed on an in-contract input
- Note: elements are nested lists

### `chunk/covers` / string_elements

- Input: `(['ab','cd','ef'],2)`
- Reason: property failed on an in-contract input
- Note: elements are strings

### `chunk/covers` / mixed_literals

- Input: `([True, None, False],2)`
- Reason: property failed on an in-contract input
- Note: mixed literal element types

### `binary_search/finds_present` / negative_numbers

- Input: `([-10, -5, 0, 5, 10], -5)`
- Reason: property failed on an in-contract input
- Note: negative numbers

### `binary_search/finds_present` / long_list_midpoint

- Input: `([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31], 31)`
- Reason: property failed on an in-contract input
- Note: long list, missed midpoint

### `binary_search/finds_present` / mixed_neg_float

- Input: `([-2.5, -1.0, 0, 1.5, 3.0], -1.0)`
- Reason: property failed on an in-contract input
- Note: mixed negative/float

### `truncate/respects_limit` / far_over_ascii

- Input: `('aaaaaaaaaaaaaaaaaaaa', 5)`
- Reason: property failed on an in-contract input
- Note: text far over limit ascii

### `truncate/respects_limit` / far_over_unicode

- Input: `('🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀', 2)`
- Reason: property failed on an in-contract input
- Note: text far over limit unicode

### `truncate/respects_limit` / limit_one_unicode

- Input: `('🚀🚀', 1)`
- Reason: property failed on an in-contract input
- Note: limit 1 unicode over

### `truncate/respects_limit` / whitespace_over

- Input: `('    ', 3)`
- Reason: property failed on an in-contract input
- Note: whitespace-only text over limit

### `chunk/covers` / rem_size_minus_one

- Input: `([1,2,3,4,5,6,7], 4)`
- Reason: property failed on an in-contract input
- Note: remainder size-1

### `chunk/covers` / size_big

- Input: `([1,2], 5)`
- Reason: property failed on an in-contract input
- Note: size larger than list

### `chunk/covers` / elem_lists

- Input: `([[1,2],[3,4],[5,6]], 2)`
- Reason: property failed on an in-contract input
- Note: elements are lists

### `chunk/covers` / elem_none

- Input: `([None,None,None], 2)`
- Reason: property failed on an in-contract input
- Note: elements are None

### `binary_search/finds_present` / last_elem

- Input: `([0,1,2,3,4], 4)`
- Reason: property failed on an in-contract input
- Note: target at last position

### `binary_search/finds_present` / two_elem_second

- Input: `([5,10], 10)`
- Reason: property failed on an in-contract input
- Note: two‑element list, target second

### `binary_search/finds_present` / neg_value

- Input: `([-10,-5,0,5,10], -5)`
- Reason: property failed on an in-contract input
- Note: negative numbers, target present

### `binary_search/finds_present` / neg_float_mix

- Input: `([-2.5,-1.0,0.0,1.5,3.0], -1.0)`
- Reason: property failed on an in-contract input
- Note: mixed negative floats, target present

### `truncate/respects_limit` / one_over_limit

- Input: `("abcdef",5)`
- Reason: property failed on an in-contract input
- Note: text one char over limit

### `truncate/respects_limit` / far_over_limit

- Input: `("aaaaaaaaaaaaaaaaaaaa",5)`
- Reason: property failed on an in-contract input
- Note: text far over limit

### `truncate/respects_limit` / small_limit_two

- Input: `("hello world",2)`
- Reason: property failed on an in-contract input
- Note: limit == 2 with longer text

### `truncate/respects_limit` / unicode_emoji

- Input: `("🚀🚀🚀🚀🚀",2)`
- Reason: property failed on an in-contract input
- Note: unicode multi-byte characters

### `truncate/respects_limit` / whitespace_only

- Input: `("   ",2)`
- Reason: property failed on an in-contract input
- Note: whitespace-only text

### `truncate/respects_limit` / limit_one_char_over_unicode

- Input: `("🙂🙂🙂🙂🙂🙂🙂🙂🙂🙂🙂",10)`
- Reason: property failed on an in-contract input
- Note: unicode text one char over limit

### `truncate/respects_limit` / whitespace_limit_one

- Input: `("  ",1)`
- Reason: property failed on an in-contract input
- Note: whitespace text with limit 1

### `rle/roundtrip` / unicode_digit

- Input: `('٠١٢',)`
- Reason: property failed on an in-contract input
- Note: Unicode digits are treated as ordinary characters, breaking count

### `chunk/covers` / singleton_oversize

- Input: `([42], 5)`
- Reason: property failed on an in-contract input
- Note: singleton with size > length

### `chunk/covers` / size_exceeds

- Input: `([1, 2], 10)`
- Reason: property failed on an in-contract input
- Note: chunk size larger than list length

### `chunk/covers` / string_elements

- Input: `(['ab', 'cd', 'ef'], 2)`
- Reason: property failed on an in-contract input
- Note: list elements are strings

### `chunk/covers` / mixed_types

- Input: `([1, 'a', [2, 3]], 2)`
- Reason: property failed on an in-contract input
- Note: list contains mixed literal types

### `binary_search/finds_present` / last_elem

- Input: `([0, 1, 2, 3, 4], 4)`
- Reason: property failed on an in-contract input
- Note: target at last index

### `binary_search/finds_present` / two_elem_last

- Input: `([5, 10], 10)`
- Reason: property failed on an in-contract input
- Note: two‑element list, target last

### `binary_search/finds_present` / neg_float

- Input: `([-5.5, -2.0, 0.0, 3.3, 7.7], -2.0)`
- Reason: property failed on an in-contract input
- Note: negative and float values

### `binary_search/finds_present` / long_mid_miss

- Input: `([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16], 16)`
- Reason: property failed on an in-contract input
- Note: long list where target may be missed by midpoint

### `truncate/respects_limit` / one_over

- Input: `('abcdefghijk', 10)`
- Reason: property failed on an in-contract input
- Note: one char over limit, may not truncate

### `truncate/respects_limit` / limit_one_unicode

- Input: `('😀😁', 1)`
- Reason: property failed on an in-contract input
- Note: limit 1 with unicode, may exceed

### `truncate/respects_limit` / unicode_over

- Input: `('🚀🚀🚀🚀🚀🚀', 5)`
- Reason: property failed on an in-contract input
- Note: unicode over limit, may not truncate

### `truncate/respects_limit` / limit_two

- Input: `('hello', 2)`
- Reason: property failed on an in-contract input
- Note: limit 2, expecting truncation but may exceed

### `truncate/respects_limit` / mixed_whitespace

- Input: `('  abc  ', 3)`
- Reason: property failed on an in-contract input
- Note: mixed whitespace, may not trim leading/trailing

### `rle/roundtrip` / only_digits_large

- Input: `('12345678901234567890',)`
- Reason: raised on an in-contract input: OverflowError: cannot fit 'int' into an index-sized integer
- Note: long digit string triggers greedy count consumption

### `rle/roundtrip` / unicode_digits

- Input: `('١٢٣',)`
- Reason: property failed on an in-contract input
- Note: unicode digits not recognized as counts

### `rle/roundtrip` / alternating_letter_digit

- Input: `('a1a1',)`
- Reason: property failed on an in-contract input
- Note: pattern creates ambiguous count-token boundaries

### `rle/roundtrip` / multiple_digit_runs

- Input: `('111222333',)`
- Reason: property failed on an in-contract input
- Note: each run encoded as count+digit leads to extra digits

### `rle/roundtrip` / leading_zeros_string

- Input: `('00123',)`
- Reason: property failed on an in-contract input
- Note: leading zeros affect encoded counts and decoding

### `rle/roundtrip` / ends_with_digit_run

- Input: `('hello123',)`
- Reason: property failed on an in-contract input
- Note: string ending with digit run causes missing char after count

### `chunk/covers` / test_size_larger

- Input: `([1, 2, 3], 10)`
- Reason: property failed on an in-contract input
- Note: size larger than list

### `chunk/covers` / test_nested_lists

- Input: `([[1, 2], [3, 4], [5]], 2)`
- Reason: property failed on an in-contract input
- Note: nested list elements

### `chunk/covers` / test_mixed_types

- Input: `([1, 'two', None, True, [3]], 3)`
- Reason: property failed on an in-contract input
- Note: mixed element types

### `binary_search/finds_present` / negative_float

- Input: `([-5.5, -2.0, 0.0, 3.3, 7.1], -2.0)`
- Reason: property failed on an in-contract input
- Note: negative float

### `binary_search/finds_present` / long_list_missed_mid

- Input: `([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49], 45)`
- Reason: property failed on an in-contract input
- Note: long list index never visited

### `binary_search/finds_present` / two_elem_last

- Input: `([5,6], 6)`
- Reason: property failed on an in-contract input
- Note: two-element list last

### `truncate/respects_limit` / one_over

- Input: `('helloo',5)`
- Reason: property failed on an in-contract input
- Note: text one char over limit

### `truncate/respects_limit` / far_over

- Input: `('aaaaaaaaaaaaaaaaaaaa',5)`
- Reason: property failed on an in-contract input
- Note: text far over limit

### `truncate/respects_limit` / combining_accent

- Input: `('e\u0301',1)`
- Reason: property failed on an in-contract input
- Note: combining character counts as two code points

### `chunk/covers` / size_greater_than_list

- Input: `([True, False], 10)`
- Reason: property failed on an in-contract input
- Note: size larger than list length

### `chunk/covers` / list_of_strings

- Input: `(['hello', 'world', 'foo', 'bar'], 3)`
- Reason: property failed on an in-contract input
- Note: elements are strings

### `binary_search/finds_present` / negative_vals

- Input: `([-20,-10,0,10,20], -10)`
- Reason: property failed on an in-contract input
- Note: negative numbers list

### `truncate/respects_limit` / one_over

- Input: `("world!",5)`
- Reason: property failed on an in-contract input
- Note: text one character over limit

### `truncate/respects_limit` / unicode_mb

- Input: `("😀😃😄😁😆",3)`
- Reason: property failed on an in-contract input
- Note: unicode multi-byte characters

### `truncate/respects_limit` / newline_text

- Input: `("\n\n\n",2)`
- Reason: property failed on an in-contract input
- Note: text with newline characters

### `truncate/respects_limit` / combining_chars

- Input: `("e\u0301",1)`
- Reason: property failed on an in-contract input
- Note: combining character sequence


## Reversals

0 record(s) have changed verdict since first adjudication.

## Reproduce or resume

`python experiments/run_code_properties.py --api --preset nemotron`

Rerunning resumes from the JSON checkpoint and does not erase prior candidates.