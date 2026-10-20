# Editorial placement: representation access

Status: proposed on October 17, 2026; no manuscript change applied. See the
[selection proposal](../../../integration/manage-work-tree/PLOT_INTEGRATION_PROPOSAL.md).

## Decision and chapter purpose

Replace Chapter 4's existing source-distance figure with this analysis. Do not
add a second figure. Chapter 4 teaches how representation and dataset
construction determine what a method can observe. The pair-level data make
the observation unit and its weighting visible, strengthening both parts of
that argument. This measures source access, not learned representation quality.

## Placement and surrounding revision

Use [Machine-Usable Hardware Representations](../../../book/contents/chapters/04-representations/04-representations.qmd#sec-hardware-representation-formats),
under “Structure Beyond Token Sequences.” Replace the exhibit currently labeled
`fig-ch04-spatial-semantic-dilation` and revise the paragraphs immediately
before and after it (currently lines 548–558). The next topic begins
“Representation structure can also affect tool turnaround.” Preserve that
progression from source access to compiler work and abstraction choice.

The existing plot and prose discuss file-level source-distance trends. The new
figure shows coverage distributions and weighting sensitivity, so a caption
swap is insufficient. Move the old slope discussion to its original companion
study if still useful. Remove unused `dil_*` inline calculations only after
checking every reference. Search the book before retiring the old figure label.

Correct the current explanation of unbound references in the same passage.
The extraction does not establish why those references were unbound. Its visitor
also includes bound references from conditional-generate branches that are
inactive for the selected parameter value. Those are separate observations.
Neither justifies describing the analysis as active, elaborated circuitry.

Suggested lead-in:

> A source interval covers very different fractions of RTL relationships
> depending on how the corpus is weighted. Across 40,825 declaration/use pairs
> with both measurements available, a 256-token interval covers 21.9 percent
> when each pair receives equal weight. Coverage rises to 84.9 percent when
> each source file receives equal weight and its pairs share that weight.

Suggested caption:

> **Source-access coverage depends strongly on the observation unit.**
> The panels show minimum contiguous source-interval coverage by repository,
> pooled coverage under pair and equal-file weighting, and concrete-syntax-tree
> path coverage for the same 40,825 matched pairs. Source intervals use tokens;
> tree paths use edges. One BaseJump file contributes 40.3 percent of the pairs,
> making the pooled result sensitive to corpus composition.

Suggested landing:

> Pair weighting describes the relationships in this corpus; equal-file
> weighting describes an average across its selected files. The large
> difference requires the architect to state which population a representation
> is intended to serve. Syntax-tree paths provide another way to locate the
> same references, but edge counts and token counts do not measure the same
> cost. Neither curve establishes that a model will make better design
> decisions from that representation.

## Evidence and citation

Use [derived/pairs.csv](derived/pairs.csv),
[derived/budget_coverage.csv](derived/budget_coverage.csv),
[derived/summary.json](derived/summary.json), and
[source_manifest.json](source_manifest.json). The packet retains the parser
version and exact matching. Of 40,995 token-measured pairs, 170 lack a tree
measurement and are excluded from the matched comparison. The inherited
344-file selection has no retained selection rationale. The cause of 1,170
unbound references is unknown. Scope and exclusions belong in the companion
method description, with a short qualification in the chapter.

The [generate-scope diagnostic](diagnostics/bsg_scatter_gather_generate_scope.json)
records `vec_size_lp=4` and bound pairs in all 11 conditional branches. Do not
convert a short syntax path into an assertion about semantic dependence,
model attention, retrieval accuracy, or reasoning performance.

Retain the relevant upstream repository and parser citations already present
in Chapter 4, and cite the six pinned source revisions from the manifest.
Attribute the initial corpus and file-level analysis to Study 09; attribute
the retained pair data, matched comparison, and weighting analysis to this
study and [provenance.yml](provenance.yml). Do not invent a published dataset
identifier before an archive exists.

## Asset and integration checks

Use [figures/fig-representation-source-access.svg](figures/fig-representation-source-access.svg)
and its PDF/PNG twins. The PNG was visually inspected during this review.
Reproduction requires the pinned packages in [requirements.txt](requirements.txt).
Follow the virtual-environment command in [README.md](README.md), then run
`data/studies/23-representation-access/reproduce.py` with that environment's
Python. The build receipt and image-bound visual review remain in the packet.

Proposed chapter asset and label: `images/fig-ch04-source-access` and
`fig-ch04-source-access`. Alt text should explain the matched population and
the 21.9 versus 84.9 percent comparison. Preserve the old evidence packet,
update all cross-references, remove unsupported adjoining claims, and render
the complete section before accepting the replacement.
