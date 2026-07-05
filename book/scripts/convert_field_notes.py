import os
import glob
import re

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    i = 0
    changed = False
    
    while i < len(lines):
        line = lines[i]
        match = re.match(r'^:::\s*\{\.callout-field-note(.*)\}$', line)
        if match:
            changed = True
            attr_str = match.group(1)
            # Find title="..."
            title_match = re.search(r'title="([^"]+)"', attr_str)
            title = title_match.group(1) if title_match else None
            
            new_lines.append("::: {.column-margin}\n")
            if title:
                new_lines.append(f"**{title}**\n\n")
        else:
            new_lines.append(line)
        i += 1
        
    if changed:
        with open(filepath, "w") as f:
            f.writelines(new_lines)
        print(f"Updated {filepath}")

print("Field notes converted.")
