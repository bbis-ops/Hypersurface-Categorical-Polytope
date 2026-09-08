# Revision record — the portable principle documentation

**7 September 2026**

This review covers the [orthant theorem](FORMAL_NEWTON_TROPICAL.md),
[polyhedral theorem](FORMAL_FACE_SELECTION.md),
[qualification theorem](FORMAL_QUALIFIED_SELECTION_STRATIFICATION.md),
and [backend contract](FACE_SELECTION_BACKEND.md).

## Presentation changes

The four guides now share editorial covers, a linked reading sequence,
rendered mathematical notation, and native Mermaid diagrams. Proofs and
extended examples use expandable sections; hypotheses and scope boundaries
remain directly visible. The covers are illustrative, not data plots.

## Substantive corrections and clarifications

| Earlier wording or omission | Revised statement and reason |
| :--- | :--- |
| Sharp formulas and numerical optimization described together as exact | The theorem's variational constant is distinguished from floating-point formulas and heuristic coupled maximization |
| The pure single-axis formula was stated with a little-oh term | The pure model has exact equality; remainder extensions require the asymptotic hypotheses |
| Every earlier order law automatically receives a sharp constant | The upgrade requires the stated leading model, localization, and uniform remainder control |
| The unrestricted orthant model includes arbitrary positive higher-degree terms | Degree greater than one makes that supremum infinite; the compact local theorem is stated explicitly |
| “Winner-take-all” could suggest one tied monomial determines the coefficient | The least degree determines the exponent; all tied lowest-layer terms enter the coefficient |
| A raywise argument was used to identify the optimized leading coefficient | A compactness bound on the rescaled maximizing set now justifies uniform convergence and maximization |
| The edge chart was called linear despite its vertex translation | Its generator map is linear; the chart itself is affine |
| The localization proof divided by a bound that could be zero | The oscillation bound handles constant perturbations separately |
| The nonempty faces were said to partition every point of the cone | They partition nonzero points; the origin is its own zero-dimensional stratum |
| A measured homogeneity near one establishes the principal-part hypothesis | It is a numerical diagnostic and does not prove the diagonal identity or uniform remainders |
| Homogeneity and isolation were described as never used to gate the backend | Both participate in the predictor's admission check; finite probes remain weaker than proofs |
| A cancelled channel automatically exposes every next layer | Only represented replacement mechanisms are available to the affine engine; completeness is an external requirement |
| A fixed chamber was easy to read as a fixed numerical exponent | Winning identities are fixed; an affine selected degree can vary within the chamber |
| Chamberwise asymptotics could be read as uniform up to cancellation walls | Fixed-parameter consequences are separated from uniform estimates requiring a positive lower witness |
| Phase licensing could be read as independent analytic verification | It checks caller Boolean attestations and has no separate positive-gain-envelope check or automatic polynomial signed-layer guard |
| Exact forward refinement was easy to read as exact inverse matching | The inverse block matches the numerical predictor's admitted face degrees within an absolute weight tolerance |

The polyhedral uniform positive-gain envelope and the signed-channel
counterexample are retained. The orthant sharp constant is derived for the
explicit positive finite model. No general signed-perturbation theorem,
complete active-set recovery, or automatic proof of caller assumptions is
claimed.

The backend guide retains the current v8 capability map and separate
`face-selection.backend.v1` / `curved-reduction.backend.v1` contracts.
The mathematical and executable changes in this revision are documentation
changes: the backend algorithms and status behavior are unchanged.

## Independent checks

The slow-crossover table was recomputed using 60-digit decimal arithmetic:
set $t=\sqrt{x}$, solve $4t^3-200st-0.001s=0$ for its positive root, and
evaluate $\Delta(s)=50st^2+0.00075st$. The five displayed slopes agree after
rounding. The isolated-gap crossover is approximately
$2.59808\times10^{-12}$ and is explicitly not a mixture-accuracy certificate.

The qualification example now includes the exact separable realization
$F=-x^4-y^2$, $G_\theta=(\theta-1/3)x+y$. Independent axis maximization gives
the displayed sum of gap powers and verifies both sides of the wall.

Executable regression and reproduction commands are linked in the revised
guides and [runbook](RUNBOOK.md). Passing examples and tests checks
implementation consistency; the mathematical conclusions rely on the
displayed proofs and hypotheses.

## Validation of this edition

| Check | Result |
| :--- | :--- |
| Orthant, face, phase, transport, discovery, and backend regression group | 96 tests passed |
| Current runbook evidence suite, including the documentation gate | 14 of 14 passed |
| Local links and anchors across these five Markdown files | 99 valid |
| Embedded examples | Five JSON blocks and four Python blocks parsed; the public Python integration example passed its assertions |
| GitHub math lint on these five files | Zero errors and zero warnings |
| Local visual review | All four guides, all four native diagrams, and expanded proof content rendered without errors; light and dark presentation inspected |

The visual check used a local Markdown/KaTeX/Mermaid preview. It was not a
live GitHub rendering check. The four SVG covers also passed XML and
accessibility-metadata checks.
