import re

with open("book/contents/chapters/06-environments/06-environments.qmd", "r") as f:
    text = f.read()

target = r"The environment guarantees that requested operations reach backend tools in declared states, enforces least-privilege sandboxing, and records produced artifacts in execution records."
replacement = r"The environment guarantees that requested operations reach backend tools in declared states, enforces least-privilege sandboxing, and records produced artifacts in execution records.[^fn-sandboxing-kubernetes-c06]"

text = text.replace(target, replacement)

footnote = r"""
[^fn-sandboxing-kubernetes-c06]: **The orchestration parallel:** Hardware engineers often assume that generating correct tool scripts is the primary bottleneck, viewing formal "environments" as unnecessary overhead. Software engineering faced a similar crisis of reproducibility with "works on my machine" scripts before containerization (Docker) and declarative orchestration (Kubernetes) became industry standard. Agentic hardware exploration requires its own orchestration layer because generative models cannot be trusted to manage shared filesystem state, clean up transient intermediate files, or manage CAD license queues without corrupting concurrent runs.
"""

# append to file if not exists
if "[^fn-sandboxing-kubernetes-c06]" not in text:
    pass  # it should have been replaced

text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/06-environments/06-environments.qmd", "w") as f:
    f.write(text)
