import os
import glob
import re

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        content = f.read()

    # Find the "## Open Research Questions" section
    if "## Open Research Questions" in content:
        parts = content.split("## Open Research Questions")
        prefix = parts[0]
        suffix = parts[1]

        # The suffix contains the questions and then possibly another section like ::: {.callout
        # Or maybe it's the end of the file.
        
        # We want to replace patterns like:
        # 1. Question text here?
        #    Discussion text here.
        # With:
        # 1. **Question text here?**
        # Discussion text here.
        
        # We will use regex to find lines starting with digit + dot, and bold them.
        # Then remove the leading spaces from the following lines.
        
        # Regex to match: \n(1-9)\. (.*?)\n   (.*?)
        # Let's write a simple line-by-line processor for the suffix.
        
        lines = suffix.split('\n')
        new_lines = []
        in_question = False
        
        for i, line in enumerate(lines):
            match = re.match(r'^(\d+)\.\s+(.*)$', line)
            if match:
                # It's a question line
                # Check if it's already bolded
                q_text = match.group(2)
                if not q_text.startswith('**'):
                    line = f"{match.group(1)}. **{q_text}**"
                new_lines.append(line)
            elif line.startswith('   ') or line.startswith('  ') or line.startswith(' - '):
                # Continuation / discussion line
                new_lines.append(line.lstrip(' -'))
            else:
                new_lines.append(line)
        
        new_suffix = '\n'.join(new_lines)
        new_content = prefix + "## Open Research Questions" + new_suffix
        
        if new_content != content:
            with open(filepath, "w") as f:
                f.write(new_content)
            print(f"Updated {filepath}")

print("Formatting complete.")
