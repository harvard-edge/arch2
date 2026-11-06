# Published CPU Errata by Subsystem

**Study ID:** `01-silicon-errata-archaeology`
**Reference:** *Architecture 2.0: Principles of AI-Native System and Chip Design*, Chapter 11 (`fig-errata-subsystem-shares`)
**Website:** [https://arch2.mlsysbook.ai](https://arch2.mlsysbook.ai)

---

## 1. Question and answer

> **Question.** Where do the defects that escaped pre-silicon verification and
> were published by the vendor fall, by subsystem?

Every erratum was mined from the current specification update (Intel) or revision
guide (AMD) for 19 CPU families, 1,774 errata extracted. Six of them have no retained or retrievable primary text and are excluded from every count (section 5), which leaves 1,768. A committed rule set assigned
each to a subsystem, and one model relabeled a seeded stratified sample of 231. The classifier
is rule-based and model-assisted, with no human label audit. No person reviewed the labels;
where this file and its scripts say "audit", they mean that model relabeling.

- No largest share and no ranking is reported as a finding about silicon errata. The ranking
  depends on how a rule-based classifier orders its classes. Over 2,000 random class orders
  of the title matches (description matches held as assigned), the largest class by rule runs 16.3 to 41.2% (median 28.0) in the applied grouping, and which
  class it is changes, and 23.9 to 50.6% (median 36.9) under the written merge rule, where the
  same class stays largest (section 3). Those spans describe the classifier. Only the recorded
  order has a relabeled sample. Earlier versions of this README said no audited class holds
  more than about a fifth, then about 30% under the written rule, then about 19 to 35% with at
  least six classes and none near half of the corpus. All three failed audit and are withdrawn.
- In every reading, memory controllers, coherence fabrics, and caches together hold a
  minority: 12.6% by rule and 8.0% adjusted (6.0 to 10.5%). That sum does not depend on how
  classes are merged. Any one-label change keeps the adjusted sum between 7.2 and 9.1%. The
  rule sum does depend on class order: 6.8 to 24.6% over 2,000 random orders (section 3).
- Errata in which an arithmetic, floating-point, or vector unit computes or
  schedules incorrectly are rare: 4 of 231 audited, about 2.2% of the population
  (0.6 to 4.4%).
- 1,541 of 1,768 errata (87%) carry no planned fix. When dispositions differ
  across steppings, the extraction retains the least resolved disposition. This
  counts documented entries, not affected shipped processors. Workaround subgroup
  counts have been withdrawn because their field extraction was not reliable
  (see the validation limits below).
- In the applied grouping, the class that joins I/O, memory controllers, and coherence is
  mostly I/O: 228 of its 347 rule-assigned errata (66%) are I/O and peripheral. The figure
  labels it "I/O, memory controller, coherence" for that reason.
- 1,530 of 1,768 errata (87%) come from Intel documents. In the 238 AMD errata alone,
  the same class holds 24.8% by rule.
- The shares have no denominator: no document reports how much logic or specified
  behavior each subsystem contains, so they are not normalized by subsystem size.

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
| Merge rule comparison | [`merge_rule_sensitivity.py`](./merge_rule_sensitivity.py), scoring through `audit_metrics.compute` | `merge_rule_sensitivity.json` |
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
The semantics are written at the top of `classification_rules.yml`. Class order changes the
rule shares: 783 of the 1,659 errata matched on their titles match more than one class (see
"Class order" below). The rules are
recorded as frozen before the audit sample was drawn, but the rules and the labeled
sample first appear together in commit 75cc61153, so the repository cannot show the order.

**Audit.** 18 errata per rule class (all 15 Unclassified), seed 20260929. As
`audit_sample.py` is written, the worksheet lists each sampled erratum's title, problem
statement, and implication in shuffled order without its rule label. The worksheet was
written to the git-ignored `.cache/` and was not retained. No copy was found in any
checkout, in git history, or in surviving local session history (searched 2026-11-02;
Claude transcripts from that date have aged out and Codex holds no session for
2026-09-29), so what the auditor actually saw cannot be shown. The auditor labeled each
by reading that text, using the class descriptions in `classification_rules.yml`,
and flagged errata whose defect is in an arithmetic, floating-point, or vector unit.
Conventions the labels mostly follow: an erratum about the logic that observes or
reports behavior (a counter, a machine-check bank) goes to that logic; a wrong or
missing #GP on an MSR access goes to instruction execution; string and locked
operations go to caches and load-store ordering. The last was not applied consistently:
ICL066 (REP MOVSB) went to instruction execution, SKX76 (lock prefix) to I/O, and ICX40
(poisoned locked transaction) to interrupts. Each row carries a one-line note,
and ambiguous rows say which other class they could be.

**The labels are a model-assisted reading, not human review.** The auditor was the
same model that wrote the rules. The code that builds the worksheet omits the rule label,
but that would not make the reading independent, and no second labeler measured inter-rater agreement.
This is a co-generation limitation: the rules and the labels share one reader's
assumptions. A blind relabel of the 231 sampled errata by an independent human, with
Cohen's kappa against the model labels, would measure agreement beyond chance and give
the adjusted shares an independent reference. It has not been done.

**Metrics.** Per-class precision with Wilson 95% intervals; population agreement and
audit-adjusted shares estimated from the stratified sample with a stratified
bootstrap (10,000 replicates, seed 20260929). Estimated agreement: 76.3% over the
twelve rule classes (70.3 to 82.0%), 81.2% over the reporting classes (75.3 to 86.7%).

**Merge or drop, decided after the audit: the written rule and what was done disagree.**
The rule: a class is reported only if its precision is at least 0.70 and its Wilson lower
bound at least 0.50. Classes that fail are merged with the class they are most often
confused with when the merge passes, or dropped. Dropped classes are shown only inside the
"not resolved" bar. The rule does not say what to do when two classes tie. Earlier versions
of `reporting_classes.yml` stated that the rule was fixed before any merge, but rule and
outcomes first appear together in commit 75cc61153, so the record cannot show that.

The applied grouping departs from the rule for three of the five failed classes. Nobody
has amended the rule to fit or changed the grouping to follow it. The figure draws the
applied grouping, and which to keep is an author decision. Everything below is computed by
`merge_rule_sensitivity.py`, and every grouping goes through the same `audit_metrics.compute`
path. All of it is modeled, since it rests on one model's labels.

| Failed class | Alone | Most confused with (relabeled rows) | Merge test | Written rule | Applied |
| :--- | ---: | :--- | :--- | :--- | :--- |
| Caches, TLBs, and load-store ordering | 6/18 | Instruction execution and exceptions (11) | 32/36, low 0.75, passes | merge | merged with Instruction execution and exceptions |
| Coherence and on-die or socket fabric | 10/18 | Power, clocking, and thermal management (4) | 31/36, low 0.71, passes | merge | merged with I/O and peripheral interfaces; Memory controller and DRAM |
| Graphics, display, and on-die accelerators | 12/18 | I/O and peripheral interfaces (3) | 32/36, low 0.75, passes | merge | drop |
| Machine check and error reporting | 10/18 | Instruction execution and exceptions (3) | 30/36, low 0.68, passes | merge | drop |
| Security and isolation features | 13/18 | Virtualization and IOMMU (4) | 34/36, low 0.82, passes | merge | merged with Virtualization and IOMMU |

Two more points. Memory controller (15/18) and I/O (16/18) each passed alone, so the rule
gives no ground for reporting them together; that follows from the coherence choice. The
applied classes do pass the test as merged, so the departure is in which merge was chosen,
not in class quality.

Every merge that passes the test, whichever class the audit confused it with:

| Failed class | Merges that pass the test |
| :--- | :--- |
| Caches, TLBs, and load-store ordering | Instruction execution and exceptions (32/36, low 0.75) |
| Coherence and on-die or socket fabric | Power, clocking, and thermal management (31/36, low 0.71); I/O and peripheral interfaces (27/36, low 0.59); Virtualization and IOMMU (27/36, low 0.59) |
| Graphics, display, and on-die accelerators | I/O and peripheral interfaces (32/36, low 0.75); Power, clocking, and thermal management (31/36, low 0.71); Virtualization and IOMMU (29/36, low 0.65); Instruction execution and exceptions (28/36, low 0.62); Interrupts, timers, reset, and system management (28/36, low 0.62); Debug, performance monitoring, and trace (27/36, low 0.59); Memory controller and DRAM (27/36, low 0.59) |
| Machine check and error reporting | Instruction execution and exceptions (30/36, low 0.68); Interrupts, timers, reset, and system management (28/36, low 0.62); I/O and peripheral interfaces (27/36, low 0.59); Memory controller and DRAM (27/36, low 0.59); Power, clocking, and thermal management (27/36, low 0.59); Virtualization and IOMMU (27/36, low 0.59) |
| Security and isolation features | Virtualization and IOMMU (34/36, low 0.82); Power, clocking, and thermal management (30/36, low 0.68); I/O and peripheral interfaces (29/36, low 0.65); Debug, performance monitoring, and trace (28/36, low 0.62); Instruction execution and exceptions (28/36, low 0.62); Interrupts, timers, reset, and system management (28/36, low 0.62); Memory controller and DRAM (28/36, low 0.62) |

"Most often confused" is not defined further in the rule. The primary reading counts a
class's own audited rows relabeled to another class. Over all 120 orders of the failed classes,
recomputing confusion against the groups formed so far gives one outcome, the same grouping.
Counting both directions makes coherence tie between power and machine check; the tie toward
machine check fails the test, so coherence would be dropped. Those readings leave the largest
class where it was, but they do not cover every reading. The machine-check count below is one
that moves it.

Shares as applied:

| Reporting class | Rule share | Audit-adjusted | 95% interval | Distinct titles only |
| :--- | ---: | ---: | :--- | ---: |
| Memory controller, coherence fabric, and I/O | 19.6% | 19.8% | 16.7 to 22.8% | 23.0% |
| Debug, performance monitoring, and trace | 18.8% | 16.3% | 12.6 to 19.4% | 14.8% |
| Core execution, caches, and TLBs | 15.9% | 20.4% | 16.1 to 25.2% | 14.7% |
| Virtualization, isolation, and security features | 13.7% | 13.8% | 12.0 to 15.8% | 11.6% |
| Power, clocking, and thermal management | 6.6% | 9.0% | 7.2 to 11.2% | 8.7% |
| Interrupts, timers, reset, and system management | 5.4% | 6.1% | 4.1 to 8.4% | 5.1% |
| Not resolved to a reported class | 19.9% | 14.7% | 10.6 to 18.8% | 22.1% |

Shares under the written rule:

| Reporting class | Rule share | Audit-adjusted | 95% interval | Distinct titles only |
| :--- | ---: | ---: | :--- | ---: |
| Machine check and error reporting + Instruction execution and exceptions + Caches, TLBs, and load-store ordering | 29.9% | 30.7% | 25.9 to 35.5% | 30.0% |
| Debug, performance monitoring, and trace | 18.8% | 16.3% | 12.6 to 19.4% | 14.8% |
| I/O and peripheral interfaces + Graphics, display, and on-die accelerators | 17.9% | 18.4% | 15.9 to 20.8% | 19.5% |
| Virtualization and IOMMU + Security and isolation features | 13.7% | 13.8% | 12.0 to 15.8% | 11.6% |
| Power, clocking, and thermal management + Coherence and on-die or socket fabric | 9.3% | 11.4% | 9.1 to 14.2% | 12.6% |
| Interrupts, timers, reset, and system management | 5.4% | 6.1% | 4.1 to 8.4% | 5.1% |
| Memory controller and DRAM | 4.1% | 3.4% | 2.7 to 4.1% | 5.1% |
| Not resolved to a reported class | 0.8% | 0.0% | 0.0 to 0.0% | 1.3% |

Machine check alone moves the largest share to 29.9%:

| One departure repaired, others as applied | Largest rule share | Largest adjusted share |
| :--- | ---: | ---: |
| Coherence and on-die or socket fabric merged with Power, clocking, and thermal management | 18.8% | 20.4% |
| Graphics, display, and on-die accelerators merged with I/O and peripheral interfaces | 24.7% | 24.1% |
| Machine check and error reporting merged with Instruction execution and exceptions | 29.9% | 30.7% |

**The machine-check target rests on a small count, so no largest share is reported.** Of
the 8 machine-check rows relabeled, 3 went to instruction execution and 2 to interrupts, and
one each to security, coherence, and I/O. Two of the 3 are one title in two families (RPL061
and ARL006, "PCONFIG Error Reporting May be Incorrect"). Counting each title once, as the
distinct-title shares do, gives a 2 to 2 tie, and the rule does not say which to take. This
study adds no tiebreak. `merge_rule_sensitivity.py` computes every tied branch and now stops
if a reading meets a tie with no branch named. The row notes cut both ways: RPL015 (labeled
security) says it could be execution, which would widen the count to 4 to 2, and RPL061 says
it could be read as a memory-encryption feature, which would leave 2 rows each for instruction
execution, interrupts, and security. All of the
following are modeled, and intervals exclude the choice of merge target.

| Reading | Largest rule share | Largest adjusted share |
| :--- | ---: | ---: |
| Applied grouping | 19.6% | 20.4% |
| Written rule | 29.9% | 30.7% |
| Each title once, machine check to instruction execution | 29.9% | 30.7% |
| Each title once, machine check to interrupts | 19.4% | 20.4% |
| The 3 rows relabeled to interrupts, rule rederived | 19.4% | 18.7% |
| One departure repaired, as in the table above | 18.8 to 29.9% | 20.4 to 30.7% |
| Every one-label change, rule rederived, ties branched (2,376 changes) | 18.8 to 34.9% | 19.7 to 35.4% |

Under the written rule, 49 of the 2,376 one-label changes can move the largest rule share.
Three do so outright (RPL061, BDF16, or ARL006 relabeled to interrupts, which gives 19.4%).
The other 46 create a tie with a branch that keeps 29.9%. One-label changes give point
estimates only. Across all of these readings the largest class runs from 18.8 to 34.9% by
rule and 18.7 to 35.4% adjusted. The class that comes out largest varies among debug,
the applied I/O class, core execution, and machine check joined to each of several classes.
The highest upper interval among the named readings is 35.5%.

Those values all use the recorded class order, so they are not a range for the largest share
(see Class order, below). The memory-system sum stays a minority across them.

**Class order.** The rule bars depend on the fixed order in which classes are tried. 783 of
the 1,659 errata matched on their titles match more than one class. Over 2,000 random orders
of the twelve rule classes (seed 20260929), with body-matched and Unclassified rows held as
assigned and no merging, the largest rule class holds 13.4 to 32.7% of the corpus and the
memory-system sum 6.8 to 24.6%, against 12.6% in the committed order. The merged readings
above all use the committed order. Adjusted shares use the labels, so order reaches them
only through the strata, and no other order has a relabeled sample.

Merges and class order vary together in the third audit's reading, kept in
`class_order.largest_merged_class`. Over the same orders and seed, the largest merged class by
rule runs 16.3 to 41.2% (median 28.0) in the applied grouping, where three classes take the
top place, and 23.9 to 50.6% (median 36.9) under the written rule, where one class holds it in
all 2,000 orders. These are extremes of a random sample of orders, not bounds.

Per-class audit results, with the outcome as applied:

| Rule class | Errata | Audited | Agree | Precision | Wilson 95% | Outcome as applied |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| Debug, performance monitoring, and trace | 333 | 18 | 15 | 0.83 | 0.61 to 0.94 | reported |
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

"Distinct titles only" counts each normalized title once, since a defect in shared
logic recurs in every family that inherits it (1,034 distinct titles).

---

## 4. Reproduce

The full path no longer runs. Five Intel documents were revised in October 2026, the pinned
PDFs are not retained, and the vendor no longer serves them. `--verify-hashes` stops at Alder
Lake, by design (run `20261102T144156Z`, exit 1, in `runs.jsonl`). The classify step needs the
text cache that the scraper writes, so it cannot run either.
That failed run is the only extraction in `runs.jsonl`, so `errata.csv` has no logged
successful run. Its earlier extraction appears only in the dated records below.

From the committed CSVs, without the PDFs:

```bash
python3 -m venv .venv
.venv/bin/pip install -r data/studies/01-silicon-errata-archaeology/requirements.txt
cd data/studies/01-silicon-errata-archaeology
../../../.venv/bin/python audit_sample.py      # verifies the committed sample; never overwrites labels
../../../.venv/bin/python audit_metrics.py
../../../.venv/bin/python merge_rule_sensitivity.py
../../../.venv/bin/python plot_errata_subsystems.py
```

Run these through `data/run_study.py` so that each attempt is logged. On 2026-11-02 they
reproduced `audit_metrics.json` byte for byte. On 2026-11-06 they were rerun after the
six exclusions in section 5, which changed every output. `merge_rule_sensitivity.py` takes about 90 s,
since it scores every one-label change. Rerunning the scraper without `--verify-hashes`
would record the new revisions; the audit must then be re-drawn and re-labeled because class
sizes change.

Earlier records, kept as dated: on 2026-09-29 a second, cold download matched all 19 SHA-256
hashes and reproduced `errata.csv` byte for byte, and `audit_sample.py` re-drew the committed
sample exactly.

## 5. Limits

### Withdrawn workaround subgroup counts (10 October 2026)

A release audit cold-downloaded all 19 vendor PDFs, matched all committed SHA-256
hashes, and reproduced the 1,774 title/ID/disposition records and the calculated
metrics. Those checks establish source identity and reproducibility, not the
correctness of every extracted body field.

The previously committed `workaround_status.csv` has been removed from the
published data. At least eight entries classified as no workaround plus guidance
contained no guidance: the parser had retained page furniture, another title,
a duplicate phrase, or punctuation. Two more workaround fields were omitted when
an entry continued on another page. These ten records were checked against the
rendered source pages; they are a confirmed minimum, not an estimate of all errors.

| Erratum | Source document | Printed page | Confirmed issue |
| :--- | :--- | ---: | :--- |
| BDF46 | [Intel 333811](https://cdrdv2.intel.com/v1/dl/getContent/333811) | 23 | Product footer mistaken for guidance |
| SKX47 | [Intel 336065](https://cdrdv2.intel.com/v1/dl/getContent/336065) | 33 | Page furniture mistaken for guidance |
| SKX98 | Intel 336065 | 45 | Page furniture mistaken for guidance |
| SPR31 | [Intel 772415](https://cdrdv2.intel.com/v1/dl/getContent/772415) | 28 | Extra punctuation mistaken for guidance |
| EMR30 | [Intel 793902](https://cdrdv2.intel.com/v1/dl/getContent/793902) | 27 | Page furniture mistaken for guidance |
| EMR48 | Intel 793902 | 32 | Page furniture mistaken for guidance |
| ADL066 | [Intel 682436](https://cdrdv2.intel.com/v1/dl/getContent/682436) | 36 | Another title mistaken for guidance |
| LNL008 | [Intel 827538](https://cdrdv2.intel.com/v1/dl/getContent/827538) | 14 | Duplicated phrase mistaken for guidance |
| ICL008 | [Intel 341079](https://cdrdv2.intel.com/v1/dl/getContent/341079) | 18 | Workaround in continuation omitted |
| LNL004 | Intel 827538 | 14 | No-workaround statement in continuation omitted |

No corrected global workaround split is reported. Recovering one requires repairing
entry boundaries, page reading order, and continuation merging; separating actual
mitigation instructions from non-actionable trailing context; and checking the
recovered fields against the sources before recomputation. Description and
implication fields used in classification fallback and the audit also need a
field-level check because they share the extractor. The subsystem estimates remain
conditional on the disclosed model-assisted labels, not an independently validated
reference classification.

`workaround_status.py` now produces only an unvalidated diagnostic worksheet in
`.cache/workaround_candidates.csv`. Its text-pattern labels do not establish that
a workaround or guidance exists. It is excluded from the publication pipeline.

### Six rows with no reachable source (2 November 2026)

Six rows in `errata.csv` have no reachable source. They are listed in
[`withdrawn_rows.csv`](./withdrawn_rows.csv): ADL090, ADL091, LNL068, LNL069, ARL072, and
ARL073, two Intel PT titles repeated across three families, all in the debug class, none in
the audit sample. The pinned revisions listed them. The October 2026 revisions (Alder Lake
041, Lunar Lake 023, Arrow Lake 024) say the erratum has been removed and give no reason.
The pinned PDFs are not retained, and the Wayback Machine index returned no capture of those
three documents for August to November 2026 (other URL forms were not tried). Their titles and
status cannot be rechecked. Since 2026-11-06 they are excluded from every count (next section). The other 388 rows of the five revised
documents matched on the later revisions in the 2026-11-02 audit. Six other errata added in
those revisions are not in this corpus.

### Six rows excluded from every count (6 November 2026)

The 2026-11-02 audit (finding F2) asked that rows without retained or retrievable primary text
leave the counts. Before deciding, each family was checked in
`~/Documents/Arch2-Private-Sources/errata-pdfs-pinned/` (no Alder, Lunar, or Arrow Lake copy),
`errata-pdfs-revised-upstream-2026-11-02/`, and `.cache/pdf/`. Every held copy is the later
revision, which prints only "removed" for these entries, and none matches the pinned hash. The
decision and reason for each row are in [`excluded_rows.csv`](./excluded_rows.csv). The rows stay
in `errata.csv` and `errata_classified.csv` as evidence. `audit_metrics.load_population()` drops
them, and every script and the chapter count through it, so the population is 1,768 rather than
1,774. None of the six is in the audit sample, so no label was added, removed, or changed. The
sample was drawn from 1,774 rows; within each stratum it is still a simple random draw from the
rows that remain, and the stratum weights now use the 1,768-row population. The 2026-11-06 runs
are in `runs.jsonl`.

### No independent human labels

The study has no independent human labels. Every adjusted share, every precision, and every
merge test rests on one model's reading. See "The labels are a model-assisted reading" above.

### Other limits

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
