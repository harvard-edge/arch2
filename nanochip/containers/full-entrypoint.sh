#!/bin/bash
set -e
# Use the pinned bundle's official tool setup without its GUI startup process.
source /etc/profile >/dev/null
if [[ "${NANOCHIP_CAPTURE_RESOURCES:-}" == "1" ]]; then
    exec /opt/nanochip-venv/bin/python -I -B /opt/nanochip-runtime/capture_resources.py \
        "${NANOCHIP_RESOURCE_RECEIPT:-/work/container-resources.json}" -- \
        /opt/nanochip-venv/bin/python -I -B -m nanochip.laboratory "$@"
fi
exec /opt/nanochip-venv/bin/python -I -B -m nanochip.laboratory "$@"
