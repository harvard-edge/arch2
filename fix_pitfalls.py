import glob
import re

for filepath in glob.glob("book/chapters/*/*.qmd"):
    with open(filepath, "r") as f:
        content = f.read()

    # We want to find the section between "## Common Pitfalls" and "## Open Questions"
    # and replace `### Title` with `**Title.** ` (and join it with the next paragraph if we want)
    # Actually, if we just replace `^### (.*)$` with `**\1.**` it will just be a bold line.
    # If the next line is text, we can join them, but markdown allows:
    # **Title.**
    # Text
    #
    # Or we can do `**Title.** ` and strip the newline.

    def process_pitfalls(match):
        section_content = match.group(1)
        # Replace `### Title\n` with `**Title.** `
        # Wait, if there's a blank line after `### Title`, we should remove it.
        # So replace `### (.*?)\n\n?` with `**\1.** `
        fixed_content = re.sub(
            r"^###\s*(.*?)\n+", r"**\1.** ", section_content, flags=re.MULTILINE
        )
        return "## Common Pitfalls\n" + fixed_content + "\n## Open Questions"

    new_content = re.sub(
        r"## Common Pitfalls\n(.*?)\n## Open Questions",
        process_pitfalls,
        content,
        flags=re.DOTALL,
    )

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
