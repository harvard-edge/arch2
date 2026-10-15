#!/usr/bin/env bash
# check_roms.sh — regenerate the ROM LUTs into a temp directory and
# sha256-compare them against the committed rtl/roms/*.hex files.
# Fails if any file differs, if any generated file is missing from the
# repo, if any committed file is not generated, or if the committed set
# is not exactly 15 files. Prints OK and exits 0 only on a full match.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROMS_DIR="$REPO_ROOT/rtl/roms"
EXPECTED_COUNT=15

if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x /opt/conda/bin/python ]; then
    PY=/opt/conda/bin/python
else
    PY=python3
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! "$PY" "$REPO_ROOT/scripts/gen_roms.py" "$TMP_DIR" >/dev/null; then
    echo "check_roms: generator failed" >&2
    exit 1
fi

fail=0

repo_count=$(find "$ROMS_DIR" -maxdepth 1 -name '*.hex' | wc -l)
if [ "$repo_count" -ne "$EXPECTED_COUNT" ]; then
    echo "COUNT: expected $EXPECTED_COUNT committed hex files, found $repo_count"
    fail=1
fi

# generated -> committed: presence + content
for f in "$TMP_DIR"/*.hex; do
    base="$(basename "$f")"
    if [ ! -f "$ROMS_DIR/$base" ]; then
        echo "MISSING from repo: $base"
        fail=1
        continue
    fi
    a="$(sha256sum "$ROMS_DIR/$base" | cut -d' ' -f1)"
    b="$(sha256sum "$f" | cut -d' ' -f1)"
    if [ "$a" != "$b" ]; then
        echo "DIFF: $base"
        fail=1
    fi
done

# committed -> generated: no untracked extras
for f in "$ROMS_DIR"/*.hex; do
    base="$(basename "$f")"
    if [ ! -f "$TMP_DIR/$base" ]; then
        echo "EXTRA in repo (not generated): $base"
        fail=1
    fi
done

if [ "$fail" -eq 0 ]; then
    echo "OK: all $EXPECTED_COUNT ROM files match (sha256)"
    exit 0
else
    echo "check_roms: FAILED" >&2
    exit 1
fi
