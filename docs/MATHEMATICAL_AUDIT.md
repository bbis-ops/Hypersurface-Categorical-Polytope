# Mathematical audit: signed face selection

The signed extension of the face-selection theorem needs an additional
uniform upper bound. A non-positive initial form alone does not exclude a
positive response. This affects the former Lemma 2 in
[`FORMAL_FACE_SELECTION.md`](FORMAL_FACE_SELECTION.md), even when all its
original analytic hypotheses hold.

## 1. An exact counterexample with a sharp constant

On the square $P=[0,1]^2$, take

$$
F(x,y)=-x^6-y^6,\qquad G(x,y)=-x^2+xy^2,\qquad v=(0,0).
$$

The origin is a simple, unique global base maximizer. The base principal
part is exact, the weights are $(1/6,1/6)$, and all uniform remainder
hypotheses hold. The face calculations are:

| Face | Initial form | Degree | Original qualification |
|---|---|---|---|
| $x$ axis | $-x^2$ | $1/3$ | non-positive |
| $y$ axis | $0$ | undefined | inactive |
| full cone | $-x^2$ | $1/3$ | non-positive |

Nevertheless, completing the square gives

$$
J_s=-x^6-y^6+s(-x^2+xy^2)
=-x^6-y^6+\frac{s}{4}y^4-s(x-y^2/2)^2.
$$

In fact the following is an **exact identity**:

$$
\boxed{
J_s=\frac{s^3}{432}
 -(y^2-s/6)^2(y^2+s/12)
 -s(x-y^2/2)^2-x^6.}
$$

Every subtracted term is nonnegative. At
$y=\sqrt{s/6}$ and $x=s/12$, which are feasible for $0<s\le6$,
the two squares vanish. Thus

$$
\frac{s^3}{432}-\frac{s^6}{12^6}
\le \Delta(s)=\max_P J_s
\le\frac{s^3}{432},
\qquad
\boxed{\Delta(s)\sim s^3/432.}
$$

There is no admissible coordinate face, but a curved approach produces the
response. On $x=y^2/2$, the perturbation becomes $y^4/4$. The effective
degree is $4/6=2/3$, giving exponent $3$ after this additional reduction.

Adding $y^5$ to $G$ makes the failure sharper: the original selector finds
the $y$ face with degree $5/6$ and licenses exponent $6$, while the same
curved witness already gives a lower bound of order $s^3$. That lower bound
alone disproves the licensed $\Theta(s^6)$ conclusion.

## 2. Why uniform remainders did not repair the proof

The invalid implication was

$$
W(z)\le0,\quad \sup_Z|e(\tau,z)|\to0
\quad\Longrightarrow\quad W(z)+e(\tau,z)\le0.
$$

It fails at zeros of $W$ and near such zeros. Even strict negativity on
the relative interior is insufficient: $-x^2<0$ there, but its normalized
values approach zero near the $y$ axis. The normalized **closed** face
$Z_S=\{z\in C_S:D_0(z)=1\}$ is compact; its relative-interior portion
generally is not. Maximizing directions can approach the boundary at a rate
depending on $s$.

Interior zero sets cause the same problem. With $D_0=x^4+y^4$ and
$R=-(x-y)^2+x^3$, both axis initial forms are negative and the full initial
form is non-positive, but $x=y=3s/8$ gives $27s^4/2048>0$.
The existing mixed-sign positivity check already leaves this latter case
unresolved; the all-negative initial form in the first example needed a new
check on higher layers.

## 3. A sufficient corrected selection theorem

Retain the original localization and principal-part assumptions. Suppose
the independently qualified faces have a minimum $q_*\in(0,1)$, and verify
the additional condition

$$
R(c)_+:=\max(R(c),0)\le K D_0(c)^{q_*}
\quad\text{throughout a neighborhood of the vertex.}\qquad\text{(U)}
$$

Then

$$
\Delta(s)=\Theta\bigl(s^{1/(1-q_*)}\bigr).
$$

**Proof.** On the compact section $D_0(z)=1$, the uniform base remainder
gives $D(c)\ge aD_0(c)$ for some $a>0$ near the origin. Put
$t=D_0(c)$. Condition (U) gives

$$
J_s(c)\le-at+sKt^{q_*}.
$$

The supremum of the right side for $t\ge0$ is a finite constant times
$s^{1/(1-q_*)}$. For the lower bound choose a fixed positive witness on a
qualified minimizing face and use the weighted dilation with
$\tau=d s^{1/(1-q_*)}$. Choose a fixed sufficiently small $d>0$ so that
$-dD_0(z)+d^{q_*}W(z)>0$. The remainders are little-oh of this scale.
Global isolation then identifies the local and global maxima. ∎

Condition (U) depends only on the local polynomial and base data, not on an
observed response. It is sufficient, and is not claimed necessary or a
complete decision procedure for signed perturbations. Nonnegative combined
coefficients automatically satisfy it. A positive witness for the full
cone's lowest weighted layer also suffices, since then every term has
degree at least $q_*$.

If there is no qualified face, $R_+\le K D_0$ instead certifies no positive
improvement for small $s$. Absence of a qualified face by itself does not.

## 4. A family of missed mechanisms

The obstruction persists for

$$
D_0=x^p+y^q,\qquad R=-a x^2+bxy^r,
\quad a,b>0,\quad q>2r,\quad rp>q,
$$

with positive integer orders. Put $B=b^2/(4a)$. Completing the square gives

$$
J_s=-x^p-y^q+sBy^{2r}-sa(x-b y^r/(2a))^2.
$$

The one-dimensional upper bound is attained up to the subleading cost
$x^p$ by taking

$$
y_s=(2rBs/q)^{1/(q-2r)},\qquad x_s=b y_s^r/(2a).
$$

Consequently

$$
\Delta(s)\sim
B\frac{q-2r}{q}\left(\frac{2rB}{q}\right)^{2r/(q-2r)}
s^{q/(q-2r)}.
$$

The omitted cost has order $s^{rp/(q-2r)}$, which is strictly higher by
$rp>q$. Yet the full-face initial form is $-a x^2$, because
$2/p<1/p+r/q$. Every original coordinate face is unqualified. This gives
a systematic source of regression examples and motivates elimination or
weighted blow-ups beyond the existing face enumeration.

**Constructive continuation.** The new
[quadratic-elimination theorem](FORMAL_CURVED_REDUCTION.md) now resolves
this family, as well as polynomial drivers and cancellations in the reduced
gain. Backend operation `curved_reduction` returns the exact exponent and
sharp coefficient after independently checking its hypotheses.

## 5. What the implementation now certifies

For a face with an all-negative initial layer, the selector combines all
higher layers and checks each positive monomial below the candidate degree
$q_*$ (or below $1$ when no face is selected). Such a term can be absorbed
if a negative initial monomial divides it componentwise. The ratio is then
a monomial of positive degree, tending uniformly to zero near the origin;
finitely many such terms can be absorbed simultaneously. Terms at or above
the cutoff are bounded by a constant times the corresponding power of
$D_0$ on its compact normalized section.

An unabsorbed positive term below the cutoff produces
`higher_order_unresolved`, which prevents theorem licensing and is retained
in the JSON scope blockers. This test is sufficient and conservative: an
unresolved status asks for more mathematical analysis, and does not assert
that a hidden positive channel exists. The backend retains candidate
exponents as unlicensed calculations when available.

Regression tests cover the exact identity and witness bounds, the incorrect
exponent-$6$ candidate, cancellation, absorbable remainders, critical terms,
and the backend's scope propagation. Run:

```bash
python -m pytest -q -p no:cacheprovider tests/test_face_selection.py tests/test_face_selection_backend.py
```

## 6. Exponent selection does not fix the active set

Even positive coefficients do not make a minimal winning face the exact
support of the perturbed optimizer. For

$$
J_s=-x^4-y^4+s(x+y^2)
$$

the minimum degree is $1/4$, supported by the $x$ axis, but

$$
x_s=(s/4)^{1/3},\quad y_s=(s/2)^{1/2},\quad
\Delta(s)=\frac{3}{4^{4/3}}s^{4/3}+\frac14s^2.
$$

Both coordinates are positive for every small $s>0$. Only the leading
rescaled profile lies on the $x$ axis. Reports of released and binding
constraints based solely on minimal winning faces describe candidate
leading channels; identifying the optimizer's exact support requires the
reduced maximization and possibly subleading analysis.
