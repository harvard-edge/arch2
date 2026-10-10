# Withdrawn Dataset History

The current evidence inventory is [provenance.yml](provenance.yml). This file
records retired material so the removal of unsupported numbers is not confused
with validation of their earlier claims.

On 10 October 2026, the release cleanup removed:

- `ch1_data.csv` through `ch12_data.csv` and `plot_ch1.png` through `plot_ch12.png`.
  Their plotting script had already been disabled because it used unsourced or
  invented values. Some files described illustrative models, but the collection
  had no retained measurement generator or independently checkable row-level
  provenance. No active chapter read these files at removal.
- The disabled `plot_all_wishlist.py` generator.
- `chapter1-github-software-hardware-divide.csv` and
  `chapter1_empirical_data_gap_and_funnel.csv`. These obsolete Chapter 1 datasets
  were not active manuscript inputs; current source-backed figures use separate
  records rather than the former generalized hardware-quality funnel.
- `chapter9-interconnect-logca-specs.csv`, removed with the Chapter 2 numerical
  LogCA figure. It combined nominal specification bandwidths with explicitly
  author-chosen invocation overheads. It was an analytical illustration, not a
  measured table of offload thresholds. The book retains the mathematical
  relationship without presenting these assumed implementation values as data.

Git history retains these files and the prior audit record. Their removal does
not make the earlier magnitudes defensible. Reintroducing a numerical claim
requires a retained execution result or an attributable source supporting that
specific value and scope.

The September 2026 withdrawal of earlier website studies and their narrower
replacements is described in [the study inventory](../studies/README.md).
