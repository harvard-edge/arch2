# Provenance notebooks

One notebook per study. Each one reads the receipt the book cites, **recomputes
the published number from the raw rows**, and says so plainly when the two
disagree. They are audits, not presentations: nothing in them restates a figure
from the manuscript.

This is the reader-facing half of the evidence discipline. `data/validate_provenance.py`
and `data/validate_figure_provenance.py` check that every dataset and figure has
a recorded source; these notebooks let anyone check that the source actually says
what the book claims.

## Why marimo rather than Jupyter

The repository already uses marimo for `labs/notebooks/`, so this follows the
house convention. Four properties earn it:

| Property | Why it matters here |
| --- | --- |
| Notebooks are **plain Python** | `git diff` is readable, review is possible, no JSON blobs or embedded output |
| **No hidden state** | Cells form a dependency graph and re-run in order, so a stale cell cannot fake agreement |
| Runs **in the browser** via WASM | A reader needs no Python, no install, no Colab account |
| Exports to **static HTML** | The already-executed page opens instantly for readers who only want to look |

Jupyter would work, but its diffs are unreadable and its execution order is not
guaranteed, which is exactly the property an audit cannot afford. If Colab is
ever wanted, `jupytext` (already a dependency) converts these files to `.ipynb`
without maintaining a second copy.

## Running one

```bash
python3 -m venv .venv-ast
.venv-ast/bin/pip install -r data/studies/02-ast-complexity-cliff/requirements.txt marimo

.venv-ast/bin/marimo edit data/notebooks/study_02_ast_complexity.py   # interactive
.venv-ast/bin/marimo run  data/notebooks/study_02_ast_complexity.py   # read-only app
```

## Publishing them

```bash
.venv-ast/bin/python data/notebooks/export_notebooks.py           # build
.venv-ast/bin/python data/notebooks/export_notebooks.py --check   # verify scrub
```

Each notebook produces two artifacts under `www/notebooks/`:

- `<name>.html` — static, already executed. Opens instantly.
- `<name>/` — the live notebook running under Pyodide. The reader's own browser
  fetches the published receipt and recomputes the number.

**Always export through that script, never by calling `marimo export` directly.**
`marimo export` walks up to the project root and copies sibling files into the
bundle; on this repository it pulls in `CLAUDE.md`. The script deletes AI
configuration files from every export and then verifies they are gone, exiting
non-zero if any survive.

## Writing a new one

The pattern that makes these audits rather than demos:

1. **State the published claim first**, in the reader's words, before any code.
2. **Load local-or-published.** Read the repository copy when running from a
   checkout, otherwise fetch the same file from the site. Find the repo root by
   walking up for a marker; the browser runtime defines `__file__` as a shallow
   virtual path, so a fixed `parents[n]` raises `IndexError` there.
3. **Show the rows**, in a table the reader can search, sort, and export. A
   receipt nobody can inspect is not evidence.
4. **Recompute the headline from those rows**, never from a stored summary.
5. **Compare recomputed against recorded, and fail loudly.** This is the cell
   that makes it an audit. Test it by tampering with the recorded value and
   confirming the verdict flips.
6. **Report the sensitivity checks next to the headline**, so a reader cannot
   leave with only the largest number.
7. **End with what the measurement does not establish.** The boundaries are why
   the study is credible.
