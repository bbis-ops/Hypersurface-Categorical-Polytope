# Revision record — corrected categorical note

**7 September 2026**

This record explains the substantive corrections to [SHORT_NOTE.md](SHORT_NOTE.md),
the [Overview](../categorical_polytope/Overview.md), and the
[expanded manuscript](PAPER_DRAFT.md). Their authoritative proof source is now
[FORMAL_THEOREMS.md](FORMAL_THEOREMS.md).

The counterexamples below concern the earlier categorical and Fisher sketches.
They are not a review of the separate Newton–tropical theorem series.

## What changed and why

| Earlier statement or presentation | Corrected edition |
| :--- | :--- |
| Every maximizer is a vertex under assumptions on summands | At least one maximizing vertex, assuming the full objective is separately quasiconvex on a box |
| The original $\Phi(\varepsilon)$ is a universal upper bound | Exact quadratic residual identity, a spectral residual bound, and curvature-normalized separation bounds |
| One cross block and the full off-diagonal matrix share one norm convention | Leakage is explicitly defined using the entire off-diagonal matrix; the two-block factor $\sqrt2$ is recorded |
| Top-$k$ search inherits a Fisher certificate for its objective | A candidate needs a proved upper bound on the same objective and actual feasible set |
| Candidate cost is the whole certification cost | Full-reference and auxiliary-model costs are stated separately |
| Fixed leakage cutoffs certify accuracy | Accuracy is tested against a proved objective-gap bound |
| A local Hessian supplies a nonlinear global certificate | A uniform remainder or other applicable global upper bound is required |
| Categorical constructions are identified with numerical corners | The analogy and the actual Cartesian feasible-set geometry are distinguished |
| Static image replacements for the diagrams | Directly visible native Mermaid, with the original node identities and directed connections |
| The old publication checklist is a readiness score | A current editorial checklist, with historical sources explicitly separated |

The diagram labels now reflect the corrected hypotheses and certificate
quantities. Those label changes are mathematical corrections, not merely
cosmetic changes. The publication title is unchanged. The previous text and
checklist remain recoverable from version history.

The legacy numerical APIs retain their computational behavior for compatibility.
Their docstrings now identify the limits of their original comparison quantities.
The new [exact reproduction script](../experiments/note_publication_check.py)
checks the corrected examples, including scaling and an equality case.
No correction to the Newton–tropical backend is implied by this note revision.

## Historical counterexamples

## 1. The original localization statement is false as written

The Overview assumes that the block terms are coordinatewise nondecreasing
and the interaction is separately quasiconvex. It concludes that every
maximizer lies at a vertex.

On $H=[0,1]^2$, take

$$
g(x)=x,\qquad h(y)=y,\qquad r(x,y)=-x^2.
$$

Both block terms are nondecreasing. The interaction is decreasing in $x$
on this interval and constant in $y$, so it is quasiconvex on every
coordinate slice. Nevertheless,

$$
C(x,y)=x-x^2+y=\frac14-(x-\tfrac12)^2+y
$$

has its unique maximum at $(1/2,1)$, with value $5/4$. The best vertex value
is $1$. Thus even the existence of a maximizing vertex fails under the
written assumptions. A monotone function plus a quasiconvex function need
not be quasiconvex or attain its maximum at an endpoint.

A valid replacement statement would assume continuity and separate
quasiconvexity of the **full objective** $C$. Iteratively replacing each
coordinate by an endpoint then proves that **some** vertex attains the
maximum. It does not prove that every maximizer is a vertex: a constant
objective already disproves that stronger conclusion.

## 2. The displayed Fisher bound is not a universal upper bound

The original expression is

$$
\Phi(\varepsilon)=\frac12
\frac{\varepsilon^2}{\lambda_{\min}(F_{\mathrm{diag}})}
\|\theta^\star\|^2\|F_{\mathrm{diag}}\|_F.
$$

Consider the exact positive-definite quadratic model

$$
F=\begin{pmatrix}4&1\\1&4\end{pmatrix},\qquad
c=\begin{pmatrix}4\\4\end{pmatrix},\qquad
C(\theta)=c^\top\theta-\frac12\theta^\top F\theta.
$$

The joint maximizer is $(4/5,4/5)$. One coordinate pass from zero, in the
order used by `separable_block_optimization`, gives $(1,3/4)`. Both points
lie in $[0,1]^2$. Their objective gap is

$$
C(4/5,4/5)-C(1,3/4)=\frac3{40}.
$$

Using the implementation's full off-diagonal norm gives
$\varepsilon=1/4$, $\lambda_{\min}(F_{\mathrm{diag}})=4$,
$\|\theta^\star\|^2=32/25$, and
$\|F_{\mathrm{diag}}\|_F=4\sqrt2$. Hence

$$
\Phi(\varepsilon)=\frac{\sqrt2}{25}
\lt\frac3{40}.
$$

This also exposes the scaling problem: multiplying both $F$ and $c$ by a
positive scalar leaves both optimizers, normalized leakage, and the stated
$\Phi$ unchanged, while multiplying the actual objective gap by that scalar.

There is a second mismatch. The prose defines leakage using one cross block
$F_{AB}$, while the implementation uses the entire off-diagonal matrix $E$.
For two symmetric blocks,

$$
\|E\|_F=\sqrt2\,\|F_{AB}\|_F.
$$

The Overview's proof line $\|E\|_F\le\varepsilon\|F_{\mathrm{diag}}\|_F$
therefore fails under its written single-block definition when $F_{AB}\ne0$.
Using that smaller leakage in the example makes the displayed bound still
smaller; it does not repair the counterexample.

## 3. The implementation's certificate has a narrower meaning

[`certify_suboptimality`](../categorical_polytope/formal_bounds.py) checks an
already supplied gap against the threshold and the computed $\Phi$.
That check can reject a failed comparison; it does not prove that $\Phi$
is an upper bound for arbitrary objectives.

In [`FisherPrunedVertexSearch.run`](../categorical_polytope/fisher_pruned_search.py),
`certified` is obtained from the auxiliary quadratic model's `factor.gap`.
The separately reported `probe_gap` compares the pruned objective value with
the full vertex reference. The implementation therefore does not justify
reading `certified` as a general theorem bounding the pruned objective's gap.

## Reproduce the Fisher counterexample

Run from the repository root:

```python
from categorical_polytope.fisher_factorization import (
    BlockFisher, BlockLayout, QuadraticJointObjective,
)

fisher = BlockFisher(
    BlockLayout(("A", "B"), (1, 1)),
    ((4.0, 1.0), (1.0, 4.0)),
)
result = QuadraticJointObjective(fisher, (4.0, 4.0)).factorization_analysis()
print(result.theta_joint, result.theta_separable)
print(result.gap, result.theoretical_bound)
assert result.gap > result.theoretical_bound
```

The implementation returns approximately `0.075` for the gap and
`0.05656854249492382` for the displayed bound. The exact calculation above
establishes the strict inequality independently of floating-point output.

## Resolution in this edition

The false statements are replaced in the short note, overview, expanded
manuscript, and proof source. The older LaTeX note is labeled as historical.

- [Theorem 1](FORMAL_THEOREMS.md#theorem-1--vertex-localization) proves the
  correct existence statement from a full-objective hypothesis.
- [Theorem 2](FORMAL_THEOREMS.md#theorem-2--quadratic-residual-and-separation-bounds)
  proves the exact residual identity and valid scale-covariant bounds.
- [Theorem 3](FORMAL_THEOREMS.md#theorem-3--a-certified-finite-candidate-search)
  gives a certificate with an explicit upper bound and a separate pruning estimate.

For the one-pass counterexample above, the corrected residual upper bound is
$3/32$, which exceeds the true gap $3/40$. The independent solve has gap
$1/5\le1/3$. The reproduction script verifies both using rational arithmetic.
