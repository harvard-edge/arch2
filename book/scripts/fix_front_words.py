import glob
import re

files = glob.glob("synthesis/book/chapters/*/index.qmd")

def bold_front_words(match):
    open_tag = match.group(1)
    content = match.group(2)
    close_tag = match.group(3)
    
    # Split content by lines
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Match a bullet point that starts with text and a colon, e.g., "- Reader test: Could an..."
        # But we must be careful not to double-bold if it's already **Text:**
        # Match pattern: "- " or "* ", optional "**", some text (not containing colon), optional "**", ":"
        m = re.match(r'^(\s*[-*]\s+)(?:\*\*)?([^:\*]+)(?:\*\*)?:(.*)$', line)
        if m:
            bullet = m.group(1)
            front_text = m.group(2).strip()
            rest_of_line = m.group(3)
            # Reconstruct with bolded front word
            line = f"{bullet}**{front_text}:**{rest_of_line}"
        new_lines.append(line)
        
    return f"{open_tag}\n{chr(10).join(new_lines)}\n{close_tag}"

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # We want to process .callout-learning-objectives and .callout-carry-forward
    new_content = re.sub(r'(::+\s*\{\s*\.callout-(?:learning-objectives|carry-forward)[^}]*\})\n(.*?)\n(::+)', bold_front_words, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Bolded front words in {filepath}")

print("Done bolding front words.")
