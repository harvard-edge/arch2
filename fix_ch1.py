import re

with open("book/contents/chapters/01-moonshot/01-moonshot.qmd", "r") as f:
    text = f.read()

text = re.sub(
    r"::: {\.column-margin}\s*\*\*Author's Note\.\*\* Richard Hamming.*?:::\n\n",
    "",
    text,
    flags=re.DOTALL,
)

target2 = r"The epochs sort architecture practice by when it happened. What follows sorts it by how much of a single workflow an automated method is allowed to touch, so a point-task assistant and a closed-loop design system both operate inside the Architecture 2.0 row rather than succeeding one another. Where learned methods participate in that work matters more than which model performs it. AI names a field and a set of techniques, not a component. When the argument needs to say which part did the work, it names the component that acted: a large language model (LLM), a regression surrogate, a search heuristic, or a formal checker."
text = text.replace(target2, "")

target3 = r"Throughout this book, the object of study is the complete human-plus-technical workflow rather than the fluency of an isolated generated response."
replacement3 = r"Throughout this book, the object of study is the end-to-end design and signoff pipeline rather than the syntactic fluency of an isolated code generator."
text = text.replace(target3, replacement3)

target4 = r"Patent offices have already been forced to rule on a version of this and ruled narrowly, that an inventor must be a person, which leaves an engineer signing for a structure a search found and they had never inspected. Photography settled the same problem in 1884, and the answer was that the work lives in the choices made before the machine acts, in the framing, the timing, and the decision that this one counts."
text = text.replace(target4, "")

with open("book/contents/chapters/01-moonshot/01-moonshot.qmd", "w") as f:
    f.write(text)
