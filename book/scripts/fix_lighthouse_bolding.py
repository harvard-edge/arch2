import glob
import re

prefixes = [
    "Context",
    "In the Lighthouse prompt",
    "Representation",
    "Takeaway",
    "Boundary",
    "Method role",
    "Rejection gate",
    "Deferred evidence",
    "Integration boundary",
    "Evidence boundary"
]

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, 'r') as f:
        content = f.read()
    
    def process_callout(match):
        open_tag = match.group(1) # e.g. "::: {.callout-lighthouse title="..."}"
        callout_text = match.group(2)
        close_tag = match.group(3)
        
        paragraphs = callout_text.split('\n\n')
        new_paragraphs = []
        for p in paragraphs:
            for prefix in prefixes:
                # Match prefix. or prefix followed by space
                pattern = r'^(?:\*\*)?' + re.escape(prefix) + r'(?:\*\*)?\.(\s+)'
                if re.match(pattern, p):
                    p = re.sub(pattern, f'**{prefix}.**\\1', p, count=1)
                    break
            new_paragraphs.append(p)
            
        return open_tag + "\n" + "\n\n".join(new_paragraphs) + "\n" + close_tag

    # Match ::: or :::: block exactly
    new_content = re.sub(r'(::+ \s*\{\s*\.callout-lighthouse[^}]*\})\n(.*?)\n(::+)', process_callout, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)

print("Lighthouse bolding applied safely.")
