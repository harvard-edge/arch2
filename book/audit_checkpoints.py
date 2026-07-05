import glob
import re

chapters = [
    "/Users/VJ/GitHub/arch2/synthesis/book/chapters/07-feedback-verification-trust/index.qmd",
    "/Users/VJ/GitHub/arch2/synthesis/book/chapters/08-running-the-loop/index.qmd",
    "/Users/VJ/GitHub/arch2/synthesis/book/chapters/09-loop-patterns-across-stack/index.qmd",
    "/Users/VJ/GitHub/arch2/synthesis/book/chapters/10-what-architect-owns/index.qmd",
]

keywords = re.compile(r"(escalate|reversib|reject|commit|decide)", re.IGNORECASE)

print("=== Audit for Potential Architect Checkpoints ===")
print(
    "Looking for paragraphs that discuss decision gates (escalate, reject, commit, reversibility).\n"
)

for chap in chapters:
    print(f"\n--- {chap.split('/')[-2]} ---")
    with open(chap, "r") as f:
        content = f.read()

    # split into paragraphs
    paragraphs = content.split("\n\n")

    for i, p in enumerate(paragraphs):
        p_clean = p.replace("\n", " ")
        if not p_clean.startswith(":::"):  # skip existing callouts
            if keywords.search(p_clean) and len(p_clean.split()) > 20:
                # only print strong candidates where they might be framing a rule or gate
                if "must" in p_clean or "should" in p_clean or "before" in p_clean:
                    print(f"\nPotential Gate (Para {i}): {p_clean[:150]}...")
