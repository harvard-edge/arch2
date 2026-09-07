import re

with open("book/contents/chapters/03-lifecycle/03-lifecycle.qmd", "r") as f:
    text = f.read()

target = r"To establish clear architectural accountability, the AI-native design system introduces the Design-Loop Card [@MitchellEtAl2019ModelCards; @GebruEtAl2021Datasheets]."
replacement = r"To establish clear architectural accountability, the AI-native design system introduces the Design-Loop Card [@MitchellEtAl2019ModelCards; @GebruEtAl2021Datasheets].[^fn-mlops-cards-c03]"

text = text.replace(target, replacement)

footnote = r"""
[^fn-mlops-cards-c03]: **The ML Parallel:** Hardware architects might naturally be skeptical of introducing new bureaucratic artifacts like "cards." However, the machine learning community faced this exact "chicken-and-egg" problem: early ML systems were deployed ad-hoc with uninspectable shadow state, leading to catastrophic production failures. The introduction of Model Cards [@MitchellEtAl2019ModelCards] and rigorous MLOps deployment pipelines transformed ML from an informal craft into an engineering discipline. The Design-Loop Card proposes this same necessary maturity leap for AI-driven silicon.
"""

# add footnote before ## Common Pitfalls
text = text.replace("## Common Pitfalls", footnote + "\n## Common Pitfalls")

with open("book/contents/chapters/03-lifecycle/03-lifecycle.qmd", "w") as f:
    f.write(text)
