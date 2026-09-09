import sys
from pathlib import Path

# Connect parent repo path to import canonical Chapter 7 script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ch7_data_dir = REPO_ROOT / "book" / "contents" / "chapters" / "07-feedback" / "data"
if str(ch7_data_dir) not in sys.path:
    sys.path.insert(0, str(ch7_data_dir))

import plot_synthesis_verification_funnel


def main():
    plot_synthesis_verification_funnel.main()


if __name__ == "__main__":
    main()
