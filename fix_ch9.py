import re

with open("book/contents/chapters/09-patterns/09-patterns.qmd", "r") as f:
    text = f.read()

target1 = r"An AI agent executing this transfer test autonomously often fails at this juncture by defaulting to the source comparator. Selecting the 32 by 32 array, the agent violates the 3\ W TDP constraint because the carried rule ignores memory traffic. The transfer test structure triggers a self-correction: the integration check flags the unmeasured memory cost, forcing the agent to retire the source rule, synthesize a new comparator that captures the memory interface overhead, and rescore the candidates before finalizing the evaluation."
replacement1 = r"An automated transfer harness that defaults to the source comparator will erroneously carry the 32 by 32 array, violating the 3\ W TDP constraint because the carried scoring rule omits memory traffic. A sound transfer harness must require the integration check to flag unmodeled interface costs, forcing the evaluation flow to retire the source rule and evaluate candidates against a memory-aware target comparator."
text = text.replace(target1, replacement1)

target2 = r"Technical reuse also depends on operational readiness: tool access, operating knowledge, review capacity, and organizational authority to challenge anomalous behavior"
replacement2 = r"Technical reuse also depends on operational readiness: tool access, operating knowledge, engineer veto rights, and instrumentation to challenge anomalous tool returns"
text = text.replace(target2, replacement2)

target3 = r"Confirm tool access, operator challenge capacity, and recorded decision authority."
replacement3 = r"Confirm tool access, engineer veto rights and instrumentation to challenge anomalous tool returns, and recorded decision authority."
text = text.replace(target3, replacement3)

target4 = r"Architectural claims must carry the compiler cost required to unlock them."
replacement4 = r"Architectural claims must carry the compiler cost required to unlock them.[^fn-compiler-dialect-decoupling-c09]"

footnote = r"""
[^fn-compiler-dialect-decoupling-c09]: **Compiler dialect decoupling (IR parallel)**: Software engineering resolved the classic $M \times N$ programming-language-to-hardware portability crisis by decoupling target-independent transformations from machine lowering through layered intermediate representations such as LLVM and MLIR [@LattnerEtAl2020MLIR]. In AI-native accelerator exploration, structuring compiler backends into dialect pipelines allows hardware design loops to parameterize tensor tiling and spatial vectorization passes without rebuilding the entire software toolchain for each candidate geometry.
"""
text = text.replace(target4, replacement4)
if "[^fn-compiler-dialect-decoupling-c09]" in text and footnote.strip() not in text:
    text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/09-patterns/09-patterns.qmd", "w") as f:
    f.write(text)
