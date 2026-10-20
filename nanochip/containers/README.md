# Local tutorial container

The learning target has been built locally for Linux ARM64. It supplies Python,
Verilator, Yosys, Make, a C++ compiler, CPU PyTorch, and NumPy. Its default thread
settings are `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
`OPENBLAS_NUM_THREADS=1`. This small recurrent workload completed its fixed
training updates with one thread; two threads exceeded the unchanged training
time budget under the same CPU quota. Image builds download dependencies.

From the repository root:

```bash
docker build --target learning \
  --build-arg PYTHON_IMAGE=python@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c \
  --progress plain -f nanochip/containers/Dockerfile \
  -t nanochip-local:0.1.0a0 nanochip
docker run --rm --pull=never --network none nanochip-local:0.1.0a0 doctor
mkdir -p output/nanochip/new-container-run
docker run --rm --pull=never --network none --cpus 2 --memory 4g \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD/output/nanochip/new-container-run,dst=/work" \
  nanochip-local:0.1.0a0 demo --output /work/demo
```

Use a new output directory for each run. The user mapping retains files under
the invoking user's UID and GID. Runtime execution uses no network. The
`functional` build target provides the hardware tools and standard-library
laboratory without the optional learning dependencies.

## Local validation evidence

The final local image identity is
`sha256:6a042b0696421955c53f2fd4d0cb79adb077084936c7047464527df726cdf6c4`.
It contains Python `3.12.12`, PyTorch `2.11.0+cpu`, NumPy `2.2.6`, Verilator
`5.006`, Yosys `0.23`, GNU Make `4.3`, and GCC `12.2.0`. The tested image
is ARM64, running on macOS ARM64 through Docker Desktop; other host and
processor combinations have not been validated. See [platform evidence](PLATFORMS.md)
for the full runtime's separate storage and execution boundaries.

The final image-default `demo` exited successfully in `72.541` seconds of
reported experiment time, with networking disabled, a two-CPU quota, and a
`4g` memory limit. No runtime thread overrides were supplied. Training receipts
confirm one thread and all `300` base, `150` adaptation, and `360` design
updates. The selected `stream_quantized_row` RTL change passed the finite
numerical and sequential differential checks. Physical execution was not
requested; complete accelerator eligibility remains false.

Build logs are retained in `output/nanochip/v0-container-build.log`.
`output/nanochip/v0-container-run/` retains the initial failures, the successful
explicit-thread run in `attempt-4/`, and the image-default run in `attempt-5/`.
Each final run retains its command, image identity, versions, raw tool receipts,
datasets, checkpoints, selected RTL, and report. Failed attempts disclosed
missing NumPy, an unmapped-UID Torch cache lookup, and incomplete updates with
two threads. NumPy is now declared in the package's learning extra; the image
provides a stable `USER` and a Torch-specific cache directory for host UID
mapping. The fixed training step counts and time budgets were preserved.

Raw reports retain container execution paths. Map `/work/` to the host mount
directory when reviewing them. The installed reference RTL also has a retained,
hash-matching copy at
`demo/design/execution/attempts/attempt-0001/candidate/reference.v`. Raw reports
and receipts are not rewritten to change execution provenance.

The base image digest and Debian snapshot `20260301T000000Z` are pinned, as are
the direct Python tool and learning versions. Transitive Python packages are
recorded in each run's `versions.json` but are not locked by wheel hashes. The
local image has not been published, and package-name ownership is not claimed.

## Physical execution with the smaller learning image

Run `nanochip physical`, `nanochip design`, and `nanochip feedback` from the host
Python installation. The existing physical runner launches a separate cached
image with `--pull=never` and `--network none`:

```text
hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38
SKY130A revision: 54435919abffb937387ec956209f9cf5fd2dfbee
```

The original alpha validation targeted the `msh_deq` block. Provisioning the
physical image and PDK remains a separate step for this smaller learning image. The tutorial image contains neither Docker nor the
PDK. Docker-in-Docker and mounting the host Docker socket are not configured;
the physical runner's bind mounts refer to host paths. See the existing
[`laboratory/physical/README.md`](../laboratory/physical/README.md) for scope and
prerequisites.

For the separately prepared one-container runtime with native physical tools,
see [FULL_RUNTIME.md](FULL_RUNTIME.md). Its candidate validation and resource
evidence do not change the smaller alpha image's measured scope.
