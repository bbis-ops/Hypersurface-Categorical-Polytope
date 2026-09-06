# Building the note

One document is built from source here: `docs/FORMAL_FACE_SELECTION.tex`, the
source of record for the face-selection law. Sections 1-11 are the proof and
its scope; 12 indexes it, and 13-15 are the three principles, the ten
implications and the portable statement. No figures, no bibliography.

Nothing else in the project needs a build step, and nothing else needs LaTeX:
the theorems, the backend, the experiments and the test suite are Python
standard library only. `pdflatex` is named nowhere in the repository outside
this file.

## Pick a route

| You want | You need | Run |
| --- | --- | --- |
| To read it now | pandoc | [HTML](#html-in-the-browser) |
| A PDF, without installing a typesetter | pandoc, any browser | [HTML](#html-in-the-browser), then print to PDF |
| An editable copy, or to hand it to someone in Word | pandoc | [Word](#word) |
| The typeset reference, with exact page layout | a TeX engine | [LaTeX](#latex) |

Every route carries the complete text and mathematics. They differ only in
presentation: the LaTeX build fixes page breaks and spacing, so it is the
typographic reference, and the others are equally faithful to the content.
Pick on what you already have installed.

## HTML in the browser

```bash
cd docs
pandoc FORMAL_FACE_SELECTION.tex -o FORMAL_FACE_SELECTION.html -s --mathml
```

Pandoc reads LaTeX directly and writes HTML without any TeX installation;
only its *PDF* writer shells out to a typesetter. `--mathml` renders the
mathematics natively in current browsers, and `-s` is required or pandoc
emits a headless fragment. Open the result and print to PDF for a
page-numbered copy.

## Word

```bash
cd docs
pandoc FORMAL_FACE_SELECTION.tex -o FORMAL_FACE_SELECTION.docx
```

## LaTeX

```bash
cd docs
pdflatex FORMAL_FACE_SELECTION.tex
pdflatex FORMAL_FACE_SELECTION.tex
```

Two passes: the second resolves the cross-references between the hypotheses,
lemmas and the numbered implications. Output: `docs/FORMAL_FACE_SELECTION.pdf`.

### If you need a TeX engine

| Platform | Command |
| --- | --- |
| Debian / Ubuntu | `sudo apt install texlive-latex-recommended texlive-latex-extra` |
| macOS | `brew install --cask basictex` |
| Windows | `winget install MiKTeX.MiKTeX` |

MiKTeX and TeX Live fetch missing packages on first use. `tectonic` is a
single-binary alternative that downloads only what a document needs:

```bash
tectonic docs/FORMAL_FACE_SELECTION.tex
```

Pandoc can also write the PDF directly if you install one of its HTML-based
engines (`weasyprint`, `wkhtmltopdf`, `prince`) or `typst`, then pass
`--pdf-engine`. None of these is required.

## Verified

The pandoc routes were checked with `pandoc 3.8.3` on a machine with no TeX
engine of any kind: both commands succeed, the note converts without
warnings, and the HTML carries its mathematics as MathML. Cross-references
and the numbered environments survive conversion.

## Other sources in docs/

Not currently distributed, kept for reference:

- `FORMAL_FACE_SELECTION.md` — a parallel plain-text rendering of the proof
  sections only, maintained by hand.
- `short_note.tex` — a shorter write-up; its LaTeX build embeds
  `experiments/figures/*.png`, so run `python experiments/run_all.py` first.
- `redo.tex` — an earlier draft without the isolation lemma or the
  non-circular admissibility definition, superseded by
  `FORMAL_FACE_SELECTION.tex`.
- `latexproof.tex` — earlier proof material.

Built PDFs are gitignored and rebuilt on demand; they are not part of the
repository.
