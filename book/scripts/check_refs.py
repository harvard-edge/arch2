#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

def main():
    book_dir = Path("synthesis/book")
    if not book_dir.exists():
        print(f"Error: Directory {book_dir} not found.")
        sys.exit(1)
    
    qmd_files = list(book_dir.rglob("*.qmd"))
    
    has_errors = False
    
    # We want to check globally across all files, because a figure in chapter 2 could be cited in chapter 3.
    # But usually, it's good to just check if it's referenced *anywhere* in the book.
    # Actually, it's safer to check if every definition has at least one reference across the whole book.
    
    all_defs = set()
    all_refs = set()
    
    # Regex to find definitions: {#fig-xxx} or {#tbl-xxx}
    # Be careful, sometimes it might be in a code block, but usually we just want to match the pattern.
    def_pattern = re.compile(r'\{#(fig-[a-zA-Z0-9_-]+|tbl-[a-zA-Z0-9_-]+)\}')
    # Regex to find references: @fig-xxx or @tbl-xxx
    ref_pattern = re.compile(r'@(fig-[a-zA-Z0-9_-]+|tbl-[a-zA-Z0-9_-]+)')
    
    file_for_def = {}
    
    for file in qmd_files:
        content = file.read_text()
        
        # Find definitions
        for match in def_pattern.finditer(content):
            def_id = match.group(1)
            all_defs.add(def_id)
            file_for_def[def_id] = file
            
        # Find references
        for match in ref_pattern.finditer(content):
            ref_id = match.group(1)
            all_refs.add(ref_id)
            
    # Check if all definitions are referenced
    for def_id in sorted(all_defs):
        if def_id not in all_refs:
            print(f"ERROR: {def_id} is defined in {file_for_def[def_id]} but is never referenced anywhere in the prose.")
            has_errors = True
            
    if has_errors:
        print("Please fix the missing cross-references by adding @fig-xxx or @tbl-xxx in the text.")
        sys.exit(1)
    else:
        print("Success: All figures and tables are properly cross-referenced.")
        sys.exit(0)

if __name__ == "__main__":
    main()
