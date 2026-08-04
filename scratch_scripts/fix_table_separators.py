import glob
import re


def fix_table_separators():
    qmd_files = sorted(glob.glob("book/**/*.qmd", recursive=True))

    for fpath in qmd_files:
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        modified = False
        new_lines = []
        for line in lines:
            # Match table separator row containing en-dashes or em-dashes
            # e.g., | – | – : |
            if re.match(r"^\s*\|(?:\s*[–—:-]+\s*\|)+\s*$", line):
                # Replace all en-dashes/em-dashes with hyphens
                fixed_line = line.replace("–", "-").replace("—", "-")
                new_lines.append(fixed_line)
                modified = True
                print(
                    f"Fixed table separator in {fpath}: {line.strip()} -> {fixed_line.strip()}"
                )
            else:
                new_lines.append(line)

        if modified:
            with open(fpath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)


if __name__ == "__main__":
    fix_table_separators()
