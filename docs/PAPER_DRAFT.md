# Extremal Selection as an Operational Substitute for Coexponentials: Fisher-Controlled Factorization

**Brisen Koch · Corrected manuscript draft · 7 September 2026**

[Short note](SHORT_NOTE.md) · [Illustrated overview](../categorical_polytope/Overview.md) · [Complete proofs](FORMAL_THEOREMS.md) · [Revision record](ORIGINAL_NOTE_REVIEW.md)

## Abstract

For nonempty $A$, the coproduct functor $A\sqcup-$ on `Set` has no left
adjoint. We use this obstruction to motivate an operational framework for
block-structured optimization: construct feasible candidates, evaluate their
full objective, and certify the remaining gap with a proved upper bound.
Three standard ingredients make the framework precise. Separate quasiconvexity
of a continuous full objective on a box ensures a maximizing vertex.
Positive-definite quadratic models admit an exact residual-gap identity and
curvature-dependent separation bounds. A finite candidate search inherits
a guarantee from an upper bound on the same objective and feasible set.
We give exact worked examples, identify the cost of the reference calculation,
and distinguish these guarantees from the repository's older diagnostic
certificate fields.

## 1. Motivation and mathematical scope

The project began with a categorical question: what remains operationally
useful when a formally dual adjunction does not exist? The proposed answer
is a selection procedure, rather than a representing object.

The categorical obstruction is elementary. For nonempty $A,Y$, a representing
set $L$ for $\mathrm{Hom}(Y,A\sqcup-)$ would satisfy, at a singleton $1$,

$$
\mathrm{Hom}(L,1)\cong\mathrm{Hom}(Y,A\sqcup1).
$$

The left side has one element; the right side has at least two. This also
shows why the empty-set cases must be stated separately.

The optimization results do not follow from the obstruction. They require
their own assumptions. In particular, a product of feasible parameter blocks
is a Cartesian product, and a geometric extreme point is not a categorical
limit or colimit. The contribution of this note is an explicit organization
of these standard mathematical ingredients with reproducible examples and
a careful account of what the software reports.

## 2. The three guarantees

### 2.1. Localization on a box

For a continuous, separately quasiconvex **full objective** $C$ on a nonempty
compact box $H$,

$$
\max_H C=\max_{\mathrm{ext}(H)}C.
$$

A maximizer exists by compactness. Each coordinate can be replaced by an
endpoint without decreasing its value, so at least one maximizing vertex
exists. This conclusion neither forces all maximizers to be vertices nor
permits the quasiconvexity assumption to be imposed only on a summand.
The full statement and proof are [Theorem 1](FORMAL_THEOREMS.md#theorem-1--vertex-localization).

### 2.2. Curvature-aware quadratic bounds

Let $Q(\theta)=c^\top\theta-\tfrac12\theta^\top F\theta$, where $F\succ0$,
and let $r_z=c-Fz$. With a proved $0\lt \mu\le\lambda_{\min}(F)$,

$$
\begin{aligned}
Q(F^{-1}c)-Q(z)&=\frac12r_z^\top F^{-1}r_z\\
&\le\frac{\|r_z\|_2^2}{2\mu}.
\end{aligned}
$$

The identity follows by completing the square about $F^{-1}c$. The inequality
uses the independently established spectral bound on $F$.

Writing $F=D+E$, with $D$ block diagonal, the independent solve $z_0=D^{-1}c$
has

$$
Q(F^{-1}c)-Q(z_0)
\le\frac{\rho^2}{2(1-\rho)}c^\top D^{-1}c,
\qquad
\rho=\|D^{-1/2}ED^{-1/2}\|_2\lt 1.
$$

This bound accounts for curvature and objective scale. A sequential coordinate
pass is a different point and uses its own residual. For a constrained
problem, feasibility of the reported candidate must also be checked; the
unconstrained maximum supplies an upper bound, which may be conservative.

[Theorem 2 and its corollaries](FORMAL_THEOREMS.md#theorem-2--quadratic-residual-and-separation-bounds)
give complete proofs, a Frobenius-norm sufficient condition, and a uniform
remainder extension. A local finite-difference Hessian alone does not provide
the required global error control for a nonlinear objective.

### 2.3. Candidate selection with an upper bound

For continuous $C$ on a nonempty compact feasible set $P$, select the best
$p$ in a finite nonempty feasible set $T$. A proved $U\ge\max_P C$ yields

$$
0\le\max_P C-C(p)\le U-C(p).
$$

The full vertex reference under the localization theorem or the quadratic
residual calculation can provide $U$. On a product box, marginal pruning also
admits the bound $\delta_A+\delta_B+\omega$, where the $\delta$ terms measure
lost marginal maxima and $\omega$ controls interaction oscillation.
[Theorem 3](FORMAL_THEOREMS.md#theorem-3--a-certified-finite-candidate-search)
states and proves both versions.

## 3. Construction and cost

A reproducible calculation records four objects: the actual feasible set,
the candidate points, the full objective values, and the source of the
upper bound. These objects determine what the reported gap means.

With at most $k$ retained vertices in each of two blocks, candidate evaluation
costs at most $k^2$ objective calls after marginal ranking. Certification
by a full vertex reference still incurs the full product cost.
Fisher diagnostics on another objective do not replace that reference.

Additional coupled constraints require renewed geometric analysis. The
intersection of a box with $x+y\le1/2$, for example, has vertices absent from
the original box. Searching only feasible original corners can miss its
linear maximum.

## 4. Exact worked examples

For $F=\left(\begin{smallmatrix}4&1\\1&4\end{smallmatrix}\right)$ and $c=(4,4)$,
the joint maximizer is $(4/5,4/5)$.

| Candidate or experiment | Exact result |
| :--- | :--- |
| One coordinate pass from zero, $(1,3/4)$ | Gap $3/40$, bounded by $3/32$ |
| Independent block solve, $(1,1)$ | Gap $1/5$, bounded by $1/3$ |
| Same matrix with $c=(4,-4)$ on $\mathbb R^2$ | Separation gap $1/3$, attaining the bound |
| Positive rescaling of $(F,c)$ | Optimizer coordinates unchanged; gaps and bounds scale together |

The localization counterexample $C(x,y)=x-x^2+y$ has maximum $5/4$ at
$(1/2,1)$, while its best box-vertex value is $1$. It invalidates the old
summand-level assumptions and motivates the corrected full-objective
condition.

All these calculations are reproduced by:

```bash
python experiments/note_publication_check.py
```

The script makes its comparisons in rational arithmetic. It verifies the
worked examples; the general conclusions are established by the proofs.

## 5. Software and evidence

The repository contains both the exact reproduction script for this edition
and older exploratory APIs. The latter continue to expose the original
`Phi` formula and auxiliary quadratic `certified` flags. The
[revision record](ORIGINAL_NOTE_REVIEW.md) shows why those fields cannot be
read as implementations of the corrected theorems.

The [historical experiment report](EXPERIMENT_REPORT.md) records numerical
demonstrations under the older conventions. Its threshold settings are not
universal accuracy bounds. In nonlinear experiments, a feasible grid point
that beats the vertex reference is useful negative evidence; a finite grid
does not prove a global maximum.

## 6. Relation to the portable selection principle

This note concerns candidate construction and objective-gap guarantees.
The repository's [Newton–tropical work](../README.md) studies singular
perturbations through feasible edge coordinates at simple polyhedral vertices.
It qualifies faces, compares surviving weighted layers, and derives response
exponents under explicit local and global hypotheses.

The connection is the insistence that the feasible geometry comes before a
selection rule. The theorem statements and backend contracts for that later
work are maintained separately in the
[face-selection manuscript](FORMAL_FACE_SELECTION.tex) and
[backend documentation](FACE_SELECTION_BACKEND.md).

## References

1. Emily Riehl, *Category Theory in Context*, Dover, 2016.
   [Author's book page](https://math.jhu.edu/~eriehl/context/).
2. Stephen Boyd and Lieven Vandenberghe, *Convex Optimization*, Cambridge
   University Press, 2004.
   [Authors' book page](https://web.stanford.edu/~boyd/cvxbook/).

The [proof source](FORMAL_THEOREMS.md) provides self-contained arguments and
the precise assumptions used in this manuscript.

**Source of this edition:** `SHORT_NOTE.md`, `Overview.md`,
`PAPER_DRAFT.md`, and `FORMAL_THEOREMS.md`, together with the exact reproduction
script. The older `short_note.tex` has not been synchronized with this
corrected Markdown edition.
