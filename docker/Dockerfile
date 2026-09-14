FROM ubuntu:24.04

# Avoid interactive prompts during apt installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV PYTHONUNBUFFERED=1

# Install core development tools, open-source EDA suite, and RISC-V cross-compilation toolchain
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    gcc \
    git \
    curl \
    ca-certificates \
    yosys \
    yosys-abc \
    iverilog \
    verilator \
    gcc-riscv64-linux-gnu \
    binutils-riscv64-linux-gnu \
    libc6-dev-riscv64-cross \
    qemu-user-static \
    python3 \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-scipy \
    python3-pandas \
    python3-matplotlib \
    python3-yaml \
    python3-rich \
    python3-click \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (SCALE-Sim and Typer CLI engine)
RUN pip3 install --no-cache-dir --break-system-packages scalesim typer

# Working directory inside the container
WORKDIR /workspace

# Default to running the full interactive demonstration suite
CMD ["python3", "labs/demo.py"]
