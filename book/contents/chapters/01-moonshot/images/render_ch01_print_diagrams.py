"""Render the two authored chapter 1 diagrams at their 4.8-inch print width.

Both SVGs use a 480-unit viewBox with 11-unit body text (7.92 pt in print).
Their PNG twins preserve the same physical dimensions at 300 dpi.
"""

from pathlib import Path
import subprocess

from generate_ch01_layers_plot import set_png_dpi


def main() -> None:
    directory = Path(__file__).resolve().parent
    for name in ("fig-design-method-progression", "fig-moonshot-prompt"):
        source = directory / f"{name}.svg"
        for extension, options in [
            ("pdf", ["-f", "pdf"]),
            ("png", ["-d", "300", "-p", "300", "-w", "1440"]),
        ]:
            target = source.with_suffix(f".{extension}")
            subprocess.run(
                ["rsvg-convert", *options, str(source), "-o", str(target)], check=True
            )
            if extension == "png":
                set_png_dpi(target, 300)
            print(target)


if __name__ == "__main__":
    main()
