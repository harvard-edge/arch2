import re


def fix_footnotes(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Pattern: [^fn-...]: **Term** is ... -> [^fn-...]: **Term**: ...
    # Or: [^fn-...]: **Term**. ... -> [^fn-...]: **Term**: ...
    def replace_fn(match):
        prefix = match.group(1)
        term = match.group(2)
        rest = match.group(3)
        return f"{prefix} **{term}**: {rest}"

    new_text = re.sub(
        r"^(\[\^fn-[a-zA-Z0-9_-]+\]:)\s+\*\*([^*]+)\*\*(?:\s+is|\.)\s+(.*)$",
        replace_fn,
        text,
        flags=re.MULTILINE,
    )

    if new_text != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"Fixed footnote colons in {path}")


fix_footnotes("book/chapters/05-methods/05-methods.qmd")
fix_footnotes("book/chapters/11-ownership/11-ownership.qmd")
