# Extremal Selection as an Operational Substitute for Coexponentials: Fisher-Controlled Factorization

**Draft** — extend from [`SHORT_NOTE.md`](SHORT_NOTE.md) and [`EXPERIMENT_REPORT.md`](EXPERIMENT_REPORT.md) (run `python experiments/generate_report.py`).

## Abstract

In the category of sets, a coexponential (left adjoint to coproduct) does not exist in general: the natural isomorphism \(\mathrm{Hom}(\mathrm{coexp}(A,Y), Z) \cong \mathrm{Hom}(Y, A \sqcup Z)\) fails by cardinality for non-trivial data. We introduce an **operational substitute** for factorization over coproduct blocks: **extremal selection** on a compact feasible polytope \(H\), **componentwise probes** built from marginal optimizers, and **Fisher off-diagonal leakage** \(\varepsilon = \|F_{AB}\|_F / \|F_{\mathrm{diag}}\|_F\) to certify when separable optimization is near-optimal. We prove (i) vertex localization of maximizers under separate monotonicity and axis quasiconvexity, (ii) a explicit bound \(\Phi(\varepsilon)\) on the joint–separable objective gap, and (iii) a constructive top-\(k\) vertex algorithm with certificates. A Python package reproduces quadratic and nonlinear toy experiments; a `face_bowl` interaction demonstrates failure of vertex localization when hypotheses break.

## 1. Introduction

Categorical dualities suggest a symmetry between products and coproducts, exponentials and coexponentials. In `Set`, curry adjunctions for Cartesian product are fundamental; dualizing naively to coproduct yields a functor that is not representable. Practitioners still perform **blockwise** optimization as if parameters were independent. We quantify when that is justified via Fisher leakage and give a constructive probe when a formal coexponential is absent.

**Contributions.**

1. Vertex localization theorem for box-constrained objectives with structured monotonicity/quasiconvexity.
2. Separable near-optimality bound \(\Phi(\varepsilon)\) and threshold \(\varepsilon_0\).
3. Implementations: `VertexProbeAlgorithm`, `FisherPrunedVertexSearch`, strict certification.
4. Nonlinear extension with empirical Fisher and explicit `face_bowl` counterexample.

## 2. Background and obstruction

See `set_category.cardinality_obstruction`: for \(|Y|, |A| \ge 1\), no finite \(C\) satisfies \(| \mathrm{Hom}(C,Z) | = (|A|+|Z|)^{|Y|}\) for all \(Z\).

**Operational substitute:** maximize over \(\mathrm{ext}(H)\); build probes per coproduct summand; penalize the uninhabited coexponential corner in diagram scoring (`extremal_substitute`).

## 3. Formal results

Core theorems (1–3): [`FORMAL_THEOREMS.md`](FORMAL_THEOREMS.md).  
Discovery proofs (A.1–G.1): [`FORMAL_DISCOVERIES.md`](FORMAL_DISCOVERIES.md) — obstruction, certification boundary, `face_bowl` counterexample, interaction taxonomy, design-rule phases.

## 4. Algorithms and complexity

- Exhaustive vertices: \(O(|\mathrm{ext}(H)|)\) — 16 corners for the default 4D box.
- Fisher-pruned: \(O(k^2)\) evaluations per block pair, \(k\) small.
- Block coordinate ascent for moderate \(\varepsilon\).

## 5. Experiments

Auto-table: [`EXPERIMENT_REPORT.md`](EXPERIMENT_REPORT.md).

**Summary (quadratic).** Strict certification holds for Fisher coupling \(f \lesssim 0.10\); fails at \(f = 0.25, 0.35\) with gaps 1.51 and 3.75. Vertex probe \(\theta = (1,0,2,3)\) throughout.

**Summary (nonlinear).** `face_bowl` at strength \(\ge 0.5\): grid maximum exceeds vertex-only maximum by up to \(\approx 0.54\) at strength 2.0 — use grid/reference search.

**Figures.** `experiments/figures/gap_vs_epsilon.png`, `experiments/figures/nonlinear_face_bowl.png`.

## 6. Discussion

**When to trust factorization.** \(\varepsilon \le 0.10\) and gap \(\le \Phi(\varepsilon)\): separable coproduct probe. Otherwise joint solve or full vertex enumeration.

**Neighbors.** Chu spaces, continuations, coalgebras carry other dual-flavored structure; they are not set-theoretic coexponentials (`neighboring_vertices`).

## 7. Conclusion

Coexponential factorization in `Set` is a shadow; extremal selection plus Fisher-controlled leakage is a measurable, implementable substitute.

## References (placeholder)

- Cartesian closed categories, Fisher information, quasiconvex analysis, vertex enumeration on polytopes.

## Appendix: Reproducibility

```bash
python experiments/run_all.py
python experiments/generate_report.py
python -m unittest discover -s tests -v
```

Package: `categorical_polytope/` (stdlib). Optional: `pip install -e ".[dev]"` for matplotlib.
