import re

with open("book/contents/chapters/08-loop/08-loop.qmd", "r") as f:
    text = f.read()

# Cut 1: Meta-narration
target1 = r"Both records run the six responsibilities of @sec-architecture-20-ontology, and the sections below follow them in order rather than announcing them. Formulate appears as the architectural decision and the frozen preregistration, Explore as the legal candidate set each arm draws from, Implement as the execution prerequisites and the recorded chronology, Evaluate as the returned simulator outputs, Interpret as the mechanism probe, and Commit as the review that assigns a status and stops."
text = text.replace(target1, "")

# Cut 2: Patronizing caricature
target2 = r"When an engineering team encounters memory stalls in high-level workloads, the instinctive reaction is to double the cache parameter in a configuration file and dispatch a batch of simulator jobs."
replacement2 = r"When high-level workload profiles reveal severe memory stall cycles, exploration often defaults to naive parameter sweeps across cache capacities without first grounding physical banking rules and thermal limits."
text = text.replace(target2, replacement2)

# Cut 3: Policy Engine fantasy
target3 = r"Future AI systems might systematically execute commitment authority by embedding strict policy engines. If an automated study satisfies all predefined formal property checks, physical bounds, and risk thresholds, the engine could programmatically delegate authority, advancing a technical recommendation directly into a committed design state. Without such mechanisms, the boundary between an automated simulation sweep and an authorized architectural decision remains manual."
replacement3 = r"Automated tooling can qualify and rank recommendations against technical thresholds, but the commitment to tape out silicon or freeze an interface remains strictly with the human commitment authority."
text = text.replace(target3, replacement3)

# Add footnote: Surrogate reward hacking
target4 = r"When evaluation proxies detach from physical ground truth, they invite the *Whac-a-Mole regression effect*, where solving an isolated metric breaks unmonitored global constraints."
replacement4 = r"When evaluation proxies detach from physical ground truth, they invite the *Whac-a-Mole regression effect*, where solving an isolated metric breaks unmonitored global constraints.[^fn-surrogate-reward-hacking-c08]"
footnote4 = r"""
[^fn-surrogate-reward-hacking-c08]: **Surrogate reward hacking (ML parallel)**: In reinforcement learning systems, optimizers routinely exploit modeling simplifications in proxy evaluators to maximize nominal scores without improving objective quality [@AmodeiEtAl2016Concrete; @SculleyEtAl2015Hidden]. Modern software engineering and ML pipelines counter this divergence by pairing fast inner-loop heuristics with multi-tiered continuous integration (CI) canary suites, directly paralleling the hardware requirement to anchor cycle-approximate simulator sweeps to periodic physical signoff gates.
"""
text = text.replace(target4, replacement4)
if "[^fn-surrogate-reward-hacking-c08]" in text and footnote4.strip() not in text:
    text += "\n" + footnote4.strip() + "\n"

with open("book/contents/chapters/08-loop/08-loop.qmd", "w") as f:
    f.write(text)
