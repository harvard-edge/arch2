import re

with open("book/contents/chapters/06-environments/06-environments.qmd", "r") as f:
    text = f.read()

target1 = r"an engineer launching tools by hand needs none of it, a closed-loop optimizer driving one tool inside a fixed container needs a wrapper and a small harness, and an AI-native design system coordinating compilers, simulators, formal checkers, and signoff flows across the stack needs every role below\."
replacement1 = r"While manual tool execution requires little enclosing infrastructure, coordinating multi-tool evaluation across compilers, simulators, and signoff engines requires separating containment, translation, coordination, and logging into distinct roles."
text = text.replace(target1, replacement1)

# Delete DevOps callouts
text = re.sub(
    r"::: {\.callout-design-principle title=\"Automate Within Recoverable Boundaries\"}.*?:::\n\n",
    "",
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r"::: {\.callout-design-principle title=\"Unrecorded Runs Cannot Justify Claims\"}.*?:::\n\n",
    "",
    text,
    flags=re.DOTALL,
)

target3 = r"The strictness of these records is directly tied to the scientific validity of the results\. ACM artifact review guidelines distinguish \*repeatability\* \(same team, same setup\), \*reproducibility\* \(different team, same setup\), and \*replicability\* \(different team, different setup\) \[\@ACM2020ArtifactReview\]\. Exact replay relies on submitting identical retained requests and recorded states\."
replacement3 = r"The strictness of these records is directly tied to isolating EDA simulator non-determinism. Exact replay relies on submitting identical retained requests and recorded states, capturing thread counts, random seeds, and host operating conditions to isolate environment noise from true physical divergence."
text = text.replace(target3, replacement3)

with open("book/contents/chapters/06-environments/06-environments.qmd", "w") as f:
    f.write(text)
