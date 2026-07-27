import re
from pathlib import Path

files = list(Path("chapters").rglob("*.qmd"))
for f in files:
    content = f.read_text()

    # Now find unreferenced figures
    figs = re.findall(r"\{(#fig-[a-zA-Z0-9_-]+)", content)
    for fig in figs:
        ref_name = fig.replace("#", "@")
        if content.count(ref_name) == 0:
            print(f"Missing ref {ref_name} in {f}")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if fig in line:
                    j = i - 1
                    while j >= 0 and not lines[j].strip():
                        j -= 1
                    if j >= 0 and not lines[j].startswith("!["):
                        # Avoid double periods
                        if lines[j].endswith("."):
                            lines[j] = lines[j][:-1] + f" ({ref_name})."
                        else:
                            lines[j] = lines[j] + f" ({ref_name})."
                        print(f"  Added to line: {lines[j]}")
                        break
            content = "\n".join(lines)

    f.write_text(content)
