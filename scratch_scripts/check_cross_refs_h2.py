import glob
import re


def audit_cross_refs():
    qmd_files = sorted(glob.glob("book/**/*.qmd", recursive=True))

    # 1. Map each section label to its heading level
    anchor_levels = {}  # sec_id -> level (1=H1, 2=H2, 3=H3, 4=H4)
    anchor_files = {}  # sec_id -> file

    header_pattern = re.compile(r"^(#+)\s+.*?\{#(sec-[a-zA-Z0-9_-]+)\}")

    for fpath in qmd_files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                m = header_pattern.match(line)
                if m:
                    level = len(m.group(1))
                    sec_id = m.group(2)
                    anchor_levels[sec_id] = level
                    anchor_files[sec_id] = fpath

    print(f"Total {{#sec-...}} headers mapped: {len(anchor_levels)}")

    # Also search for any {#sec-...} defined on non-headers
    all_sec_anchors = re.compile(r"\{#(sec-[a-zA-Z0-9_-]+)\}")
    non_header_sec_anchors = {}
    for fpath in qmd_files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("#"):
                    for m in all_sec_anchors.finditer(line):
                        sec_id = m.group(1)
                        if sec_id not in anchor_levels:
                            non_header_sec_anchors[sec_id] = fpath

    if non_header_sec_anchors:
        print(f"Non-header sec anchors found: {list(non_header_sec_anchors.keys())}")

    # 2. Scan all @sec-... occurrences
    ref_pattern = re.compile(r"@(sec-[a-zA-Z0-9_-]+)")

    h3_or_h4_refs = []

    for fpath in qmd_files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                for m in ref_pattern.finditer(line):
                    ref_id = m.group(1)
                    level = anchor_levels.get(ref_id)
                    if level is not None and level > 2:
                        h3_or_h4_refs.append((fpath, line_no, ref_id, level))

    print(f"\nTotal H3/H4 cross-references found: {len(h3_or_h4_refs)}")
    for fpath, line_no, ref_id, level in h3_or_h4_refs:
        print(f"  {fpath}:{line_no} -> @{ref_id} (H{level})")


if __name__ == "__main__":
    audit_cross_refs()
