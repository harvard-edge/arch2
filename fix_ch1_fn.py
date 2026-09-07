import re

with open("book/contents/chapters/01-moonshot/01-moonshot.qmd", "r") as f:
    text = f.read()

target = r"The case for building Layer 3 systems rather than stopping at Layer 1 point assistance is not an architectural preference. It follows from where a semiconductor project schedule actually spends its time."
replacement = r"The case for building Layer 3 systems rather than stopping at Layer 1 point assistance is not an architectural preference. It follows from where a semiconductor project schedule actually spends its time.[^fn-agentic-eda-ci-parallel]"
text = text.replace(target, replacement)

footnote = r"""
[^fn-agentic-eda-ci-parallel]: **Agentic execution and the CI/CD precedent**: Hardware architects routinely dismiss autonomous agentic EDA loops as impractical due to the notorious fragility, non-determinism, and license contention of commercial CAD toolchains. This skepticism directly mirrors the software engineering consensus of the late 1990s regarding Continuous Integration and Continuous Deployment (CI/CD). Practitioners then argued that complex distributed software could never be compiled, tested, and deployed automatically without human release engineers intervening to resolve environment drift and flaky tests. Software engineering resolved this dilemma not by eliminating bugs, but by formalizing reproducible, hermetic build environments (such as containerized sandboxes and declarative dependency graphs in Bazel), strict interface contract testing, and automated canary rollback gates. In an AI-native design system, autonomous agent exploration similarly succeeds only when wrapped in hermetic containerized tool harnesses, bounded by deterministic execution budgets, and checked by formal interface assertion monitors (such as SystemVerilog Assertions for AXI protocol compliance) that reject invalid mutations before they consume downstream EDA capacity.
"""

if "[^fn-agentic-eda-ci-parallel]" in text and footnote.strip() not in text:
    text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/01-moonshot/01-moonshot.qmd", "w") as f:
    f.write(text)
