import os
import glob
import re

chapters = sorted(glob.glob("/Users/VJ/GitHub/arch2/synthesis/book/chapters/*/*.qmd"))

for chap in chapters:
    chap_name = os.path.basename(os.path.dirname(chap))
    print(f"=== {chap_name} ===")
    with open(chap, "r") as f:
        lines = f.readlines()

    in_crux = False
    crux_lines = []

    for line in lines:
        if "callout-crux" in line:
            in_crux = True
            continue
        if in_crux:
            if line.strip() == ":::":
                in_crux = False
            else:
                crux_lines.append(line.strip())

        if line.startswith("## "):
            print(line.strip())

    print("CRUX:")
    print(" ".join(crux_lines))
    print()
