# Building the PDFs

## Nothing else in the repository needs LaTeX

The PDFs are optional build artifacts. They are gitignored and rebuilt on
demand, and no other part of the project depends on a TeX installation: the
theorems, the backend, the experiments and the whole test suite run on the
Python standard library. `pdflatex` appears nowhere in the repository outside
this file. If you have no TeX engine, everything except these two PDFs still
works, and the [no-LaTeX route](#if-you-have-no-tex-engine) below produces
readable output from the same sources.

## Face-selection law (the 15-page note)

Source of record: `docs/FORMAL_FACE_SELECTION.tex`. Sections 1-11 are the
proof and its scope; 12 indexes it, and 13-15 are the three principles, the
ten implications and the portable statement. No figures, no bibliography.

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

Needs `experiments/figures/*.png` (from `python experiments/run_all.py`).

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

### Regenerate figures and tables first

```bash
python experiments/run_all.py
python experiments/generate_report.py
```

## If you have no TeX engine

Pandoc reads LaTeX directly and needs no TeX installation to write HTML or
Word output, so the same `.tex` sources still give a readable document. Only
pandoc's *PDF* writer shells out to a typesetting engine; the routes below
avoid it.

```bash
cd docs
pandoc FORMAL_FACE_SELECTION.tex -o FORMAL_FACE_SELECTION.html -s --mathml
pandoc short_note.tex             -o short_note.html             -s --mathml
```

`--mathml` renders the mathematics natively in current browsers. Open the
result and print to PDF for a page-numbered copy. `-s` is required: without
it pandoc emits a fragment with no document head.

For an editable copy, or to hand the proof to someone who wants Word:

```bash
pandoc FORMAL_FACE_SELECTION.tex -o FORMAL_FACE_SELECTION.docx
```

Both routes were checked against `pandoc 3.8.3` on a machine with no TeX
engine of any kind installed. Cross-references and the numbered environments
survive; precise page breaks and the LaTeX-specific spacing do not, so the
`pdflatex` output above stays the typographic record.

To produce a PDF from pandoc without a browser, install one of its HTML-based
engines (`weasyprint`, `wkhtmltopdf`, `prince`) or `typst`, then pass it with
`--pdf-engine`. None of these is required by this repository.

## Installing a TeX engine

Only needed for the `pdflatex` routes above.

| Platform | Command |
| --- | --- |
| Debian / Ubuntu | `sudo apt install texlive-latex-recommended texlive-latex-extra` |
| macOS | `brew install --cask basictex` |
| Windows | `winget install MiKTeX.MiKTeX` |

MiKTeX and TeX Live both install missing packages on first use. `tectonic` is
a smaller single-binary alternative that fetches what a document needs:

```bash
tectonic docs/FORMAL_FACE_SELECTION.tex
```
