# Editorial placement: persistent workaround support

Status: optional proposal on October 17, 2026; no manuscript change applied.
See the [selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

## Decision and chapter purpose

Add to Chapter 9 only if another empirical exhibit earns the space. This is
the first figure to omit if the revision must remain small. Chapter 9 already
has measured software-performance evidence. The Linux history adds a distinct
point: a software release also carries support for hardware conditions that
persist across later releases. The argument remains understandable without
this figure, which makes it useful rather than necessary.

## Placement and surrounding revision

Use [Version Dependencies and Interface Contracts](../../../book/contents/chapters/09-patterns/09-patterns.qmd#sec-version-dependencies-contracts),
after the paragraph ending “rather than assuming an isolated binary recreates
the earlier system” (currently line 307), before the existing MLPerf H100
discussion. Keep that existing figure; it measures performance changes and
does not duplicate support persistence. This should be the chapter's only new
figure. Chapter 11 may refer back to it without reproducing it.

Suggested lead-in:

> Software versions also preserve support for hardware conditions that remain
> relevant after the original release. Across ten sampled Linux releases, the
> number of named arm64 erratum configuration options rises from 10 in v4.4
> to 52 in v6.12. Every option present in v4.4 remains in each later sample.

Suggested caption:

> **Hardware workaround support persists across sampled Linux releases.**
> Bars count explicitly prompted Boolean arm64 erratum options in ten pinned
> releases from v4.4 through v6.12. The ten options present in v4.4 appear in
> every later sample; the remaining portions count other options. Release
> samples are unevenly spaced. Counts describe configuration support, not
> distinct defects or measured runtime overhead.

Suggested landing:

> An option's applicability must travel with its name. For example,
> `ARM64_ERRATUM_819472` identifies particular Cortex-A53 revisions and cache
> conditions. Its presence in a kernel configuration records support for a
> workaround; the effect on a deployed workload still requires measurement.

Connect the next paragraph with “Version changes can also alter measured
performance on nominally identical accelerators,” then continue the existing
MLPerf evidence. Read the section continuously to avoid a detour from transfer
claims into a general history of operating systems.

## Evidence and citation

The packet retains pinned Kconfig sources and release identities. Use
[release_counts.csv](release_counts.csv), [options.csv](options.csv), and
[pins.json](pins.json). The source population comprises ten selected releases,
not every intermediate release. New symbols can reflect changed processor
coverage or configuration structure. Presence does not show that a workaround
is enabled or exercised on a particular machine.

Add an exact Linux source-history citation using the pinned revisions in this
packet. A citation to Linux's patch-submission instructions does not support
these counts. Do not infer 52 distinct defects, a growth rate of chip defects,
or a performance penalty. No kernels were built for this study.

## Asset and integration checks

Use [figure.svg](figure.svg) with its PDF/PNG twins. The PNG was visually
inspected during this review. From the repository root run
`python3 data/studies/14-linux-errata-workarounds/collect.py` and then
`python3 data/studies/14-linux-errata-workarounds/reproduce.py`; preserve
the source snapshots and build receipt.

Proposed chapter asset and label: `images/fig-ch09-workaround-support` and
`fig-ch09-workaround-support`. Alt text should describe the retained ten options
and the total of 52 in the last sample. If the figure is omitted, preserve the
packet for tutorials rather than automatically substituting another paragraph.
