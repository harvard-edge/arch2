"""Inventory, copy, and verify only the prepared runtime's declared build inputs.

Build helper: Python 3.11+ (tomllib). It does not install or execute Nanochip,
Docker, EDA, training, or simulation. Source acceptance remains the owner's job.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import stat

try:
    import tomllib
except ImportError:
    raise SystemExit("The snapshot build helper requires Python 3.11+; the runtime wheel still supports Python 3.10+")


SCHEMA = "nanochip-runtime-snapshot/v2"
FORBIDDEN = {".claude", ".codex", ".gemini", ".git", "__pycache__", "local-check", "output", "outputs", "build", "dist"}


def _allowed(relative):
    return (not relative.is_absolute() and ".." not in relative.parts
            and not FORBIDDEN.intersection(relative.parts)
            and relative.name not in {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
            and (not relative.parts or relative.parts[0] not in {"book", "docs", "cards", "cockpit", "labs"})
            and not any(part.startswith(".env") for part in relative.parts))


def _file(source, relative):
    if not _allowed(relative):
        raise ValueError(f"Private/generated or escaping input refused: {relative}")
    path = source / relative
    if not path.resolve(strict=True).is_relative_to(source) or not path.is_file():
        raise ValueError(f"Build input is not a contained regular file: {relative}")
    return path


def _copy_sources(recipe):
    result = []
    for line in re.sub(r"\\\r?\n", " ", recipe).splitlines():
        if not line.lstrip().upper().startswith("COPY "):
            continue
        arguments = shlex.split(line.strip(), comments=True)[1:]
        if any(item.startswith("--from") for item in arguments) or arguments[0].startswith("["):
            raise ValueError("Snapshot COPY audit needs explicit host inputs; unsupported COPY form")
        arguments = [item for item in arguments if not item.startswith("--")]
        if len(arguments) < 2:
            raise ValueError("Malformed Docker COPY instruction")
        result.extend(arguments[:-1])
    return result


def inventory(source):
    source = Path(source).resolve(strict=True)
    config = tomllib.loads(_file(source, Path("pyproject.toml")).read_text())
    settings = config["tool"]["setuptools"]
    package_roots = {name: Path(name.removeprefix("nanochip").lstrip(".").replace(".", "/"))
                     for name in settings["packages"]}
    if settings["package-dir"] != {"nanochip": "."} or any(
            (name != "nanochip" and not name.startswith("nanochip."))
            or not all(part.isidentifier() for part in name.split(".")) for name in package_roots):
        raise ValueError("Unsupported package mapping; inspect the runtime closure before snapshotting")
    wheel = set()
    unmatched = []
    for directory in package_roots.values():
        wheel.update(path.relative_to(source) for path in (source / directory).glob("*.py"))
    for name, patterns in settings["package-data"].items():
        for pattern in patterns:
            if not _allowed(package_roots[name] / pattern):
                raise ValueError(f"Unsafe package-data pattern: {name}:{pattern}")
            matches = [path for path in (source / package_roots[name]).glob(pattern) if path.is_file()]
            if not matches:
                unmatched.append(f"{name}:{pattern}")
            wheel.update(path.relative_to(source) for path in matches)
    for directory in (source / "engine", source / "laboratory"):
        for path in directory.rglob("*.py"):
            relative = path.relative_to(source)
            if _allowed(relative) and relative not in wheel:
                raise ValueError(f"Runtime Python is outside declared packages: {relative}")
    recipe = Path("containers/FullDockerfile")
    copied = set()
    copy_sources = _copy_sources(_file(source, recipe).read_text())
    for pattern in copy_sources:
        relative = Path(pattern)
        if not _allowed(relative) or pattern in (".", "./"):
            raise ValueError(f"Unsafe Docker COPY source: {pattern}")
        matches = list(source.glob(pattern))
        if not matches:
            raise ValueError(f"Docker COPY input is missing: {pattern}")
        for path in matches:
            relative = path.relative_to(source)
            if path.is_dir():
                selected = {item for item in wheel if item.is_relative_to(relative)}
                if not selected:
                    raise ValueError(f"Docker COPY directory has no declared package files: {relative}")
                copied.update(selected)
            else:
                copied.add(relative)
    if wheel - copied:
        raise ValueError("Package files absent from Docker COPY inputs: " + ", ".join(map(str, sorted(wheel - copied))))
    files = wheel | copied | {Path("pyproject.toml"), recipe,
        Path("containers/FullDockerfile.dockerignore"), Path("containers/snapshot_runtime.py")}
    paths = {str(relative): _file(source, relative) for relative in sorted(files)}
    return {"schema": SCHEMA, "distribution": config["project"]["name"],
            "version": config["project"]["version"], "packages": settings["packages"],
            "wheel_files": sorted(map(str, wheel)), "docker_copy_sources": copy_sources,
            "unmatched_data_patterns": unmatched,
            "files": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()},
            "modes": {name: stat.S_IMODE(path.stat().st_mode) for name, path in paths.items()}}


def verify(source, manifest):
    expected = json.loads(Path(manifest).read_text())
    _verify_context_files(Path(source), expected)
    actual = inventory(source)
    if expected != actual:
        raise ValueError("Snapshot manifest differs from current source/input closure")
    return actual


def _verify_context_files(source, expected):
    actual = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Snapshot context contains a symlink: {path.relative_to(source)}")
        if path.is_file():
            actual.add(str(path.relative_to(source)))
    if actual != set(expected["files"]):
        raise ValueError("Snapshot context has missing or unmanifested files")


def create(source, output):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.is_relative_to(source):
        raise ValueError("Snapshot output must be outside the authored package")
    before = inventory(source)
    output.mkdir(parents=True, exist_ok=False)
    target = output / "snapshot/nanochip"
    for name, digest in before["files"].items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_file(source, Path(name)), destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Source changed while copying: {name}; partial output retained")
    if inventory(source) != before or inventory(target) != before:
        raise ValueError("Source/input closure changed while copying; partial output retained")
    _verify_context_files(target, before)
    manifest = output / "snapshot.json"
    with manifest.open("x") as stream:
        json.dump(before, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "create", "verify"))
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="new snapshot root, for create")
    parser.add_argument("--manifest", type=Path, help="existing manifest, for verify")
    args = parser.parse_args(argv)
    if args.command == "create":
        if args.output is None:
            parser.error("create requires --output")
        print(create(args.source, args.output))
    elif args.command == "verify":
        if args.manifest is None:
            parser.error("verify requires --manifest")
        verify(args.source, args.manifest)
        print(json.dumps({"verified": True, "manifest": str(args.manifest)}))
    else:
        print(json.dumps(inventory(args.source), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
