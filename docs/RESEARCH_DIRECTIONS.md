# Research directions (weekend probes)

Three extensions suggested for the discovery system, with implementations and formal sketches.

---

## 1. Categories where the coexponential exists

**Question.** In which settings does a coexponential (or proxy) exist, and does vertex localization survive?

**Toy probes** (`coexponential_alternatives.py`):

| Setting | Representability proxy | Vertex localization (face_bowl) |
|---------|------------------------|----------------------------------|
| `FINITE_SET` | Obstructed (Prop A.1) | Fails at strength ~0.19 (Theorem C.1) |
| `PRESHEAF_TOY` | Pointwise exponential | Same onset — geometric, not setting |
| `ABELIAN_GROUP_TOY` | Additive Hom proxy | Same |
| `POINTED_SUSPENSION` | Suspension cardinality shift | Same |

**Formal sketch (Proposition H.1).** If \(C(\theta) = g+h+r+s\cdot I(\theta)\) and \(I\) violates axis quasiconvexity on a face of \(H\), then \(\arg\max_H C \not\subseteq \mathrm{ext}(H)\) regardless of whether a coexponential exists in the ambient category. Coexponential representability changes **factorization probes**, not the **signature** of \(I\).

**Proof idea.** Theorem C.1 is purely analytic on \(H\); no functor \(Z \mapsto \mathrm{Hom}(Y,A\sqcup Z)\) enters the maximum principle.

**Run:** `python experiments/run_research_probes.py` → discovery `localization_signature_geometric`.

---

## 2. Enriched V-categories: limits, colimits, weighted Fisher

**Question.** When the Fisher matrix is enriched by weights \(w_{ij} \in V\), how do colimit (max-plus) and limit (min-plus) duals interact with leakage \(\varepsilon\)?

**Implementation** (`enriched_fisher.py`):

\[
\varepsilon_w = \frac{\|W \circ F_{\mathrm{off}}\|_F}{\|W \circ F_{\mathrm{diag}}\|_F},
\qquad
\text{colimit}_w(x_0,x_1) = \max(w_0 x_0, w_1 x_1),
\qquad
\text{limit}_w = \min(w_0 x_0, w_1 x_1).
\]

**Formal sketch (Lemma H.2).** Asymmetric weights widen \(\text{colimit}_w - \text{limit}_w\). Weighted \(\varepsilon_w\) can cross \(\varepsilon_0\) while unweighted \(\varepsilon\) does not — certification is **enrichment-dependent**.

**Proof idea.** \(\varepsilon_w\) is a monotone rescaling of off-diagonal mass; choosing \(w\) to stress cross-block entries increases \(\varepsilon_w\) without changing the underlying statistical model.

**Discovery:** `enriched_epsilon_cert_flip`, `colimit_limit_weight_gap`.

---

## 3. Live empirical Fisher for learners

**Question.** If a learner’s internal diagram polytope is the box \(H\), can we measure \(\varepsilon\) live and detect when to abandon corner-hunting?

**Implementation** (`learner_diagram.py`):

1. State \(\theta \in H\) (diagram coordinates).
2. `empirical_fisher_at` objective at \(\theta\).
3. Compare `vertex_maximize` vs `grid_maximize` → `gap_vertex_grid`.
4. `recommend_search_mode`: `CORNER_HUNTING` | `BLOCK_COORDINATE` | `INTERIOR_SEARCH`.

**Operational rule.**

| Signal | Action |
|--------|--------|
| `gap_vertex_grid > tol` | **Interior search** (Theorem C.1 regime) |
| \(\varepsilon > \varepsilon_0\) | Block coordinate ascent |
| else, certified | Corner / separable probe |

**Formal sketch (Proposition H.3).** If \(\hat\varepsilon\) (empirical Fisher) exceeds \(\varepsilon_0\) or \(C(\theta_{\mathrm{grid}}) - C(\theta_{\mathrm{vertex}}) > \tau\), then any algorithm restricted to \(\mathrm{ext}(H)\) is **unsound** for maximizing \(C\).

**Discovery:** `learner_interior_switch`, `learner_low_leakage_corners`.

**Phase 2 — trajectory logging:** `LearnerTrajectoryLog` appends \(\theta_t\), writes JSON, replays with `load_json`. Discovery: `learner_trajectory_interior`.

```bash
python experiments/log_learner_trajectory.py --out experiments/sample_learner_log.json
```

---

## 4. Finite presheaf site (not only cardinality)

**Module:** `presheaf_site.py` — objects `U`, `V`, `UV`, cover families, pointwise \((F^G)(c) = F(c)^{G(c)}\).

**Lemma H.4.** Exponentials exist **per object** on the site; global Set coexponential remains obstructed.

**Discovery:** `presheaf_site_exponential`.

---

## 5. Lawvere metric enrichment

**Module:** `lawvere_metric.py` — block distances \(d_{ij}\), weights \(w_{ij} = e^{-d_{ij}}\), metric colimit/limit.

**Lemma H.5.** Large block distance **dampens** \(\varepsilon_{\mathrm{Lawvere}}\) vs plain Fisher.

**Discovery:** `lawvere_metric_epsilon`.

---

## Commands

```bash
python experiments/run_research_probes.py
python experiments/log_learner_trajectory.py
python -m categorical_polytope discover   # base 10
python -m categorical_polytope research   # research 9
```

Artifacts: `experiments/research_discoveries.json`, `docs/RESEARCH_DISCOVERIES.md`, `docs/FORMAL_RESEARCH_ALL.md` (H.1–H.10), `docs/FORMAL_FRIDAY_PROOFS.md`, `experiments/sample_learner_log.json`, `experiments/category_tutor_session.json`.

```bash
python experiments/run_category_tutor.py
python -m categorical_polytope tutor
```

---

## Loop closure (live polytope while learning coexp)

**Free default:** scripted learner JSON on \(H\) — this is the reproducible run of record.

**Optional real learner:** `--api` against any OpenAI-compatible endpoint. Keys are
checked in order `LOOP_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`; an
`OPENROUTER_API_KEY` alone defaults to `https://openrouter.ai/api/v1` with model
`stealth/ox-alpha`. Override with `--model` / `--base-url` (or `LOOP_API_MODEL` /
`LOOP_API_BASE`).

Enter the key with the helper (masked input, never echoed, never written into
the repo), which then verifies it with one round-trip:

```powershell
.\scripts\set_api_key.ps1          # add -Persist to keep it across terminals
```

```bash
source scripts/set_api_key.sh      # Git Bash; must be sourced, not executed
```

Then:

```bash
python experiments/run_loop_closure.py --check   # validate key/endpoint only
python experiments/run_loop_closure.py --api     # full session
```

On OpenRouter the request adds `response_format: json_object` (the learner
protocol wants a bare JSON object) and `reasoning: {exclude: true}` (Ox Alpha is
a reasoning model; its chain-of-thought is not part of the reported diagram
state). Endpoints that reject either are retried once without them.

The saved summary records the backend as `model@host` and lists any turn that fell
back to the scripted arc after an endpoint error, so an `--api` artifact cannot be
mistaken for a clean real-learner trace. **Reproducibility caveat:** a stealth or
preview model may be renamed, repriced, or withdrawn; cite such runs as informal
observations and re-run against a stable named model for any published claim.

```bash
python experiments/run_loop_closure.py
python experiments/plot_loop_closure.py
python -m categorical_polytope loop
```

Artifacts: `experiments/loop_closure_session.json`, `docs/LOOP_CLOSURE.md`, `experiments/figures/loop_closure_timeline.png`.

The loop: Set obstruction → learner reports \((\lambda,\sigma,\text{confusion})\) → live \(\hat\varepsilon\) + grid–vertex gap → `INTERIOR_SEARCH` when face_bowl coupling wins.

---

## Friday–Saturday immediate batch

```bash
python experiments/run_friday_probes.py
python -m categorical_polytope friday
```

| Probe | Module | Discovery id |
|-------|--------|----------------|
| Enriched coexp UP | `enriched_coexp.py` | `enriched_coexp_up` |
| Lawvere + face_bowl | `lawvere_face_bowl.py` | `lawvere_face_bowl_threshold` |
| Sheafified certificate | `sheaf_certificate.py` | `sheafified_certificate` |
| Category-learning session | `category_learning_session.py` | `category_learning_phenomenology` |

Artifacts: `experiments/friday_discoveries.json`, `docs/FRIDAY_DISCOVERIES.md`, `experiments/CATEGORY_LEARNING_PHENOMENOLOGY.md`.
