import re

with open("book/contents/chapters/07-feedback/07-feedback.qmd", "r") as f:
    text = f.read()

target1 = r"Combining machine-usable state representations \(\@sec-data-representations-world-models\), smallest sufficient methods \(\@sec-methods-generation-prediction-optimization\), sandboxed execution environments \(\@sec-architecture-environments-tool-interfaces\), and qualified feedback mechanisms completes the technical foundation of Part II, and Part III puts that foundation to work in executed studies\."
text = text.replace(target1, "")

target2 = r"the \*verification scissors\*"
replacement2 = r"the widening divergence between reachable state-space complexity and dynamic verification coverage"
text = text.replace(target2, replacement2)

target3 = r"Whether verifying an isolated mechanism or an end-to-end outcome, assurance engineering structures architectural verification by linking high-level performance and correctness claims directly to supporting tool checks and explicit assumptions \[\@Kelly2004GSN\]\."
replacement3 = r"Structured verification signoff links high-level performance SLAs and functional contracts directly to tool checks, coverage targets, and explicit operating assumptions."
text = text.replace(target3, replacement3)

target4 = r"frozen product requirements documents \(PRDs\)"
replacement4 = r"frozen architectural specifications (MAS)"
text = text.replace(target4, replacement4)

target5 = r"cryptographically signed PRD waiver"
replacement5 = r"cryptographically sealed SDC timing waiver manifest"
text = text.replace(target5, replacement5)

with open("book/contents/chapters/07-feedback/07-feedback.qmd", "w") as f:
    f.write(text)
