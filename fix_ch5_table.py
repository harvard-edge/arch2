import re

with open("book/contents/chapters/05-methods/05-methods.qmd", "r") as f:
    text = f.read()

target1 = r"\| \*\*Critique\*\* \| Testable defect, missing assumption, or conflict tied to named artifact\. \| Route to revision owner; critique neither alters candidates nor replaces checks\. \|"
replacement1 = r"| **Static Analysis** | Testable defect, missing assumption, or conflict tied to named artifact. | Route to revision owner; analysis neither alters candidates nor replaces checks. |"
text = text.replace(target1, replacement1)

target2 = r"\| \*\*Explanation\*\* \| Proposed mechanism and distinguishing contrast conditions\. \| Compare against alternative baseline; explanation does not substitute for verification\. \|"
replacement2 = r"| **Diagnostic Localization** | Proposed mechanism and distinguishing contrast conditions. | Compare against alternative baseline; analysis does not substitute for verification. |"
text = text.replace(target2, replacement2)

with open("book/contents/chapters/05-methods/05-methods.qmd", "w") as f:
    f.write(text)
