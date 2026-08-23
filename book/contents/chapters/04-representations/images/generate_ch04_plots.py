"""Generate Matplotlib figures for Chapter 4 (Representations)."""

import sys
from pathlib import Path

# Add book directory to sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Add chapter data dir to sys.path
data_dir = Path(__file__).resolve().parents[1] / "data"
if str(data_dir) not in sys.path:
    sys.path.insert(0, str(data_dir))

import plot_architecture_data_scarcity
import plot_hardware_representation_dilation

if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Generating Chapter 4 figures...")
    plot_architecture_data_scarcity.main()
    plot_hardware_representation_dilation.main()
    print("Chapter 4 figures generated successfully.")
