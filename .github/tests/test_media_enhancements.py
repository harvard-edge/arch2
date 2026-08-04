from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "compliance" / "media-enhancements.yml"


class MediaEnhancementTests(unittest.TestCase):
    def test_generated_manifest_is_current(self) -> None:
        result = subprocess.run(
            [
                "python3",
                str(ROOT / ".github" / "scripts" / "build_media_enhancements.py"),
                "--check",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_entry_has_delivery_fields_and_no_placeholders(self) -> None:
        document = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
        entries = document.get("media_enhancements", [])
        self.assertEqual(len(entries), 45)
        urls = [entry.get("url") for entry in entries]
        self.assertEqual(len(urls), len(set(urls)), "duplicate manifest URLs")
        for entry in entries:
            for field in ("url", "owner", "nature", "description"):
                self.assertTrue(entry.get(field), f"missing {field}: {entry}")
            self.assertNotIn("TODO", str(entry))


if __name__ == "__main__":
    unittest.main()
