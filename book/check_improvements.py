import os
import glob
import re

chapters = sorted(glob.glob("/Users/VJ/GitHub/arch2/synthesis/book/chapters/*/*.qmd"))

print("=== 1. Checking Prose Style Violations ===")
llm_ism_pattern = re.compile(
    r"(?i)(is simpler|is broader|is narrower|is important|is simple|rule is simple|point is|name is deliberate):\s"
)
tilde_pattern = re.compile(r"\d+~[a-zA-Z]+")

for chap in chapters:
    with open(chap, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if llm_ism_pattern.search(line):
            print(
                f"[{os.path.basename(os.path.dirname(chap))}] LLM-ism (line {i+1}): {line.strip()}"
            )
        if tilde_pattern.search(line):
            print(
                f"[{os.path.basename(os.path.dirname(chap))}] Forbidden tilde (line {i+1}): {line.strip()}"
            )

print("\n=== 2. Checking Callout Density ===")
callout_types = [
    "field-note",
    "failure-mode",
    "architect-checkpoint",
    "evidence-packet",
    "engineer-move",
]
for chap in chapters:
    counts = {c: 0 for c in callout_types}
    with open(chap, "r") as f:
        content = f.read()
        for c in callout_types:
            counts[c] = content.count(f"callout-{c}")

    missing = [c for c in callout_types if counts[c] == 0]
    print(
        f"[{os.path.basename(os.path.dirname(chap))}] Missing need-driven callouts: {', '.join(missing)}"
    )

print("\n=== 3. Extracting Design Principles ===")
for chap in chapters:
    chap_name = os.path.basename(os.path.dirname(chap))
    with open(chap, "r") as f:
        content = f.read()

    parts = content.split("callout-design-principle")
    for p in parts[1:]:
        # extract the title from title="..."
        title_match = re.search(r'title="([^"]+)"', p)
        title = title_match.group(1) if title_match else "NO TITLE"
        print(f"[{chap_name}] Principle: {title}")
