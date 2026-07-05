# Architecture 2.0 Synthesis Lecture

This directory contains the Quarto source for **Architecture 2.0: Agentic
Design Loops for Computing-System Synthesis**.

Architecture 2.0 treats the architecture design loop itself as the object of
design. The lecture focuses on represented intent, constraints, world models,
tools, feedback, evidence, rejection, and human architectural judgment.

## Local Build

Run commands from this directory:

```bash
./arch2 build            # HTML + PDF (the usual build)
```

That builds both:

- `book/_build/index.html`
- `book/_build/Architecture-2.0.pdf`

Pick formats with flags, or build one target when iterating:

```bash
./arch2 build --html --pdf     # both, explicitly
./arch2 build --pdf            # PDF only
./arch2 build --html --no-layout   # HTML only, skip the PDF layout scan
./arch2 build --all           # HTML + PDF + EPUB in one pass
```

`build` and `render` share one native pipeline: the CLI owns figure preparation,
a single Quarto render pass, and every post-build audit (figure, HTML, EPUB, PDF
layout) plus scratch cleanup. There are no Quarto pre/post-render hooks; the
`arch2` CLI drives the whole build. `render --to all|html|pdf|epub` is the
lower-level single-target form; `build` is the flag-driven front end.

Preview and clean:

```bash
./arch2 serve             # build the HTML site, then serve it at 127.0.0.1:8766
./arch2 serve --no-build  # serve the existing build without rebuilding
./arch2 clean             # remove _build/ and stray LaTeX scratch files
```

## Quality Gates

Use the composed checks before publishing or committing:

```bash
./arch2 check precommit
./arch2 check standard
```

Lower-level checks are grouped by purpose:

```bash
./arch2 validate refs
./arch2 validate citations
./arch2 validate concepts
./arch2 validate disclosure
./arch2 validate svg book/chapters book/appendices
./arch2 verify figures
./arch2 verify html
./arch2 layout scan
```

Install the local commit hook with:

```bash
pip install pre-commit
pre-commit install
```

## Repository Layout

```text
synthesis/
├── arch2                         # CLI wrapper
├── cli/                          # arch2 command implementation
├── book/                         # Quarto book source
│   ├── _quarto.yml
│   ├── index.qmd
│   ├── chapters/
│   ├── appendices/
│   ├── csl/
│   ├── scripts/
│   └── tex/
├── data/                         # checked-in receipts and small datasets
├── references/                   # bibliography and source notes
└── scripts/                      # corpus and analysis helpers
```

Generated build output is intentionally ignored under `book/_build/`.

## Review Loop

The `arch2 loop` commands create source-grounded review packets and triage
reports for manuscript improvement:

```bash
./arch2 loop packet --focus progressive-disclosure
./arch2 loop review --reviewer gemini --model gemini-3.1-pro-preview
./arch2 loop triage
./arch2 loop learn
```

Loop artifacts are local working files under `.arch2/reviews/loop/` and should
not be committed.
