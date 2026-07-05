import os
import glob
import re

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    in_rq_block = False
    
    for line in lines:
        # 1. Replace brackets around cross-references
        line = re.sub(r'\[[Ss]ee (@sec-[^\]]+)\]', r'see \1', line)
        line = re.sub(r'\[(@sec-[^\]]+)\]', r'\1', line)
        
        # 2. Check for research question opening tag
        # e.g., ::: {.callout-research-question title="Open Research Questions"}
        if re.search(r':::\s*\{[^}]*callout-research-question[^}]*\}', line):
            in_rq_block = True
            match = re.search(r'title="([^"]+)"', line)
            title = match.group(1) if match else "Open Research Questions"
            new_lines.append(f"## {title}\n")
        elif in_rq_block and line.strip() == ":::":
            # This is the closing tag for the research question block
            in_rq_block = False
            # skip adding this line
        else:
            new_lines.append(line)
            
    with open(filepath, "w") as f:
        f.writelines(new_lines)

print("Formatting applied.")
