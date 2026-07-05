import glob
import re

files = sorted(glob.glob("synthesis/book/chapters/*/index.qmd"))

for filepath in files:
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    in_research = False
    print(f"\n--- {filepath} ---")
    for line in lines:
        if line.startswith("## Open Research"):
            in_research = True
        elif in_research and line.startswith("##"):
            in_research = False
            
        if in_research and '@sec-' in line:
            print(line.strip())
