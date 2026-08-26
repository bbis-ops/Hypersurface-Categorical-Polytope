# Runbook — reproduce all deliverables

From package root (`categorical_polytope/`):

## One command

```bash
python experiments/run_all.py
```

Produces:

- `experiments/results.json` — quadratic Fisher coupling sweep
- `experiments/nonlinear_results.json` — interaction modes including `face_bowl`
- `experiments/figures/gap_vs_epsilon.png` (if matplotlib installed)
- `experiments/figures/nonlinear_face_bowl.png` (if matplotlib installed)
- `docs/EXPERIMENT_REPORT.md` — auto tables from JSON
- `docs/DISCOVERIES.md` + `docs/FORMAL_DISCOVERIES.md` + `experiments/discoveries.json` — findings and proofs

Or only the report:

```bash
python experiments/generate_report.py
python experiments/run_discoveries.py
python experiments/run_research_probes.py
```

## Demo + tests

```bash
python -m categorical_polytope
python -m categorical_polytope firsts
python -m categorical_polytope discover
python -m unittest discover -s tests -v
```

## Notebook

```bash
jupyter notebook notebooks/fisher_extremal_demo.ipynb
```

## Install (editable)

```bash
pip install -e ".[dev]"
```

## Read order for paper draft

0. `categorical_polytope/Overview.md` — integrated hub (start here)
1. `docs/SHORT_NOTE.md` — 1-page map
2. `docs/FORMAL_THEOREMS.md` — statements + proof sketches
3. `docs/PAPER_DRAFT.md` — extended draft with experiment summary
4. `docs/EXPERIMENT_REPORT.md` — auto-generated tables
5. `docs/BUILD_PDF.md` — LaTeX / pandoc PDF instructions
6. `experiments/results.json` + `nonlinear_results.json` — raw numbers

## Design thresholds (quick reference)

| epsilon | Action |
|---------|--------|
| <= 0.10 | Separable coproduct probe |
| 0.10 – 0.25 | Block coordinate ascent + verify gap |
| > 0.25 | Joint / full ext(H) search |

| interaction | Vertex localization |
|-------------|---------------------|
| bilinear, triple | Yes (on box) |
| face_bowl | **No** — use `grid_maximize` |
