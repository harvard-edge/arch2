#!/usr/bin/env python3
"""Interactive demonstration runner for the Grounded Micro-Loops Workbench."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    cmd = [sys.executable, str(ROOT / "run_all.py"), "--demo"] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
