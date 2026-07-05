import re
import glob

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        content = f.read()
        
    # Replace **Author's Note:** with ✒︎ **Author's Note:**
    new_content = re.sub(r'\*\*Author\'s Note:', r'✒︎ **Author\'s Note:', content)
    
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Added glyph to {filepath}")

# Also update _quarto.yml to add reference-location: margin to html
with open("synthesis/book/_quarto.yml", "r") as f:
    yaml = f.read()

# find citation-location: margin under html and add reference-location: margin above it
yaml = re.sub(r'(default-image-extension: svg\n)(\s+)(citation-location: margin)', r'\1\2reference-location: margin\n\2\3', yaml)
with open("synthesis/book/_quarto.yml", "w") as f:
    f.write(yaml)
print("Updated _quarto.yml")
