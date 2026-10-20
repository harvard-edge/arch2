"""Check the dependency overlay and retain exact installed runtime identities."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess

from packaging.requirements import Requirement


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    expected = {}
    for line in (directory / "full-runtime-constraints.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            actual = metadata.version(name)
            if actual != version:
                raise RuntimeError(f"Pinned dependency differs: {name}: {actual} != {version}")
            expected[name] = actual
    for text in metadata.requires("torch"):
        requirement = Requirement(text)
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        version = metadata.version(requirement.name)
        if requirement.specifier and version not in requirement.specifier:
            raise RuntimeError(f"Unsatisfied Torch dependency: {text}; installed {version}")
    import torch
    import numpy

    if torch.get_num_threads() != 1 or torch.zeros(1).numpy().dtype != numpy.dtype("float32"):
        raise RuntimeError("CPU thread or NumPy interoperation check failed")
    torch.optim.Adam([torch.nn.Parameter(torch.zeros(1))])
    pdk = Path("/foss/pdks/sky130A").resolve(strict=True)
    if pdk != Path("/foss/pdks/ciel/sky130/versions/54435919abffb937387ec956209f9cf5fd2dfbee/sky130A"):
        raise RuntimeError("Pinned SKY130A identity differs")

    def tool(*command):
        return subprocess.check_output(
            ["/bin/bash", "-c", 'source /etc/profile >/dev/null; exec "$@"', "nanochip-tool", *command],
            text=True, stderr=subprocess.STDOUT, timeout=30).strip()

    result = dict(python=platform.python_version(), architecture=platform.machine(),
                  constraints=expected, torch_threads=torch.get_num_threads(), pdk=str(pdk),
                  tools={name: tool(*command) for name, command in {
                      "librelane": ("librelane", "--version"), "openroad": ("openroad", "-version"),
                      "yosys": ("yosys", "-V"), "verilator": ("verilator", "--version"),
                      "make": ("make", "--version"), "c++": ("c++", "--version")}.items()},
                  distributions=[dict(name=d.metadata["Name"], version=d.version,
                                      location=str(d.locate_file("")))
                                 for d in metadata.distributions()],
                  declared_licenses={name: {
                      "expression": metadata.metadata(name).get("License-Expression"),
                      "license": metadata.metadata(name).get("License"),
                  } for name in ("torch", "numpy", "librelane", "setuptools")})
    if args.package:
        import nanochip
        package = Path(nanochip.__file__).resolve().parent
        result["package"] = dict(version=metadata.version("nanochip"), files={
            str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(package.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        })
    (directory / "environment.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(verified=True, python=result["python"], torch=expected["torch"],
                          numpy=expected["numpy"], architecture=result["architecture"])))


if __name__ == "__main__":
    main()
