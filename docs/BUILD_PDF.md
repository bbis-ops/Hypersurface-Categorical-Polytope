# Building PDF from the short note

## Option A — LaTeX (figures embedded)

Requires `pdflatex` and `experiments/figures/*.png` (from `python experiments/run_all.py`).

```bash
cd docs
pdflatex short_note.tex
pdflatex short_note.tex
```

Output: `docs/short_note.pdf`

## Option B — Pandoc from Markdown

```bash
pandoc SHORT_NOTE.md -o SHORT_NOTE.pdf --pdf-engine=pdflatex
```

## Option C — HTML (no LaTeX)

```bash
pandoc SHORT_NOTE.md -o SHORT_NOTE.html -s
```

Open in browser; print to PDF.

## Regenerate figures and tables first

```bash
python experiments/run_all.py
python experiments/generate_report.py
```
