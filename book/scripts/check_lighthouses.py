import glob
import re

for filepath in sorted(glob.glob("synthesis/book/chapters/*/index.qmd")):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find all lighthouse callouts
    # ::: {.callout-lighthouse ...} ... :::
    matches = re.finditer(r':::\s*\{\s*\.callout-lighthouse[^}]*\}(.*?):::', content, re.DOTALL)
    for match in matches:
        print(f"--- {filepath} ---")
        lines = match.group(1).strip().split('\n')
        # Just print the first few words of each paragraph
        for line in lines:
            if line.strip():
                # print first 10 words
                print(" ".join(line.split()[:10]))
        print("")
