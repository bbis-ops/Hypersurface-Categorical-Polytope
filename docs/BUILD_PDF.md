# Building the PDFs

## Face-selection law (the 15-page note)

Source of record: `docs/FORMAL_FACE_SELECTION.tex`. Sections 1-11 are the
proof and its scope; 12 indexes it, and 13-15 are the three principles, the
ten implications and the portable statement. Requires `pdflatex` only - no
figures, no bibliography.

```bash
cd docs
pdflatex FORMAL_FACE_SELECTION.tex
pdflatex FORMAL_FACE_SELECTION.tex
```

Two passes: the second resolves the cross-references between the hypotheses,
lemmas and the numbered implications. Output: `docs/FORMAL_FACE_SELECTION.pdf`.

`docs/FORMAL_FACE_SELECTION.md` is a parallel plain-text rendering of the
proof sections only, kept by hand. `docs/redo.tex` is an earlier draft without
the isolation lemma or the non-circular admissibility definition; it is
superseded by the file above.

## Short note

### Option A — LaTeX (figures embedded)

Requires `pdflatex` and `experiments/figures/*.png` (from `python experiments/run_all.py`).

```bash
cd docs
pdflatex short_note.tex
pdflatex short_note.tex
```

Output: `docs/short_note.pdf`

### Option B — Pandoc from Markdown

```bash
pandoc SHORT_NOTE.md -o SHORT_NOTE.pdf --pdf-engine=pdflatex
```

### Option C — HTML (no LaTeX)

```bash
pandoc SHORT_NOTE.md -o SHORT_NOTE.html -s
```

Open in browser; print to PDF.

### Regenerate figures and tables first

```bash
python experiments/run_all.py
python experiments/generate_report.py
```
