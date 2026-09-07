import re

with open("book/contents/chapters/05-methods/05-methods.qmd", "r") as f:
    text = f.read()

target = r"- \*\*Unsynthesizable RTL generation in LLM code synthesis:\*\* Language models trained primarily on software repositories emit Verilog code that parses cleanly in syntax linters but introduces multi-clock-domain race conditions, missing reset logic, or unsynthesizable latch arrays \[\@VerilogEval; \@RTLLM\]\."

replacement = r"""- **The "Garbage-In, Garbage-Out" open-source Verilog problem:** Software engineering has successfully leveraged LLMs because GitHub is filled with high-quality, executable, and heavily tested software frameworks. In contrast, open-source hardware repositories are notoriously unreliable—often consisting of undergraduate homework, non-synthesizable testbenches, and severe clock-domain crossing (CDC) violations. Language models trained on this distribution reliably hallucinate Verilog that passes syntax checks but fails formal verification, introduces race conditions, or infers unroutable latch arrays [@VerilogEval; @RTLLM]. Consequently, deploying generative models for physical design absolutely requires rigid, sandboxed CI/CD linting pipelines (e.g., CDC checks, SpyGlass) as the primary filter; an LLM without strict linting guardrails will confidently automate the injection of fatal hardware bugs."""

text = text.replace(target, replacement)

with open("book/contents/chapters/05-methods/05-methods.qmd", "w") as f:
    f.write(text)
