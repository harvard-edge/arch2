# Originality and Self-Overlap Record

This delivery record distinguishes passage reuse from cited intellectual continuity. It is a
screening aid, not a legal opinion or a substitute for the Publisher's similarity and permissions
review.

- Last verified: 2026-08-04 against manuscript content commit
  `3d6882f9252493717944ca9172b86db350262d72`
- July 15 screening scope: 14 units (the then-current Preface, Chapters 1–10, and Appendices
  A–C recorded in the manifest at `f5516e52`)
- Current manuscript structure: 14 units (Preface, Chapters 1–11, and Appendices A–B)
- Current exact-passage result: no reuse detected from the comparison sources below at the
  stated thresholds; this rerun includes Chapter 11 and the current Appendix B
- Cited prior-author-work disclosures: 6 grouped disclosures
- Current third-party epigraphs: 10 across Chapters 1–7 and 9–11
- Epigraphs with source-level text and metadata fully verified in this record: 9. Chapter 11's
  exact text is verified in the MIT Press third edition, and multiple page-specific records support
  the first-edition page, but direct primary-image verification of the cited 1969 page remains open.

## Screening Method and Results

The manuscript prose was normalized by removing markup, code blocks, citations, URLs, and
punctuation before exact token-sequence comparison. The rerun used the 14 current manuscript
units listed above. It compared exact normalized word windows at each stated threshold and
extended every matching window to its full exact length. This method can find copied passages,
but it does not detect paraphrase, translation, conceptual inheritance, or a redrawn figure.

### Current release rerun: 2026-08-04

| Comparison source | Scope | Threshold | Result |
| --- | --- | --- | --- |
| *Machine Learning Systems* | 82 current Volume 1, Volume 2, and shared front- and back-matter `.qmd` files at local source commit `4557489e5855a874f45832c0b2124977dfea3f98` | 12 consecutive normalized words | No match of 13 or more words. One 12-word sequence, “is at least as good on every objective and strictly better on,” appears in Chapter 1 and an MLSysBook part opener. It is a standard statement of Pareto dominance, not a distinctive passage. |
| “Architecture 2.0: Why Computer Architects Need a Data-Centric AI Gymnasium” | Public SIGARCH post fetched 2026-08-04 | 10 consecutive normalized words | No exact match. Chapter 5 cites and paraphrases the post. |
| “Architecture 2.0 Workshop: How Machine Learning Will Redefine Computer Architecture and Systems” | Public SIGARCH post fetched 2026-08-04 | 10 consecutive normalized words | No exact match. Chapter 5 cites and summarizes the workshop agenda. |
| “Architecture 2.0: Foundations of Artificial Intelligence Agents for Modern Computer System Design” | Final nine-page IEEE *Computer* PDF, document 10857820, DOI `10.1109/MC.2024.3521641`, SHA-256 `eefa6ce0340f0a1178ba25856e3bf3bc867f5f5a7034c5b4ed1a50b41900852b` | 10 consecutive normalized words, checked with PDF hyphens both separated and joined | No exact match of 10 or more words in either normalization. The book cites and develops the article's concepts in new prose. |
| MLSysBook media | 3,079 source-controlled image, vector, and PDF assets compared by SHA-256 with 139 source-controlled book assets | Byte identity | No identical cross-repository asset. This does not rule out independently redrawn figures that use the same cited facts. |

The media counts in this rerun use `git ls-files` so generated build artifacts and untracked files
cannot change the comparison scope. The 2025 foundations comparison used the final IEEE PDF
retained in the author's local archive. OpenAlex and Semantic Scholar both classify the public
article as closed access, so the delivery record identifies the checked file by document number,
DOI, page count, and hash without redistributing it.

### Historical screening: 2026-07-15

The following table preserves the earlier result and its then-current source scopes. Those results
apply only to the July 15 manuscript snapshot; the current release result is recorded above.

| Comparison source | Scope | Threshold | Result |
| --- | --- | --- | --- |
| *Machine Learning Systems* | 80 current Volume 1, Volume 2, and shared-front-matter `.qmd` files in the author's local source tree | 12 consecutive normalized words | No match of 13 or more words. One generic 12-word sequence, “data that can be adapted to a wide range of downstream tasks,” appears in Chapter 1 and the MLSysBook glossary. It is not a distinctive passage. |
| “Architecture 2.0: Why Computer Architects Need a Data-Centric AI Gymnasium” | Public SIGARCH post fetched 2026-07-14 | 10 consecutive normalized words | No exact match. Chapter 5 cites and paraphrases the post. |
| “Architecture 2.0 Workshop: How Machine Learning Will Redefine Computer Architecture and Systems” | Public SIGARCH post fetched 2026-07-14 | 10 consecutive normalized words | No exact match. Chapter 5 cites and summarizes the workshop agenda. |
| “Architecture 2.0: Foundations of Artificial Intelligence Agents for Modern Computer System Design” | Final nine-page IEEE *Computer* PDF, document 10857820, DOI `10.1109/MC.2024.3521641`, SHA-256 `eefa6ce0340f0a1178ba25856e3bf3bc867f5f5a7034c5b4ed1a50b41900852b` | 10 consecutive normalized words, checked with PDF hyphens both separated and joined | No exact match of 10 or more words in the July 15 snapshot's 14 manuscript units. The longest match in either normalization was five generic words. The book cites and develops the article's concepts in new prose. |
| MLSysBook media | 10,511 current image, vector, and PDF assets compared by SHA-256 with 150 current book assets | Byte identity | No identical cross-repository asset. This does not rule out independently redrawn figures that use the same cited facts. |

The exact-sequence screen does not detect paraphrase or conceptual inheritance. The disclosures
below therefore remain necessary even though both recorded screens found no passage-level reuse
at their stated thresholds.

## Disclosures of Prior Author Work

These rows identify the prior work and the book's use of it. “Cited development” means the book
extends or applies the earlier idea in new prose; it does not claim that the earlier work is a
third-party source.

| Book location | Prior author work | Relationship | Editorial disposition |
| --- | --- | --- | --- |
| Preface and Chapter 1 | Reddi and Yazdanbakhsh, “Architecture 2.0: Foundations of Artificial Intelligence Agents for Modern Computer System Design” (2025) | The Preface cites the article as the source of the broad Architecture 2.0 vision and distinguishes the book's formulation from the article. Chapter 1 cites it when distinguishing established, human-directed architecture practice from broader participation by learned methods. The book's bounded-study, claim-review, evidence, and decision-rights framework is a substantial further development. | Disclose as the book's cited conceptual predecessor. The July 15 final-PDF screen found no exact sequence of 10 or more normalized words in that manuscript snapshot. |
| Chapter 5 | Reddi and Yazdanbakhsh, “Architecture 2.0: Why Computer Architects Need a Data-Centric AI Gymnasium” (2023) | Chapter 5 cites and restates the need for data-centric, shared architecture environments. | Disclose as a cited conceptual predecessor. The July 15 screen found no exact sequence of 10 or more normalized words. |
| Chapter 5 | Architecture 2.0 SIGARCH workshop outcome report (2023), coauthored by Reddi | Chapter 5 condenses the report's six-part community agenda into the environment and infrastructure argument. | Disclose as a cited summary. The July 15 screen found no exact sequence of 10 or more normalized words. |
| Chapters 1–2 and 10 | MLPerf papers coauthored by Reddi | The book uses MLPerf as precedent for benchmark governance, fixed scenarios, provenance, and comparable reporting. Chapter 2 also paraphrases published participation and scale statistics. | Keep the citations and disclose the recurring precedent. The July 15 screen found no passage-level reuse from MLSysBook. |
| Chapters 1, 2, 4–6, and 8 | ArchGym, QuArch, and related papers from the author's research collaborations | The book summarizes the published systems and uses them as worked precedents for environments, architecture question answering, and bounded evaluation. | Treat as cited descriptions of coauthored or author-affiliated research. Confirm the final author lists in the bibliography rather than leaving “and others” where delivery metadata requires complete credits. |
| Chapters 1-2, 5, 7, and 9 | MLSysBook themes and examples | Benchmarking discipline, multidimensional efficiency, data movement, reward gaming, reliability incidents, and system-level evidence also appear in the author's ML-systems teaching. | Disclose thematic continuity. The July 15 screen found no passage reuse of 13 or more normalized words and no byte-identical media. |

## Direct Third-Party Quotations

Ten of the eleven numbered chapters currently open with an epigraph. Chapter 8
alone uses an author-written opening. The retained epigraphs are the only
third-party passages found by the direct-quotation inventory. The lighthouse prompt,
captions, definition blocks, listings, and callout prose are author-written. Goodhart's
law is currently paraphrased and cited rather than quoted.

| Chapter | Quotation and stated source | Words | Delivery status |
| --- | --- | ---: | --- |
| 1 | “The purpose of computing is insight, not numbers.” — Richard Hamming, *Numerical Methods for Scientists and Engineers* (1962) | 8 | Exact text verified in the McGraw-Hill first edition, p. v. Publisher quotation disposition remains open. |
| 2 | “Feedback is the control of a system … the simple feedback of the control engineers.” — Norbert Wiener, *The Human Use of Human Beings* (1950) | 44 | Exact text and corrected source verified in the Houghton Mifflin first edition, p. 71. This is the longest epigraph and the highest permissions burden. Obtain Publisher clearance or replace it with author-written prose. |
| 3 | “All models are wrong, but some are useful.” — George E. P. Box, “Robustness in the Strategy of Scientific Model Building” (1979) | 8 | Text verified as the section heading on p. 202 of *Robustness in Statistics*, edited by Robert L. Launer and Graham N. Wilkinson (Academic Press, 1979). Publisher quotation disposition remains open. |
| 4 | “The limits of my language mean the limits of my world.” — Ludwig Wittgenstein, *Tractatus Logico-Philosophicus* (1922) | 11 | Exact text verified as proposition 5.6 in the translation by F. P. Ramsey, edited by C. K. Ogden (Kegan Paul, Trench, Trubner & Co., 1922). Publisher confirmation remains necessary for the applicable publication territories. |
| 5 | “We shape our tools and thereafter they shape us.” — John Culkin, *Saturday Review* (1967) | 9 | Exact text verified in John M. Culkin, “A Schoolman’s Guide to Marshall McLuhan,” *Saturday Review*, March 18, 1967, p. 70. Publisher quotation disposition remains open. |
| 6 | “But they are useless. They can only give you answers.” — Pablo Picasso, *The Paris Review* (1964) | 10 | Exact text and calculating-machine context verified in William Fifield, “Pablo Picasso—A Composite Interview,” *The Paris Review* 32 (Summer–Fall 1964), p. 62. Publisher quotation disposition remains open. |
| 7 | “Program testing can be used to show the presence of bugs, but never to show their absence!” — Edsger W. Dijkstra, *Notes on Structured Programming* (1970) | 17 | Exact text verified in EWD249, “On the reliability of mechanisms,” in *Notes on Structured Programming* (1970), using the University of Texas at Austin E. W. Dijkstra Archive. Publisher quotation disposition remains open. |
| 9 | “There is no single development … one order of magnitude improvement …” — Fred Brooks, “No Silver Bullet” (1986) | 27 | Exact text verified in Frederick P. Brooks Jr., UNC technical report TR86-020 (September 1986), p. 1. The preceding sentence supplies the decade horizon; the epigraph does not silently combine it with later abstract wording. Obtain Publisher clearance or replace it with author-written prose. |
| 10 | “Measurements are key.” — H. James Harrington, *Business Process Improvement* (1991) | 3 | Exact text verified on p. 82 through the digitized 1991 McGraw-Hill edition, ISBN `0-07-026768-5`. Publisher quotation disposition remains open. |
| 11 | “Everyone designs who devises courses of action aimed at changing existing situations into preferred ones.” — Herbert A. Simon, *The Sciences of the Artificial* (1969) | 15 | Exact text verified in the MIT Press third edition (1996), p. 111. MIT Press verifies the 1969 first-edition metadata, and multiple page-specific scholarly records cite the same sentence to the first edition, p. 55, but a directly inspectable primary image of that page was not available for this audit. Primary verification of the first-edition page and Publisher quotation disposition remain open. |

## Delivery Actions

1. Obtain and record the Publisher's quotation disposition for every retained external epigraph.
2. Obtain or inspect a primary copy of the 1969 first edition of Simon's *The Sciences of the
   Artificial* and confirm the Chapter 11 page attribution.
3. Rerun the recorded comparisons if manuscript prose changes after content commit
   `3d6882f9252493717944ca9172b86db350262d72`.
4. Give this disclosure, the permissions ledger, and any written permissions to the series editor
   with the manuscript.
