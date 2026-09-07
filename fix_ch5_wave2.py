import re

with open("book/contents/chapters/05-methods/05-methods.qmd", "r") as f:
    text = f.read()

# Fix 1: Pre-flight
target1 = r"Prospective studies pass through six pre-flight criteria to determine whether direct tool execution or conventional heuristics settle the question within budget\.\n\n1\. State the architecture decision.*?\n6\. Reject proposed methods when data, representations, legal actions, evaluators, support, total costs, fallbacks, or stopping rules are inadequate\.\n\n@fig-method-selection-guide composes those criteria into a conditional flow"
replacement1 = r"To determine whether direct tool execution or conventional heuristics settle the question within budget, @fig-method-selection-guide composes these constraints into a conditional flow"
text = re.sub(target1, replacement1, text, flags=re.DOTALL)

# Fix 2: Rename critique
target2 = r"Critique: Testable defect, missing assumption.*?critique neither alters candidates nor replaces checks\."
replacement2 = r"Static Analysis / Rule Checking: Testable defect, missing assumption... analysis neither alters candidates nor replaces checks."
text = re.sub(target2, replacement2, text, flags=re.DOTALL)

# Fix 3: Rename explanation
target3 = r"Explanation: Proposed mechanism and distinguishing contrast conditions.*?explanation does not substitute for verification\."
replacement3 = r"Diagnostic Localization / Failure Analysis: Proposed mechanism and distinguishing contrast conditions... analysis does not substitute for verification."
text = re.sub(target3, replacement3, text, flags=re.DOTALL)

# Fix 4: Algorithm 5.1
target4 = (
    r"```pseudocode\n#\| label: alg-dynamic-rate-limiting.*?\n\\end{algorithm}\n```"
)
replacement4 = r"Standard token-bucket and leaky-bucket admission control formulas based on downstream queue utilization ($\rho_i = \lambda_i / \mu_i$) readily adapt to generative loops. When $\rho_i$ exceeds a declared threshold $\rho_{\text{limit}}$, the orchestration harness enforces explicit rate limits on agent token generation, transforming LLM prompt filtering from a heuristic chat persona into a quantifiable admission control mechanism."


def repl(m):
    return replacement4


text = re.sub(target4, repl, text, flags=re.DOTALL)

with open("book/contents/chapters/05-methods/05-methods.qmd", "w") as f:
    f.write(text)
