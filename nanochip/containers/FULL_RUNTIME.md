# Full native runtime

The full runtime combines the pinned physical tool bundle with CPU learning
in one container. The tested image uses ARM64. Physical commands execute inside that container;
neither Docker-in-Docker nor a host Docker socket is used. The smaller,
previously validated `nanochip-local:0.1.0a0` image remains available separately.

The dependency stage and a source-snapshot candidate image are built and
verified. The installed candidate completed the connected functional system
experiment and instructor Labs 1–7 in one offline container. Final full-system
physical validation, Lab 9 composition, and the final source freeze remain
separate acceptance steps.

## Build and launch

Run the source build after the component interfaces and physical profile are frozen:

```bash
docker build --target full --progress plain \
  -f nanochip/containers/FullDockerfile \
  -t nanochip-local:full-0.1.0a0 nanochip
```

The same recipe uses BuildKit's `TARGETARCH`: `arm64` selects the original
ARM64 lock/constraints; `amd64` selects the independently verified AMD64 pair.
Set `docker build --platform linux/amd64 ...` for the latter. Selection checks
the executing base machine and fails before installation for unsupported or
mismatched architectures. The base remains the pinned multiarchitecture index.
Both source lock pairs remain under `/opt/nanochip-runtime/locks/`; selected
effective files are retained as `requirements-full.lock` and
`full-runtime-constraints.txt`. `platform.json` records the target, observed
machine, pinned index/expected platform child, source lock names, and hashes.
This architecture-aware source recipe has focused selection tests; final source
images still need their scheduled per-platform builds and execution proof.

The host-side launcher uses only Python's standard library and an existing
Docker engine. Its CLI handler is `nanochip.laboratory.launch.main(argv)`;
the root CLI forwards `nanochip launch` arguments to it. For example:

```bash
nanochip launch --output output/nanochip/full-doctor-first \
  --image nanochip-local:full-candidate-0.1.0a0 \
  --cores 2 --memory 7g --timeout 60 -- doctor
```

Each launch requires a new output receipt directory. With `--workspace`, the
workspace must already exist and the receipt directory must resolve inside it.
That workspace is the sole host mount, at `/work`; course files and checkpoints
therefore persist across launches. Paths and symlink containment are validated
before creating receipts. Existing evidence is never reused as a new output.
Without `--workspace`, the new output directory itself remains the sole `/work`
mount, preserving the earlier behavior.

After the updated full image is validated, the student workflow is:

```bash
mkdir student-work
nanochip launch --workspace student-work --output student-work/launches/init --timeout 60 -- \
  course init /work/course --mode student
```

Implement the student hook in `student-work/course/labs/lab01_data.py`, then run
it against the same persistent course workspace with a fresh launch receipt:

```bash
nanochip launch --workspace student-work --output student-work/launches/lab01 --timeout 240 -- \
  course run --workspace /work/course --lab 1 --mode student \
  --cores 2 --physical-mode native
```

The launcher resolves the cached tag to its immutable image ID before execution,
validates the full-runtime and physical-base labels, disables pulling and
networking, maps the invoking UID/GID, and records `launch.json`, `image.json`,
and `container.log` inside each fresh receipt directory. `workspace_root` and
`workspace_mapping` identify the resolved host mount; `output_container_path`
and `container_resource_path` record each receipt's container location. Timeout
removes the named container and terminates the host client process group. Host Ctrl-C first sends SIGINT to the owned container and waits up to
five seconds; if it remains active or signaling fails, forced cleanup follows.
The launcher records graceful versus forced cleanup and re-raises the original
interrupt. Normal exit and timeout policy are unchanged. A zero process exit is distinct from acceptance of a design.

For the next source-frozen image, the launcher also selects a private cgroup
namespace and requests `container-resources.json` inside that launch's receipt
directory. It passes the computed `/work/...` destination through the single
literal `NANOCHIP_RESOURCE_RECEIPT` environment value; the entrypoint preserves
it as one quoted argument. The default without a persistent workspace remains
`/work/container-resources.json`. An opt-in
supervisor runs the same Nanochip argument vector, forwards SIGINT/SIGTERM/SIGHUP,
and preserves the child's exit status. After the child exits, it reads only
its own cgroup counters: memory peak/current/limit/events, CPU counters/quota,
and peak PID count where available. The reported memory includes the small
supervisor and all tool descendants; it is cgroup usage, including accounted
file cache, rather than Python heap size. Capture failures do not change the
child's exit status. Unreadable counters are explicit, and a killed supervisor
or older image can leave no receipt; the host launch receipt then records
`container_resources.status = "unavailable"`. No peak is inferred from a limit.
The helper passed a small Linux cgroup-v2 smoke test using a bind mount and the
unchanged candidate; its integration into a rebuilt final image is pending.

The Python API is `launch(LaunchRequest(output, command, image=..., cores=2,
memory="7g", timeout_s=21600, uid=None, gid=None, workspace=None))`. CLI arguments form a tuple;
they are passed directly to the installed Nanochip entrypoint without shell
interpolation. Receipts report host/engine architecture, available output disk,
engine RAM, requested memory, and cached launch timing. The memory limit is
configurable; a request above engine RAM is a limit, not additional capacity.
See [platform and resource evidence](PLATFORMS.md) for the tested boundary. The current
launcher default and new examples use a `7g` configured budget. The isolated
complete-core LEF retry measured `7,211,315,200` bytes of cgroup peak memory
under a `7` GiB (`7,516,192,768`-byte) cap, with no limit or OOM events; the
previous `6g` ceiling cannot accommodate that observed run. Evidence is
`output/nanochip/complete-core-physical-20261018/strict-complete-core-lef-retry-1/receipt.json`.
This is producer-completion evidence, not a proven minimum or final-profile
success. Currently free VM memory and headroom were not measured. Final resource
guidance remains pending complete-run peak measurements. Historical `6g` and
`8g` receipts retain the limits actually requested. The updated final image
remains unbuilt and unvalidated.

The provisional whole complete-core physical budget is `14400` seconds;
mapped correspondence remains a separate `3600` seconds. The outer launcher
defaults to `21600` seconds: one selected physical run, one mapped check, and
`3600` seconds for course, learning, and collection. The
[retained calculation](../../output/nanochip/complete-core-physical-20261018/flow-runtime-analysis-1/budget-decision.json)
uses the `9136.582`-second assembly of historical nonoverlapping stages, not a
fresh measurement of the new generic repair profile. These budgets are not
completion promises. Every-candidate physical studies may need a larger
explicit total. For the future validated full image, a selected-design launch is:

```bash
nanochip launch --output output/nanochip/full-system-first \
  --image nanochip-local:full-0.1.0a0 --cores 2 --memory 7g --timeout 21600 -- \
  system --output /work/system --physical-timeout 14400 --correspondence-timeout 3600
```

## Fixed dependencies and provenance

The base is
`hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38`.
It supplies Python `3.12.3`, LibreLane `2.4.12`, the physical tools, NumPy
`2.4.2`, and SKY130A revision `54435919abffb937387ec956209f9cf5fd2dfbee`.

The learning overlay adds CPU Torch `2.11.0+cpu` and setuptools `81.0.0` in a
virtual environment that inherits the pinned system packages. The setuptools
overlay satisfies Torch's `<82` requirement without replacing the bundle's
system installation. The environment inherits pip `26.0.1` and wheel `0.46.3`.
Every newly downloaded wheel is SHA-256 locked in `requirements-full.lock`.
Inherited direct and transitive package versions are fixed by the base image
and checked against `full-runtime-constraints.txt`; installation uses `--no-deps`.
The verifier checks Torch's active dependency requirements, NumPy conversion,
an optimizer initialization, one-thread execution, the PDK identity, and tool
versions. The final source stage also records installed package asset hashes.

The entrypoint loads the bundle's official tool profile while preserving its
Python tool paths. It starts Nanochip rather than the upstream GUI. Runtime
defaults select native physical execution and one Torch/OpenMP thread. A stable
`USER` and a Torch-specific cache directory support arbitrary mapped UIDs; the
base's `HOME` setting is preserved.

`/opt/nanochip-runtime/environment.json` records effective versions, distribution
locations, tool identities, declared package licenses, and installed source
hashes. Native physical receipts retain the inherited tool-bundle identity;
the launcher also supplies `NANOCHIP_RUNTIME_IMAGE_ID` for the exact full image.

## Candidate functional validation

The local candidate tag is `nanochip-local:full-candidate-0.1.0a0`, with identity
`sha256:1679d80d9d2501f048d0fa6eb920c62e0aa21c3fcd294af94a88ac81d4576bc6`.
It was built from the verified snapshot under
`output/nanochip/full-candidate-01/snapshot/`; its source manifest SHA-256 is
`afe8b6c8464948bc34fe2928a679ee6128d802d356c60a5fb6e358cd12203d9c`.
The source-stage build took `5.112` seconds using the prepared dependency layer.
Docker daemon disk accounting reports `21,578,251,573` bytes (`20.096` GiB)
for this candidate, including shared layers. Its `16,990,126,080` shared bytes
are shared with other cached images; its unique contribution in that cache is
`4,588,125,493` bytes. The earlier raw image-inspect `Size` field of
`4,581,955,589` bytes does not represent this daemon's full image footprint.
See [the storage audit](PLATFORMS.md) before planning installation space.

The actual host launcher and `doctor` passed with the installed candidate.
One subsequent outer container, with networking disabled, two CPUs, an `8g`
memory limit, and UID/GID mapping, sequentially completed:

- `system --functional-only --output /work/system` in `121.825` seconds.
- `course init /work/course --mode instructor` in `0.074` seconds.
- `course run-all --workspace /work/course --mode instructor --through 7 --timeout-s 180`
  in `28.614` seconds.

All commands exited zero; outer wall time was `150.778` seconds. All seven course
progress records are complete. System training receipts retain all requested
updates at one thread. Before execution, the runtime verified its installed
source/assets and the frozen KPU manifest against the source snapshot. The
functional comparison selected the same best action across its learned and
conventional arms; this run does not establish a learned design advantage.
No physical flow was requested. Retained reports and exact commands are in
`output/nanochip/full-candidate-01/validation/`.

The candidate tag is separate from the final full-runtime tag. A later source
freeze and complete-system/course proof require their own image identity and
fresh receipts.

## Measured preparation

The verified dependency image is
`sha256:4ae42a229214a2aa1c17a71b7c180607ccd91731b5bc86d74b96dedda3e890a7`.
Daemon disk accounting reports `21,570,270,520` bytes (`20.089` GiB), including
shared layers. Shared images and build caches must be accounted for separately;
the raw image-inspect size is retained in preparation evidence, not used as an
installation-space requirement. The separate wheel download retained
`149,190,418` bytes and took `3.409` seconds. The latest dependency-stage build
took `24.352` seconds. These are preparation costs, separate from experiments.

Evidence is under `output/nanochip/full-container-dependencies.*`,
`full-dependencies-build*`, `full-dependency-checks.json`, and
`full-dependency-licenses.json`. The pinned upstream bundle already reports
dependency conflicts in optional packages; the overlay adds none in the
recorded comparison. Selected tool and course execution still need their own
checks. Execution is validated only as Linux ARM64 containers on macOS ARM64
with Docker Desktop. Native Linux hosts, AMD64 Nanochip execution, and Windows hosts
have not been validated. Separate AMD64 dependency checks under emulation
passed as documented below. The multiarchitecture upstream index is not execution
evidence for those platforms.

The base image's OCI metadata declares Apache-2.0 for IIC-OSIC-TOOLS. Individual
tools and PDK components retain their component licenses. Installed metadata
records Torch's BSD-3-Clause, setuptools' MIT, LibreLane's Apache-2.0, and NumPy's
combined license expression. The existing package retains the frozen KPU
license and notices. Images and packages remain local; no registry publication
or package-name ownership is claimed.

## Separate AMD64 dependency preparation

The separate tag `nanochip-local:full-dependencies-amd64-0.1.0a0` identifies
`sha256:ce2fc423abbff913875c7ada20972bf97028d78b0bfbce1044e92596e0d5cf3b`.
It uses the pinned AMD64 physical-bundle child
`sha256:872e7e57e31966dead2ae6ed31f6277fb9ec92f20cc66afbb3f39f57b2b1e708`,
`requirements-full-amd64.lock`, and independently inspected
`full-runtime-constraints-amd64.txt`. The ARM64 lock and successful images remain
unchanged. No Nanochip source is installed in this dependency-only image.

The pull took `118.715` seconds, CPU Torch wheel download `1.828` seconds,
and offline dependency build `22.701` seconds. The retained build command was:

```bash
docker build --platform linux/amd64 --network none --progress plain \
  -f nanochip/containers/AMD64DependenciesDockerfile \
  -t nanochip-local:full-dependencies-amd64-0.1.0a0 \
  output/nanochip/amd64-dependency-prep-20261018/build-context
```

That retained context contains the verifier, independent locks, and verified
local wheelhouse. A subsequent offline check under AMD64 emulation on ARM64,
with one CPU, `1g`, mapped UID/GID, and private cgroup, passed in `6.094` seconds.
It verified Python `3.12.3`, Torch `2.11.0+cpu`, NumPy `2.4.2`, transitive pins,
NumPy conversion, optimizer initialization, one thread, PDK, and tool versions.
Peak cgroup memory was `389,316,608` bytes; no OOM/limit event was recorded.
These are dependency checks, not model training, course, or physical execution.

Daemon disk accounting reports `23,088,412,218` bytes (`21.503` GiB), including
shared layers, for this image. Declared licenses are retained for Torch
(BSD-3-Clause), setuptools (MIT), LibreLane (Apache-2.0), and NumPy's combined
license expression. Evidence is under
`output/nanochip/amd64-dependency-prep-20261018/`, including source/wheel hashes,
image/platform identity, commands, environment, and cgroup counters. See
[PLATFORMS.md](PLATFORMS.md) for storage accounting and limits. The AMD64 source
build and full functional/course validation remain deferred until scheduling
and final source/profile freeze; emulated checks do not establish native AMD64
performance.

## Installed student-hook and interruption validation

The source-frozen image will retain `validate_course_student_extension.py`
under `/opt/nanochip-runtime/`. The previously proven host-helper snapshot has
SHA-256 `bcb99a1454af9d7daf70dff067a1e8e5f8eda8d2e831a1969da496c6652b140a`;
the refined current source has SHA-256
`f14dda952da5ca940540ddb606170b72e240d416289834c63a9641502e505181`.
The refinement uses a complete attributed source sentence when it fits the
existing context budget and records its workspace-defined retrieval policy.
It has not yet repeated the full helper run; the old
host receipt does not prove this version. Final source freeze and installed
execution must record and verify the finalized helper hash.
The helper initializes a fresh student workspace, runs the student data hook,
bounded instructor prerequisites, then compares reference and student retrieval
through the saved model and fresh shared complete-core harness. Its host proof
is retained; the final installed-image execution is pending. It demonstrates
component composition and lineage rather than a learning benefit.

Use the final verified image identity and a new mount root. The fixed bash
entrypoint initializes the tool profile, then the resource supervisor runs the
installed helper without shell interpolation of its argument vector:

```bash
mkdir output/nanochip/final-installed-extension
docker run --rm --pull=never --network none --cpus 1 --memory 7g \
  --cgroupns private --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD/output/nanochip/final-installed-extension,dst=/work" \
  --entrypoint /bin/bash nanochip-local:full-0.1.0a0 -c \
  'source /etc/profile >/dev/null; exec /opt/nanochip-venv/bin/python -I -B /opt/nanochip-runtime/capture_resources.py /work/container-resources.json -- /opt/nanochip-venv/bin/python -I -B /opt/nanochip-runtime/validate_course_student_extension.py /work/course'
```

The physical adapter, when it catches SIGINT, terminates its owned tool
sessions/descendants, retains an interrupted partial receipt, and re-raises.
Forced outer cleanup can prevent inner receipts from being flushed; absent
resource/physical receipts must remain unavailable. This establishes process
cleanup behavior, not GDS checkpoint restart or training/course resume.
Final installed validation must include a bounded physical-process stub under
SIGINT as well as the normal functional/course path; it must not report the
stub as physical acceptance.

A retained lifecycle-only container fixture exercised this path with the current
physical `_execute` source and owned child/grandchild processes, one CPU and
`256m`, networking disabled. Host Ctrl-C preserved SIGINT exit semantics in both
trials. The responsive case exited after `0.684` seconds of interruption handling,
retained interrupted stub and resource receipts, and verified neither tool was
live. The unresponsive case exited after `5.366` seconds with forced cleanup;
resource capture remained unavailable. Neither named container remained.
Evidence, source hashes, both initial BuildKit lookup failures, corrected cached-tag
fixture build, commands, and receipts are retained under
`output/nanochip/launcher-interrupt-smoke-20261018/`. This tiny fixture is separate
from the source-frozen full image and establishes no EDA acceptance or restart
capability; the installed final-image lifecycle check remains pending.

The same recipe also retains `validate_course_extension_capstone.py` under
`/opt/nanochip-runtime/`. Its current preparation hash is
`f04216b78fcfe8be61c6e38d2567eb40e4070a1f3a2d59bdfb66f5d5e8fb15f7`;
source/profile freeze and installed execution are pending. After the instructor
workspace completes Labs 1–9 and the extension workspace completes Labs 1–7,
its planned inner command is:

```bash
/opt/nanochip-venv/bin/python -I -B \
  /opt/nanochip-runtime/validate_course_extension_capstone.py \
  /work/student-extension /work/instructor /work/student-capstone \
  --cores 2 --physical-mode native \
  --check-timeout 180 --correspondence-timeout 3600
```

Run this through the same initialized tool profile and resource supervisor,
using a distinct resource receipt path. The new sidecar directory must be
outside both workspaces. The helper verifies source/event/artifact identities
before reusing the instructor Lab 8 P&R result. Fresh mapped-netlist workload
correspondence is conditional on an exact winning RTL/configuration match;
a mismatch is not accepted by copying another candidate's physical result.
It does not rerun P&R or alter either workspace's progress log. CLI mode/path
fixes and STA compatibility verification remain gating work for final execution.

[Deferred candidate commands](FINAL_CANDIDATE_COMMANDS.md) collect the planned
frozen-snapshot build, immutable image resolution, offline sequential instructor
and extension checks, helper provenance, and per-phase cgroup receipts. They
have not been executed and remain gated by source/profile freeze.

Prepared correspondence commands now declare a separate `3600`-second wall
budget with two cores and native mode. This is an engineering bound; mapped
compilation and complete workload time still require actual measurements.

## Retained source packaging audit

The current delivery audit adds `containers/snapshot_runtime.py` with explicit
`inventory`, `create`, and `verify` commands. After the component owners freeze
the source, the [candidate protocol](FINAL_CANDIDATE_COMMANDS.md) creates a fresh
minimal Docker context and verifies it before building. The manifest binds the
declared wheel files, every host Docker `COPY` input, recipe, Docker ignore file,
and snapshot utility by bytes and file modes. Creation rejects existing
destinations and source drift; verification rejects added context files.
Private AI configuration, unrelated book material, and generated outputs are
excluded. The build helper requires Python 3.11 or newer, independently of the
installed package's Python requirement.

All Python modules in the declared physical package, including `signal_graph.py`,
`cell_repair.py`, and `cell_models.py`, are wheel inputs. Its package-data rule
now includes authored first-level `*.tcl` files, so new repair wrappers cannot
silently disappear from the wheel. The default-profile producer
`teaching_core/backend.py` is also bound as package source. The final protocol
compares the complete installed package file hashes and runtime helpers with
the frozen manifest before running dependent checks. Physical receipt source
lists remain the physical owner's responsibility as repair helpers become
active. No final snapshot, image build, or installed-image verification has been
performed for these changes.

The focused snapshot and offline packaging checks passed together: `20` tests
in `2.36` seconds. They cover private/configuration exclusions, added or changed
inputs, source drift, destination preservation, package discovery, all authored
physical Tcl assets, exact wheel-to-manifest file and byte equality, and an
isolated wheel installation outside the repository.
This is source-delivery preparation evidence while the physical profile changes.
The read-only inventory and delivery source hashes are retained under
`output/nanochip/delivery-closure-audit-20261018/`; no final snapshot was created.

The nonfinal audit under `output/nanochip/current-package-audit-20261018/`
verified `184` packaged source/asset files byte-for-byte in the wheel, recorded
`12` container build inputs, and found no missing runtime Python modules or
source changes during the passing audit. The outside-repository installation
and console/resource checks passed: `6` packaging tests in `2.24` seconds.
The retained wheel SHA-256 is
`48b8006558902db52210c1a0373b21a3448bf9b1daba534bfabdf6341d3c14c6`.
`summary-attempt-2.json` and its before/after manifests record exact source,
helper, lock, and recipe identities. The first attempt's incorrect in-repository
test staging is retained separately; it was an audit setup error. This wheel
is preparation evidence, not final source freeze or image/physical acceptance.

The repeated-workspace host boundary tests cover persisted student edits,
separate resource receipts, unchanged prior evidence, resolved workspace/output
symlinks, rejected escapes and missing directories, and literal entrypoint
resource arguments. A real repeated-workspace course run with the final source-frozen image is
still required. A separate COPY-only overlay provided the narrower engineering
proof below; it did not rebuild the installed Nanochip package.

## Persistent-workspace engineering proof

The distinct COPY-only overlay `nanochip-local:workspace-smoke-0.1.0a0` has
identity `sha256:2c190abc387f064ca1e8e416466269b376d5df48dded6d218109f08d6a451106`.
It retains the older ARM64 candidate's installed course package and copies only
the current entrypoint and resource helper. The existing candidate identity
was verified unchanged before and after the build. The copied entrypoint
SHA-256 is `8ee56513f924111fdb490060ab2bc928a23a3d20407e748d004928c7f99519bc`;
the resource helper SHA-256 is
`3add849ceef1ba70087a0c4a557c7fc287a8a1dad36545345d4c909f69fccf7c`.

The current host launcher initialized a persistent student workspace, then ran
Lab 1 in student mode after a host edit to its implementation. The edit's hash
matched the completed course event. Both launches mounted only that same
workspace, retained separate nested resource receipts, and left the first
launch's receipt/resource hashes unchanged. They ran offline with one CPU,
`512m`, mapped UID/GID, and a `60`-second bound per launch. The engineering hook
delegated to the installed reference splitter, demonstrating persistence/source
identity rather than a student-design, learning, or human-usability result.
No EDA or model training was requested.

Evidence is `output/nanochip/workspace-overlay-smoke-20261018/`: exact build and
launch commands, copied hashes, immutable image identity, host-edit source,
course event, resource counters, and summary. This retires launcher/entrypoint
persistence uncertainty with the older package; it does not establish the final
Nanochip installation, cumulative later-lab protocol, or full-course acceptance.
