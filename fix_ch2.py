import re

with open("book/contents/chapters/02-pressures/02-pressures.qmd", "r") as f:
    text = f.read()

target1 = r"This structural shift raises two governing questions. Why does modern architecture work demand new forms of design assistance, and where can that assistance genuinely help without weakening the empirical rigor of architectural comparisons?"
text = text.replace(target1, "")

target2 = r"Warehouse scale pulls preceding hardware and software pressures into a single architecture problem. Server and accelerator choices no longer exist in a vacuum; they ripple outward through network topology, collective communication, cluster scheduling, failure handling, deployment policies, and facility power and cooling."
replacement2 = r"At warehouse scale, server and accelerator microarchitectures couple directly to bisection bandwidth, collective communication schedules, tail-latency queueing, and facility thermal limits."
text = text.replace(target2, replacement2)

target3 = r"Expanding the system boundary does not merely multiply the number of design choices; it couples them into an intractable combinatorial web. Understanding why manual design loops fail under this burden requires examining the sheer mathematical magnitude of the resulting search spaces."
replacement3 = r"Expanding the system boundary compounds cross-layer dependencies, generating a combinatorial search space that defies exhaustive manual evaluation."
text = text.replace(target3, replacement3)

# Remove fig-bottleneck-causal-loop entirely if possible, but let's just replace the text
text = re.sub(
    r"!\[Local capacity bottlenecks create self-reinforcing evaluation backlog loops.*?\]\(images/fig-bottleneck-causal-loop\)\{#fig-bottleneck-causal-loop.*?\}\n",
    "",
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r"Missing or stale information makes this worse, because the backlog feeds itself \(@fig-bottleneck-causal-loop\)\. Stale context admits invalid candidates, the invalid candidates consume the very runs that would have refreshed the context, and the review queue that should have caught them falls further behind, so the next round of choices is made on information staler still\.",
    "Missing or stale context acts as an admission control failure: invalid candidates consume the very simulator licenses and queue slots that would have evaluated valid candidates, triggering resource starvation.",
    text,
    flags=re.DOTALL,
)

with open("book/contents/chapters/02-pressures/02-pressures.qmd", "w") as f:
    f.write(text)
