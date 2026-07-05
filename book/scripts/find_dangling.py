import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by double newline to get paragraphs
    paragraphs = re.split(r'\n\s*\n', content)
    
    for i, p in enumerate(paragraphs):
        p_strip = p.strip()
        # Ignore empty, code blocks, lists, headers, html, tables, callouts, latex
        if not p_strip or p_strip.startswith(('#', '-', '*', '>', '|', '!', '```', ':', '<', '$$', '\\', '@', '[', '{')):
            continue
        # Ignore figures and tables syntax
        if p_strip.startswith('![') or p_strip.startswith(':::'):
            continue
            
        # Count sentences roughly by looking for periods followed by space or end of string, excluding abbreviations like e.g.
        # But a simpler heuristic: if the paragraph is less than say 150 characters, or has only 1 sentence
        sentences = re.split(r'[.!?](?:\s|$)', p_strip)
        sentences = [s for s in sentences if len(s.strip()) > 3]
        
        if len(sentences) == 1 and len(p_strip.split()) < 30:
            print(f"--- File: {os.path.basename(filepath)} ---")
            print(f"Paragraph: {p_strip}\n")

def main():
    chapters_dir = '/Users/VJ/GitHub/arch2/synthesis/book/chapters'
    for root, dirs, files in os.walk(chapters_dir):
        for file in files:
            if file.endswith('.qmd'):
                process_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
