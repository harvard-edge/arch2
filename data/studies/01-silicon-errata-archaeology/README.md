# Published CPU Errata by Subsystem

**Study ID:** `01-silicon-errata-archaeology`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*, Chapter 11 (`fig-errata-subsystem-shares`)
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Question and answer

> **Question.** Where do the defects that escaped pre-silicon verification and
> were published by the vendor fall, by subsystem?

Every erratum was mined from the current specification update (Intel) or revision
guide (AMD) for 19 CPU families, 1,774 errata in all. A committed rule set assigned
each to a subsystem, and a seeded stratified sample of 231 was audited.

- No audited class holds more than about a fifth of the errata. Memory controllers,
  coherence fabrics, and I/O together hold 19.7% (audit-adjusted, 95% interval
  16.7 to 22.8%). Core execution with caches and TLBs holds a comparable 20.4%
  (16.1 to 25.2%). Debug, performance monitoring, and trace hold 16.5%.
- Errata in which an arithmetic, floating-point, or vector unit computes or
  schedules incorrectly are rare: 4 of 231 audited, about 2.2% of the population
  (0.6 to 4.4%).
- 87% of errata carry no planned fix.

> **Note on the earlier version.** A study with this ID previously reported that
> 31.3% of 1,771 errata sat in the "Memory Hierarchy". That figure was an artifact:
> the classifier returned "Memory Hierarchy" whenever no keyword matched, matched
> substrings ("alu" inside "value"), truncated the four AMD families to hand-typed
> totals, and carried 80 placeholder titles and several wrong document numbers.
> It was deleted on 29 September 2026. Nothing from it is reused here: the
> documents were downloaded again, the scraper, rules, and audit are new, and two
> of the 19 documents were replaced because the old ones were for different
> products (Broadwell-EP is 333811, not the Xeon E7 v4 update 334163; Zen 4 Genoa
> is 57095, not the Bergamo/Siena guide 57926; Zen 5 Turin is 58251, not the
> Turin Dense guide 58730).

---

## 2. Sources

One row per document in [`sources.csv`](./sources.csv), with URL, document number,
revision, and date as printed on the document's title page, page count, SHA-256,
and retrieval date. The PDFs are not committed; `mine_cpu_errata.py` downloads them
into the git-ignored `.cache/pdf/`, and `--verify-hashes` refuses to continue if a
vendor has since revised one.

Extraction counts against each document's own summary table. "Summary table" counts
every id the table lists; "Removed" are ids the document marks as removed, moved,
replaced, or duplicated, in both the summary table and the detailed section.

| Family | Document | Revision | Date | Summary table | Removed | Extracted |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: |
| Broadwell-EP | Intel 333811 | 008US | April 2022 | 109 | 3 | 106 |
| Skylake-SP | Intel 336065 | 017US | October 2020 | 116 | 0 | 116 |
| Cascade Lake | Intel 338848 | 028US | October 2023 | 75 | 0 | 75 |
| Ice Lake-SP | Intel 637780 | 026US | March 2026 | 177 | 4 | 173 |
| Sapphire Rapids | Intel 772415 | 022US | August 2026 | 165 | 0 | 165 |
| Emerald Rapids | Intel 793902 | 023US | July 2026 | 160 | 2 | 158 |
| Coffee Lake | Intel 337346 | 008 | November 2025 | 157 | 5 | 152 |
| Ice Lake (client) | Intel 341079 | 023 | April 2026 | 92 | 3 | 89 |
| Tiger Lake | Intel 631123 | 034 | April 2026 | 75 | 2 | 73 |
| Rocket Lake | Intel 634808 | 012 | April 2023 | 36 | 1 | 35 |
| Alder Lake | Intel 682436 | 040 | September 2026 | 94 | 3 | 91 |
| Raptor Lake | Intel 740518 | 031 | September 2026 | 80 | 0 | 80 |
| Meteor Lake | Intel 792254 | 024 | September 2026 | 83 | 1 | 82 |
| Lunar Lake | Intel 827538 | 022 | September 2026 | 72 | 4 | 68 |
| Arrow Lake | Intel 834774 | 023 | September 2026 | 76 | 3 | 73 |
| Zen 1 (Naples) | AMD 55449 | 1.21 | August 2023 | 76 | 0 | 76 |
| Zen 2 (Rome) | AMD 56323 | 1.03 | February 2026 | 49 | 0 | 49 |
| Zen 4 (Genoa) | AMD 57095 | 1.05 | November 2025 | 66 | 0 | 66 |
| Zen 5 (Turin) | AMD 58251 | 1.30 | July 2025 | 47 | 0 | 47 |
| **Total** | | | | 1805 | 31 | 1774 |

---

## 3. Pipeline

| Step | Script | Output |
| :--- | :--- | :--- |
| Fetch, extract, check | [`data/scrapers/mine_cpu_errata.py`](../../scrapers/mine_cpu_errata.py) | `sources.csv`, `errata.csv`, `.cache/errata_text.jsonl` |
| Classify | [`classify_errata.py`](./classify_errata.py) with [`classification_rules.yml`](./classification_rules.yml) | `errata_classified.csv` |
| Draw audit sample | [`audit_sample.py`](./audit_sample.py) | `audit_sample.csv` (labels added by the auditor) |
| Audit metrics | [`audit_metrics.py`](./audit_metrics.py) with [`reporting_classes.yml`](./reporting_classes.yml) | `audit_metrics.json` |
| Figure | [`plot_errata_subsystems.py`](./plot_errata_subsystems.py) | `book/contents/chapters/11-ownership/images/fig-errata-subsystem-shares.{svg,pdf,png}` |

**Completeness checks, each fatal.** For every document the scraper compares the
ids in the detailed errata section with the ids in the document's summary table
(Intel "Summary Tables of Changes", AMD "Cross-Reference of Processor Revision to
Errata"). It fails on any id in one and not the other, on a removal marker present
in only one place, on an unexplained gap in Intel's sequential numbering, on a
missing or truncated title, on a missing fix status, and on a detailed title that
does not contain the title fragment the summary table prints on that id's row
(1,665 of 1,774 titles carry such a fragment; the rest have none on that row).
Intel headings are found by font weight with PyMuPDF because the reading order of
client-part tables is not reliable in plain text.

**Classification.** Whole-word or phrase matching only, patterns stored as data,
classes tried in a fixed order, title first and the problem statement only when the
title matches nothing, and an explicit Unclassified bucket with no default class.
The semantics are written at the top of `classification_rules.yml`. The rules were
frozen before the audit sample was drawn.

**Audit.** 18 errata per rule class (all 15 Unclassified), seed 20260929. The
worksheet the auditor read listed each sampled erratum's title, problem statement,
and implication in shuffled order without its rule label. The auditor labeled each
by reading that text, using the class descriptions in `classification_rules.yml`,
and flagged errata whose defect is in an arithmetic, floating-point, or vector unit.
Conventions applied consistently: an erratum about the logic that observes or
reports behavior (a counter, a machine-check bank) goes to that logic; a wrong or
missing #GP on an MSR access goes to instruction execution; string and locked
operations go to caches and load-store ordering. Each row carries a one-line note,
and ambiguous rows say which other class they could be.

**The labels are a model-assisted reading, not human review.** The auditor was the
same model that wrote the rules. The worksheet hid the rule label, but that does not
make the reading independent, and no second labeler measured inter-rater agreement.

**Metrics.** Per-class precision with Wilson 95% intervals; population agreement and
audit-adjusted shares estimated from the stratified sample with a stratified
bootstrap (10,000 replicates, seed 20260929). Estimated agreement: 76.3% over the
twelve rule classes (70.3 to 82.1%), 81.2% over the reporting classes (75.3 to 86.7%).

**Merge or drop, decided after the audit.** A class is reported only if its
precision is at least 0.70 and its Wilson lower bound at least 0.50. Classes that
failed were merged with the class they were most often confused with when the merge
passed, or dropped. Dropped classes are shown only inside the "not resolved" bar.

| Rule class | Errata | Audited | Agree | Precision | Wilson 95% | Outcome |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| Debug, performance monitoring, and trace | 339 | 18 | 15 | 0.83 | 0.61 to 0.94 | reported |
| Machine check and error reporting | 247 | 18 | 10 | 0.56 | 0.34 to 0.75 | dropped |
| I/O and peripheral interfaces | 228 | 18 | 16 | 0.89 | 0.67 to 0.97 | reported |
| Instruction execution and exceptions | 177 | 18 | 15 | 0.83 | 0.61 to 0.94 | reported |
| Virtualization and IOMMU | 170 | 18 | 17 | 0.94 | 0.74 to 0.99 | reported |
| Power, clocking, and thermal management | 117 | 18 | 17 | 0.94 | 0.74 to 0.99 | reported |
| Caches, TLBs, and load-store ordering | 104 | 18 | 6 | 0.33 | 0.16 to 0.56 | merged |
| Interrupts, timers, reset, and system management | 96 | 18 | 15 | 0.83 | 0.61 to 0.94 | reported |
| Graphics, display, and on-die accelerators | 89 | 18 | 12 | 0.67 | 0.44 to 0.84 | dropped |
| Security and isolation features | 73 | 18 | 13 | 0.72 | 0.49 to 0.88 | merged |
| Memory controller and DRAM | 72 | 18 | 15 | 0.83 | 0.61 to 0.94 | reported |
| Coherence and on-die or socket fabric | 47 | 18 | 10 | 0.56 | 0.34 to 0.75 | merged |
| Unclassified | 15 | 15 | 0 | 0.00 | 0.00 to 0.20 | no rule matched |

### Reported shares

| Reporting class | Rule share | Audit-adjusted | 95% interval | Distinct titles only |
| :--- | ---: | ---: | :--- | ---: |
| Memory controller, coherence fabric, and I/O | 19.6% | 19.7% | 16.7 to 22.8% | 23.0% |
| Debug, performance monitoring, and trace | 19.1% | 16.5% | 12.8 to 19.7% | 15.0% |
| Virtualization, isolation, and security features | 13.7% | 13.7% | 11.9 to 15.8% | 11.6% |
| Core execution, caches, and TLBs | 15.8% | 20.4% | 16.1 to 25.2% | 14.7% |
| Power, clocking, and thermal management | 6.6% | 9.0% | 7.1 to 11.2% | 8.7% |
| Interrupts, timers, reset, and system management | 5.4% | 6.1% | 4.1 to 8.4% | 5.1% |
| Not resolved to a reported class | 19.8% | 14.6% | 10.6 to 18.7% | 22.0% |

"Distinct titles only" counts each normalized title once, since a defect in shared
logic recurs in every family that inherits it (1,036 distinct titles).

---

## 4. Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r data/studies/01-silicon-errata-archaeology/requirements.txt
.venv/bin/python data/scrapers/mine_cpu_errata.py --verify-hashes
cd data/studies/01-silicon-errata-archaeology
../../../.venv/bin/python classify_errata.py
../../../.venv/bin/python audit_sample.py      # verifies the committed sample; never overwrites labels
../../../.venv/bin/python audit_metrics.py
../../../.venv/bin/python plot_errata_subsystems.py
```

Verified 2026-09-29: a second, cold download matched all 19 SHA-256 hashes and
reproduced `errata.csv` byte for byte, and `audit_sample.py` re-drew the committed
sample exactly. If a vendor revises a document, `--verify-hashes` stops; rerunning
without it records the new revision, and the audit must then be re-drawn and
re-labeled because class sizes change.

## 5. Limits

- A published erratum is what a vendor chose to document, not a census of escapes.
- Descriptions are not committed, so re-reading the audit needs the vendor PDFs.
- 18 errata per class gives wide per-class intervals.
- Family set: 15 Intel families (Broadwell-EP to Arrow Lake) and 4 AMD server
  families (Zen 1, 2, 4, 5); Zen 3 and all AMD client parts are not included,
  matching the earlier study's family list.

## 6. Citation

```bibtex
@book{reddi2026architecture2,
  author    = {Vijay Janapa Reddi},
  title     = {Architecture 2.0: Principles of AI-Native System and Chip Design},
  year      = {2026},
  url       = {https://arch2.mlsysbook.ai}
}
```
