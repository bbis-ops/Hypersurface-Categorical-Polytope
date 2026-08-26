# Adversarial verification certificate: V.7--V.14

Backend: `stealth/ox-alpha@openrouter.ai`. Generated candidates are untrusted data; every retained expression passes the AST whitelist and is adjudicated locally.

Local adjudicator version: **15**.

This certificate distinguishes parse-valid proposals from candidates satisfying a theorem's hypotheses. `outside_scope` is never counted as a verification. A `counterexample` is a numerical survivor requiring independent analytic review; it is not silently deleted.

| Law | parse-valid corpus | in-scope verified | counterexamples | outside scope | rejected/inconclusive |
|---|---:|---:|---:|---:|---:|
| V.7 | 208 | 125 | 0 | 11 | 72 |
| V.8 | 203 | 121 | 0 | 53 | 29 |
| V.9 | 214 | 123 | 0 | 45 | 46 |
| V.10 | 271 | 141 | 0 | 87 | 43 |
| V.11 | 226 | 121 | 0 | 9 | 96 |
| V.12 | 153 | 141 | 0 | 10 | 2 |
| V.13 | 156 | 123 | 0 | 33 | 0 |
| V.14 | 221 | 119 | 0 | 98 | 4 |

## Campaign accounting

- API items requested across small rate-safe batches: **1867**
- Parse-valid items returned before deduplication: **1686**
- Unique retained corpus: **1652**
- Provider-reported prompt tokens: **34,759**
- Provider-reported completion tokens: **302,162**
- Provider-reported total tokens: **336,921**
- In-scope verified: **1014**
- Numerical counterexamples requiring review: **0**
- Outside theorem hypotheses: **346**

## Counterexample ledger

No numerical survivor is currently logged.

## Finite-guard failures

The adversarial search found **51** bases with an independently confirmed off-vertex maximum that at least one finite guard missed. These confirm V.13 while refuting exhaustive interpretations of the detection algorithm; they remain in `verification_guard_failures.json`.

## Resolved apparent counterexamples

- **V.7 / exp_decay_hump**: counterexample -> verified; quadratic exponent matched
- **V.7 / tanh_cubic_x**: verified -> outside_scope; not a finite-slope separable breaker
- **V.7 / sin_quartic_y**: verified -> outside_scope; not a finite-slope separable breaker
- **V.7 / exp_flat_bump**: counterexample -> verified; quadratic exponent matched
- **V.7 / log_soft_start**: verified -> outside_scope; not a finite-slope separable breaker
- **V.7 / sinh_exp_cliff**: counterexample -> verified; quadratic exponent matched
- **V.8 / fifteen_sin**: verified -> outside_scope; measured homogeneity is outside this theorem slice
- **V.8 / sqrt_ratio**: counterexample -> outside_scope; measured homogeneity is outside this theorem slice
- **V.10 / s11_plus_s21_cos**: counterexample -> verified; fractional exponent matched
- **V.10 / oneml12_kk**: counterexample -> verified; fractional exponent matched
- **V.10 / oneml165_atan**: counterexample -> verified; fractional exponent matched
- **V.10 / sig165_tansq**: counterexample -> outside_scope; measured homogeneity is outside this theorem slice
- **V.10 / combo11_tanh**: counterexample -> verified; fractional exponent matched
- **V.11 / gate_trig_mix**: counterexample -> verified; measured gap stayed below dense amplitude ceiling
- **V.11 / ring_gate**: counterexample -> verified; measured gap stayed below dense amplitude ceiling
- **V.13 / gauss_bump_31_68**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / gauss_bump_81_34**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / tilt_bump_34_72**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / tilt_bump_22_81**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / tilt_bump_tanh**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / tilt_bump_sqrt**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / tilt_bump_quad**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_top_right**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_top_left**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_left**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_bottom**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_right_low**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / edge_peak_top_low**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / spike_offcorner_00**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / spike_offcorner_01**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / spike_offcorner_11**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / spike_ultrathin_00**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / alias_sin16_product**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / alias_sin24_sq**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / alias_sin8_product**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.13 / alias_sin16_cos16**: counterexample -> verified; adversarial guard caught independent off-vertex witness
- **V.14 / aniso_x2_y6_geomean**: counterexample -> verified; weighted unified exponent matched
- **V.14 / iso_b2_diagonalcusp**: counterexample -> verified; weighted unified exponent matched
- **V.14 / octic_two_dir**: counterexample -> outside_scope; base has an unpenalized/non-coercive flat direction
- **V.9 / abs_crease_a4_b7**: counterexample -> verified; directional exponent and coefficient matched
- **V.9 / nested_crease_1**: counterexample -> verified; directional exponent and coefficient matched
- **V.9 / nested_crease_2**: counterexample -> verified; directional exponent and coefficient matched
- **V.9 / nested_crease_4**: counterexample -> verified; directional exponent and coefficient matched
- **V.12 / essential_aniso**: counterexample -> verified; master exponent matched
- **V.12 / sinh_growth**: counterexample -> verified; master exponent matched
- **V.12 / survivor_coeff_down**: counterexample -> verified; master exponent matched
- **V.12 / survivor_tanh_swap**: counterexample -> verified; master exponent matched
- **V.12 / survivor_pow5**: counterexample -> verified; master exponent matched
- **V.12 / exp_family_cubic**: counterexample -> verified; master exponent matched
- **V.12 / survivor_plus_quartic**: counterexample -> verified; master exponent matched
- **V.12 / mixed_functional_3_5**: counterexample -> verified; master exponent matched
- **V.10 / diff_sin_135**: counterexample -> verified; fractional exponent matched
- **V.10 / sum_negtanh_165**: counterexample -> verified; fractional exponent matched
- **V.10 / coef_doubled_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / coef_asym_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / freq_tripled_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / tanh_distraction_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / atan_distraction_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / exp_decay_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / twin_sines_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / half_amplitude_s135**: counterexample -> verified; fractional exponent matched
- **V.10 / baseline_s15**: verified -> outside_scope; no resolved inward fractional gap
- **V.10 / product_bounded_s15**: verified -> outside_scope; no resolved inward fractional gap
- **V.10 / baseline_s11**: counterexample -> verified; fractional exponent matched
- **V.10 / atan_s11**: counterexample -> verified; fractional exponent matched
- **V.10 / damped_osc_s11**: counterexample -> verified; fractional exponent matched
- **V.10 / baseline_s12**: counterexample -> verified; fractional exponent matched
- **V.10 / coef_tripled_tanh_s12**: counterexample -> verified; fractional exponent matched
- **V.10 / split_osc_s12**: counterexample -> verified; fractional exponent matched
- **V.10 / sublin_num_bounded_den**: counterexample -> verified; fractional exponent matched
- **V.12 / distract_double**: counterexample -> verified; master exponent matched
- **V.10 / tanh_squared_12**: counterexample -> verified; fractional exponent matched
- **V.10 / cos_kmod_12**: counterexample -> verified; fractional exponent matched
- **V.12 / survivor_coeff_bk**: counterexample -> verified; master exponent matched
- **V.14 / aniso_x2_y6_y5**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_coefficient**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_scale**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_difference**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_cross_cance**: counterexample -> verified; weighted unified exponent matched
- **V.14 / aniso_swapped**: counterexample -> verified; weighted unified exponent matched
- **V.14 / rational_pert**: counterexample -> verified; weighted unified exponent matched
- **V.14 / ridge_bent_survivor**: counterexample -> verified; weighted unified exponent matched
- **V.13 / separable_sharps**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.12 / tanh_soft_corner**: counterexample -> verified; master exponent matched
- **V.12 / sum_power_form**: counterexample -> verified; master exponent matched
- **V.12 / survivor_rescale**: counterexample -> verified; master exponent matched
- **V.13 / sep_gauss_aniso**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.13 / tanh_L1_spike**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.13 / diamond_exp**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.13 / edge_lam0**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.13 / two_point_intersect**: counterexample -> verified; V.13 witness confirmed; finite adversarial guard missed it
- **V.14 / iso_b6_a5**: counterexample -> verified; weighted unified exponent matched
- **V.14 / iso_b8_a7**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_half_scale**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_sum_mixed**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_bk_coupled**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_cancellatio**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_cosh_cross**: counterexample -> verified; weighted unified exponent matched
- **V.14 / survivor_atan_cross**: counterexample -> verified; weighted unified exponent matched
- **V.14 / xcoeff_scale**: counterexample -> verified; weighted unified exponent matched
- **V.14 / vanishing_xpenalty_a**: counterexample -> verified; weighted unified exponent matched
- **V.10 / coeff_half_sum_tanh**: counterexample -> verified; fractional exponent matched
- **V.10 / coeff_asym_weights**: counterexample -> verified; fractional exponent matched

## Reproduce or resume

`python experiments/run_verification_campaign.py --api --per-law 64 --in-scope-per-law 64 --batch-size 32 --model stealth/ox-alpha`

Rerunning resumes from the JSON checkpoint and does not erase prior candidates or counterexamples.