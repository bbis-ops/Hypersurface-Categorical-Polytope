# Formal Theorems

Notation: \(H \subset \mathbb{R}^n\) compact polytope (box), partition \(\theta = (\theta_A, \theta_B)\) into blocks.  
\(F\) Fisher information at the probe with block \(F_{AA}, F_{BB}, F_{AB}=F_{BA}^\top\).  
\(\varepsilon = \|F_{AB}\|_F / \|F_{\mathrm{diag}}\|_F\) (normalized off-diagonal leakage).

Objective (hypersurface model):

\[
C(\theta) = g(\theta_A) + h(\theta_B) + r(\theta),
\]

where \(g,h\) are separately non-decreasing in block coordinates and \(r\) is quasiconvex-increasing in \(\lambda\) and quasiconvex-decreasing in \(\sigma\) along box edges.

---

## Theorem 1 (Vertex Localization)

**Assumptions.**

1. \(H = \prod_i [a_i, b_i]\) (compact box).
2. \(g\) separately monotone in coordinates of \(A\); \(h\) separately monotone in coordinates of \(B\).
3. \(r\) quasiconvex on each coordinate axis of \(H\) with extrema at interval endpoints.

**Claim.** Every global maximizer \(\theta^\star\) of \(C\) on \(H\) satisfies \(\theta^\star \in \mathrm{ext}(H)\).

**Proof sketch.** Weierstrass: \(C\) continuous on compact \(H\), maximum attained. For a box, separate monotonicity in \((b,k)\)-type coordinates implies \(C\) is dominated by the face at block maxima; quasiconvexity of \(r\) in \((\lambda,\sigma)\) pushes marginals to axis endpoints. Marginal optima of quasiconvex functions over a polytope occur at vertices. Hence no strict improvement from interior points; \(\theta^\star\) is a corner.

**Remark.** Theorem 1 is **structural** (no Fisher bound). Fisher enters Theorems 2–3.

**Box corner (independent constraints):** \(\theta^\star = (\lambda_{\max}, \sigma_{\min}, B_{\max}, k_{\max})\) for the default hypersurface split.

---

## Theorem 2 (Separable Near-Optimality)

**Assumptions.** Theorem 1; local quadratic approximation \(C(\theta) \approx \theta^\top c - \frac{1}{2}\theta^\top F \theta\) near \(\theta^\star\); block Fisher with \(\|F_{AB}\|_F \le \varepsilon \|F_{\mathrm{diag}}\|_F\).

Let \(\theta^\star\) be the joint maximizer (solve \(F\theta = c\)) and \(\theta_{\mathrm{sep}}\) the one-pass block-coordinate maximizer.

**Claim.**

\[
C(\theta^\star) - C(\theta_{\mathrm{sep}}) \le \Phi(\varepsilon),
\qquad
\Phi(\varepsilon) = \frac{1}{2}\,\frac{\varepsilon^2}{\lambda_{\min}(F_{\mathrm{diag}})}\,
\|\theta^\star\|^2\,\|F_{\mathrm{diag}}\|_F.
\]

**Explicit threshold.**

\[
\varepsilon_0 = \frac{\lambda_{\min}(F_{\mathrm{diag}})}{L_g + L_h + \kappa_r},
\]

with \(L_g, L_h\) Lipschitz constants for monotone blocks and \(\kappa_r\) curvature bound for \(r\). If \(\varepsilon \le \varepsilon_0\), then \(\Phi(\varepsilon)\) is below a design tolerance and separable optimization is certified near-optimal.

**Proof sketch.** Write \(F = F_{\mathrm{diag}} + E\), \(\|E\|_F \le \varepsilon \|F_{\mathrm{diag}}\|_F\). Perturbation of the linear system \(F\theta = c\) yields \(\|\theta^\star - \theta_{\mathrm{sep}}\| = O(\varepsilon)\). Lipschitz \(C\) gives gap \(O(\varepsilon^2)\) with the stated \(\Phi\).

**Implementation:** `formal_bounds.TheoremConstants.Phi`, `leakage_gap_bound`.

---

## Theorem 3 (Constructive Probe Existence)

**Assumptions.** Theorem 2; coproduct decomposition \(H \cong H_A \times H_B\) with cross-information / Fisher budget \(\varepsilon\).

**Claim.** There exists a componentwise probe \(p = (p_A, p_B)\) with \(p_A \in \mathrm{ext}(H_A)\), \(p_B \in \mathrm{ext}(H_B)\), assembled from marginal optimizations, such that

\[
C(p) \ge C(\theta_{\mathrm{sep}}) - \delta(\varepsilon),
\qquad
\delta(\varepsilon) \le \Phi(\varepsilon).
\]

**Construction (Algorithm 1).**

1. Enumerate \(V_A = \mathrm{ext}(H_A)\), \(V_B = \mathrm{ext}(H_B)\).
2. Score marginals; take top-\(k\) candidates per block (Fisher-pruned search).
3. For \((v_A, v_B) \in V_A^{(k)} \times V_B^{(k)}\), if feasible in \(H\), evaluate \(C\); else project to nearest feasible vertex.
4. Return argmax with certificate \(C(\theta^\star) - C(p) \le \Phi(\varepsilon)\).

**Implementation:** `VertexProbeAlgorithm`, `FisherPrunedVertexSearch`.

---

## Corollary (Coproduct Robustness)

Small violations of statistical independence (\(F_{AB} \neq 0\)) with \(\varepsilon\) small imply coproduct-like factorization is **stable**: objective gap and parameter drift bounded by \(\Phi(\varepsilon)\) and \((\varepsilon/\lambda_{\min})\|\theta^\star\|\) respectively.

**Implementation:** `decomposition_stability.assess_decomposition`.

---

## Remark (Non-quadratic extension)

When \(C\) is not quadratic, replace \(F\) by the **empirical Fisher** (finite-difference Hessian proxy) at the vertex probe \(\theta^\star\):

\[
\hat F_{ij} \approx -\frac{\partial^2 C}{\partial \theta_i \partial \theta_j}(\theta^\star).
\]

Then \(\varepsilon\), \(\Phi(\varepsilon)\), and certification proceed as in Theorem 2 **locally**. Strong interaction terms (`softplus`, `trig`) may break global vertex localization; always run exhaustive search on \(\mathrm{ext}(H)\) and compare to separable block ascent.

**Implementation:** `nonlinear_objective.NonlinearStudy`, `empirical_fisher_at`.

---

## Formalized discoveries (proofs)

Automated searches in `discoveries.py` are matched to labeled propositions with proof sketches:

| Label | Discovery id | Role |
|-------|----------------|------|
| Proposition A.1 | `obstruction_minimal` | Coexponential absent in Set (minimal probe) |
| Lemma A.2 | `growth_rate_mismatch` | Exponential vs polynomial growth in \|Z\| |
| Proposition B.1 | `cert_boundary_fisher` | Strict certification threshold in toy Fisher model |
| Lemma B.2 | `phi_slack_sweet_spot` | Conservatism of Φ(ε) |
| Theorem C.1 | `face_bowl_onset` | Counterexample to Theorem 1 |
| Proposition C.2 | `interaction_landscape` | Structural vs cross-block failure modes |
| Lemma D.1 | `hypersurface_corner_invariant` | Probe argmax decoupled from coupling |
| Lemma E.1 | `prune_topk_gap` | Top-k soundness condition |
| Proposition F.1 | `strategy_transitions` | Piecewise design-rule phases |
| Proposition G.1 | `conceptual_ccc_corner` | CCC beats coexponential shadow |

Full proofs: [`FORMAL_DISCOVERIES.md`](FORMAL_DISCOVERIES.md).  
Regenerate: `python experiments/run_discoveries.py` (writes proofs + verification in `discoveries.json`).
