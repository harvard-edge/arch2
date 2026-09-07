import re

with open("book/contents/chapters/05-methods/05-methods.qmd", "r") as f:
    text = f.read()

target = r"```latex\n#\| html-no-end: false.*?\\end{algorithm}\n```\n\nCandidate generation increases arrival rate \$g\$"

replacement = r"Standard token-bucket and leaky-bucket admission control formulas based on downstream queue utilization ($\rho_i = \lambda_i / \mu_i$) readily adapt to generative loops. When $\rho_i$ exceeds a declared threshold $\rho_{\text{limit}}$, the orchestration harness enforces explicit rate limits on agent token generation, transforming LLM prompt filtering from a heuristic chat persona into a quantifiable admission control mechanism.\n\nCandidate generation increases arrival rate $g$"


def repl(m):
    return replacement


text = re.sub(target, repl, text, flags=re.DOTALL)

with open("book/contents/chapters/05-methods/05-methods.qmd", "w") as f:
    f.write(text)
