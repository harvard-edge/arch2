"""python -m nanochip.laboratory.physical --rtl SOURCE --output NEW_DIRECTORY"""

import argparse
import json
from pathlib import Path

from .flow import run_physical

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--rtl", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--timeout-s", type=float, default=900)
parser.add_argument("--cores", type=int, default=1)
args = parser.parse_args()
result = run_physical(args.rtl, args.output, args.timeout_s, args.cores)
print(
    json.dumps(
        {k: result.get(k) for k in ("status", "ok", "details", "boundary", "checks")},
        indent=2,
    )
)
raise SystemExit(0 if result["ok"] else 2)
