import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import csv
    import io
    import statistics
    from pathlib import Path

    import marimo as mo

    # Runs from a checkout or from the browser. See study_02 for the rationale.
    SITE = "https://arch2.mlsysbook.ai"

    def _find_repo():
        try:
            here = Path(__file__).resolve()
        except (NameError, OSError):
            return None
        for parent in [here, *here.parents]:
            if (parent / "data" / "studies").is_dir():
                return parent
        return None

    REPO = _find_repo()

    def load(local_relpath: str, site_relpath: str) -> str:
        if REPO is not None:
            candidate = REPO / local_relpath
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        try:
            import pyodide.http as _ph

            return _ph.open_url(f"{SITE}/{site_relpath}").read()
        except ImportError:
            from urllib.request import urlopen

            with urlopen(f"{SITE}/{site_relpath}") as r:
                return r.read().decode("utf-8")

    PILOT_TEXT = load(
        "data/studies/06-eda-seed-dispersion/openroad_gcd_placement_seed_pilot.csv",
        "data/observatory/openroad_gcd_placement_seed_pilot.csv",
    )
    return PILOT_TEXT, csv, io, mo, statistics


@app.cell
def _(mo):
    mo.md(
        r"""
        # Study 06 · How much does a placement seed move the result?

        **The published claim:** across 20 OpenROAD placement runs that differ
        only in the global-placement random seed, area moves by **0.84%** and
        setup slack by **3.83%**. Slack is the more seed-sensitive quantity by
        roughly a factor of five.

        This notebook is different in shape from study 02. That one parses a
        corpus; this one is a **controlled experiment**, so the interesting
        question is not only "what is the number" but "was the control actually
        held". A seed sweep that accidentally varied the floorplan would produce
        a large, meaningless dispersion. The checks below test the control before
        they report the result.

        > This study replaced a file whose values came from `_gaussian_noise()`
        > while its header named OpenROAD, Yosys and OpenSTA versions that were
        > string literals in the generator. It claimed 3.2% to 7.8% dispersion.
        > The measured answer is smaller and the ratio between the two metrics is
        > the part that survived.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""## 1. The runs""")
    return


@app.cell
def _(PILOT_TEXT, csv, io, mo):
    rows = list(
        csv.DictReader(l for l in io.StringIO(PILOT_TEXT) if not l.startswith("#"))
    )
    runs = mo.ui.table(
        [
            {
                "seed": int(r["seed"]),
                "status": r["status"],
                "GPL seed": int(r["gpl_random_seed"]),
                "area um2": float(r["detailedplace_instance_area_um2"]),
                "setup WNS ns": float(r["detailedplace_setup_wns_ns"]),
                "wall s": float(r["wall_time_seconds"]),
                "floorplan sha256": r["floorplan_odb_sha256"][:12],
            }
            for r in rows
        ],
        page_size=10,
        label=f"{len(rows)} OpenROAD runs",
    )
    runs
    return rows, runs


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Was the experiment actually controlled?

        Three things must hold before any dispersion number means anything.
        Every run must have completed, every run must have started from the
        **same floorplan**, and the seed must actually have **varied**.
        """
    )
    return


@app.cell
def _(mo, rows):
    _passed = sum(1 for r in rows if r["status"] == "pass")
    _rc_ok = sum(1 for r in rows if int(r["docker_returncode"]) == 0)
    _floorplans = {r["floorplan_odb_sha256"] for r in rows}
    _seeds = {int(r["gpl_random_seed"]) for r in rows}
    _placements = {r["placement_odb_sha256"] for r in rows}
    _errors = sum(
        int(r["globalplace_flow_errors"]) + int(r["detailedplace_flow_errors"])
        for r in rows
    )

    _checks = [
        ("every run completed", _passed == len(rows), f"{_passed}/{len(rows)} pass"),
        ("docker exited 0 every time", _rc_ok == len(rows), f"{_rc_ok}/{len(rows)}"),
        (
            "one shared floorplan input",
            len(_floorplans) == 1,
            f"{len(_floorplans)} distinct floorplan hash",
        ),
        (
            "the seed really varied",
            len(_seeds) == len(rows),
            f"{len(_seeds)} distinct seeds",
        ),
        (
            "placements actually differ",
            len(_placements) > 1,
            f"{len(_placements)} distinct placement hashes",
        ),
        ("no flow errors", _errors == 0, f"{_errors} errors"),
    ]
    _ok = all(c[1] for c in _checks)
    control = mo.md(
        "| Control | Holds | Evidence |\n| --- | --- | --- |\n"
        + "\n".join(f"| {n} | {'yes' if v else 'NO'} | {e} |" for n, v, e in _checks)
        + (
            "\n\n**The control holds.** One floorplan in, twenty distinct seeds, "
            "twenty distinct placements out. Any spread below is attributable to "
            "the seed."
            if _ok
            else "\n\n**A control failed. The dispersion below is not attributable "
            "to the seed alone.**"
        )
    )
    control
    return (control,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. The dispersion

        Spread is reported as range over mean, which is the quantity the book
        quotes. It is deliberately not a standard deviation: with twenty samples
        the range is what an engineer actually risks hitting.
        """
    )
    return


@app.cell
def _(mo, rows, statistics):
    def _spread(col):
        vals = [float(r[col]) for r in rows]
        mean = statistics.fmean(vals)
        return (max(vals) - min(vals)) / abs(mean) * 100, min(vals), max(vals), mean

    area_pct, area_lo, area_hi, area_mean = _spread("detailedplace_instance_area_um2")
    wns_pct, wns_lo, wns_hi, wns_mean = _spread("detailedplace_setup_wns_ns")
    ratio = wns_pct / area_pct

    mo.md(
        f"""
        | Metric | Min | Max | Mean | Spread (range / mean) |
        | --- | ---: | ---: | ---: | ---: |
        | Instance area (um2) | {area_lo:,.2f} | {area_hi:,.2f} | {area_mean:,.2f} | **{area_pct:.2f}%** |
        | Setup WNS (ns) | {wns_lo:.6f} | {wns_hi:.6f} | {wns_mean:.6f} | **{wns_pct:.2f}%** |

        Timing is **{ratio:.1f}x** more seed-sensitive than area.

        That ratio is the architectural point, and it survives regardless of how
        the spread is summarized. An optimizer scored on area will read this flow
        as nearly deterministic. The same flow scored on slack is not, so a
        single run is not evidence of an improvement.
        """
    )
    return (
        area_hi,
        area_lo,
        area_mean,
        area_pct,
        ratio,
        wns_hi,
        wns_lo,
        wns_mean,
        wns_pct,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. What this pilot does not establish

        - **One design, one platform.** GCD on Nangate45. A larger design with
          real congestion would very likely disperse more, not less.
        - **Twenty seeds is a pilot**, not a distribution. The range is a floor
          on what the flow can do, not a bound.
        - **Placement only.** Routing and full signoff are not in this loop, and
          they are where slack usually moves further.
        - The run is pinned by ORFS commit and container digest, so it is
          repeatable; that is a different claim from being representative.
        """
    )
    return


if __name__ == "__main__":
    app.run()
