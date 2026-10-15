#!/usr/bin/env bash
# Bit-exact self-reference model (TASK_SPEC 1.5): reads a memory image,
# writes the int32 logits the chip produces, little-endian row-major
# [seq_len, vocab], no padding.
set -euo pipefail
exec python3 "$(dirname "$0")/fxmodel.py" "$1" "$2"
