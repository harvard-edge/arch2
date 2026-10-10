# Architecture 2.0 Data and Provenance

This directory holds source datasets, measurement harnesses, simulator outputs,
and reproduction scripts used by the book and its [public data page](../www/data.qmd).
The [study inventory](studies/README.md) identifies the retained studies and their
limits; chapter datasets have a separate [provenance guide](datasets/README.md).

## Layout

| Location | Contents |
| --- | --- |
| `datasets/` | Chapter datasets, upstream source snapshots, plotting scripts, and `provenance.yml` |
| `studies/01-silicon-errata-archaeology/` | Rebuilt extraction and classification of published CPU errata |
| `studies/02-ast-complexity-cliff/` | Source-syntax measurements from pinned RTL repositories |
| `studies/06-eda-seed-dispersion/` | Twenty executed OpenROAD placement runs and raw stage metrics |
| `studies/08-testbench-vacuity-and-judge-bias/` | Executed VerilogEval mutation pilot; the folder name is historical |
| `studies/09-representation-dilation/` | Declaration-to-use distances in token order and syntax trees |
| `studies/ai_systolic_array_study/` | Recorded model proposal and SCALE-Sim comparison on a synthetic workload |
| `scrapers/` | Source miners and measurement harnesses |
| `notebooks/` | Notebooks that recompute selected study summaries |
| `processed/` | Processed corpora and intermediate tables |

Studies support both the manuscript and the website. Some chapters read study
files directly; others use derived chapter datasets or generated figures.

## What the evidence means

- **Measured:** outputs of an executed parser, simulator, or other tool under
  recorded inputs and configuration. Simulation results are measurements of that
  model, not silicon measurements or proof of performance on an application.
- **Mined or transcribed:** values extracted from primary documents or copied
  from an attributed source. Source fidelity and any subsequent classification
  must be checked separately.
- **Analytical:** results calculated from explicit equations and assumptions.
  They support the stated model, not an empirical claim about an unmeasured system.
- **Conceptual:** diagrams or examples that explain a relationship. They are not
  observations and cannot establish a measured magnitude.

Generated artifacts and analytical calculations exist in the repository. The
integrity requirement is to distinguish them from empirical evidence and to trace
empirical claims to actual sources or retained execution outputs. Equations and
conceptual diagrams do not supply missing empirical data. A source URL, tool name,
or `verified` label alone does not establish that a value is correct.

## Reproduction and verification

Use each study's linked instructions in the [inventory](studies/README.md) for
pinned sources, dependencies, commands, and claim boundaries. Recomputing an
aggregate, checking a source hash, replaying a simulation, and independently
replicating a study are different levels of verification.

```bash
python3 data/validate_provenance.py
python3 data/validate_figure_provenance.py
```

These validators check selected metadata patterns, explicit figure declarations,
source paths, and recorded CSV row counts. They do not establish source accuracy,
complete source coverage, execution history, or whether a cited study supports a
claim. A declared input path does not prove that the plotting code reads it.

The October 2026 integrity audit recomputed the retained Studies 02, 06, and 08
headlines, checked Study 06's 40 raw metric-file hashes, and reconstructed Study
08's 338 mutant hashes from pinned source. It did not rerun those tools. Retention
limits and earlier rerun coverage remain documented with the studies.

## Withdrawn material

Earlier fabricated or unsupported datasets were withdrawn; the retained errata,
AST, placement, and mutation studies must not inherit their predecessors' claims.
The release cleanup removes the twelve obsolete `ch1_data.csv` through
`ch12_data.csv` files and their `plot_chN.png` outputs, plus
`chapter1-github-software-hardware-divide.csv` and
`chapter1_empirical_data_gap_and_funnel.csv`. The [study history](studies/README.md#withdrawn-predecessors)
distinguishes replacements from studies that remain withdrawn.
