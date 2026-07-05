import glob
import re

def is_title_cased(text):
    # Extremely basic check: look for lowercase words that shouldn't be (ignoring small words)
    small_words = {"a", "an", "and", "as", "at", "but", "by", "en", "for", "if", "in", "of", "on", "or", "the", "to", "v", "v.", "via", "vs"}
    words = text.split()
    if not words: return True
    
    # First and last word should always be capitalized
    if not words[0][0].isupper() and words[0].isalpha(): return False
    if not words[-1][0].isupper() and words[-1].isalpha(): return False
    
    for w in words[1:-1]:
        clean_w = re.sub(r'[^a-zA-Z]', '', w)
        if not clean_w: continue
        if clean_w.islower() and clean_w not in small_words:
            return False
    return True

for fname in sorted(glob.glob("synthesis/book/chapters/*/index.qmd")):
    with open(fname) as f:
        for i, line in enumerate(f):
            if line.startswith("## "):
                title = line[3:].strip()
                # strip out any pandoc anchors {#sec-xyz}
                title = re.sub(r'\{#.*?\}', '', title).strip()
                if not is_title_cased(title):
                    print(f"{fname}:{i+1}: {title}")
