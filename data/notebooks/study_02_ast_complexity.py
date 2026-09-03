import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import csv
    import io
    import json
    import statistics
    from pathlib import Path

    import marimo as mo

    # This notebook runs two ways, and both must give the same answer.
    #
    #   Locally, it reads the receipts in this repository.
    #   In the browser (marimo WASM), there is no filesystem, so it fetches the
    #   same files from the published site.
    #
    # A reader who opens the hosted notebook is therefore auditing the exact
    # artifacts the book ships, not a copy prepared for the demo.

    SITE = "https://arch2.mlsysbook.ai"

    def _find_repo():
        """Repo root when running from a checkout; None in the browser.

        The browser runtime does define __file__, but as a shallow virtual path,
        so walking a fixed number of parents raises IndexError there. Walk up
        looking for a marker instead, and give up quietly if there is none.
        """
        try:
            here = Path(__file__).resolve()
        except (NameError, OSError):
            return None
        for parent in [here, *here.parents]:
            if (parent / "data" / "source-receipts").is_dir():
                return parent
        return None

    REPO = _find_repo()

    def load(local_relpath: str, site_relpath: str) -> str:
        """Return file text from the repo if present, else from the site."""
        if REPO is not None:
            candidate = REPO / local_relpath
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        try:
            import pyodide.http as _ph  # only exists in the browser runtime

            return _ph.open_url(f"{SITE}/{site_relpath}").read()
        except ImportError:
            from urllib.request import urlopen

            with urlopen(f"{SITE}/{site_relpath}") as r:
                return r.read().decode("utf-8")

    RECEIPT_TEXT = load(
        "data/source-receipts/hardware_ast_complexity_measured.csv",
        "data/observatory/hardware_ast_complexity_measured.csv",
    )
    SOURCES_TEXT = load(
        "data/source-receipts/hardware_ast_complexity_measured_sources.csv",
        "data/observatory/hardware_ast_complexity_measured_sources.csv",
    )
    SUMMARY_TEXT = load(
        "data/studies/02-ast-complexity-cliff/hardware_ast_complexity_measured_summary.json",
        "data/observatory/hardware_ast_complexity_measured_summary.json",
    )
    return (
        RECEIPT_TEXT,
        SOURCES_TEXT,
        SUMMARY_TEXT,
        csv,
        io,
        json,
        mo,
        statistics,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Study 02 · Source complexity of benchmark RTL vs. production RTL

        **The published claim:** benchmark reference RTL is about **6.7x** simpler
        than production-oriented open RTL, measured as concrete syntax nodes per
        module declaration.

        This notebook is the claim's audit trail. It reads the receipt the book
        cites, recomputes the headline number from the raw rows, and fails if the
        two disagree. Nothing here restates a number from the manuscript; every
        figure below is derived in front of you.

        > An earlier version of this study published **175x** from a file that no
        > tool produced. Its per-module values were literal tables inside its own
        > generator, and the commit hashes in its header were hand-typed
        > placeholders. That file now sits marked in `data/synthetic/`. This
        > notebook exists so the replacement can be checked rather than trusted.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""## 1. What the receipt says about itself""")
    return


@app.cell
def _(RECEIPT_TEXT, csv, io, mo):
    _header = [l for l in RECEIPT_TEXT.splitlines() if l.startswith("#")]
    _cols = next(
        csv.reader(
            io.StringIO(
                "\n".join(l for l in RECEIPT_TEXT.splitlines() if not l.startswith("#"))
            )
        )
    )
    # A receipt states its source either in a header block or per row. This one
    # does it per row, which is the stronger form: provenance travels with the
    # measurement instead of describing the file as a whole.
    _per_row = [
        c
        for c in _cols
        if c
        in (
            "repository_url",
            "repository_commit",
            "source_path",
            "source_sha256",
            "citation",
            "source_url",
            "reference",
        )
    ]
    if _header:
        provenance = mo.md("```\n" + "\n".join(_header) + "\n```")
    elif _per_row:
        provenance = mo.md(
            "This receipt carries **per-row provenance** rather than a header "
            "block, which is the stronger form: the source travels with each "
            "measurement instead of describing the file as a whole.\n\n"
            + "\n".join(f"- `{c}`" for c in _per_row)
        )
    else:
        provenance = mo.md(
            "**No provenance in the header and none per row.** That is itself a "
            "finding: this file cannot be traced to a source."
        )
    provenance
    return (provenance,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Every row names the file it came from

        A receipt is only as good as its weakest row. Each measurement below
        carries the repository, the pinned commit, the path inside that
        repository, and the SHA-256 of the exact file bytes that were parsed.
        """
    )
    return


@app.cell
def _(RECEIPT_TEXT, csv, io, mo):
    rows = list(
        csv.DictReader(l for l in io.StringIO(RECEIPT_TEXT) if not l.startswith("#"))
    )
    table = mo.ui.table(
        [
            {
                "corpus": r["corpus_category"],
                "repo": r["dataset_name"],
                "commit": r["repository_commit"][:12],
                "module": r["module_name"],
                "syntax nodes": int(r["concrete_syntax_nodes"]),
                "clean LoC": int(r["clean_loc"]),
                "source_sha256": r["source_sha256"][:12],
            }
            for r in rows
        ],
        page_size=8,
        label=f"{len(rows):,} parsed module declarations",
    )
    table
    return rows, table


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Recompute the headline number

        The ratio is a median of medians only in the sensitivity check; the headline
        is module-weighted, so it is the median over all modules in each group.
        """
    )
    return


@app.cell
def _(mo, rows, statistics):
    BENCH = "AI benchmark reference RTL"
    PROD = "Production-oriented open RTL"

    def _median(group, col):
        return statistics.median(
            int(r[col]) for r in rows if r["corpus_category"] == group
        )

    bench_nodes = _median(BENCH, "concrete_syntax_nodes")
    prod_nodes = _median(PROD, "concrete_syntax_nodes")
    bench_loc = _median(BENCH, "clean_loc")
    prod_loc = _median(PROD, "clean_loc")
    node_ratio = prod_nodes / bench_nodes
    loc_ratio = prod_loc / bench_loc

    n_bench = sum(1 for r in rows if r["corpus_category"] == BENCH)
    n_prod = sum(1 for r in rows if r["corpus_category"] == PROD)

    mo.md(
        f"""
        | Measure | Benchmark ({n_bench:,} modules) | Production ({n_prod:,} modules) | Ratio |
        | --- | ---: | ---: | ---: |
        | Median concrete syntax nodes | {bench_nodes:,} | {prod_nodes:,} | **{node_ratio:.2f}x** |
        | Median clean lines of code | {bench_loc:,} | {prod_loc:,} | {loc_ratio:.2f}x |
        """
    )
    return (
        BENCH,
        PROD,
        bench_loc,
        bench_nodes,
        loc_ratio,
        n_bench,
        n_prod,
        node_ratio,
        prod_loc,
        prod_nodes,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Does the recomputation match what was recorded?

        This is the cell that makes the notebook an audit rather than a
        presentation. If the receipt is edited, or the summary drifts from the
        rows it claims to summarize, this cell turns red.
        """
    )
    return


@app.cell
def _(SUMMARY_TEXT, json, loc_ratio, mo, node_ratio):
    _summary = json.loads(SUMMARY_TEXT)
    _recorded = _summary["module_weighted_ratios"]
    _checks = [
        (
            "concrete syntax node ratio",
            node_ratio,
            _recorded["median_concrete_syntax_node_ratio"],
        ),
        ("clean LoC ratio", loc_ratio, _recorded["median_clean_loc_ratio"]),
    ]
    _lines, _ok = [], True
    for _name, _live, _rec in _checks:
        _agree = abs(_live - _rec) < 1e-6
        _ok &= _agree
        _lines.append(
            f"| {_name} | {_live:.6f} | {_rec:.6f} | {'match' if _agree else 'DISAGREE'} |"
        )
    verdict = mo.md(
        "| Quantity | Recomputed here | Recorded in summary | |\n| --- | ---: | ---: | --- |\n"
        + "\n".join(_lines)
        + (
            "\n\n**The receipt agrees with itself.**"
            if _ok
            else "\n\n**MISMATCH. Do not cite this study until it is resolved.**"
        )
    )
    verdict
    return (verdict,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. The claim the book is allowed to make

        The pooled ratio is not the whole story, and the notebook should not let a
        reader walk away with only the largest number. Two sensitivity checks move
        it, and both are reported in the manuscript alongside the headline.
        """
    )
    return


@app.cell
def _(SUMMARY_TEXT, json, mo, node_ratio):
    _s = json.loads(SUMMARY_TEXT)
    _cb = _s["corpus_balanced_sensitivity"]["median_concrete_syntax_node_ratio"]
    _df = _s["diagnostic_free_sensitivity"]["ratios"][
        "median_concrete_syntax_node_ratio"
    ]
    mo.md(
        f"""
        | Weighting | Ratio |
        | --- | ---: |
        | Module-weighted, all files (headline) | **{node_ratio:.2f}x** |
        | Diagnostic-free files only | {_df:.2f}x |
        | Equal weight per repository | {_cb:.2f}x |

        The direction survives every weighting. The magnitude does not, which is
        why the manuscript states all three and calls the pooled figure a result
        for these six repositories rather than a universal ratio.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 6. Where the corpora came from

        The miner clones each repository at a pinned commit and verifies the
        checked-out SHA before parsing, so a moved branch cannot silently change
        the result.
        """
    )
    return


@app.cell
def _(SOURCES_TEXT, csv, io, mo):
    _src = list(
        csv.DictReader(l for l in io.StringIO(SOURCES_TEXT) if not l.startswith("#"))
    )
    corpora = mo.ui.table(
        [
            {
                "repository": s["dataset_name"],
                "role": s["corpus_category"],
                "commit": s["repository_commit"],
                "files parsed": int(s["selected_files"]),
                "modules": int(s["parsed_modules"]),
                "url": s["repository_url"],
            }
            for s in _src
        ],
        page_size=10,
        label="pinned corpora",
    )
    corpora
    return (corpora,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 7. What this measurement does not establish

        - It measures **source syntax**, not elaborated design. Files are parsed
          standalone with error recovery, not preprocessed with a full include path.
        - Parser diagnostics are retained rather than used to drop macro-heavy
          production RTL, which would bias the comparison toward simple files.
        - Hierarchy depth follows an instantiation only when the child module name
          has exactly one definition in the corpus, so it is a **lower bound**.
        - Clock-event and CDC counts elsewhere in the receipt are **lexical
          indicators**, not verified clock domains or crossings.
        - Six repositories were chosen for being public and pinnable. Nothing here
          generalizes to closed commercial IP.

        To regenerate the underlying data rather than audit it, see
        `data/studies/02-ast-complexity-cliff/REPRODUCE.md`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
