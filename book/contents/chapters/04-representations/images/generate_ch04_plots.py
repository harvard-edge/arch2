"""Generate Matplotlib figures for Chapter 4 (Representations)."""

import sys
from pathlib import Path

# Add book directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import matplotlib.pyplot as plt
import numpy as np

from _python.plots import COLORS, apply_style


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
