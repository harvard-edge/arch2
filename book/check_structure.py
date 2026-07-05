import os
import glob
import re

chapters = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "chapters/*/*.qmd")))

for chap in chapters:
    print(f"=== {os.path.basename(os.path.dirname(chap))} ===")
    with open(chap, "r") as f:
        lines = f.readlines()

    crux_found = False
    gives_you_found = False
    principle_found = False
    prompt_found = False
    research_found = False
    carry_forward_found = False

    first_heading_idx = -1
    gives_you_idx = -1
    carry_forward_idx = -1

    for i, line in enumerate(lines):
        if line.startswith("## ") and first_heading_idx == -1:
            first_heading_idx = i

        if "callout-crux" in line:
            crux_found = True

        if "callout-learning-objectives" in line:
            gives_you_found = True
            gives_you_idx = i

        if "callout-design-principle" in line:
            principle_found = True

        if "callout-lighthouse" in line:
            prompt_found = True

        if "callout-research-question" in line:
            research_found = True

        if "callout-carry-forward" in line:
            carry_forward_found = True
            carry_forward_idx = i

    issues = []
    if not crux_found:
        issues.append("Missing: The crux")
    if not gives_you_found:
        issues.append("Missing: What this chapter gives you")
    if not principle_found:
        issues.append("Missing: Design principle")
    if not prompt_found:
        issues.append("Missing: Lighthouse prompt")
    if not research_found:
        issues.append("Missing: Open research questions")
    if not carry_forward_found:
        issues.append("Missing: What to carry forward")

    if gives_you_found and first_heading_idx != -1:
        dist = first_heading_idx - gives_you_idx
        if dist > 25:
            issues.append(f"'What this chapter gives you' is at line {gives_you_idx} but first heading is at {first_heading_idx} (Too far apart?)")

    if carry_forward_found:
        dist_from_end = len(lines) - carry_forward_idx
        if dist_from_end > 30:
            issues.append(f"'What to carry forward' is at line {carry_forward_idx} out of {len(lines)} (Not at the very end?)")

    if not issues:
        print("  All structural elements present.")
    else:
        for issue in issues:
            print(f"  - {issue}")
    print()
