import re
import glob

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        content = f.read()
        
    # Replace ✒︎ **Author's Note: with **Author's Note:
    new_content = re.sub(r'✒︎ \*\*Author\'s Note:', r'**Author\'s Note:', content)
    
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Removed glyph from {filepath}")

