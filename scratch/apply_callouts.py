import glob
import re

files = glob.glob("synthesis/book/chapters/*/index.qmd")
for fpath in files:
    with open(fpath, "r") as f:
        content = f.read()
    
    if "## What to carry forward" in content:
        # Split into before and after the header
        parts = content.split("## What to carry forward\n")
        if len(parts) != 2:
            print(f"Skipping {fpath}, unexpected split count")
            continue
        
        before = parts[0]
        after = parts[1]
        
        # We need to find where to put the closing :::
        # Usually before the first footnote [^fn-...] or at the end of the file.
        lines = after.split("\n")
        end_idx = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("[^fn-"):
                end_idx = i
                break
        
        # Ensure there's a blank line before the closing :::
        callout_content = "\n".join(lines[:end_idx]).rstrip() + "\n"
        footnotes = "\n".join(lines[end_idx:])
        
        new_after = f"::: {{.callout-carry-forward title=\"What to carry forward\"}}\n{callout_content}\n:::\n\n{footnotes}"
        new_content = before + new_after
        
        with open(fpath, "w") as f:
            f.write(new_content)
        print(f"Updated {fpath}")

