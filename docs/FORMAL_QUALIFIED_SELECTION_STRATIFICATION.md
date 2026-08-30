# The stratified qualified-selection law

Formal result **V.18** · backend asset `portable-principle.v7` · executable
implementation: `categorical_polytope/face_selection_phase.py`.

## Abstract

The face-selection phase fan cannot be complete if it assumes that every face
mechanism remains admissible throughout parameter space. A leading channel can
vanish by cancellation, become non-positive, or become positive and enter the
competition. These are qualification transitions, not degree-order
transitions.

V.18 incorporates them into the exact phase structure. For mechanisms with
affine degree and combined coefficient laws

$$
q_j(\theta)=a_j+b_j\theta,
\qquad
c_j(\theta)=u_j+v_j\theta,
$$

define the qualified set

$$
\mathcal Q(\theta)=
\left\{
j:
F_j\text{ is geometrically admitted},\;
c_j(\theta)>0,\;
0<q_j(\theta)<1
\right\}.
$$

The selected degree is

$$
q_*(\theta)=\min_{j\in\mathcal Q(\theta)}q_j(\theta).
$$

Every possible change is contained in the finite wall set

$$
q_i=q_j,qquad q_i=0,qquad q_i=1,qquad c_i=0.
$$

Thus qualification, selection, and scaling form one exact stratified law.

---

## Theorem V.18 — stratified qualified selection

Let $[L,U]$ be a closed parameter interval and let $J$ be a finite collection
of localized face mechanisms. Assume:

1. tangent-cone geometry and face incidence are fixed on $[L,U]$;
2. each mechanism represents a single positive monomial channel, or a group of
   like channels whose coefficients have first been combined exactly;
3. every combined coefficient $c_j$ and degree $q_j$ is affine;
4. local base maximality, principal-remainder control, and global isolation
   hold uniformly on the interval; and
5. coefficient positivity is a valid certificate of positivity for each
   represented face initial form.

Remove the points satisfying

$$
q_i=q_j,\quad q_i=0,\quad q_i=1,\quad\text{or}\quad c_i=0.
$$

On every remaining open chamber:

- the sign of every coefficient is constant;
- the relevance status of every degree is constant;
- the qualified set $\mathcal Q$ is constant;
- the strict degree ordering is constant;
- the winning mechanism is constant; and
- whenever $\mathcal Q$ is nonempty,

  $$
  \Delta(s;\theta)=
  \Theta\!\left(s^{1/(1-q_*(\theta))}\right).
  $$

At a coefficient wall $c_j=0$, the corresponding weighted layer cancels. The
selector removes that channel at the wall and exposes the next qualified layer
or face. Therefore exponent changes caused by exact cancellation are predicted
by the same finite stratification.

### Proof

The signs of the affine functions $c_j$, $q_j$, $1-q_j$, and $q_i-q_j$ are
constant between consecutive roots. Hence coefficient positivity, relevance,
and degree ordering are constant on each chamber. Their conjunction makes the
qualified set and its argmin constant. Uniform face-selection hypotheses then
convert the selected degree into the stated asymptotic consequence. At
$c_j=0$, the represented initial form vanishes exactly and is not a positive
channel, so it is excluded before the minimum is taken. ∎

---

## Worked cancellation-driven transition

Consider two already localized mechanisms:

$$
q_A=\frac14,qquad c_A(\theta)=\theta-\frac13,
$$

and

$$
q_B=\frac12,qquad c_B=1.
$$

For $\theta<1/3$, $A$ is non-positive and $B$ controls:

$$
q_*=\frac12,qquad \gamma=2.
$$

At $\theta=1/3$, $A$ cancels exactly, so $B$ still controls. For
$\theta>1/3$, $A$ becomes positive and its lower weighted degree wins:

$$
q_*=\frac14,qquad \gamma=\frac43.
$$

This transition is invisible to a phase diagram that compares degree laws
alone: the two degrees never cross. It is exposed only by qualified selection.

---

## Machine-readable qualification certificate

At every queried parameter, the backend classifies each mechanism as one of:

- `qualified` — positive with $0<q<1$;
- `cancelled` — the combined coefficient is exactly zero;
- `non_positive` — the coefficient is negative;
- `zero_weight` — $q\le0$;
- `critical` — $q=1$;
- `subleading` — $q>1$; or
- `geometry_filtered` — the face mechanism was not admitted.

Only `qualified` mechanisms enter the minimum. The response contains the full
certificate, the winners, the exponent consequence, and exact robustness
distance to the nearest wall where the selected mechanism actually changes.

## Scope boundary

Affine coefficient positivity completely decides a single monomial channel and
an exactly combined collection of like monomials. It does not by itself decide
positivity of a general mixed-sign initial form with different monomial
signatures. Such forms require an explicit positivity witness or an additional
semialgebraic positivity stratum. Geometry changes also require separate
strata.

The v4 backend therefore requires explicit uniform analytic assumptions before
labeling the asymptotic consequence `licensed`. Otherwise it returns the exact
qualified-selection calculation as `unlicensed` with named blockers.

## Reproduce

```bash
python -m categorical_polytope.adjudication.polyhedra.backend \
  --input experiments/face_selection_qualified_v18_request.json --pretty
python -m pytest -q tests/test_face_selection_phase.py
```
