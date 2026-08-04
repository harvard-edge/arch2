import glob
import re

for filepath in glob.glob("book/chapters/*/*.qmd"):
    with open(filepath, "r") as f:
        content = f.read()

    def process_pitfalls(match):
        section_content = match.group(1)

        # 1. Convert `**Title**\ntext` to `**Title.** text`
        # 2. Convert `**Title:**\ntext` to `**Title.** text`
        # 3. Convert `**Title:** text` to `**Title.** text`
        # 4. Convert `**Title** text` to `**Title.** text`

        lines = section_content.split("\n")
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Match `**Some Title**` or `**Some Title:**` on its own line
            m_alone = re.match(r"^\*\*(.*?)(:|\.)?\*\*\s*$", line)
            if m_alone:
                title = m_alone.group(1).strip()
                # Next line might be the text, or a blank line.
                # If there's a blank line, skip it.
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if (
                    j < len(lines)
                    and not lines[j].startswith("**")
                    and not lines[j].startswith("##")
                ):
                    # Found text!
                    new_lines.append(f"**{title}.** {lines[j].strip()}")
                    i = j
                else:
                    new_lines.append(f"**{title}.**")
            else:
                # Match `**Some Title:** text` or `**Some Title** text`
                m_inline = re.match(r"^\*\*(.*?)(:|\.)?\*\*\s*(.+)$", line)
                if m_inline:
                    title = m_inline.group(1).strip()
                    text = m_inline.group(3).strip()
                    new_lines.append(f"**{title}.** {text}")
                else:
                    new_lines.append(line)
            i += 1

        fixed_content = "\n".join(new_lines)
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
        print(f"Formatted {filepath}")
