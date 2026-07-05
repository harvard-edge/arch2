import os
import glob
import re

for filepath in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(filepath, "r") as f:
        content = f.read()
    
    # Extract all footnote definitions
    # Regex for ^\[\^([^\]]+)\]:(.*)$
    # Note: they might span multiple lines if they are indented, but usually they are one line.
    footnote_defs = {}
    
    def_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$', re.MULTILINE)
    for match in def_pattern.finditer(content):
        fn_id = match.group(1)
        fn_text = match.group(2).strip()
        footnote_defs[fn_id] = fn_text
        
    # Remove definitions from content
    content = def_pattern.sub('', content)
    
    # Now we need to process paragraphs.
    # We can split by \n\n. But wait, code blocks or lists might be tricky.
    # Instead, we can just find the footnote reference \[ \^ID \] in the text.
    # And we can just replace the reference with an inline Quarto aside?
    # Quarto aside: [footnote text]{.aside}
    # Wait, the user said "right after the paragraph".
    # Let's split by double newline.
    paragraphs = content.split('\n\n')
    new_paragraphs = []
    
    for p in paragraphs:
        # Find all footnotes referenced in this paragraph
        refs = re.findall(r'\[\^([^\]]+)\]', p)
        # Remove the references from the paragraph text
        p_clean = re.sub(r'\[\^([^\]]+)\]', '', p)
        new_paragraphs.append(p_clean)
        
        # Append the footnote text right after
        for ref in refs:
            if ref in footnote_defs:
                # Add it as a blockquote or simple bold text
                # We use > **Note:** text
                fn_text = footnote_defs[ref]
                # Some already start with **Term**: so we can just prefix with >
                if not fn_text.startswith("**"):
                    fn_text = "**Note:** " + fn_text
                new_paragraphs.append(f"> {fn_text}")

    
    new_content = '\n\n'.join(new_paragraphs)
    
    # Cleanup any stray multiple newlines that might have been created
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    
    with open(filepath, "w") as f:
        f.write(new_content)

print("Footnotes converted to inline blocks.")
