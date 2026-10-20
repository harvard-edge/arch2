"""Select verified locks for the BuildKit target and the executing base platform."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil


BASE_INDEX = "hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38"
PLATFORMS = {
    "arm64": {
        "machines": ("aarch64", "arm64"),
        "requirements": "requirements-full.lock",
        "constraints": "full-runtime-constraints.txt",
        "image": "hpretl/iic-osic-tools@sha256:ec3170b0bd0d4ba9fce9f7c38c01570bb349b395a6802a998fd4289c35039516",
    },
    "amd64": {
        "machines": ("x86_64", "amd64"),
        "requirements": "requirements-full-amd64.lock",
        "constraints": "full-runtime-constraints-amd64.txt",
        "image": "hpretl/iic-osic-tools@sha256:872e7e57e31966dead2ae6ed31f6277fb9ec92f20cc66afbb3f39f57b2b1e708",
    },
}


def select(directory: Path, target_arch: str, machine: str):
    if target_arch not in PLATFORMS:
        raise ValueError(f"Unsupported BuildKit TARGETARCH {target_arch!r}; use arm64 or amd64")
    chosen = PLATFORMS[target_arch]
    if machine.lower() not in chosen["machines"]:
        raise ValueError(f"Base machine {machine!r} differs from BuildKit TARGETARCH {target_arch!r}")
    selections = {"requirements-full.lock": chosen["requirements"],
                  "full-runtime-constraints.txt": chosen["constraints"]}
    # Validate both sources before replacing either effective file.
    sources = {output: (directory / "locks" / source).read_bytes()
               for output, source in selections.items()}
    receipt = {"schema": "nanochip-runtime-platform/v1", "target_architecture": target_arch,
               "machine": machine, "physical_base_index": BASE_INDEX,
               "physical_platform_image": chosen["image"], "effective_files": {}}
    for output, source in selections.items():
        shutil.copyfile(directory / "locks" / source, directory / output)
        receipt["effective_files"][output] = {"source": f"locks/{source}",
            "sha256": hashlib.sha256(sources[output]).hexdigest()}
    (directory / "platform.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-arch", required=True)
    args = parser.parse_args(argv)
    receipt = select(Path(__file__).resolve().parent, args.target_arch, platform.machine())
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
