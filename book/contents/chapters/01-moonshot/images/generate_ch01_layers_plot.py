"""Render the authored operational-layers SVG at its 4.8-inch print width.

The 760-unit viewBox stacks Layer 1 at the bottom and Layer 3 at the top.
The PNG twin retains that physical width at 300 dpi.
"""

from pathlib import Path
import struct
import subprocess
import zlib


def set_png_dpi(path: Path, dpi: int) -> None:
    """Record print density without resampling the rendered pixels."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pixels_per_meter = round(dpi / 0.0254)
    payload = struct.pack(">IIB", pixels_per_meter, pixels_per_meter, 1)
    chunk_type = b"pHYs"
    density = (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload))
    )
    chunks = [data[:8]]
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk = data[offset : offset + length + 12]
        if chunk[4:8] != b"pHYs":
            chunks.append(chunk)
        if chunk[4:8] == b"IHDR":
            chunks.append(density)
        offset += length + 12
    path.write_bytes(b"".join(chunks))


def main() -> None:
    source = (
        Path(__file__).resolve().parent / "fig-ch01-three-layers-ai-integration.svg"
    )
    for extension, options in [
        ("pdf", ["-f", "pdf"]),
        ("png", ["-d", "300", "-p", "300", "-w", "1440"]),
    ]:
        target = source.with_suffix("." + extension)
        subprocess.run(
            ["rsvg-convert", *options, str(source), "-o", str(target)], check=True
        )
        if extension == "png":
            set_png_dpi(target, 300)
        print(target)


if __name__ == "__main__":
    main()
