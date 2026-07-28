# Figure source receipts

Each `chapterN-*.csv` here is the data behind a printed or explicitly deferred
quantitative figure. Executable `{python}` figure cells read these receipts
(see each cell's `# Receipt:` comment and provenance block); the files exist so
each retained quantitative figure is transcribed, inspectable, and reproducible
rather than hand-drawn.

## Raw Sources and Regeneration

The 2026 quantitative-grounding figures derive their receipts from raw upstream
datasets kept in [`sources/`](sources/):

| Figure (chapter) | Receipt | Raw source in `sources/` |
| --- | --- | --- |
| `fig-accelerator-landscape` (ch1) | `chapter1-accelerator-landscape.csv` | `reuther-laics-2025.csv` |
| `fig-swebench-progress` (ch1) | `chapter1-swebench-verified.csv` | `epoch-benchmarks.csv` |
| `fig-training-compute-growth` (ch2) | `chapter2-training-compute.csv` | `epoch-notable-models.csv` |
| `fig-simulator-tax` (ch5) | `chapter5-simulator-tax.csv` | synthesized (see `regenerate.py`) |
| `fig-hardware-efficiency` (ch10) | `chapter10-hardware-efficiency.csv` | `epoch-ml-hardware.csv` |
| `fig-task-horizon` (deferred from ch11) | `chapter11-task-horizon.csv` | `metr-time-horizon.yaml` |

To refresh a figure with newer data: re-fetch its raw source into `sources/`
(URLs in `regenerate.py`), run `python3 data/source-receipts/regenerate.py` to
rewrite the receipts, then rebuild the book. `regenerate.py` reproduces the
current receipts byte-for-byte.
