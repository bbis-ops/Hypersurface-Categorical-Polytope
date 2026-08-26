# Experiment report (auto-generated)

Generated: 2026-05-23 00:59 UTC

Sources: `experiments/results.json`, `experiments/nonlinear_results.json`.

## Coexponential obstruction (Set)

cardinality mismatch: |Hom(C,Z)| = |Z|^|C| cannot match |Hom(Y,A+Z)| = (|A|+|Z|)^|Y| for all Z unless trivial constants.

## Quadratic Fisher sweep (2-block toy)

| Fisher coupling f | epsilon | gap (joint-sep) | Phi bound | strict cert | vertex theta |
|------------------|---------|-----------------|-----------|-------------|--------------|
| 0.00 | 0.0000 | 0.0000 | 0.0000 | True | (1.0,0.0,2.0,3.0) |
| 0.01 | 0.0141 | 0.0025 | 0.0028 | True | (1.0,0.0,2.0,3.0) |
| 0.05 | 0.0707 | 0.0594 | 0.0657 | True | (1.0,0.0,2.0,3.0) |
| 0.10 | 0.1414 | 0.2301 | 0.2549 | True | (1.0,0.0,2.0,3.0) |
| 0.25 | 0.3536 | 1.5052 | 2.1962 | False | (1.0,0.0,2.0,3.0) |
| 0.35 | 0.4950 | 3.7477 | 9.3854 | False | (1.0,0.0,2.0,3.0) |

**Findings.**

- Vertex probe remains at CCC corner (1, 0, 2, 3) for all couplings tested.
- Strict certification passes for f <= 0.10 (epsilon <= ~0.14); fails for f = 0.25 and 0.35.
- Gap grows with f while vertex search value stays at 7.0 (hypersurface composite on vertices).

## Nonlinear interactions

### bilinear

| strength | gap_sep | gap_vs_grid | vertex_ok | epsilon |
|----------|---------|-------------|-----------|---------|
| 0.00 | 0.0000 | — | True | 0.0000 |
| 0.10 | 0.0000 | — | True | 0.0000 |
| 0.25 | 0.0000 | — | True | 0.0000 |
| 0.50 | 0.0000 | — | True | 0.0000 |
| 0.80 | 0.0000 | — | True | 0.0000 |
| 1.00 | 0.0000 | — | True | 0.0000 |

### face_bowl

| strength | gap_sep | gap_vs_grid | vertex_ok | epsilon |
|----------|---------|-------------|-----------|---------|
| 0.00 | 0.0000 | 0.0000 | True | 0.0000 |
| 0.10 | 0.0000 | 0.0000 | True | 0.0000 |
| 0.25 | 0.0000 | 0.0014 | True | 0.0000 |
| 0.50 | 0.0000 | 0.0583 | False | 0.0000 |
| 0.80 | 0.0000 | 0.1265 | False | 0.0000 |
| 1.00 | 0.0000 | 0.1721 | False | 0.0000 |
| 1.50 | 0.0000 | 0.3519 | False | 0.0000 |
| 2.00 | 0.0000 | 0.5432 | False | 0.0000 |

**Findings.**

- `bilinear` / `triple`: separable gap 0 on box; vertex localization holds.
- `face_bowl`: `gap_vs_grid` > 0 for strength >= 0.5 — grid reference beats vertex-only search (Theorem 1 breakdown).

## Figures

- `experiments/figures/gap_vs_epsilon.png`
- `experiments/figures/nonlinear_face_bowl.png`

Regenerate: `python experiments/run_all.py` then `python experiments/generate_report.py`.
