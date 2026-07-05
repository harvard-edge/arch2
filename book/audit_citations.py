import glob
import re

bib_file = "/Users/VJ/GitHub/arch2/synthesis/references/references.bib"
chapters = glob.glob(
    "/Users/VJ/GitHub/arch2/synthesis/book/chapters/**/*.qmd", recursive=True
)
chapters.append("/Users/VJ/GitHub/arch2/synthesis/book/index.qmd")

# Extract keys from bib
bib_keys = set()
with open(bib_file, "r") as f:
    for line in f:
        m = re.match(r"@\w+\{([^,]+),", line.strip())
        if m:
            bib_keys.add(m.group(1))

print(f"Total entries in references.bib: {len(bib_keys)}")

# Extract cited keys from qmd
cited_keys = set()
for chap in chapters:
    with open(chap, "r") as f:
        content = f.read()
        # Find citations like @author2023 or [@author2023] or [-@author2023]
        # Regex to capture the key: @([a-zA-Z0-9_:-]+)
        matches = re.findall(r"@([a-zA-Z0-9_:-]+)", content)
        for m in matches:
            # Filter out Quarto's cross-references like @sec-, @fig-, @tbl-, @eq-
            if not m.startswith(("sec-", "fig-", "tbl-", "eq-", "lst-")):
                cited_keys.add(m)

print(f"Total unique citations in text: {len(cited_keys)}")

missing_in_bib = cited_keys - bib_keys
if missing_in_bib:
    print(f"\nERROR: Cited in text but missing in references.bib: {missing_in_bib}")
else:
    print("\nAll text citations exist in references.bib.")

unused_in_bib = bib_keys - cited_keys
if unused_in_bib:
    print(f"\nUnused in text (but in bib): {len(unused_in_bib)} keys")

# Now check for potential hallucinations or missing seminals.
print(
    "\nSeminal AI for Architecture papers to check in references.bib (case-insensitive check):"
)
seminals = [
    "Apollo",
    "ArchGym",
    "Mirhoseini",
    "AutoPhase",
    "MicroGrad",
    "AlphaDev",
    "AlphaFold",
    "Mankowitz",
    "LLM4EDA",
    "ChipNeMo",
    "VeriGen",
]
with open(bib_file, "r") as f:
    bib_text = f.read().lower()

for s in seminals:
    if s.lower() in bib_text:
        print(f"Found mention of: {s}")
    else:
        print(f"MISSING seminal topic/author: {s}")
