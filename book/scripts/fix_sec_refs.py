#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

def main():
    book_dir = Path("synthesis/book/chapters")
    qmd_files = list(book_dir.rglob("*.qmd"))
    
    # 1. Collect all defined sections
    defined_secs = set()
    def_pattern = re.compile(r'\{#(sec-[a-zA-Z0-9_-]+)\}')
    
    for file in qmd_files:
        content = file.read_text()
        for match in def_pattern.finditer(content):
            defined_secs.add(match.group(1))
            
    # 2. Collect all referenced sections
    referenced_secs = set()
    ref_pattern = re.compile(r'@(sec-[a-zA-Z0-9_-]+)')
    
    for file in qmd_files:
        content = file.read_text()
        for match in ref_pattern.finditer(content):
            referenced_secs.add(match.group(1))
            
    missing_defs = referenced_secs - defined_secs
    if missing_defs:
        print("Missing section definitions:")
        for missing in sorted(missing_defs):
            print(f" - {missing}")
            # Try to auto-fix if possible
            expected_header = missing.replace('sec-', '').replace('-', ' ').lower()
            
            for file in qmd_files:
                content = file.read_text()
                lines = content.splitlines()
                changed = False
                for i, line in enumerate(lines):
                    if line.startswith('#') and '{#sec-' not in line:
                        clean_header = re.sub(r'^#+\s*', '', line).lower()
                        # fuzzy match
                        if clean_header.startswith(expected_header) or expected_header in clean_header:
                            lines[i] = f"{line} {{#{missing}}}"
                            changed = True
                            print(f"   -> Auto-fixed in {file.name}: {lines[i]}")
                            break
                if changed:
                    file.write_text('\n'.join(lines) + '\n')
    else:
        print("All @sec references have matching definitions.")

if __name__ == "__main__":
    main()
