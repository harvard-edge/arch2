#!/usr/bin/env python3
"""Cut the durable record subset from the upstream CI ZIP and index the whole ZIP.

The ZIP expires upstream on 2027-01-06 and is not tracked (see README.md). This
script writes the tracked files that replace it for figure reproduction:

  raw/artifact-index.tsv          one line per ZIP member: size, packed size, CRC-32
  raw/run-records-subset.tar.gz   exact bytes of the selected members
  raw/job-113223652131.log.gz     exact bytes of the job log, when --job-log is given
"""
import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "raw/librelane-spm-ihp-sg13g2-run-37749124131-artifact-11539925672.zip"
INDEX = HERE / "raw/artifact-index.tsv"
SUBSET = HERE / "raw/run-records-subset.tar.gz"
JOB_LOG = HERE / "raw/job-113223652131.log.gz"
SELECTED = re.compile(
    r"^(?:"
    r"[0-9]{2}-.+/runtime\.txt"
    r"|[0-9]{2}-.+/[^/]+\.process_stats\.json"
    r"|final/metrics\.json|resolved\.json|warning\.log|error\.log"
    r"|01-verilator-lint/verilator-lint\.log"
    r"|05-yosys-jsonheader/yosys-jsonheader\.log"
    r"|59-magic-streamout/magic-streamout\.log"
    r"|67-klayout-drc/klayout-drc\.log"
    r"|72-netgen-lvs/netgen-lvs\.log"
    r")$"
)


def deterministic_gzip(payload):
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", compresslevel=9, fileobj=buffer, mtime=0
    ) as stream:
        stream.write(payload)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-log", type=Path, help="Log fetched from the jobs API")
    args = parser.parse_args()
    metadata = json.loads((HERE / "raw/artifact-metadata.json").read_text())
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    assert metadata["digest"] == f"sha256:{digest}", "ZIP does not match API digest"
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = sorted(archive.infolist(), key=lambda item: item.filename)
        lines = ["path\tfile_size\tcompress_size\tcrc32"]
        lines += [
            f"{m.filename}\t{m.file_size}\t{m.compress_size}\t{m.CRC:08x}"
            for m in members
        ]
        INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for member in members:
                if not SELECTED.fullmatch(member.filename):
                    continue
                info = tarfile.TarInfo(member.filename)
                info.size = member.file_size
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(archive.read(member)))
    SUBSET.write_bytes(deterministic_gzip(tar_bytes.getvalue()))
    if args.job_log:
        JOB_LOG.write_bytes(deterministic_gzip(args.job_log.read_bytes()))
    print(f"{INDEX.name}: {len(members)} members; {SUBSET.name}: {SUBSET.stat().st_size} bytes")


if __name__ == "__main__":
    main()
