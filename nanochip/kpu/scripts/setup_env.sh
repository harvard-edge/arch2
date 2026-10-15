#!/usr/bin/env bash
# setup_env.sh — one-command toolchain setup for the nano-kpu flow.
#
# Conda-centric design (see README):
#   1. find conda, or bootstrap Miniconda into ~/miniconda3 (no root needed)
#   2. create a DEDICATED conda env `nano-kpu` with verilator / yosys /
#      python=3.12 / numpy from conda-forge — never installs into an
#      existing base env (shared base envs are routinely broken)
#   3. write scripts/kpu-env.sh (generated) which puts the env on PATH
#   4. download the Nangate45 liberty (pinned by commit + sha256; not
#      bundled for license reasons)
#
# Then: `source scripts/kpu-env.sh` and use make lint / make quick / make synth.
# Idempotent: existing env / tools / liberty are detected and skipped.
# Exit status: 0 if everything is usable, 1 otherwise.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_NAME="nano-kpu"
LIB_URL="https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/19c2b08c4caa7d5fae6fecd81415e808f7a92b83/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"
LIB_DEST="harness/lib/NangateOpenCellLibrary_typical.lib"
LIB_SHA256="8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"

MINICONDA_URLS=(
    "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    "https://mirrors.aliyun.com/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh"
)

FAILURES=()
pass() { printf '  [ OK ] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; FAILURES+=("$1"); }
info() { printf '  [ .. ] %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

sha256_of() {
    if have sha256sum; then sha256sum "$1" | awk '{print $1}';
    elif have shasum; then shasum -a 256 "$1" | awk '{print $1}';
    else return 1; fi
}

echo "== nano-kpu environment setup (conda-centric) =="
echo "repo root: $ROOT"
echo

# ---------------------------------------------------------------- 1. conda
echo "-- conda (existing or bootstrapped Miniconda)"
CONDA=""
if have conda; then
    CONDA="$(command -v conda)"
elif [ -x "$HOME/miniconda3/bin/conda" ]; then
    CONDA="$HOME/miniconda3/bin/conda"
fi
if [ -z "$CONDA" ]; then
    info "conda not found — bootstrapping Miniconda into ~/miniconda3"
    INST="$(mktemp /tmp/miniconda-installer.XXXXXX.sh)"
    GOT=0
    for url in "${MINICONDA_URLS[@]}"; do
        info "trying $url"
        if curl -fSL --connect-timeout 20 -o "$INST" "$url"; then GOT=1; break; fi
    done
    if [ "$GOT" = "1" ] && bash "$INST" -b -p "$HOME/miniconda3" >>/tmp/miniconda-install.log 2>&1; then
        CONDA="$HOME/miniconda3/bin/conda"
        pass "Miniconda installed to ~/miniconda3 (log: /tmp/miniconda-install.log)"
    else
        rm -f "$INST"
        fail "could not bootstrap Miniconda — install conda manually (https://docs.conda.io/en/latest/miniconda.html) and re-run"
    fi
else
    pass "conda found: $CONDA"
fi

# ---------------------------------------------------------------- 2. dedicated env
echo "-- conda env '$ENV_NAME' (verilator 5.x, yosys >= 0.64, python 3.12 + numpy)"
ENV_BIN=""
if [ -n "$CONDA" ]; then
    BASE="$("$CONDA" info --base 2>/dev/null)"
    ENV_BIN="$BASE/envs/$ENV_NAME/bin"
    if [ ! -x "$ENV_BIN/verilator" ] || [ ! -x "$ENV_BIN/yosys" ] \
        || ! "$ENV_BIN/python3" -c "import numpy" >/dev/null 2>&1; then
        info "creating/updating env '$ENV_NAME' from conda-forge (a few minutes)"
        if "$CONDA" create -y -n "$ENV_NAME" --override-channels -c conda-forge \
                verilator yosys python=3.12 numpy >>/tmp/nano-kpu-conda-create.log 2>&1 \
           || "$CONDA" install -y -n "$ENV_NAME" --override-channels -c conda-forge \
                verilator yosys python=3.12 numpy >>/tmp/nano-kpu-conda-create.log 2>&1; then
            pass "env '$ENV_NAME' ready (log: /tmp/nano-kpu-conda-create.log)"
        else
            fail "conda env creation failed — see /tmp/nano-kpu-conda-create.log"
        fi
    else
        pass "env '$ENV_NAME' already present"
    fi
fi

# checks run against the env binaries directly (PATH not required)
check_verilator() {
    [ -n "$ENV_BIN" ] && [ -x "$ENV_BIN/verilator" ] || return 1
    local out ver major
    out="$("$ENV_BIN/verilator" --version 2>/dev/null)" || return 1
    ver="$(awk '{print $2}' <<<"$out")"; major="${ver%%.*}"
    printf '  expected vs found: verilator 5.x vs %s\n' "$ver"
    [ "$major" = "5" ] && { pass "verilator $ver"; return 0; }
    fail "verilator major must be 5.x (found $ver)"
}
check_yosys() {
    [ -n "$ENV_BIN" ] && [ -x "$ENV_BIN/yosys" ] || return 1
    local out ver maj min
    out="$("$ENV_BIN/yosys" -V 2>/dev/null | head -n1)" || return 1
    ver="$(awk '{print $2}' <<<"$out")"
    maj="${ver%%.*}"; min="${ver#*.}"; min="${min%%.*}"; min="${min%%+*}"
    printf '  expected vs found: yosys >= 0.64 vs %s\n' "$ver"
    if [ "$maj" -gt 0 ] 2>/dev/null || { [ "$maj" = "0" ] && [ "$min" -ge 64 ] 2>/dev/null; }; then
        pass "yosys $ver"
    else
        fail "yosys >= 0.64 required (found $ver)"
    fi
}
check_numpy() {
    [ -n "$ENV_BIN" ] && [ -x "$ENV_BIN/python3" ] || return 1
    if "$ENV_BIN/python3" -c "import numpy" >/dev/null 2>&1; then
        pass "numpy $("$ENV_BIN/python3" -c 'import numpy; print(numpy.__version__)') for env python3"
    else
        fail "numpy not importable by env python3"
    fi
}
check_verilator || fail "verilator unavailable in env '$ENV_NAME'"
check_yosys     || fail "yosys unavailable in env '$ENV_NAME'"
check_numpy     || fail "numpy unavailable in env '$ENV_NAME'"
echo

# ---------------------------------------------------------------- 3. kpu-env.sh
if [ -n "$ENV_BIN" ] && [ -d "$ENV_BIN" ]; then
    cat > scripts/kpu-env.sh <<EOF
# generated by scripts/setup_env.sh — source to put the '$ENV_NAME'
# toolchain env on PATH (verilator / yosys / python3+numpy).
export PATH="$ENV_BIN:\$PATH"
EOF
    pass "scripts/kpu-env.sh written — run: source scripts/kpu-env.sh"
fi

# ---------------------------------------------------------------- 4. Nangate45 liberty
echo "-- Nangate45 liberty (expected: sha256 $LIB_SHA256)"
mkdir -p "$(dirname "$LIB_DEST")"
if [ -f "$LIB_DEST" ] && [ "$(sha256_of "$LIB_DEST")" = "$LIB_SHA256" ]; then
    pass "$LIB_DEST already present, sha256 matches — skipping download"
else
    if [ -f "$LIB_DEST" ]; then
        info "existing $LIB_DEST has a different sha256 ($(sha256_of "$LIB_DEST")) — re-downloading"
    else
        info "$LIB_DEST not present — downloading"
    fi
    TMP="$(mktemp "$(dirname "$LIB_DEST")/.lib_download.XXXXXX")"
    trap 'rm -f "$TMP"' EXIT
    DL_OK=0
    if have curl; then
        curl -fSL --retry 2 -o "$TMP" "$LIB_URL" && DL_OK=1 || true
    elif have wget; then
        wget -O "$TMP" "$LIB_URL" && DL_OK=1 || true
    else
        fail "neither curl nor wget available — fetch $LIB_URL manually into $LIB_DEST"
        DL_OK=2
    fi
    if [ "$DL_OK" = "0" ]; then
        rm -f "$TMP"
        fail "download failed (no network?) — check connectivity/proxy, or fetch $LIB_URL manually into $LIB_DEST"
    elif [ "$DL_OK" = "1" ]; then
        GOT="$(sha256_of "$TMP")"
        printf '  expected vs found: sha256 %s vs %s\n' "$LIB_SHA256" "$GOT"
        if [ "$GOT" = "$LIB_SHA256" ]; then
            mv -f "$TMP" "$LIB_DEST"
            pass "$LIB_DEST downloaded and verified"
        else
            rm -f "$TMP"
            fail "sha256 mismatch for downloaded liberty — deleted it (refusing drifted cell-library content)"
        fi
    fi
    trap - EXIT
fi
echo

# ---------------------------------------------------------------- summary
if [ ${#FAILURES[@]} -eq 0 ]; then
    echo "SETUP OK."
    echo "next steps: source scripts/kpu-env.sh   # put the env on PATH"
    echo "            make lint / make quick / make synth"
    exit 0
else
    echo "SETUP FAIL — ${#FAILURES[@]} problem(s):"
    for f in "${FAILURES[@]}"; do echo "  - $f"; done
    echo "after fixing, re-run: scripts/setup_env.sh"
    exit 1
fi
