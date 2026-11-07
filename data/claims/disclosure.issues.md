# Disclosure issues

- CLM-D-015: "remain open" conflicts with LICENSE.md and README.md, which reserve all rights and say visibility grants no reuse.
- CLM-D-009: no inter-agent bus was found outside the figure and its caption.
- CLM-D-010: the caption says the author decides what reaches the harness, with no exception. The body concedes unreviewed passes.
- CLM-D-008: pre-commit is no-render. Compilation happens in CI, so "compiles" does not describe the commit step.
- CLM-D-011, CLM-D-012: no retained draft. The sentence read "thirty pages ... in under two minutes" until a1b630b3d removed the numbers, with no receipt for either wording.
- CLM-D-013: "some" passes may understate unreviewed volume, at 22.2 commits per day and 302 on 2026-09-11.
- CLM-D-007, CLM-D-018: no tracked per-citation record. Commit messages are the only tracked trace.
- CLM-D-001, CLM-D-004: author facts no tracked file can test. LInc returned 403.
- CLM-D-006, CLM-D-013: the rewording is uncommitted, and history cannot apportion drafting between author and agents.

## Ledger decisions, 2026-11-06 (claim-ledger agent, front and back matter)

- CLM-D-006: restamped with changed evidence. fig-microprocessor-trends.yml was re-audited on 2026-11-06 (inputs relocated, new auditor), which changed its hash. Neither figure audit can carry a claim about the whole authoring process, so evidence is now data/validate_evidence_audit.py (requires an auditor separate from the producer), .pre-commit-config.yaml (evidence-audit hook), and the two audit records. This supports "audit results" by a separate auditor and that producer sessions made figure data. No tracked file shows agents drafting text; that rests on commit history and the author. history_test count updated from 18 records (16 PASS, 2 FAIL) to 32 (32 PASS); the earlier FAIL records are not in the working tree.
- CLM-D-008: restamped. .pre-commit-config.yaml changed in bb4efb87 by adding the provenance, evidence-audit and run-log hooks, plus evidence-byte excludes. It still does not compile; publish-site.yml still renders HTML, PDF and EPUB and verifies release identity. The sentence reads correctly for the pipeline (CI compiles), not for the commit step.
- CLM-D-013: restamped and CODEOWNERS added. The config shows tracked rules gating commits. .github/CODEOWNERS names the author as owner of /book/, which supports commit authority over the manuscript. Neither shows that some passes run unreviewed.
- Left for the author (no evidence, nothing honest to attach, none moved to not_claims): D-001 (sabbatical, a biographical fact only the author can attest), D-003, D-004, D-005, D-007, D-009, D-010, D-011, D-012, D-015 (contradicted by LICENSE.md), D-018.

## Resolutions, 2026-11-07 (front and back matter claims pass)

- CLM-D-001, outcome 3: sabbatical and ETH time are the author's own circumstances. Moved to not_claims.
- CLM-D-003, outcome 3: daily work with generative AI is the author's own working circumstance. Moved to not_claims; the commit-rate proxy was dropped with the claim.
- CLM-D-004, outcome 3: first-person account of how the author built their own workflow. Moved to not_claims. Judgment call: the workflow is private and untracked, LInc returned 403, so no honest evidence can be attached.
- CLM-D-005, outcome 3 after softening: "generative models excel at" became "I have found generative models adept at", the author's own experience. Moved to not_claims.
- CLM-D-007, outcome 3: "I structured the authoring workflow around ... review roles" is the author's account of their own process. Moved to not_claims, quoting the first-person clause. Judgment call, same as D-004; commit messages corroborate that such passes ran, not their coverage.
- CLM-D-009, outcome 2: caption reworded so the bus is the diagram's system-on-chip analogy for the orchestration that routes drafts between roles, not a literal component. The new sentence describes the book's own figure and moved to not_claims. Image unchanged; caption is 520 characters.
- CLM-D-010, outcome 2: "decides, in order, what reaches" became "holds commit authority over what reaches", matching the body (some passes run unreviewed) and CLM-D-013. Evidence .github/CODEOWNERS.
- CLM-D-011, CLM-D-012, outcome 3: the author's recollection of a discarded early draft and their own rebuild. Moved to not_claims.
- CLM-D-015, outcome 2: "remain open" became "are freely readable online". No license or open-access status is asserted (Bucket A). Evidence publish-site.yml (GitHub Pages deploy to arch2.mlsysbook.ai) and README.md (public site links); LICENSE.md stays as contrary evidence on reuse.
- CLM-D-018, outcome 3 after softening: "flags" became "is tasked with flagging", the author's stated design intent for the role. Moved to not_claims. No per-finding record is tracked.
