"""Render the authored fig-ch01-three-layers-ai-integration SVG as PDF and PNG."""

from pathlib import Path
import subprocess


def main() -> None:
    source = (
        Path(__file__).resolve().parent / "fig-ch01-three-layers-ai-integration.svg"
    )
    for extension, options in [
        ("pdf", ["-f", "pdf"]),
        ("png", ["-d", "300", "-p", "300", "-w", "3000"]),
    ]:
        target = source.with_suffix("." + extension)
        subprocess.run(
            ["rsvg-convert", *options, str(source), "-o", str(target)], check=True
        )
        print(target)


if __name__ == "__main__":
    main()
