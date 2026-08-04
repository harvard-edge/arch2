# Originality and Self-Overlap Record

This delivery record distinguishes passage reuse from cited intellectual continuity. It is a
screening aid, not a legal opinion or a substitute for the Publisher's similarity and permissions
review.

- Last verified: 2026-07-15 against the revised worktree; exact release commit pending
- Manuscript units audited: 14 (Preface, Chapters 1–11, and Appendices A–B)
- Exact passage reuse detected from the comparison sources below: none at the stated thresholds
- Cited prior-author-work disclosures: 6 grouped disclosures
- Current third-party epigraphs: 10 across Chapters 1–7 and 9–11
- Epigraphs with source-level text and metadata verified in this record: 8; verification remains
  open for Chapters 10 and 11

## Screening Method and Results

The manuscript prose was normalized by removing markup, code blocks, citations, URLs, and
punctuation before exact token-sequence comparison. This method can find copied passages, but it
does not detect paraphrase, translation, conceptual inheritance, or a redrawn figure.

| Comparison source | Scope | Threshold | Result |
| --- | --- | --- | --- |
| *Machine Learning Systems* | 80 current Volume 1, Volume 2, and shared-front-matter `.qmd` files in the author's local source tree | 12 consecutive normalized words | No match of 13 or more words. One generic 12-word sequence, “data that can be adapted to a wide range of downstream tasks,” appears in Chapter 1 and the MLSysBook glossary. It is not a distinctive passage. |
| “Architecture 2.0: Why Computer Architects Need a Data-Centric AI Gymnasium” | Public SIGARCH post fetched 2026-07-14 | 10 consecutive normalized words | No exact match. Chapter 5 cites and paraphrases the post. |
| “Architecture 2.0 Workshop: How Machine Learning Will Redefine Computer Architecture and Systems” | Public SIGARCH post fetched 2026-07-14 | 10 consecutive normalized words | No exact match. Chapter 5 cites and summarizes the workshop agenda. |
| “Architecture 2.0: Foundations of Artificial Intelligence Agents for Modern Computer System Design” | Final nine-page IEEE *Computer* PDF, document 10857820, DOI `10.1109/MC.2024.3521641`, SHA-256 `eefa6ce0340f0a1178ba25856e3bf3bc867f5f5a7034c5b4ed1a50b41900852b` | 10 consecutive normalized words, checked with PDF hyphens both separated and joined | No exact match of 10 or more words in the 14 manuscript units. The longest match in either normalization was five generic words. The book cites and develops the article's concepts in new prose. |
| MLSysBook media | 10,511 current image, vector, and PDF assets compared by SHA-256 with 150 current book assets | Byte identity | No identical cross-repository asset. This does not rule out independently redrawn figures that use the same cited facts. |

The 2025 foundations comparison used the final IEEE PDF retained in the author's local archive.
OpenAlex and Semantic Scholar both classify the public article as closed access, so the delivery
record identifies the checked file by document number, DOI, page count, and hash without
redistributing it. The exact-sequence screen does not detect paraphrase or conceptual inheritance;
the disclosure below therefore remains necessary even though no passage-level reuse was found.

## Disclosures of Prior Author Work

These rows identify the prior work and the book's use of it. “Cited development” means the book
extends or applies the earlier idea in new prose; it does not claim that the earlier work is a
third-party source.

| Book location | Prior author work | Relationship | Editorial disposition |
| --- | --- | --- | --- |
| Preface and Chapter 1 | Reddi and Yazdanbakhsh, “Architecture 2.0: Foundations of Artificial Intelligence Agents for Modern Computer System Design” (2025) | The Preface cites the article as the source of the broad Architecture 2.0 vision and distinguishes the book's formulation from the article. Chapter 1 cites it when distinguishing established, human-directed architecture practice from broader participation by learned methods. The book's bounded-study, claim-review, evidence, and decision-rights framework is a substantial further development. | Disclose as the book's cited conceptual predecessor. The final-PDF screen found no exact sequence of 10 or more normalized words in the manuscript. |
| Chapter 5 | Reddi and Yazdanbakhsh, “Architecture 2.0: Why Computer Architects Need a Data-Centric AI Gymnasium” (2023) | Chapter 5 cites and restates the need for data-centric, shared architecture environments. | Disclose as a cited conceptual predecessor. No exact sequence of 10 or more normalized words was found. |
| Chapter 5 | Architecture 2.0 SIGARCH workshop outcome report (2023), coauthored by Reddi | Chapter 5 condenses the report's six-part community agenda into the environment and infrastructure argument. | Disclose as a cited summary. No exact sequence of 10 or more normalized words was found. |
| Chapters 1–2 and 10 | MLPerf papers coauthored by Reddi | The book uses MLPerf as precedent for benchmark governance, fixed scenarios, provenance, and comparable reporting. Chapter 2 also paraphrases published participation and scale statistics. | Keep the citations and disclose the recurring precedent. No passage-level reuse from MLSysBook was found. |
| Chapters 1, 2, 4–6, and 8 | ArchGym, QuArch, and related papers from the author's research collaborations | The book summarizes the published systems and uses them as worked precedents for environments, architecture question answering, and bounded evaluation. | Treat as cited descriptions of coauthored or author-affiliated research. Confirm the final author lists in the bibliography rather than leaving “and others” where delivery metadata requires complete credits. |
| Chapters 1-2, 5, 7, and 9 | MLSysBook themes and examples | Benchmarking discipline, multidimensional efficiency, data movement, reward gaming, reliability incidents, and system-level evidence also appear in the author's ML-systems teaching. | Disclose thematic continuity. The screen found no passage reuse of 13 or more normalized words and no byte-identical media. |

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
| 10 | “Measurements are key.” — H. James Harrington, *Business Process Improvement* (1991) | 3 | The manuscript cites p. 82 of the 1991 McGraw-Hill book. Exact-text verification and Publisher quotation disposition remain open. |
| 11 | “Everyone designs who devises courses of action aimed at changing existing situations into preferred ones.” — Herbert A. Simon, *The Sciences of the Artificial* (1969) | 15 | The manuscript cites p. 55 of the 1969 MIT Press book. Exact-text verification and Publisher quotation disposition remain open. |

## Delivery Actions

1. Obtain and record the Publisher's quotation disposition for every retained external epigraph.
2. Rerun the recorded foundations comparison against the exact release commit and record that
   identity in this report.
3. Give this disclosure, the permissions ledger, and any written permissions to the series editor
   with the manuscript.
