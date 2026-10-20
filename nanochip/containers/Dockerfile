# Local tutorial image; build and validation evidence is documented in README.md.
# Build context is nanochip/ (not the manuscript repository).
ARG PYTHON_IMAGE=python@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
FROM ${PYTHON_IMAGE} AS functional

# The archive follows the pinned base's 2026-02-24 creation date so development
# headers match its installed libc and Perl runtime packages.
ARG DEBIAN_SNAPSHOT=20260301T000000Z
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s/ bookworm main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s/ bookworm-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=1 -o Acquire::http::Timeout=30 update \
    && apt-get install -y --no-install-recommends ca-certificates g++ make verilator yosys \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN python -m pip install --no-cache-dir --timeout 30 --retries 1 setuptools==81.0.0 wheel==0.47.0
WORKDIR /opt/nanochip
# An allowlist keeps outputs, manuscript files and AI configuration out.
COPY pyproject.toml __init__.py ./
COPY engine ./engine
COPY laboratory ./laboratory
COPY kpu ./kpu
COPY trajectories/variants ./trajectories/variants
RUN python -m pip install --no-cache-dir --no-build-isolation --no-deps . \
    && rm -rf /opt/nanochip
WORKDIR /work
ENTRYPOINT ["nanochip"]
CMD ["doctor"]

FROM functional AS learning
# CPU wheels avoid pulling a CUDA toolchain into this small tutorial.
ARG TORCH_VERSION=2.11.0
RUN python -m pip install --no-cache-dir --timeout 30 --retries 1 --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}"
# Parameter identity hashes use Tensor.numpy(); Torch does not declare NumPy.
ARG NUMPY_VERSION=2.2.6
RUN python -m pip install --no-cache-dir --timeout 30 --retries 1 "numpy==${NUMPY_VERSION}"
# Arbitrary host UID mappings have no passwd entry. Torch's cache initialization
# calls getpass.getuser(), even for the eager optimizer used by this tutorial.
ENV USER=nanochip TORCHINDUCTOR_CACHE_DIR=/tmp/nanochip-torch-inductor \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

# Default target is the functional image; request --target learning explicitly.
FROM functional AS default
