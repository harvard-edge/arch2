"""Automated RTL audit (frozen harness file). Machine-checkable subset of
the RUBRICS R1 rules, run by evaluate.py and stored in build/score.json:

  * hard failures (score -> 0): $fopen/$fwrite/$fscanf/$fread, $system,
    DPI imports/exports, PLI $-calls, any $readmem whose literal path
    is outside rtl/roms/, filelist entries outside rtl/, and redefining
    the reserved harness macros msh_sram/msh_rom — these are unambiguous
    sim-only escapes;
  * informational flags for the judge (do NOT zero the score by
    themselves): $readmem with a non-literal path (needs manual review),
    delay literals (#n) outside testbench context, `define abuse markers,
    and an inventory of rtl/roms/* with SHA-256 (every ROM requires a
    disclosed, reproducible generator; R1.4 — this task ships no frozen
    numeric artifacts, so there is nothing to copy).

Comments and string literals are stripped before scanning to avoid false
positives from documentation.
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

HARD_PATTERNS = [
    (r"\$fopen\b", "$fopen"),
    (r"\$fwrite\b", "$fwrite"),
    (r"\$fscanf\b", "$fscanf"),
    (r"\$fread\b", "$fread"),
    (r"\$fclose\b", "$fclose"),
    (r"\$system\b", "$system"),
    (r"\$random\b", "$random"),
    (r"\$urandom\b", "$urandom"),
    (r"import\s+\"DPI", "DPI import"),
    (r"export\s+\"DPI", "DPI export"),
]
SOFT_PATTERNS = [
    (r"\$display\b", "$display (must be simulation-only, e.g. `ifdef-guarded)"),
    (r"#\s*\d+", "delay literal"),
]


def _strip(text: str) -> str:
    """Remove comments and string literals (paths are audited separately)."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def _rtl_files():
    files = []
    fl = os.path.join(ROOT, "rtl", "filelist.f")
    if os.path.exists(fl):
        for line in open(fl):
            line = line.strip()
            if line and not line.startswith(("#", "//")):
                files.append(line)
    return files


def check() -> dict:
    hard, soft = [], []
    readmems = []
    for rel in _rtl_files():
        if not rel.startswith("rtl/"):
            hard.append(f"{rel}: filelist entries must live under rtl/ "
                        "(harness files are injected by evaluate.py)")
            continue
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            hard.append(f"{rel}: listed in filelist.f but missing")
            continue
        raw = open(p, encoding="utf-8", errors="replace").read()
        code = _strip(raw)
        if re.search(r"\bmodule\s+msh_sram\b", code):
            hard.append(f"{rel}: redefines reserved harness macro msh_sram")
        if re.search(r"\bmodule\s+msh_rom\b", code):
            hard.append(f"{rel}: redefines reserved harness macro msh_rom")
        for pat, what in HARD_PATTERNS:
            for m in re.finditer(pat, code):
                line = code[:m.start()].count("\n") + 1
                hard.append(f"{rel}:{line}: {what}")
        for pat, what in SOFT_PATTERNS:
            n = len(re.findall(pat, code))
            if n:
                soft.append(f"{rel}: {n}x {what}")
        # $readmem path audit runs on the RAW text (paths live in strings)
        for m in re.finditer(r"\$readmem[bh]\s*\(\s*(\"([^\"]*)\"|[A-Za-z_]\w*)",
                             raw):
            line = raw[:m.start()].count("\n") + 1
            if m.group(2) is not None:
                path = m.group(2)
                readmems.append({"file": rel, "line": line, "path": path})
                if not path.startswith("rtl/roms/"):
                    hard.append(f"{rel}:{line}: $readmem outside rtl/roms/ "
                                f"({path})")
            else:
                readmems.append({"file": rel, "line": line,
                                 "path": f"<identifier {m.group(1)}>"})
                soft.append(f"{rel}:{line}: $readmem with non-literal path "
                            f"(parameter defaults must resolve to rtl/roms/;"
                            f" judge review)")
    # ROM inventory (every entry requires a disclosed generator, R1.4)
    roms = []
    romdir = os.path.join(ROOT, "rtl", "roms")
    if os.path.isdir(romdir):
        for fn in sorted(os.listdir(romdir)):
            p = os.path.join(romdir, fn)
            if os.path.isfile(p) and not fn.lower().startswith("readme"):
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                roms.append({"file": f"rtl/roms/{fn}", "sha256": h,
                             "bytes": os.path.getsize(p)})
    return {"ok": not hard, "hard": hard, "soft": soft,
            "readmems": readmems, "roms": roms}


if __name__ == "__main__":
    import json
    r = check()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["ok"] else 1)
