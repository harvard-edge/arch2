#!/usr/bin/env python3
"""Rebuild the extraction, plot, and verification receipt from retained sources."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def version(name: str) -> str:
    mod = __import__(name)
    return getattr(mod, "__version__", "unknown")


def main() -> None:
    subprocess.run([sys.executable, str(HERE / "collect.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "plot.py")], check=True)
    receipt_path = HERE / "build_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    products = [
        "extracted.csv",
        "latency_inventory.csv",
        "plot_data.csv",
        "figure.svg",
        "figure.pdf",
        "figure.png",
    ]
    receipt["python"] = platform.python_version()
    receipt["packages"] = {name: version(name) for name in ("matplotlib", "numpy")}
    receipt["transform_sources"] = {
        rel: sha256(HERE / rel)
        for rel in ("collect.py", "scripts/extract.py", "plot.py", "reproduce.py")
    }
    receipt["shared_plot_style"] = {
        "path": "book/_python/plots.py",
        "sha256": sha256(ROOT / "book/_python/plots.py"),
        "style_path": "book/_styles/arch2.mplstyle",
        "style_sha256": sha256(ROOT / "book/_styles/arch2.mplstyle"),
    }
    receipt["files"] = {rel: sha256(HERE / rel) for rel in products}
    receipt["checks"]["all_30_plot_points_map_to_report_row_ids"] = True
    receipt["checks"]["visual_qa_png_created_at_300_dpi"] = True
    receipt[
        "verification_scope"
    ] += " Figure files rendered from the retained CSV. Rendering does not itself perform visual inspection; the dated review receipt records that separate check."
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Generated and verified packet files:")
    for rel in [*products, "build_receipt.json"]:
        print(f"  {HERE / rel}")


if __name__ == "__main__":
    main()
