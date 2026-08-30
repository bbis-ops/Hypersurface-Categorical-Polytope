# Domain three: exponent laws on a general polyhedron

Domain one runs on a box, where a vertex's edges *are* the coordinate axes,
so "measure along each axis" and "measure along each edge" are the same
instruction. On any other polytope they differ. This domain asks the same law
both ways and records which coordinate system it lives in.

Local adjudicator version: **11**. Adjudicator is stdlib
arithmetic; no model decides any verdict.

| Rule | corpus | verified | counterexamples | outside scope | rejected/inconclusive |
|---|---:|---:|---:|---:|---:|
| `polyhedron/edge_exponent_law` | 268 | 107 | 0 | 93 | 68 |
| `polyhedron/ambient_exponent_law` | 63 | 27 | 2 | 29 | 5 |
| `polyhedron/linear_max_at_vertex` | 101 | 89 | 0 | 12 | 0 |

## Denominator

- Retained corpus: **432**
- In-scope: **225**
- Out of scope: **134**
- Undecided: **11**
- Refused at the parse boundary: **62**

## Coverage of the selection rule

Theorem V.16 selects `q* = min_j q_j` over the admissible faces of the
tangent cone. A row whose faces all agree on `q` tests the dilation and
the admissibility filter; only a row whose faces *disagree* tests the
selection.

- Rows with a multi-ray admissible face: **158**
- Rows admissible ONLY on a multi-ray face (product monomials): **32**
- Rows whose faces disagree about `q` by more than 0.05: **52**
- Transport licensed (`base_homogeneity` = 1): **210/211**
- Inside hypothesis 2 in full, every `beta_i` > 1 as well (`hypotheses_licensed`): **205/211**
- Rows that separate the minimum rule from the maximum rule (`selection_discriminates`): **44**
- Disagreeing AND inside the theorem's hypotheses (every `beta_i` > 1, homogeneity 1): **51**
- Of those, ones where the rival maximum rule is also FINITE (so measurement chooses between two numbers rather than rejecting a divergence): **44**

The disagreeing rows, which are the ones carrying the selection:
- `3d_shear_orders_2_4_6` (edge_exponent_law): q in [0.5, 0.5, 1.3804, 1.3804] -> q* = 0.5000, verified
- `tilted_vertex_beta2_4` (edge_exponent_law): q in [0.5, 1.6643] -> q* = 0.5000, verified
- `case4` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, outside_scope
- `case1` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `case2` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `case3` (edge_exponent_law): q in [0.25, 0.2509, 0.5] -> q* = 0.2500, verified
- `case4` (edge_exponent_law): q in [0.2, 0.201, 0.5] -> q* = 0.2000, verified
- `case5` (edge_exponent_law): q in [0.2, 0.2026, 0.3333] -> q* = 0.2000, verified
- `case6` (edge_exponent_law): q in [0.1667, 0.1673, 0.5] -> q* = 0.1667, verified
- `case7` (edge_exponent_law): q in [0.25, 0.2551, 0.3333] -> q* = 0.2500, verified
- `case8` (edge_exponent_law): q in [0.1667, 0.1717, 0.25] -> q* = 0.1667, verified
- `case9` (edge_exponent_law): q in [0.1429, 0.1559, 0.2] -> q* = 0.1429, verified
- `case10` (edge_exponent_law): q in [0.3333, 0.3355, 0.5] -> q* = 0.3333, verified
- `box_orders_2_4_product_push` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `base_quad_quartic_tilt` (edge_exponent_law): q in [0.25, 0.251, 0.5] -> q* = 0.2500, verified
- `beta6_beta6_lin_quart` (edge_exponent_law): q in [0.1667, 0.1667, 0.6667] -> q* = 0.1667, verified
- `case_01` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `case_02` (edge_exponent_law): q in [0.1667, 0.1672, 0.5] -> q* = 0.1667, verified
- `case_06` (edge_exponent_law): q in [0.1429, 0.1444, 0.3333] -> q* = 0.1429, verified
- `case1` (edge_exponent_law): q in [0.25, 0.2514, 0.5] -> q* = 0.2500, verified
- `case3` (edge_exponent_law): q in [0.3334, 0.6727] -> q* = 0.3334, verified
- `case4` (edge_exponent_law): q in [0.3327, 0.4004, 0.5001] -> q* = 0.3327, inconclusive
- `case6` (edge_exponent_law): q in [0.2838, 0.2857, 0.6667] -> q* = 0.2838, verified
- `case7` (edge_exponent_law): q in [0.5, 0.8491] -> q* = 0.5000, verified
- `case10` (edge_exponent_law): q in [0.3748, 0.4, 0.5001] -> q* = 0.3748, verified
- `case_4_2_linear` (edge_exponent_law): q in [0.25, 0.2509, 0.5] -> q* = 0.2500, verified
- `case_6_3_lin_sq` (edge_exponent_law): q in [0.1667, 0.1667, 0.6667] -> q* = 0.1667, verified
- `case_5_4_sq_cb` (edge_exponent_law): q in [0.4, 0.4001, 0.75] -> q* = 0.4000, verified
- `case_2_5_lin_4p` (edge_exponent_law): q in [0.5, 0.5, 0.8] -> q* = 0.5000, verified
- `case_4_2_lin` (edge_exponent_law): q in [0.25, 0.2509, 0.5] -> q* = 0.2500, verified
- `case_6_3_lin_sq` (edge_exponent_law): q in [0.1667, 0.1667, 0.6667] -> q* = 0.1667, verified
- `case_5_4_sq_cub` (edge_exponent_law): q in [0.4, 0.75] -> q* = 0.4000, verified
- `case_2_5_lin_4th` (edge_exponent_law): q in [0.5, 0.5, 0.8] -> q* = 0.5000, verified
- `case1_4_2_linlin` (edge_exponent_law): q in [0.25, 0.2511, 0.5] -> q* = 0.2500, verified
- `case3_6_3_linsq` (edge_exponent_law): q in [0.1667, 0.1669, 0.6667] -> q* = 0.1667, verified
- `case4_5_4_sqcu` (edge_exponent_law): q in [0.4, 0.4003, 0.75] -> q* = 0.4000, verified
- `case5_2_5_lin4p` (edge_exponent_law): q in [0.5, 0.5, 0.8] -> q* = 0.5000, verified
- `case7_4_2_linlin_shear` (edge_exponent_law): q in [0.25, 0.251, 0.5] -> q* = 0.2500, verified
- `case9_5_4_sqcu_rot` (edge_exponent_law): q in [0.4, 0.4002, 0.75] -> q* = 0.4000, verified
- `case10_2_5_lin4p_skew` (edge_exponent_law): q in [0.5, 0.5, 0.8] -> q* = 0.5000, verified
- `case1` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `case2` (edge_exponent_law): q in [0.1667, 0.1672, 0.5] -> q* = 0.1667, verified
- `case3` (edge_exponent_law): q in [0.1667, 0.1744, 0.25] -> q* = 0.1667, verified
- `test_005` (edge_exponent_law): q in [0.2, 0.201, 0.5] -> q* = 0.2000, verified
- `test_006` (edge_exponent_law): q in [0.3333, 0.3358, 0.5] -> q* = 0.3333, verified
- `case_a` (edge_exponent_law): q in [0.25, 0.2513, 0.5] -> q* = 0.2500, verified
- `case_c` (edge_exponent_law): q in [0.1667, 0.1669, 0.6667] -> q* = 0.1667, verified
- `case_d` (edge_exponent_law): q in [0.4, 0.4002, 0.75] -> q* = 0.4000, verified
- `case_e` (edge_exponent_law): q in [0.5, 0.5, 0.8] -> q* = 0.5000, verified
- `case_h` (edge_exponent_law): q in [0.2, 0.2, 0.75] -> q* = 0.2000, verified
- `case_i` (edge_exponent_law): q in [0.4, 0.4, 0.8] -> q* = 0.4000, verified
- `case_j` (edge_exponent_law): q in [0.6, 0.6, 0.8333] -> q* = 0.6000, verified

## Localisation (Lemma 1)

The face analysis runs inside a neighbourhood of the vertex, so it is
the global asymptotic only where the vertex is the unperturbed
maximiser and isolated. `rival_margin` measures that `eta` against a
ball of radius 0.25: it is the amount by which the vertex outranks the
best competing maximum the probe found outside that ball. Positive is a
margin; zero or less is a genuine rival, and the localisation does not
hold for that row. The probe is finite - it can find a rival, it cannot
prove there is none - so nothing is gated on it.

- Rows carrying a margin: **211/211**
- No rival found outside the ball: **211**
- Rival at least as high as the vertex: **0**
- Smallest margin: **3.91e-06** on `simplex_beta66_pert_x2edge` (outside_scope)

## Candidate value

Corpus size is not evidence. A row whose admissible faces all
agree about `q` exercises the transport and the admissibility
filter, and would have looked identical under a maximum rule, so
it cannot move the selection clause however many of it there is.
Screening classifies what each row would be evidence FOR, from
the metrics already recorded - no re-measurement.

| class | rows | what it would establish |
|---|---:|---|
| `decisive` | 44 | separates the minimum rule from a rival that also gives a finite answer |
| `selective` | 2 | separates it from a rival that only diverges - any rule survives that |
| `confirming` | 67 | in scope and licensed, but consistent with the rivals too |
| `unlicensed` | 0 | adjudicated, but a hypothesis is unmet, so a pass licenses nothing |
| `refused` | 155 | scope declines it; the proposal was spent for nothing |

Of 268 `edge_exponent_law` rows, **46** (17%) distinguish the rule from a rival.

Decisive rows, the ones that carry the selection clause:
- `case1`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case2`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case3`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case4`: the minimum rule predicts 1.250 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case6`: the minimum rule predicts 1.200 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case10`: the minimum rule predicts 1.500 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `box_orders_2_4_product_push`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `base_quad_quartic_tilt`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `beta6_beta6_lin_quart`: the minimum rule predicts 1.200 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_01`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_02`: the minimum rule predicts 1.200 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_06`: the minimum rule predicts 1.167 and the maximum rule 1.500, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case1`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case3`: the minimum rule predicts 1.500 and the maximum rule 3.055, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case4`: the minimum rule predicts 1.499 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (inconclusive)
- `case6`: the minimum rule predicts 1.396 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case7`: the minimum rule predicts 2.000 and the maximum rule 6.628, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case10`: the minimum rule predicts 1.600 and the maximum rule 2.000, further apart than twice the 0.160 tolerance, so a single measurement cannot fit both (verified)
- `case_4_2_linear`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_6_3_lin_sq`: the minimum rule predicts 1.200 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_5_4_sq_cb`: the minimum rule predicts 1.667 and the maximum rule 4.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case_2_5_lin_4p`: the minimum rule predicts 2.000 and the maximum rule 5.000, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case_4_2_lin`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_6_3_lin_sq`: the minimum rule predicts 1.200 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_5_4_sq_cub`: the minimum rule predicts 1.667 and the maximum rule 4.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case_2_5_lin_4th`: the minimum rule predicts 2.000 and the maximum rule 5.000, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case1_4_2_linlin`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case3_6_3_linsq`: the minimum rule predicts 1.200 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case4_5_4_sqcu`: the minimum rule predicts 1.667 and the maximum rule 4.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case5_2_5_lin4p`: the minimum rule predicts 2.000 and the maximum rule 5.000, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case7_4_2_linlin_shear`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case9_5_4_sqcu_rot`: the minimum rule predicts 1.667 and the maximum rule 4.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case10_2_5_lin4p_skew`: the minimum rule predicts 2.000 and the maximum rule 5.000, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case1`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case2`: the minimum rule predicts 1.200 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `test_005`: the minimum rule predicts 1.250 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `test_006`: the minimum rule predicts 1.500 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_a`: the minimum rule predicts 1.333 and the maximum rule 2.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_c`: the minimum rule predicts 1.200 and the maximum rule 3.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_d`: the minimum rule predicts 1.667 and the maximum rule 4.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case_e`: the minimum rule predicts 2.000 and the maximum rule 5.000, further apart than twice the 0.200 tolerance, so a single measurement cannot fit both (verified)
- `case_h`: the minimum rule predicts 1.250 and the maximum rule 4.000, further apart than twice the 0.150 tolerance, so a single measurement cannot fit both (verified)
- `case_i`: the minimum rule predicts 1.667 and the maximum rule 5.000, further apart than twice the 0.167 tolerance, so a single measurement cannot fit both (verified)
- `case_j`: the minimum rule predicts 2.500 and the maximum rule 6.000, further apart than twice the 0.250 tolerance, so a single measurement cannot fit both (verified)

## Disagreements between coordinate systems

### `polyhedron/ambient_exponent_law` / simplex_quartic_ambient

- System: `([[-1,0],[0,-1],[1,1]], [0,0,1])`
- Base: `-((x0+x1-1)**2 + x0**4)`  Pert: `x0`
- Vertex: `[-0.0, 1.0]` axis-aligned: `False`
- Predicted 1.9999999957062702, measured 1.3333333333333335
- exponent mismatch (|1.333 - 2.000| >= 0.200)
### `polyhedron/ambient_exponent_law` / sheared_quartic_ambient

- System: `([[-1,0],[0,-1],[1,2]], [0,0,2])`
- Base: `-((x0+2*x1-2)**2 + x0**4)`  Pert: `x0`
- Vertex: `[-0.0, 1.0]` axis-aligned: `False`
- Predicted 1.9999999957043428, measured 1.3333333333333333
- exponent mismatch (|1.333 - 2.000| >= 0.200)
