import glob
import re

chapters = sorted(glob.glob("book/contents/chapters/**/*.qmd", recursive=True))

print("Chapter | Word Count | Reads like abstract?")
print("-" * 50)

for chap in chapters:
    with open(chap, "r") as f:
        content = f.read()

    # Strip YAML frontmatter
    content = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL)

    # Find text between the main title (# Title) and the first section (## Section)
    match = re.search(
        r"^# (.*?)\n(.*?)(?=\n## )", content, flags=re.DOTALL | re.MULTILINE
    )

    if match:
        title = match.group(1).strip()
        intro_text = match.group(2).strip()
        # Remove empty lines and code blocks for word counting
        clean_text = re.sub(r"```.*?```", "", intro_text, flags=re.DOTALL)
        word_count = len(clean_text.split())

        name = chap.split("/")[-2]
        print(f"{name:20} | {word_count:4} words |")
        print(f"PREVIEW: {clean_text[:150]}...\n")
    else:
        print(f"Could not parse {chap}")
