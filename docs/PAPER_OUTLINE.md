# Extended Paper Outline

**Title:** *Extremal Selection as an Operational Substitute for Coexponentials: Fisher-Controlled Factorization*

## Abstract (draft)

Coexponentials (left adjoints to coproduct) do not exist in `Set`. We introduce extremal selection on compact polytopes and componentwise probes as an operational substitute, with Fisher off-diagonal leakage \(\varepsilon\) certifying when coproduct-style factorization is stable. Main results: vertex localization (Theorem 1), separable near-optimality bound \(\Phi(\varepsilon)\) (Theorem 2), and a constructive top-\(k\) vertex algorithm (Theorem 3). Numerical experiments on 2- and 3-block models confirm gap growth with \(\varepsilon\) and strict certification thresholds.

## 1. Introduction

- Motivation: categorical duality vs statistical independence
- Coexponential absent in `Set`; cardinality obstruction
- Contribution: Fisher-controlled extremal toolkit

## 2. Formal setup

- Box \(H\), blocks \(A,B\), objective \(C = g + h + r\)
- Fisher block matrix, normalized leakage \(\varepsilon\)

## 3. Main theorems

- Theorem 1: Vertex localization (proof sketch)
- Theorem 2: \(\Phi(\varepsilon)\) bound, \(\varepsilon_0\)
- Theorem 3: Constructive probe, \(\delta(\varepsilon) \le \Phi(\varepsilon)\)

## 4. Algorithms

- `VertexProbeAlgorithm`: \(O(|\mathrm{ext}(H)|)\)
- `FisherPrunedVertexSearch`: \(O(k^2)\) per block pair
- Strict certification predicate

## 5. Numerical demonstrations

- Figure: `experiments/figures/gap_vs_epsilon.png`
- Table: `experiments/results.json`
- 3-block failure mode when \(\varepsilon > 0.25\)
- **Non-quadratic:** `experiments/nonlinear_results.json` — `face_bowl` interaction shows grid max \(>\) vertex max (Theorem 1 requires hypotheses)

## 6. Categorical discussion

- Coproduct vs coexponential vs CCC corner
- Neighbor vertices (Chu, continuation, coalgebra)
- Operational substitute limits

## 7. Conclusion

- Design rules R1–R5
- Open problems: nonlinear objectives, high-dimensional \(H\), empirical Fisher estimation

## Appendix

- `docs/FORMAL_THEOREMS.md`
- Test suite: `tests/test_firsts.py`
