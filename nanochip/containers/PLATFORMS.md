# Platform and resource evidence

The prepared full runtime has actual execution evidence on macOS `26.4`, an
Apple M5 Max ARM64 host, using Docker Desktop `29.3.0` and its Linux ARM64 VM.
The host has `64` GiB RAM. This is execution at the native processor architecture
inside a VM. It is not a native Linux-host trial or an emulated AMD64 trial.
The candidate remains local, separate from the final full-runtime tag. A separate
AMD64 dependency image has since passed bounded checks under emulation; this is
preparation evidence, not Nanochip execution on AMD64.

## Distribution requirements and current boundary

| PROJECT_PLAN requirement | Actual evidence | Remaining acceptance work |
| --- | --- | --- |
| Versioned container and installed Python interface | Candidate image ID and source snapshot in [FULL_RUNTIME.md](FULL_RUNTIME.md); installed `doctor`, connected functional system, instructor Labs 1–7 passed | Rebuild after final source freeze; validate that exact final image |
| Supported laptop OS/architecture | macOS ARM64 with Docker Desktop, Linux ARM64 containers | Native Linux ARM64/AMD64 hosts, macOS Intel, Windows/WSL, and emulated execution are untested; the POSIX UID/process-group launcher is not implemented for native Windows Python |
| Image and installation disk | Daemon accounting below, public manifest compressed bytes retained | Fresh download/unpack/build peak disk and final-image compressed size are unmeasured |
| Memory requirement | Two-CPU functional/course run completed with `--memory 8g`; isolated complete-core LEF producer peaked at `7,211,315,200` bytes under `7g`; VM capacity recorded below | Complete-course peak RAM, minimum viable RAM, and final-profile requirements remain unmeasured |
| Startup cost | Five new cached-image `doctor` containers measured below | Cold engine startup and first image download measured separately in a future fresh-install trial |
| Offline, no API key/GPU | Functional system and Labs 1–7 ran with `--network none`; CPU Torch, no API service or GPU requested | Repeat complete final reference path after source freeze |
| Persistent student work/checkpoint recovery | One explicit `/work` bind mount retained writable outputs, datasets, checkpoints, and course progress under host UID/GID; a separate host CLI probe preserved Lab 1 while interrupting and restarting Lab 2 in a new attempt | Repeat interruption recovery in the final installed container; mid-training optimizer resume is not implemented or claimed |
| Native and emulated trials separate | ARM64 Nanochip execution and AMD64 emulated dependency checks identified separately | AMD64 Nanochip functional/course execution and actual native AMD64 host trials remain pending |

Receipts from the host launcher now include host and engine architectures,
image architecture, their relationship, host output-disk capacity, engine RAM,
requested memory, and timing. `same_architecture` describes the CPU architecture;
it does not imply the absence of a VM. Requested resource limits are not measured
usage or guarantees of available capacity.

Future complete-core execution uses provisional wall budgets of `14400`
seconds for physical implementation and `3600` seconds for mapped
correspondence. The outer launcher allows `21600` seconds, including a further
`3600` seconds for course, learning, and collection. The
[budget calculation](../../output/nanochip/complete-core-physical-20261018/flow-runtime-analysis-1/budget-decision.json)
links these values to observation 3's `9136.582`-second historical stage assembly.
Checkpoint reuse, mixed historical resources, and the corrected future KLayout
arguments prevent treating that assembly as a fresh-profile runtime promise.
Historical run limits remain unchanged; final source-image validation is pending.

## Storage and memory accounting

The retained audit is `output/nanochip/platform-audit-20261018/`. Its
`inventory.json` holds raw selected daemon/host fields, `computed.json` holds
unit conversions, and registry manifests preserve compressed-layer sizes.
At the audit instant:

| Object | Daemon image size, including shared layers | Shared with other images | Unique in this cache |
| --- | ---: | ---: | ---: |
| Full candidate | 21,578,251,573 bytes | 16,990,126,080 bytes | 4,588,125,493 bytes |
| Full dependency stage | 21,570,270,520 bytes | 16,990,126,080 bytes | 4,580,144,440 bytes |
| Pinned physical base | 20,732,027,416 bytes | 16,319,819,776 bytes | 4,412,207,640 bytes |

The candidate's full daemon size is `20.096` GiB. Do not sum these image sizes:
Docker shares layers. Do not use the smaller raw `docker image inspect .Size`
field as the full installation footprint on this daemon. Docker documents
`system df` image size as shared plus unique; shared storage also means several
images need less space than the sum of their virtual sizes.
[Docker disk accounting](https://docs.docker.com/reference/cli/docker/system/df/),
[Docker image storage](https://docs.docker.com/engine/storage/drivers/).

The daemon reported `44,443,747,781` bytes of image-layer storage and build-cache
entry sizes summed to `13,589,081,104` bytes. These are separate accounting views;
the cache sum is not an additional unique-disk estimate. Host output storage had
`1,179,437,072,384` bytes free; the Docker VM filesystem reported
`1,816,718,094,336` bytes free. A VM virtual filesystem's free space is not a
reservation on the host. Neither figure substitutes for measuring peak build
storage. The retained functional/course validation contains `1,934` files,
`267,308,407` logical bytes and `271,970,304` allocated bytes; this excludes
other experiments, image/cache storage, and temporary peak usage.

The Docker VM reported `8,214,757,376` bytes (`7.651` GiB) RAM. The requested
`8g` Docker limit is `8,589,934,592` bytes, above that VM capacity. The successful
run therefore does not demonstrate eight GiB of available RAM or establish a
minimum RAM requirement. No Docker VM memory setting was changed during this audit. New full-runtime
examples and the launcher default now use a `7g` configured budget. The strict
complete-core LEF retry measured `7,211,315,200` bytes of cgroup peak usage under
a `7` GiB (`7,516,192,768`-byte) limit, with zero limit/OOM events and final
`OOMKilled=false`. Its geometry and writer settings were unchanged. That observed
run exceeds the previous `6g` ceiling, so future defaults deliberately increase
the budget. The receipt is
`output/nanochip/complete-core-physical-20261018/strict-complete-core-lef-retry-1/receipt.json`.
This is not a proven minimum or final-profile success. Historical `6g` and `8g`
receipts retain their actual limits. Current available VM memory/headroom is
unknown, and complete-run peaks remain necessary before giving final resource
guidance. The updated final image is still unbuilt and unvalidated.
The next full image's opt-in resource supervisor is prepared to retain its own
container cgroup `memory.peak` after child exit. A tiny bind-mounted-helper smoke
passed on Linux cgroup v2 with the unchanged candidate: measured peak
`27,824,128` bytes under a `134,217,728`-byte cap. This is helper validation only,
not a full-experiment memory measurement or final-image integration proof.
Evidence is `output/nanochip/resource-capture-smoke-20261018/`. Supervisor-killed
or unreadable-counter cases remain explicitly unavailable; sampled
`docker stats` values are not substituted for a final peak.

Reproduce local accounting without pulling, building, or pruning:

```bash
docker info --format '{{json .}}'
docker system df -v
docker image inspect nanochip-local:full-candidate-0.1.0a0
python3 output/nanochip/platform-audit-20261018/reproduce-accounting.py
```

The retained helper filters daemon settings to resource and selected image
fields; it does not retain proxy/account configuration. Accounting changes when
images, caches, or active jobs change. No cache cleanup was performed.

## Cached startup measurement

With the engine already running, the candidate cached, two CPUs, requested
`8g`, mapped UID/GID, and networking disabled, five separate `doctor` launches
all passed. End-to-end host-launcher elapsed time was `0.523`–`1.030` seconds,
median `0.583` seconds. Each trial created a fresh container. This includes
cached image/engine inspection, entrypoint profile setup, `doctor`, and client
exit. It excludes image download, build, cold Docker engine boot, and Torch
training. A separate physical job was active; this is an observed small sample,
not a startup guarantee. Exact timings and receipts are in `startup-summary.json`
and `startup-01/` through `startup-05/` under the audit directory.

## AMD64 preparation under emulation

The pinned public physical-bundle digest is an OCI index with separate Linux
ARM64 and AMD64 images. The AMD64 child pulled locally is:

```text
hpretl/iic-osic-tools@sha256:872e7e57e31966dead2ae6ed31f6277fb9ec92f20cc66afbb3f39f57b2b1e708
```

Its manifest declares `4,838,808,485` compressed layer bytes. The actual pull
completed in `118.715` seconds on the recorded connection/cache state; this is
one observed preparation trial, not a fresh-install bandwidth guarantee.
The official CPU Torch CPython 3.12 x86_64 wheel is `190,312,281` bytes and matched
SHA-256 `f82e2ae20c1545bb03997d1cc3143d94e14b800038669ee1aca45808a9acc338`.
Its download took `1.828` seconds. With the reused verified setuptools wheel,
the separate wheelhouse retains `191,374,302` bytes. The ARM64 lock and images
were unchanged.

The dependency-only tag `nanochip-local:full-dependencies-amd64-0.1.0a0` has
identity `sha256:ce2fc423abbff913875c7ada20972bf97028d78b0bfbce1044e92596e0d5cf3b`.
The offline build used only the hash-locked local wheelhouse and took `22.701`
seconds. Actual inherited Python/package versions were inspected first, then
pinned independently in `full-runtime-constraints-amd64.txt`. This image has no
installed Nanochip source. The Docker build retained a lint warning about an
explicit constant AMD64 `FROM --platform`; installation and export passed.

A separate offline verification under AMD64 emulation on the ARM64 engine,
limited to one CPU and `1g` RAM with mapped UID/GID, passed in `6.094` seconds.
It verified Python `3.12.3`, CPU Torch `2.11.0+cpu`, NumPy `2.4.2`, one thread,
NumPy interoperation, Adam initialization, pinned transitive versions, PDK
identity, and physical tool version commands. It ran no model training,
Nanochip experiment, course lab, or physical flow. The private cgroup recorded
peak memory `389,316,608` bytes (`0.363` GiB), with no memory limit/OOM events.
This is a dependency-check peak including the supervisor, not a Nanochip memory
requirement or whole-VM/host overhead measurement.

Daemon accounting reports the AMD64 base at `22,083,117,004` bytes (`20.567` GiB)
and its dependency image at `23,088,412,218` bytes (`21.503` GiB), each including
shared layers. They share `17,244,278,784` bytes in this cache. Storage peaks
were not measured. After preparation, host storage reported
`1,153,641,435,136` free bytes and the Docker VM filesystem reported
`1,792,648,892,416` free bytes; these are capacity observations, not peak usage
or reserved host space. Full preparation evidence, licenses, exact commands, hashes,
platform metadata, and resource counters are retained under
`output/nanochip/amd64-dependency-prep-20261018/`.

The next step, after root schedules it and freezes the physical profile/source,
is an independently tagged AMD64 Nanochip source image, built from the same
`FullDockerfile` using its tested `TARGETARCH` lock selection, and bounded offline
`doctor`/course smoke. Then execute the unchanged functional system and Labs 1–7
protocol with explicit `--platform linux/amd64`, recording wall time, cgroup peak,
identity, and any fixed-training-budget failure. Do not overwrite the ARM64 image
or final tag. Native AMD64 host execution remains a separate trial. Docker
Desktop includes emulation, but computation under emulation can be slow;
a dependency check cannot establish Nanochip compatibility or native AMD64
performance. [Docker multiplatform execution](https://docs.docker.com/build/building/multi-platform/).
