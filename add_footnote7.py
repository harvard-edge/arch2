import re

with open("book/contents/chapters/07-feedback/07-feedback.qmd", "r") as f:
    text = f.read()

target = r"The insufficiency of structural coverage is exposed when highly covered testbenches allow severe mutant escape rates (@fig-testbench-vacuity)."
replacement = r"The insufficiency of structural coverage is exposed when highly covered testbenches allow severe mutant escape rates (@fig-testbench-vacuity).[^fn-red-teaming-c07]"

text = text.replace(target, replacement)

footnote = r"""
[^fn-red-teaming-c07]: **The ML safety parallel:** In machine learning, relying on an optimizer to verify its own behavior led to the discovery of *reward hacking* and *proxy gaming*, where agents ruthlessly exploit flaws in their evaluation environments to achieve high scores without actually solving the intended task [@AmodeiEtAl2016Concrete]. The ML community responded by formalizing rigorous "red-teaming" and adversarial testing pipelines, treating the evaluation environment as an adversary rather than a cooperative partner. In AI-driven hardware, treating verification merely as a cooperative testbench-generation task guarantees vacuous test suites; the verification harness must be explicitly adversarial to break the self-verification paradox.
"""

text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/07-feedback/07-feedback.qmd", "w") as f:
    f.write(text)
