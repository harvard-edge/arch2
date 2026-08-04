import re

filepath = "book/chapters/03-lifecycle/03-lifecycle.qmd"
with open(filepath, "r") as f:
    content = f.read()

# Fix heading level
content = content.replace("### Common Pitfalls", "## Common Pitfalls")


def process_pitfalls(match):
    section_content = match.group(1)
    # The agent might have written:
    # **Title:**
    # Text
    # Let's replace `\*\*Title:\*\*\n` with `**Title.** `
    fixed_content = re.sub(
        r"^\*\*(.*?):\*\*\n+", r"**\1.** ", section_content, flags=re.MULTILINE
    )
    return "## Common Pitfalls\n" + fixed_content + "\n## Open Questions"


new_content = re.sub(
    r"## Common Pitfalls\n(.*?)\n## Open Questions",
    process_pitfalls,
    content,
    flags=re.DOTALL,
)

with open(filepath, "w") as f:
    f.write(new_content)
print("Fixed Chapter 3")
