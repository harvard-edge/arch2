import os
import glob

# 1. Remove unicode pen character ✒︎
# 2. Fix the extra ::: in ch 7 and ch 8
# 3. Add {#sec-...} to Ch 7 headers

ch7_file = "synthesis/book/chapters/07-feedback-verification-trust/index.qmd"
with open(ch7_file, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("## Fidelity Ladders and Evidence Ledgers") and "{#sec" not in line:
        line = "## Fidelity Ladders and Evidence Ledgers {#sec-fidelity-ladders-and-evidence-ledgers}\n"
    elif line.startswith("## Commitment Levels and Reversibility") and "{#sec" not in line:
        line = "## Commitment Levels and Reversibility {#sec-commitment-levels-and-reversibility}\n"
    elif line.startswith("## Proxy Mismatch, Metric Gaming, and Calibration") and "{#sec" not in line:
        line = "## Proxy Mismatch, Metric Gaming, and Calibration {#sec-proxy-mismatch-metric-gaming-and-calibration}\n"
    elif line.startswith("## Evidence Disputes and the Trust Checklist") and "{#sec" not in line:
        line = "## Evidence Disputes and the Trust Checklist {#sec-evidence-disputes-and-the-trust-checklist}\n"
    new_lines.append(line)

# Remove extra ::: at the end
while new_lines and new_lines[-1].strip() == ":::":
    new_lines.pop()
    # also pop any empty lines before it just in case
    while new_lines and new_lines[-1].strip() == "":
        new_lines.pop()

with open(ch7_file, "w") as f:
    f.writelines(new_lines)


ch8_file = "synthesis/book/chapters/08-running-the-loop/index.qmd"
with open(ch8_file, "r") as f:
    lines = f.readlines()
while lines and lines[-1].strip() == ":::":
    lines.pop()
    while lines and lines[-1].strip() == "":
        lines.pop()
with open(ch8_file, "w") as f:
    f.writelines(lines)

# Remove ✒︎ from all files
for fp in glob.glob("synthesis/book/chapters/*/index.qmd"):
    with open(fp, "r") as f:
        content = f.read()
    if "✒︎" in content:
        content = content.replace("✒︎", "")
        with open(fp, "w") as f:
            f.write(content)

print("Fixes applied.")
