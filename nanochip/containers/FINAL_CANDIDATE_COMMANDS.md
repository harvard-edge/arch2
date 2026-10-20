# Deferred candidate build and verification commands

These commands are prepared, not executed. The prerequisite is a passing fresh
registered production-path preflight: ClockFanoutRepair, native `100um` repair,
`50um` capacitance repair, supported slew repair, and bounded antenna repair.
It must use the final authored helpers and defaults rather than importing a
previous repaired checkpoint in place of those production steps. This is a
bounded preflight, not full extracted or layout acceptance. After that proof
and owner review, freeze the implementation, course interfaces, tool compatibility,
defaults, and helper versions, then create the snapshot below.

Do not schedule a separate hours-long engineering full flow before the image
build. The installed instructor course through Lab 9 owns the sole next fresh
DRT, RCX, final DRC/LVS, and mapped-workload validation. Run all phases below
sequentially, without concurrent AMD64 training or P&R. If the preflight fails,
resolve that failure before freezing or building; if installed validation fails,
retain its receipts and diagnose that exact run before deciding on another
source revision. Full acceptance is an outcome of the installed run, not a
prerequisite for building the implementation that will be tested.
The physical, mapped-correspondence, and outer-launcher budgets below are
respectively `14400`, `3600`, and `21600` seconds. They are provisional wall
bounds, not measured fresh-run completion times or laptop promises. The
[retained calculation](../../output/nanochip/complete-core-physical-20261018/flow-runtime-analysis-1/budget-decision.json)
binds the decision to observation 3's `9136.582`-second historical stage assembly;
the new generic profile remains unmeasured. The outer allowance includes one
selected physical run, its mapped check, and `3600` seconds for other course,
learning, and collection work. Every-candidate physical studies may need a
larger explicit outer budget. In the cumulative course, Lab 9's additional
mapped check shares the extra allowance with other course work; the outer limit
does not reserve enough time for every nested limit to be exhausted in sequence.
The earlier `487.68`-second continuation stopped at a removed DRT flag before
actual detailed routing. Subsequent repair probe 5 completed in
`210.9344537500292` seconds with zero TT/SS/FF fanout, slew, and capacitance
violations, positive setup/hold slack, and independently reloaded strict antenna
counts of zero nets and pins. Its receipt and independent review are under
`output/nanochip/complete-core-physical-20261018/` in
`incremental-antenna-electrical-probe-5/` and `probe5-independent-review-1/`.
This is preliminary unextracted global-route evidence, not final acceptance.
The downstream `selected-clean-drt-continuation-1/engineering-receipt.json`
is now terminal: error, return code `1`, elapsed `3496.968823208008` seconds.
It emitted GDS and completed detailed routing with zero route DRC errors, but
post-route antenna checking found `344` violating nets and `460` pins. Extracted
STA reported `5080` slew and `1359` capacitance violations; fanout was zero.
Native setup/hold violation counts were zero, and the final explicit coverage
receipt passed all nine corners, so the recorded routed-timing check passes.
A zero-byte Magic LEF then stopped pin-property checking before final Magic/
KLayout DRC and LVS completed. GDS emission does not establish layout acceptance.
The receipt remains ineligible; `checkpoint/lineage.json` binds reused views.
This engineering continuation cannot replace fresh installed-course execution.

The separate `strict-complete-core-lef-retry-1/receipt.json` now records strict
LEF producer completion using the original geometry and writer settings:
return code `0`, a completed `117136`-byte LEF, and
`159.51865199999884` seconds elapsed under one CPU, a `7` GiB memory cap, and
a `600`-second bound. Retained cgroup peak memory was `7211315200` bytes;
memory-event `max`, `oom`, and `oom_kill` counts were zero, and final container
`OOMKilled` was false. The measured peak exceeds the earlier `6g` ceiling;
future commands below deliberately use a `7g` configured budget. This does not
prove a minimum requirement or final-profile success. The current strict wrapper covers Magic WriteLEF,
StreamOut, DRC, and SpiceExtraction; `strict-magic-native-smoke-2/` records
actual small positive producers and failed-child negative controls. The
original failed continuation remains unchanged. The isolated retry establishes
producer completion only, without DRC/LVS, antenna/electrical, or fresh-course
acceptance.

The later `strict-layout-tail-continuation-2/engineering-receipt.json` records
completed layout checks and LVS for its reused layout. Its inherited antenna
and electrical failures remain binding. Those engineering results do not
establish acceptance of the new production profile or the installed course.
Fresh extracted physical checks, mapped correspondence, and complete installed
acceptance remain pending; fresh completion cost is unknown.
A nonfinal reused-binary nominal mapped
checkpoint passed in `358.534440245` seconds after an earlier `201.30`-second
compile measurement; this does not measure the final fresh multi-profile run. Confirm the accepted DRT/STA and mapped-compiler profiles and
the budgets before execution; do not run them blindly or silently relax a
measured budget.

## Build the frozen ARM64 candidate

Before freezing, make packaged capability statements independent of a
particular run's outcome. `doctor` describes implemented interfaces and tool
availability; only candidate-linked receipts establish physical acceptance.
The packaged course guide must describe that distinction without a global
"still needs its first run" status that would require changing package bytes
after success. Freeze those statements with the code. Record resulting image
identity, measured runtime, and acceptance in retained output reports and the
external delivery documentation, which are not installed runtime inputs.

Use a fresh Bash shell, retaining the same shell variables across these blocks.
Start from the repository root, only after the owners authorize the source freeze.
The snapshot build helper needs Python 3.11 or newer; this does not change the
installed package's Python requirement. Creation refuses an existing output
root and any detected source drift. Verification rejects added context files,
changed bytes or modes, and inputs outside the declared package/build closure.

```bash
set -euo pipefail
unset PYTHONPATH PYTHONHOME
python3 nanochip/containers/snapshot_runtime.py create --source nanochip \
  --output output/nanochip/full-final-candidate-01
nanochip_snapshot="$PWD/output/nanochip/full-final-candidate-01/snapshot/nanochip"
nanochip_manifest="$PWD/output/nanochip/full-final-candidate-01/snapshot.json"
python3 "$nanochip_snapshot/containers/snapshot_runtime.py" verify \
  --source "$nanochip_snapshot" --manifest "$nanochip_manifest"
nanochip_runroot="$PWD/output/nanochip/full-final-candidate-01/validation"
mkdir "$nanochip_runroot"
nanochip_manifest_sha=$(python3 -c 'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$nanochip_manifest")
docker build --platform linux/arm64 --target full --progress plain \
  --label "org.nanochip.source-manifest-sha256=$nanochip_manifest_sha" \
  -f "$nanochip_snapshot/containers/FullDockerfile" \
  -t nanochip-local:full-candidate-final-arm64-0.1.0a0 \
  "$nanochip_snapshot" >"$nanochip_runroot/build.log" 2>&1
nanochip_image_id=$(docker image inspect \
  nanochip-local:full-candidate-final-arm64-0.1.0a0 --format '{{.Id}}')
docker image inspect "$nanochip_image_id" >"$nanochip_runroot/image.json"
```

The recipe's one-thread environment applies during dependency verification.
This BuildKit command does not impose a build-wide CPU or RAM quota; schedule
it separately from the physical run. Every validation run below has an explicit
two-CPU/`7g` limit, offline execution, mapped UID/GID, one persistent output mount,
and a private cgroup. `7g` accommodates the measured isolated LEF peak; it is a
configured budget, not a proven minimum or final-profile success. Current
free VM memory/headroom and final minimum guidance remain unmeasured pending
complete-run peaks.

## Build and install the host launcher from that same snapshot

Use the existing local build tools; these commands download nothing and stop
if setuptools or wheel is unavailable. Build from a disposable copy so backend
metadata never changes the frozen Docker context. Retain the wheel, SHA-256,
build-tool versions, and installation log. The launcher venv has no system-site
packages or learning extra. Its isolated interpreter is used explicitly below
from the validation directory, rather than an ambient `nanochip` command.

```bash
nanochip_build_python=$(command -v python3)
nanochip_host_root="$nanochip_runroot/host-launcher"
mkdir "$nanochip_host_root"
env -u PYTHONPATH -u PYTHONHOME "$nanochip_build_python" - \
  "$nanochip_snapshot" "$nanochip_manifest" "$nanochip_host_root" \
  >"$nanochip_host_root/build.log" 2>&1 <<'PY'
from pathlib import Path
from importlib import metadata
import hashlib, json, os, shutil, sys, zipfile
source, manifest_path, root = [Path(p).resolve() for p in sys.argv[1:]]
os.chdir(root)
versions = {name: metadata.version(name) for name in ("setuptools", "wheel", "pip")}
assert int(versions["setuptools"].split(".")[0]) >= 77
(root / "build-tools.json").write_text(json.dumps({"python": sys.version, "tools": versions}, indent=2) + "\n")
stage = root / "build-source/nanochip"
shutil.copytree(source, stage)
wheels = root / "wheels"
wheels.mkdir()
os.chdir(stage)
from setuptools import build_meta
wheel = wheels / build_meta.build_wheel(str(wheels))
manifest = json.loads(manifest_path.read_text())
expected = {name: manifest["files"][name] for name in manifest["wheel_files"]}
with zipfile.ZipFile(wheel) as archive:
    actual = {name.removeprefix("nanochip/"): hashlib.sha256(archive.read(name)).hexdigest()
              for name in archive.namelist() if name.startswith("nanochip/") and not name.endswith("/")}
assert actual == expected, "Host wheel differs from the frozen source closure"
identity = {"wheel": str(wheel), "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
(root / "wheel-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
PY
python3 "$nanochip_snapshot/containers/snapshot_runtime.py" verify \
  --source "$nanochip_snapshot" --manifest "$nanochip_manifest"
nanochip_host_wheel=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wheel"])' \
  "$nanochip_host_root/wheel-identity.json")
env -u PYTHONPATH -u PYTHONHOME "$nanochip_build_python" -I -m venv "$nanochip_host_root/venv"
nanochip_host_python="$nanochip_host_root/venv/bin/python"
"$nanochip_host_python" -I -m pip install --no-index --no-deps --no-compile \
  "$nanochip_host_wheel" >"$nanochip_host_root/install.log" 2>&1
(
  cd "$nanochip_host_root"
  "$nanochip_host_python" -I -B - "$nanochip_manifest" <<'PY'
from pathlib import Path
import hashlib, importlib.util, json, nanochip, sys
assert sys.prefix != sys.base_prefix
assert importlib.util.find_spec("torch") is None
assert importlib.util.find_spec("numpy") is None
package = Path(nanochip.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve())
manifest = json.loads(Path(sys.argv[1]).read_text())
expected = {name: manifest["files"][name] for name in manifest["wheel_files"]}
actual = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in package.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
assert actual == expected, "Host installation differs from the frozen source closure"
print(json.dumps({"isolated_host_package": str(package), "version": nanochip.__version__,
                  "python": sys.version, "executable": sys.executable}))
PY
) >"$nanochip_host_root/installed-identity.json"
"$nanochip_host_python" -I -B -m nanochip.laboratory --version \
  >"$nanochip_host_root/version.txt"
cd "$nanochip_host_root"
```

## Run installed checks with retained peak memory

Define this host shell function in the same shell. It preserves positional
arguments, initializes the pinned tool profile, and emits a distinct cgroup
resource receipt per container. Each command uses the resolved immutable image
ID rather than the mutable candidate tag.

```bash
nanochip_run() {
  local nanochip_resource_name="$1"
  shift
  docker run --rm --pull=never --network none --cpus 2 --memory 7g \
    --cgroupns private --user "$(id -u):$(id -g)" \
    --env "NANOCHIP_RUNTIME_IMAGE_ID=$nanochip_image_id" \
    --mount "type=bind,src=$nanochip_runroot,dst=/work" \
    --entrypoint /bin/bash "$nanochip_image_id" -c \
    'source /etc/profile >/dev/null; exec /opt/nanochip-venv/bin/python -I -B /opt/nanochip-runtime/capture_resources.py "$@"' \
    nanochip-verify "/work/$nanochip_resource_name" -- \
    /opt/nanochip-venv/bin/python -I -B "$@"
}

nanochip_run provenance-resources.json -c \
  'import hashlib,json,pathlib,nanochip
p=pathlib.Path("/opt/nanochip-runtime")
package=pathlib.Path(nanochip.__file__).resolve().parent
helpers={"containers/"+n:p/n for n in ("capture_resources.py","validate_course_student_extension.py","validate_course_extension_capstone.py","select_full_runtime.py","verify_full_runtime.py")}
helpers["containers/full-entrypoint.sh"]=pathlib.Path("/usr/local/bin/nanochip-full-entrypoint")
print(json.dumps({"platform":json.loads((p/"platform.json").read_text()),"environment":json.loads((p/"environment.json").read_text()),"package_files":{str(f.relative_to(package)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(package.rglob("*")) if f.is_file() and "__pycache__" not in f.parts and f.suffix!=".pyc"},"helper_hashes":{n:hashlib.sha256(f.read_bytes()).hexdigest() for n,f in helpers.items()}},indent=2))' \
  >"$nanochip_runroot/runtime-provenance.json" 2>"$nanochip_runroot/provenance.log"

python3 - "$nanochip_manifest" "$nanochip_runroot/runtime-provenance.json" <<'PY'
import json, sys
from pathlib import Path
manifest, actual = [json.loads(Path(p).read_text()) for p in sys.argv[1:]]
expected = {name: manifest["files"][name] for name in manifest["wheel_files"]}
assert actual["package_files"] == expected, "Installed package differs from the frozen source closure"
assert actual["environment"]["package"]["files"] == expected, "Build-time installed package differs"
for name, digest in actual["helper_hashes"].items():
    assert manifest["files"][name] == digest, name
for name, record in actual["platform"]["effective_files"].items():
    selected = Path(record["source"]).name
    assert record["sha256"] == manifest["files"]["containers/" + selected], name
print("Frozen package, default-profile source, runtime helpers, and selected lock identities verified")
PY

nanochip_run doctor-resources.json -m nanochip.laboratory doctor \
  >"$nanochip_runroot/doctor.json" 2>"$nanochip_runroot/doctor.log"
nanochip_run system-resources.json -m nanochip.laboratory system \
  --functional-only --output /work/system --cores 2 --timeout 180 \
  --correspondence-timeout 3600 \
  >"$nanochip_runroot/system.log" 2>&1
nanochip_run core-feedback-resources.json -m nanochip.laboratory core-feedback \
  --output /work/core-feedback --timeout 180 \
  >"$nanochip_runroot/core-feedback.log" 2>&1
nanochip_run init-resources.json -m nanochip.laboratory course init \
  /work/instructor --mode instructor >"$nanochip_runroot/instructor-init.log" 2>&1
"$nanochip_host_python" -I -B -m nanochip.laboratory launch \
  --image "$nanochip_image_id" --workspace "$nanochip_runroot" \
  --output "$nanochip_runroot/launches/instructor" \
  --cores 2 --memory 7g --timeout 21600 -- course run-all \
  --workspace /work/instructor --mode instructor --through 9 \
  --timeout-s 180 --physical-timeout-s 14400 \
  --cores 2 --physical-mode native --correspondence-timeout-s 3600 \
  >"$nanochip_runroot/instructor-launch.json" 2>"$nanochip_runroot/instructor-launch.log"
nanochip_run extension-resources.json \
  /opt/nanochip-runtime/validate_course_student_extension.py /work/student-extension \
  >"$nanochip_runroot/extension.log" 2>&1
nanochip_run extension6-resources.json -m nanochip.laboratory course run \
  --workspace /work/student-extension --lab 6 --mode instructor \
  --cores 2 --physical-mode native --correspondence-timeout-s 3600 \
  >"$nanochip_runroot/extension6.log" 2>&1
nanochip_run extension7-resources.json -m nanochip.laboratory course run \
  --workspace /work/student-extension --lab 7 --mode instructor \
  --cores 2 --physical-mode native --correspondence-timeout-s 3600 \
  >"$nanochip_runroot/extension7.log" 2>&1
nanochip_run sidecar-resources.json \
  /opt/nanochip-runtime/validate_course_extension_capstone.py \
  /work/student-extension /work/instructor /work/student-capstone \
  --cores 2 --physical-mode native --check-timeout 180 --correspondence-timeout 3600 \
  >"$nanochip_runroot/sidecar.log" 2>&1
```

Stop on any nonzero status and retain that phase's files; run commands one at a
time so the status is reviewed before a dependent phase. Verify image/source
manifest identity, every installed package/helper hash, named acceptance checks,
the core-feedback authored numerical failure, repaired next action and hidden-feedback
control, all nine instructor progress records, sidecar exact RTL/config/receipt linkage,
fresh mapped workload, file ownership, and resource counters. A zero process
exit alone is insufficient. The sidecar reuses P&R only; a winning design mismatch
must remain unresolved. Measure each phase's external wall time separately from
its internal receipt timing and cgroup peak.

The instructor phase uses the installed host launcher to enforce the `21600`
outer bound. Its tool log, launch receipt, and cgroup resource receipt are under
`launches/instructor/`; all other per-phase resource paths above remain unchanged.
Lab 8 owns the fresh full physical implementation and its mapped check. Lab 9
binds that exact Lab 8 receipt/core/configuration to the selected winner and
runs fresh mapped correspondence only when RTL and configuration match; it
does not rerun P&R. The extension sidecar follows the same retained-layout rule.
Do not add a default `system` physical run or every-candidate P&R to this
sequence; the earlier `system --functional-only` phase intentionally excludes it.

Run the final-image interruption/process-lifecycle smoke separately using a
bounded stub. Existing fixture evidence is described in FULL_RUNTIME.md; it does
not substitute for validating the final installed flow code or establish GDS
restart/resume.

For AMD64, schedule a separate candidate with the same frozen snapshot
and `FullDockerfile`, `--platform linux/amd64`, a distinct candidate tag/run root,
and the unchanged functional/course protocol. Record emulation explicitly on
this ARM64 host. Do not infer native AMD64 performance from emulated results.

## Exercise the installed persistent-workspace launcher

Run these additional lightweight phases with the same final immutable image.
The fixture edits only a new output workspace, never the source snapshot. Its
Lab 1 hook deliberately delegates to the installed reference splitter to test
persistence and source identity; this is not a student-design or learning claim.
Each host launch uses the isolated venv installed above from the same frozen
snapshot as the image. `-I` ignores source `PYTHONPATH` and user-site packages.
The later Lab 2 instructor phase checks cumulative reuse of Lab 1.

```bash
nanochip_student_workspace="$nanochip_runroot/persistent-student-work"
mkdir "$nanochip_student_workspace"
"$nanochip_host_python" -I -B -m nanochip.laboratory launch --image "$nanochip_image_id" \
  --workspace "$nanochip_student_workspace" \
  --output "$nanochip_student_workspace/launches/init" \
  --cores 2 --memory 7g --timeout 60 -- \
  course init /work/course --mode student \
  >"$nanochip_runroot/persistent-init.json"

python3 - "$nanochip_student_workspace" <<'PY'
from pathlib import Path
import hashlib, json, sys
workspace = Path(sys.argv[1])
hook = workspace / "course/labs/lab01_data.py"
hook.write_text('"""Host-edited engineering fixture; uses the installed group splitter."""\n'
    'from nanochip.laboratory.course.components import split_by_group\n\n'
    'def split_records(records, *, seed, fractions=None):\n'
    '    return split_by_group(records, seed=seed, fractions=fractions)\n')
expected = {"hook_sha256": hashlib.sha256(hook.read_bytes()).hexdigest(),
    "init_receipts": {name: hashlib.sha256((workspace / "launches/init" / name).read_bytes()).hexdigest()
        for name in ("launch.json", "container-resources.json")}}
(workspace / "expected-persistence.json").write_text(json.dumps(expected, indent=2) + "\n")
PY

"$nanochip_host_python" -I -B -m nanochip.laboratory launch --image "$nanochip_image_id" \
  --workspace "$nanochip_student_workspace" \
  --output "$nanochip_student_workspace/launches/lab01" \
  --cores 2 --memory 7g --timeout 240 -- \
  course run --workspace /work/course --lab 1 --mode student \
  --cores 2 --physical-mode native --correspondence-timeout-s 3600 \
  >"$nanochip_runroot/persistent-lab01.json"
"$nanochip_host_python" -I -B -m nanochip.laboratory launch --image "$nanochip_image_id" \
  --workspace "$nanochip_student_workspace" \
  --output "$nanochip_student_workspace/launches/lab02" \
  --cores 2 --memory 7g --timeout 240 -- \
  course run --workspace /work/course --lab 2 --mode instructor \
  --cores 2 --physical-mode native --correspondence-timeout-s 3600 \
  >"$nanochip_runroot/persistent-lab02.json"

python3 - "$nanochip_student_workspace" "$nanochip_image_id" <<'PY'
from pathlib import Path
import hashlib, json, sys
workspace = Path(sys.argv[1]).resolve()
expected = json.loads((workspace / "expected-persistence.json").read_text())
hook = workspace / "course/labs/lab01_data.py"
assert hashlib.sha256(hook.read_bytes()).hexdigest() == expected["hook_sha256"]
events = [json.loads(line) for line in (workspace / "course/progress.jsonl").read_text().splitlines() if line]
latest = {row["lab"]: row for row in events}
assert latest[1]["status"] == latest[2]["status"] == "complete"
assert latest[1]["mode"] == "student"
assert latest[1]["implementation"]["sha256"] == expected["hook_sha256"]
for name, digest in expected["init_receipts"].items():
    assert hashlib.sha256((workspace / "launches/init" / name).read_bytes()).hexdigest() == digest
for phase in ("init", "lab01", "lab02"):
    receipt_root = workspace / "launches" / phase
    receipt = json.loads((receipt_root / "launch.json").read_text())
    assert receipt["ok"] and receipt["image"]["id"] == sys.argv[2]
    assert receipt["workspace_root"] == str(workspace)
    assert receipt["command"].count("--mount") == 1
    assert receipt["container_resource_path"] == f"/work/launches/{phase}/container-resources.json"
    resource = json.loads((receipt_root / "container-resources.json").read_text())
    assert resource["resources"]["peak_status"] == "available"
assert not (workspace / "container-resources.json").exists()
print("Persistent workspace, edited hook, cumulative lab, and separate resource receipts verified")
PY
```

Leave architect disposition pending. Retain Lab 9's immutable pending-review
template; a human completes a separate copy outside the attempt. Do not infer
approval from process status or mutate course progress to simulate review.
