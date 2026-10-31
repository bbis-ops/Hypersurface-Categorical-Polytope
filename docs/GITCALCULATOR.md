# The gitcalculator

**The face-selection law as a calculator** · computed by the backend, certified
against the theorem, attacked by the counter-arguments, pinned to git.

[**Quick start →**](#quick-start) · [Reading a receipt](#reading-a-receipt) · [The exact certificate](#the-exact-certificate) · [Certified measurement](#certified-measurement) · [Counter-arguments](#counter-arguments) · [History](#history-answers-have-commits) · [The tape](#the-tape) · [Web calculator](#the-web-calculator) · [Scope](#scope-and-limits)

| 01 · Theorem | 02 · Backend | 03 · Counter-arguments | 04 · Git |
| :--- | :--- | :--- | :--- |
| [Polyhedral selection law](FORMAL_FACE_SELECTION.md) | [Backend contract](FACE_SELECTION_BACKEND.md) | [Mathematical audit](MATHEMATICAL_AUDIT.md) | Blob ids, code states, history |

The repository holds three things about one result: the mathematics that states
the law, the backend that executes it, and the counter-arguments that bound it.
The gitcalculator puts them on one receipt. For a polyhedron $P$, a base
objective $F$ and a perturbation $G$ it returns the response exponent

$$
\Delta(s)=M(s)-F(v)-sG(v)=\Theta\left(s^{\gamma}\right),\qquad
\gamma=\frac{1}{1-q_\ast},
$$

together with the evidence for each step:

1. **Compute.** The public backend runs unchanged
   (`categorical_polytope.adjudication.polyhedra.backend`).
2. **Certify.** An independent checker re-derives the local model from the
   request alone and discharges the theorem's hypotheses in exact rational
   arithmetic wherever it can.
3. **Attack.** Thirteen counter-arguments from the repository's own audit and
   revision records are applied to the input. A separate measurement computes
   certified lower bounds on $\Delta(s)$ that can contradict a prediction.
4. **Pin.** Every source file and cited document is identified by its git blob
   id. The same input can be replayed against every code state in the
   repository's history.

```mermaid
flowchart LR
  accTitle: One calculation, four columns
  accDescr: A request goes to the backend, then to the exact certificate, the counter-arguments and the certified measurement. Git provenance pins all of them, and a history replay asks every earlier code state the same question.
  request("Request<br/>P, F, G")
  backend("Backend<br/>face selection")
  certificate("Exact certificate<br/>H0 to H5")
  counter("Counter-arguments<br/>and certified bounds")
  receipt("Receipt<br/>content-addressed")
  history("History<br/>every code state")
  request --> backend --> certificate --> counter --> receipt
  receipt --> history
  classDef input fill:#102734,stroke:#8199a4,color:#edf2f4
  classDef work fill:#173b46,stroke:#87b8bd,color:#edf2f4
  classDef result fill:#283b3b,stroke:#d9b77b,stroke-width:2px,color:#fff1d6
  class request input
  class backend,certificate,counter work
  class receipt,history result
  linkStyle default stroke:#9b875f,stroke-width:2px
```

---

## Quick start

Run from the repository root with Python 3.10 or newer. The calculator uses the
standard library and the local package only.

```bash
python -m gitcalculator calc --preset tilted-simplex
```

The printed receipt opens with the verdict:

```text
ANSWER    PROVED   Δ(s) = Θ(s^4/3)
          γ = 4/3   q* = 1/4   C = 0.47247 (backend, measured)
          Every hypothesis of the theorem is discharged in exact arithmetic.
```

Any input works the same way:

```bash
python -m gitcalculator calc --system "([[-1,0],[0,-1],[1,1]], [0,0,1])" --base "-((x0+x1-1)**2 + x0**4)" --perturbation "x0"
```

| Command | What it does |
| :--- | :--- |
| `calc` | One receipt; `--json` for the full record, `--history` to add the replay, `--observed 4/3` for the inverse check |
| `presets` | The thirteen canonical calculations |
| `counter` | Every counter-argument with its claim, refutation and executable witness; exits nonzero if a witness fails |
| `history` | Replays one input across every code state in git |
| `tape record` / `tape verify` | Records calculations in [`calculations/`](../calculations/) and checks them for drift |
| `site --out DIR` | Builds the static web calculator |

After `python -m pip install -e .` the same commands are available as
`gitcalculator`.

## Reading a receipt

The verdict combines all four columns.

| Verdict | Meaning |
| :--- | :--- |
| `proved` | Every hypothesis of the polyhedral theorem is discharged in exact arithmetic, or Lemma 2 proves $\Delta(s)=0$ for small $s$ |
| `proved-v22` | The separately scoped curved-reduction theorem [V.22](FORMAL_CURVED_REDUCTION.md) applies, with its own exact checks |
| `licensed` | The backend licenses the answer, but at least one hypothesis rests on a numerical probe or fails the exact check |
| `unlicensed` | An exponent was computed, but a hypothesis fails or is unresolved |
| `refused` | The input lies outside the law as stated |
| `contradicted` | Certified lower bounds outgrow a licensed exponent: a candidate counterexample to the backend |

Each theorem step is printed as a row of the **theorem ledger**: the clause
and its document anchor, what the backend computed for it, the exact
certificate, and the counter-arguments aimed at that step. A link has one of
these statuses.

| Status | Meaning |
| :--- | :--- |
| `exact` | Proved here with rational arithmetic |
| `probed` | Supported only by the backend's finite numerical probe |
| `failed` | Shown false, exactly |
| `unresolved` | The sufficient exact test does not decide it |
| `not_reached` | An earlier link failed, so the premise is missing |

The receipt id is a content address: a SHA-256 over the input, the code state,
the calculator's own code, and the discrete outcome. The same calculation on
the same code always prints the same id.

## The exact certificate

[`certify.py`](../gitcalculator/certify.py) checks each link of
[the polyhedral theorem](FORMAL_FACE_SELECTION.md) for polynomial $F$ and $G$.
It shares no numerics with the backend's predictor.

| Link | Exact method |
| :--- | :--- |
| [Standing assumptions](FORMAL_FACE_SELECTION.md#0-standing-assumptions) | Boundedness by an exact Fourier–Motzkin recession test; full dimension by an explicit interior point; polynomial degree from the syntax tree |
| [Simple vertex](FORMAL_FACE_SELECTION.md#1-setup) | Exact vertex enumeration; exactly $n$ active constraints; $A_Sv=b_S$ and $A_Su_i=-e_i$ verified |
| [Transport, V.20](FORMAL_AMBIENT_FACE_TRANSPORT.md#statement) | The repository's compiler, then a proof of the pullback identity by exact agreement on a $(d+1)^n$ product grid |
| [Hypothesis 0](FORMAL_FACE_SELECTION.md#2-global-isolation) | A nonnegative base loss with positive pure edge terms, or a concavity certificate together with strict local maximality |
| [Hypotheses 1 and 2](FORMAL_FACE_SELECTION.md#4-hypotheses-with-uniform-remainders) | The weighted Newton data of $D$: every monomial other than the diagonal principal part must have weighted degree above one |
| [Faces](FORMAL_FACE_SELECTION.md#5-faces-and-admissibility-defined-from-the-data-alone) | Exact restriction, first nonzero layer, and a rational relative-interior witness |
| [Hypothesis 5](FORMAL_FACE_SELECTION.md#6-upper-control-on-unqualified-faces) | Monomial domination and absorption, a sufficient test |

The envelope test needs one line of algebra. A positive monomial whose weighted
degree is at least the cutoff is bounded by the base on the compact normalized
section. A positive monomial below the cutoff is absorbed when a negative
monomial $N$ divides it componentwise:

$$
-bN+aNm=-N\left(b-am\right)\le0\quad\text{near the vertex, because }m\to0.
$$

When every positive monomial is controlled, $R_+\le KD_0^{q_\ast}$ holds near
the vertex. With no qualified face, the same test with cutoff one proves
$\Delta(s)=0$ for small $s$ by Lemma 2.

The certificate also compares its exact $q_\ast$ and minimal winning faces with
the backend's selection.

## Certified measurement

[`measure.py`](../gitcalculator/measure.py) supplies evidence that does not
depend on the theory. For a sequence of perturbation sizes $s$, a search in
logarithmic edge coordinates proposes a point $c$. The point is rounded to
twelve significant digits, mapped to $x=\Phi(c)$, and verified to lie in $P$.
Then

$$
L(s)=F(x)-F(v)+s\left(G(x)-G(v)\right)
$$

is evaluated exactly from the user's expressions. Every printed value is a
proved inequality $\Delta(s)\ge L(s)$, rounded down, and the receipt's own
decimals reproduce it.

The search follows the optimizer path by geometric extrapolation: optimal
coordinates follow power laws in $s$, so a narrow curved ridge such as
$x=y^2/2$ stays inside the search. Each available prediction is then judged.

- **consistent:** the local log–log slopes approach the predicted $\gamma$.
- **contradicted:** the slopes stay below $\gamma$ and $L(s)/s^{\gamma}$ rises
  monotonically. Certified gains outgrow the predicted order at the tested
  scales.
- **inconclusive:** neither holds. Bounds that fall short of a prediction can
  mean only that the search missed the optimum.

A finite sequence of scales cannot disprove an asymptotic statement. A
contradiction is certified evidence at the tested scales, and it is reported as
exactly that.

## Counter-arguments

[`counter.py`](../gitcalculator/counter.py) turns the repository's refuted claims
into checks. Each entry carries the refuted claim, the counterexample as the
documents state it, an executable witness with the outcome the current code
must produce, and an assessment of how it bears on your input: `blocks`,
`caveat`, `averted` or `clear`.

| Id | Refuted claim | Source |
| :--- | :--- | :--- |
| `ambient-axes` | Ambient axes decide the exponent | [V.20](FORMAL_AMBIENT_FACE_TRANSPORT.md#why-ambient-axes-fail) |
| `signed-channel` | A non-positive initial form excludes gain | [Audit §1](MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant) |
| `signed-sharp` | A qualified face fixes the exponent despite signed terms below it | [Audit §1](MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant) |
| `interior-zero` | Negative axis forms rule out gain | [Audit §2](MATHEMATICAL_AUDIT.md#2-why-uniform-remainders-did-not-repair-the-proof) |
| `empty-not-zero` | No qualified face means no response | [Scope](FORMAL_FACE_SELECTION.md#10-scope) |
| `active-set` | The winning face is the optimizer's support | [Audit §6](MATHEMATICAL_AUDIT.md#6-exponent-selection-does-not-fix-the-active-set) |
| `homogeneity-probe` | A measured homogeneity near one proves the principal part | [Hypotheses](FORMAL_FACE_SELECTION.md#4-hypotheses-with-uniform-remainders) |
| `isolation-probe` | Finding no rival maximizer proves uniqueness | [Isolation](FORMAL_FACE_SELECTION.md#2-global-isolation) |
| `critical-layer` | Degree-one terms obey the same law | [Term classes](FACE_SELECTION_BACKEND.md#term-level-perturbation-classification) |
| `tied-coefficient` | One tied monomial determines the coefficient | [Revision record](PRINCIPLE_DOCUMENTATION_REVIEW.md#substantive-corrections-and-clarifications) |
| `finite-scale` | The asymptotic law gives the response at a given $s$ | [Finite scale](CURVED_FINITE_SCALE.md) |
| `inverse-tolerance` | Inverse matching identifies the mechanism exactly | [Inverse](FACE_SELECTION_BACKEND.md#forward-and-inverse-power) |
| `non-simple` | The law applies at any vertex | [Scope](FORMAL_FACE_SELECTION.md#10-scope) |

`python -m gitcalculator counter` runs all thirteen witnesses. A regression
test also checks that every cited file and heading exists.

Two calculations show what the combination adds.

- **The ambient-axis answer is contradicted.** On the tilted simplex the
  ambient axes predict $\gamma=2$. The certified bounds follow
  $s^{4/3}$, with $L(s)/s^{4/3}$ agreeing with the exact coefficient
  $3\cdot4^{-4/3}$ to eleven significant digits, and contradict the exponent $2$.
- **A licensed answer can rest on a false hypothesis.** For
  $F=-(x_0^2+x_0x_1+x_1^2)$ on the unit square the backend measures a
  homogeneity of $1.0$ and licenses $\gamma=2$. The cross term $x_0x_1$ has the
  principal weight, so the diagonal principal part of Hypothesis 2 fails
  exactly. The exponent agrees with the measurement, but the theorem as stated
  does not deliver it. The receipt reports `licensed`, not `proved`.

## History: answers have commits

An answer is a function of the input and of the code, and git records every
code state the repository has had.
[`history.py`](../gitcalculator/history.py) groups commits by **code
identity**, the blob ids of the package's Python files, so a documentation-only
commit never needs recomputing. It then asks each state three questions: the
public backend, the V.22 operation where it existed, and the exact selection
core judging the same exact edge data. Every exponent a state licensed is
audited against the certified bounds. The core is audited only when the
current certificate shows that its assumed analytic hypotheses hold.

```bash
python -m gitcalculator history --preset signed-sharp
```

For the audit's sharpened counterexample, the replay recovers the episode that
the [mathematical audit](MATHEMATICAL_AUDIT.md) describes:

| Code state | Answer |
| :--- | :--- |
| `64db362` · backend introduced | The exact core **licenses** $\gamma=6$; the certified bounds contradict it |
| `90105c2` · *Correct curved-channel face selection* | The license is withheld (`higher_order_unresolved`); V.22 returns $\gamma=3$ with coefficient $1/432$ |
| Later states | Unchanged |

The replay runs each state's own code in this process, with its copy of
`categorical_polytope` swapped into `sys.modules`. Snapshots are extracted
with `git archive` into the ignored `tmp/gitcalculator/` directory.

## The tape

A desk calculator prints a paper tape; this one commits it.
[`calculations/`](../calculations/) holds one JSON file per canonical
calculation: its input, its discrete outcome, and the commit and code identity
it was recorded with.

```bash
python -m gitcalculator tape verify
```

The command recomputes every entry and prints any field that drifted. A change
to the backend, the certificate or the counter-arguments that alters a
recorded answer cannot pass silently. Record new entries deliberately with
`tape record`.

## The web calculator

```bash
python -m gitcalculator site --out tmp/gitcalculator/site
```

The build writes three files:

- `index.html` is the calculator.
- `ledger.json` holds recorded receipts and histories for the presets, so the
  page is complete before any Python starts.
- `bundle.json` is a deduplicated store of git blobs: every code state that had
  the backend, the gitcalculator, and the cited documents.

Where the browser allows WebAssembly, *Run Python here* loads
[Pyodide](https://pyodide.org) 0.26.4, writes the bundled blobs into its file
system, checks every file against its git blob id, and runs the same Python as
the command line. Custom inputs and history replays then run in the page. The
browser receipt reports the same code identity as a local run. Where
WebAssembly is unavailable, the page keeps the recorded receipts and prints the
equivalent command line for any input.

Serve the directory with any static server. The
[`gitcalculator` workflow](../.github/workflows/gitcalculator.yml) runs the tests,
the counter-argument witnesses and the tape on every push and pull request.
Publishing to GitHub Pages is opt-in: set the repository's Pages source to
*GitHub Actions* and add a repository variable `GITCALCULATOR_PAGES` with the
value `true`. Each push to `main` then builds the site from the full history and
deploys it.

## Scope and limits

- The certificate covers polynomial $F$ and $G$. Non-polynomial inputs keep
  the backend's own evidence, and the certificate reports `not_reached`.
- The Hypothesis 5 test and the concavity rules are sufficient, not necessary.
  An `unresolved` link asks for more analysis; it does not assert failure.
- Hypothesis 0 is certified only by the two exact routes. Otherwise it remains
  the backend's finite probe.
- Certified bounds are lower bounds at finitely many scales, in dimension at
  most four. They support or contradict a prediction at those scales; they are
  not an asymptotic proof.
- History replays execute the repository's past code. They report what that
  code answered, including errors, and they need the full git history.

[Return to the README →](../README.md) · [Backend contract](FACE_SELECTION_BACKEND.md) · [Mathematical audit](MATHEMATICAL_AUDIT.md)
