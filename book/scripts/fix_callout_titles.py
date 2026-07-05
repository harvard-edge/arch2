import glob
import re

files = glob.glob("synthesis/book/chapters/*/index.qmd")

prefixes_to_remove = [
    r"Architect Checkpoint:\s*",
    r"Architect's checkpoint:\s*",
    r"The crux:\s*",
    r"Lighthouse prompt:\s*",
    r"Lighthouse Prompt:\s*",
    r"Field note:\s*",
    r"Field Note:\s*",
    r"Evidence packet:\s*",
    r"Evidence Packet:\s*",
    r"Failure mode:\s*",
    r"Failure Mode:\s*",
    r"Design principle:\s*",
    r"Design Principle:\s*",
    r"Engineer move:\s*",
    r"Engineer Move:\s*"
]

regex_pattern = re.compile(r'title="(' + '|'.join(prefixes_to_remove) + r')(.*?)"', re.IGNORECASE)

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # We want to replace title="Prefix: Actual Title" with title="Actual Title"
    new_content = regex_pattern.sub(r'title="\2"', content)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Fixed titles in {filepath}")

