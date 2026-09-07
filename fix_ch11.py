import re

with open("book/contents/chapters/11-ownership/11-ownership.qmd", "r") as f:
    text = f.read()

target1 = r"Finally, the accountable organization provisions resources for these functions and owns the real-world product consequences. *In order* means that specification changes, constraint waivers, and promotions to the common baseline receive an architect's current recommendation and a recorded authority decision in strict serial order, even when exploration proceeds in parallel. One person may occupy both the architect and commitment-authority functions only when the record identifies which function is being exercised, preserves their distinct rights and responsibilities, and keeps independent checks and organizational accountability explicit. This separation prevents a successful local tool run from silently authorizing a global tapeout."
replacement1 = r"Finally, the accountable organization provisions resources for these functions and owns the real-world product consequences. *In order* means that multi-domain verification signoff (timing, power grid, thermal) must formally precede business authorization of non-recurring reticle mask capital. This separation prevents a successful local tool run from silently authorizing a global tapeout."
text = text.replace(target1, replacement1)

target2 = r"3. **Escalation under unresolved scope:** When specialists cannot reconcile scopes within allocated budgets, the transition remains blocked and the unresolved system contract is escalated to the commitment authority."
replacement2 = r"3. **Unresolved Contract Block:** When formal proofs and cycle-accurate models cannot reconcile interface invariants within verification budgets, candidate promotion remains blocked and the contract discrepancy is flagged for microarchitectural review before signoff."
text = text.replace(target2, replacement2)

target3 = r"Human factors research distinguishes misuse (inappropriate reliance on automation) from disuse (neglecting automation capabilities entirely) [@ParasuramanRiley1997HumansAutomation]. In architectural deployment, misuse accepts a generated accelerator pipeline without verifying its pipeline-stall assumptions, while disuse ignores the generator because its initial proposals were naive. Classic human-automation frameworks separate information acquisition, analysis, decision selection, and action implementation [@ParasuramanEtAl2000LevelsAutomation]. When applied to architecture..."
replacement3 = r"Uncritical acceptance of automated DRC/STA reports causes undetected physical escapes, while total disuse of generative tools forfeits machine-scale design exploration. When applied to architecture..."
text = text.replace(target3, replacement3)

# Add footnote
target4 = r"This operational separation ensures that raw specialist data is synthesized before executive commitment, preventing commitment authorities from approving tapeout decisions by mere implication."
replacement4 = r"This operational separation ensures that raw specialist data is synthesized before executive commitment, preventing commitment authorities from approving tapeout decisions by mere implication.[^fn-kernel-maintainer-c11]"
footnote = r"""
[^fn-kernel-maintainer-c11]: **Linux kernel maintainer hierarchy (governance parallel)**: Software engineering resolved the identical ownership dilemma when scaling the Linux kernel across thousands of untrusted, distributed contributors. Rather than requiring lead architects to hand-audit every line of C code or blindly trusting external patches, the kernel established a hierarchical subsystem maintainer model backed by the Developer Certificate of Origin (DCO, the `Signed-off-by:` convention) and automated invariant fuzzing (syzkaller, KernelCI) [@Corbet2006KernelDevelopment]. In Architecture 2.0, the automated generator acts as an untrusted contributor submitting candidate patches, while the architect functions as the subsystem maintainer who validates formal interface contracts, monitors regression telemetry, and takes legal and operational signoff ownership before merging to trunk.
"""
text = text.replace(target4, replacement4)
if "[^fn-kernel-maintainer-c11]" in text and footnote.strip() not in text:
    text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/11-ownership/11-ownership.qmd", "w") as f:
    f.write(text)
