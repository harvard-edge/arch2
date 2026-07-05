import glob
import re

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        content = f.read()
        
    # Find all column-margin blocks
    # Note: this simple regex assumes the block ends with ::: on a new line
    matches = re.finditer(r':::\s*\{\.column-margin\}\n(.*?)\n:::', content, re.DOTALL)
    for i, match in enumerate(matches):
        note = match.group(1).strip()
        words = len(note.split())
        print(f"--- {filepath} (Note {i+1}) ---")
        print(f"Word count: {words}")
        print(note)
        print()
