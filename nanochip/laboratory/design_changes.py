"""Explicit, source-pinned dequantizer design actions.

``stream_quantized_row`` replaces the 1024-bit dynamically indexed read with a
constant low-nibble read and a four-bit shift on each output element. Input
staging, arithmetic, handshake, and write schedule remain unchanged. The
invariant at S_WR element i is that the low ``4*(d-i)`` bits of ``new_qrow``
equal those of ``old_qrow >> (4*i)``. Bits above that loaded suffix may differ
between jobs. Complete row intake establishes the invariant and each S_WR
clock preserves it. The contract requires complete, legal row segments, d a
multiple of four in [4,256], and one or two representable quantization groups.
Only y_data on y_we is meaningful; unused combinational bus values can differ.
Finite simulation is deliberately not labeled formal equivalence.
"""

from __future__ import annotations

from dataclasses import asdict
import difflib
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil

from . import dequant_probe
from .adapters import BLOCK_SCOPE
from .contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    ContractError,
    Task,
    file_sha256,
)


REFERENCE_SOURCE = Path(__file__).resolve().parents[1] / "kpu/rtl/msh_deq.v"
REFERENCE_SHA256 = "6294a0a15c11eba09693557f2a23cd4e049ea9776499ff6487cedffcd4724273"
DESIGN_ACTIONS = ("retain_indexed_read", "stream_quantized_row")
_INDEXED_READ = """    wire [6:0]  w_j   = wr_i[7:1];
    wire [7:0]  w_qb  = qrow_v[8*w_j +: 8];
    wire [3:0]  w_nib = wr_i[0] ? w_qb[7:4] : w_qb[3:0];"""
_STREAMING_READ = """    // Consume staged nibbles in the sequential S_WR order.
    wire [3:0]  w_nib = qrow_v[3:0];"""
_WRITE_STEP = """            if (state == S_WR) begin
                pack_v[32*wr_i[1:0] +: 32] <= w_y;"""
_STREAMING_STEP = """            if (state == S_WR) begin
                qrow_v <= {4'b0, qrow_v[1023:4]};
                pack_v[32*wr_i[1:0] +: 32] <= w_y;"""


def apply_design_change(source_text: str, action_name: str) -> str:
    """Apply one named action only to the exact reviewed reference revision."""
    if action_name not in DESIGN_ACTIONS:
        raise ContractError(f"Unknown design action: {action_name}")
    if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != REFERENCE_SHA256:
        raise ContractError(
            "Design change requires the exact reviewed reference source hash"
        )
    for anchor in (_INDEXED_READ, _WRITE_STEP):
        if source_text.count(anchor) != 1:
            raise ContractError("Design change anchor must occur exactly once")
    if action_name == "retain_indexed_read":
        return source_text
    return source_text.replace(_INDEXED_READ, _STREAMING_READ).replace(
        _WRITE_STEP, _STREAMING_STEP
    )


def _hardware_tokens(source: str) -> tuple[str, ...]:
    """Ignore comments/formatting while preserving Verilog tokens and strings."""
    lexemes = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)
    uncommented = lexemes.sub(
        lambda match: match[0] if match[0].startswith('"') else " ", source
    )
    return tuple(
        re.findall(
            r'"(?:\\.|[^"\\])*"|\\\S+|(?:\d+)?\'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ?]+'
            r"|[A-Za-z_$][A-Za-z0-9_$]*|\d+|===|!==|>>>|<<<|==|!=|<=|>=|&&|\|\||<<|>>|\+:|-:|\S",
            uncommented,
        )
    )


def _is_right_four_literal(token: str) -> bool:
    if token == "4":
        return True
    match = re.fullmatch(r"([1-9][0-9]*)?'[dD]4", token)
    # A one- or two-bit decimal literal truncates 4, so cannot mean right four.
    return bool(match and (match[1] is None or int(match[1]) >= 3))


def validate_action_conformance(original: str, changed: str, action_name: str) -> None:
    """Enforce this exercise's narrow structural action boundary, not a proof.

    Retain is byte-for-byte identity. Streaming admits only the reviewed active
    RTL edit: read qrow_v[3:0] and nonblockingly shift qrow_v four bits in the
    existing S_WR block. Comments, whitespace, unused old read declarations,
    and ``qrow_v >> 4`` (including an unsigned decimal sized 4) are accepted.
    Other implementations need an explicit new action and its own checks.
    Functional simulation and the differential checker remain separate gates.
    """
    expected = apply_design_change(original, action_name)
    if not isinstance(changed, str) or not changed.strip():
        raise ContractError("Transformation must return nonempty RTL text")
    if action_name == "retain_indexed_read":
        if changed != original:
            raise ContractError(
                "retain_indexed_read must return the exact original source"
            )
        return
    tokens = _hardware_tokens(changed)
    if tokens == _hardware_tokens(original):
        raise ContractError(
            "stream_quantized_row must change hardware; comments/formatting do not count"
        )
    # Normalize the admitted alternate spelling of this one assignment. Final
    # whole-module comparison also constrains its position and surrounding FSM.
    canonical_shift = _hardware_tokens("qrow_v <= {4'b0, qrow_v[1023:4]};")
    normalized = []
    index = 0
    while index < len(tokens):
        if (
            tokens[index : index + 4] == ("qrow_v", "<=", "qrow_v", ">>")
            and index + 5 < len(tokens)
            and tokens[index + 5] == ";"
            and _is_right_four_literal(tokens[index + 4])
        ):
            normalized.extend(canonical_shift)
            index += 6
        else:
            normalized.append(tokens[index])
            index += 1
    admitted = [
        expected,
        expected.replace(
            _STREAMING_READ,
            "\n".join(_INDEXED_READ.splitlines()[:2]) + "\n" + _STREAMING_READ,
        ),
    ]
    if tuple(normalized) not in tuple(_hardware_tokens(text) for text in admitted):
        raise ContractError(
            "stream_quantized_row requires the admitted low-nibble read and "
            "nonblocking right-four shift in S_WR; unsupported active RTL edit"
        )


def design_change_task(source: Path | None = None) -> Task:
    """Freeze the unchanged oracle, checker, and two permissible design actions."""
    source = Path(source) if source is not None else REFERENCE_SOURCE
    apply_design_change(source.read_text(), "retain_indexed_read")
    return Task(
        task_id="nanochip-dequant-design-change-v1",
        allowed_actions=DESIGN_ACTIONS,
        required_checks=(CheckRequirement("dequant_vectors", BLOCK_SCOPE),),
        max_proposals=2,
        max_attempts=2,
        specification={
            "purpose": "explicit RTL transformation with finite block-level verification",
            "source_sha256": file_sha256(source),
            "transformer_sha256": file_sha256(Path(__file__)),
            "bench_sha256": file_sha256(dequant_probe.BENCH),
            "probe_sha256": file_sha256(Path(dequant_probe.__file__)),
            "vector_seed": dequant_probe.VECTOR_SEED,
            "design_features": {
                "row_values": 256,
                "quant_bits": 4,
                "access_order": "ascending",
                "index_step": 1,
                "start_index": 0,
                "passes": 1,
                "revisit": False,
                "reload_per_row": True,
            },
            "equivalence_scope": "legal complete rows; controls and valid Y writes; not exhaustive",
        },
    )


class DesignChangeMaterializer:
    """Materialize an inspectable patch plus all VerilatorBackend inputs."""

    def __init__(self, source: Path | None = None, transformer=None):
        self.source = Path(source) if source is not None else REFERENCE_SOURCE
        self.transformer = transformer

    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        if (
            action.name not in DESIGN_ACTIONS
            or action.name not in task.allowed_actions
            or action.parameters
        ):
            raise ContractError(
                "Design actions accept only the two named actions without parameters"
            )
        bound_inputs = (
            (self.source, "source_sha256"),
            (Path(__file__), "transformer_sha256"),
            (dequant_probe.BENCH, "bench_sha256"),
            (Path(dequant_probe.__file__), "probe_sha256"),
        )
        for path, key in bound_inputs:
            if file_sha256(path) != task.specification.get(key):
                raise ContractError(
                    f"Design input changed after task construction: {key}"
                )
        original = self.source.read_text()
        extension_path = (
            Path(inspect.getsourcefile(self.transformer)).resolve()
            if self.transformer
            else None
        )
        if extension_path and file_sha256(extension_path) != task.specification.get(
            "extension_sha256"
        ):
            raise ContractError("Student extension changed after task construction")
        changed = (self.transformer or apply_design_change)(original, action.name)
        validate_action_conformance(original, changed, action.name)
        root = Path(workspace) / "candidate"
        root.mkdir(parents=True)
        (root / "msh_deq.v").write_text(changed)
        (root / "reference.v").write_text(original)
        (root / "change.diff").write_text(
            "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    changed.splitlines(keepends=True),
                    fromfile="reference/msh_deq.v",
                    tofile=f"{action.name}/msh_deq.v",
                )
            )
        )
        shutil.copyfile(dequant_probe.BENCH, root / "dequant_tb.cpp")
        shutil.copyfile(dequant_probe.__file__, root / "probe.py")
        shutil.copyfile(Path(__file__), root / "design_changes.py")
        (root / "task.json").write_text(json.dumps(asdict(task), indent=2) + "\n")
        names = [
            "msh_deq.v",
            "reference.v",
            "change.diff",
            "dequant_tb.cpp",
            "probe.py",
            "design_changes.py",
            "task.json",
        ]
        if extension_path:
            shutil.copyfile(extension_path, root / "student_extension.py")
            names.append("student_extension.py")
        return Candidate(
            action.name,
            task.task_id,
            str(root),
            action,
            tuple(Artifact.from_file(root, name) for name in names),
            task_digest=task.digest,
        )


def _equivalence_miter(reference: str, candidate: str) -> str:
    """Compare controls continuously after reset, data only on valid writes."""
    header = reference.split("    localparam S_IDLE", 1)[0]
    header = header.replace(
        "    output wire         done\n",
        "    output wire         done,\n" "    output wire         equivalent\n",
    )
    inputs = (
        "clk",
        "rst_n",
        "job_valid",
        "job_d",
        "job_gsz",
        "job_ybuf",
        "ws_valid",
        "ws_data",
        "ws_count",
        "ws_shift",
        "ws_last",
    )
    widths = {
        "job_ready": "",
        "ws_ready": "",
        "y_we": "",
        "y_addr": "[11:0] ",
        "y_data": "[127:0] ",
        "y_buf": "[3:0] ",
        "done": "",
    }
    declarations = "".join(
        f"    wire {width}ref_{name};\n" for name, width in widths.items()
    )

    def instance(module: str, prefix: str) -> str:
        connections = [f".{name}({name})" for name in inputs]
        connections += [f".{name}({prefix}{name})" for name in widths]
        return f"    {module} u_{module} (" + ", ".join(connections) + ");\n"

    compare = " && ".join(
        f"({name} == ref_{name})" for name in widths if name != "y_data"
    )
    # Addr and buf are defined on idle cycles in this source and identical;
    # uninitialized data storage is intentionally checked only on valid writes.
    compare += " && (!y_we || (y_data == ref_y_data))"
    wrapper = (
        header
        + declarations
        + instance("reference_deq", "ref_")
        + instance("candidate_deq", "")
        + f"    assign equivalent = {compare};\nendmodule\n"
    )
    return (
        wrapper
        + reference.replace("module msh_deq (", "module reference_deq (", 1)
        + candidate.replace("module msh_deq (", "module candidate_deq (", 1)
    )


_STRESS_BENCH = r"""// Dual-RTL differential check, deterministic seed, legal complete rows.
#include "Vmsh_deq.h"
#include "verilated.h"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
class Stress {
    Vmsh_deq dut;
    uint32_t seed = 20261017;
    bool initialized = false;
    uint32_t random() { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed; }
public:
    uint64_t cycles = 0, writes = 0, jobs = 0, resets = 0, stalls = 0;
    void tick() {
        dut.clk = 0; dut.eval();
        if (initialized && !dut.equivalent) throw std::runtime_error("RTL mismatch");
        if (initialized && dut.y_we) ++writes;
        dut.clk = 1; dut.eval(); dut.clk = 0; dut.eval(); ++cycles;
    }
    void reset() {
        dut.rst_n = 0; dut.job_valid = 0; dut.ws_valid = 0;
        tick(); initialized = true; tick(); dut.rst_n = 1; tick(); ++resets;
        if (!dut.job_ready) throw std::runtime_error("reset failed");
    }
    void start(unsigned d, unsigned group) {
        if (!dut.job_ready) throw std::runtime_error("job not ready");
        dut.job_d = d; dut.job_gsz = group; dut.job_ybuf = random() % 16;
        dut.job_valid = 1; tick(); dut.job_valid = 0;
    }
    void segment(unsigned size) {
        for (unsigned pos = 0; pos < size;) {
            dut.ws_valid = 0;
            for (unsigned n = random() % 4; n; --n) tick();
            unsigned shift = random() % 16;
            unsigned count = std::min(size - pos, 1 + random() % (16 - shift));
            for (unsigned word = 0; word < 4; ++word) dut.ws_data[word] = random();
            dut.ws_shift = shift; dut.ws_count = count;
            dut.ws_last = (pos + count == size); dut.ws_valid = 1;
            unsigned wait = 0;
            while (true) {
                dut.eval(); bool ready = dut.ws_ready; tick();
                if (ready) break;
                ++stalls; if (++wait > 1000) throw std::runtime_error("stream timeout");
            }
            dut.ws_valid = 0; pos += count;
        }
    }
    void job(unsigned d, unsigned group) {
        start(d, group); segment(2 * d / group); segment(d / group); segment(d / 2);
        unsigned wait = 0;
        while (!dut.job_ready) {
            tick(); if (++wait > 2000) throw std::runtime_error("job timeout");
        }
        ++jobs;
    }
    void run() {
        dut.clk = 0; dut.job_valid = 0; dut.ws_valid = 0;
        dut.ws_count = 0; dut.ws_shift = 0; dut.ws_last = 0; reset();
        // Every supported row size, both representable group counts, back-to-back jobs.
        for (unsigned pass = 0; pass < 3; ++pass)
            for (unsigned d = 4; d <= 256; d += 4) {
                if (d <= 255) job(d, d);
                job(d, d / 2);
            }
        // Abort in each segment (empty and a staged beat in flight).
        for (unsigned phase = 0; phase < 3; ++phase)
            for (unsigned active = 0; active < 2; ++active) {
                start(256, 128);
                if (phase > 0) segment(4);
                if (phase > 1) segment(2);
                while (!dut.ws_ready) tick();
                if (active) {
                    for (unsigned i = 0; i < 4; ++i) dut.ws_data[i] = random();
                    dut.ws_count = 1; dut.ws_shift = 0; dut.ws_last = 0; dut.ws_valid = 1;
                    tick(); dut.ws_valid = 0;
                }
                reset(); job(4, 2); job(256, 128);
            }
        // Abort output on a variety of partially consumed rows, then reload shorter rows.
        for (unsigned delay : {0u, 1u, 2u, 3u, 4u, 17u, 127u, 254u}) {
            start(256, 128); segment(4); segment(2); segment(128);
            while (!dut.y_we) tick();
            for (unsigned i = 0; i < delay; ++i) tick();
            reset(); job(4, 4); job(256, 128);
        }
    }
};
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv); Stress stress;
    try { stress.run(); }
    catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
    std::cout << "EQUIVALENCE_JSON {\"ok\":true,\"jobs_completed\":" << stress.jobs
              << ",\"cycles_checked\":" << stress.cycles << ",\"valid_writes\":" << stress.writes
              << ",\"resets\":" << stress.resets << ",\"stream_stall_cycles\":" << stress.stalls << "}\n";
}
"""


def run_sequential_equivalence(
    candidate: Path,
    output_dir: Path,
    timeout_s: float = 120,
    *,
    reference: Path | None = None,
) -> dict:
    """Fresh bounded differential RTL execution; never an exhaustive proof.

    Tests all supported sizes and group counts with three nonperiodic payload
    sequences, immediate next jobs, input stalls, and reset during each intake
    state and partially emitted output. The original frozen RTL is the oracle.
    """
    import math
    import time

    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be finite and positive")
    candidate = Path(candidate).resolve()
    reference = Path(reference).resolve() if reference is not None else REFERENCE_SOURCE
    original = reference.read_text()
    apply_design_change(original, "retain_indexed_read")
    changed = candidate.read_text()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("equivalence output directory must be empty")
    (output_dir / "reference.v").write_text(original)
    (output_dir / "candidate.v").write_text(changed)
    (output_dir / "miter.v").write_text(_equivalence_miter(original, changed))
    (output_dir / "stress.cpp").write_text(_STRESS_BENCH)
    shutil.copyfile(Path(__file__), output_dir / "checker.py")
    started = time.perf_counter()
    deadline = started + timeout_s
    result = {
        "mode": "fresh",
        "status": "unavailable",
        "ok": False,
        "scope": "bounded sequential differential RTL simulation",
        "limits": [
            "Not exhaustive equivalence",
            "Legal complete row protocol",
            "Output data compared only when y_we is asserted",
        ],
        "seed": 20261017,
        "candidate_sha256": file_sha256(output_dir / "candidate.v"),
        "reference_sha256": file_sha256(output_dir / "reference.v"),
        "miter_sha256": file_sha256(output_dir / "miter.v"),
        "bench_sha256": file_sha256(output_dir / "stress.cpp"),
        "checker_sha256": file_sha256(output_dir / "checker.py"),
    }
    compiler = shutil.which("verilator")
    if compiler:
        version = dequant_probe._run(
            [compiler, "--version"],
            output_dir,
            output_dir / "version.log",
            min(5, timeout_s),
        )
        result["tool_version"] = (output_dir / "version.log").read_text().strip()
        result["version_probe"] = version
        if version["returncode"] == 0 and not version["timed_out"]:
            build = dequant_probe._run(
                [
                    compiler,
                    "--cc",
                    "--exe",
                    "--build",
                    "-j",
                    "2",
                    "-O1",
                    "-Wno-fatal",
                    "--top-module",
                    "msh_deq",
                    "--Mdir",
                    str(output_dir / "obj"),
                    "-o",
                    "equivalence_probe",
                    str(output_dir / "miter.v"),
                    str(output_dir / "stress.cpp"),
                ],
                output_dir,
                output_dir / "build.log",
                max(0.001, deadline - time.perf_counter()),
            )
            result["build"] = build
            result["status"] = "timeout" if build["timed_out"] else "build_failed"
            if build["returncode"] == 0 and not build["timed_out"]:
                binary = output_dir / "obj/equivalence_probe"
                simulation = dequant_probe._run(
                    [str(binary)],
                    output_dir,
                    output_dir / "simulation.log",
                    max(0.001, deadline - time.perf_counter()),
                )
                result["simulation"] = simulation
                result["binary_sha256"] = file_sha256(binary)
                for line in (output_dir / "simulation.log").read_text().splitlines():
                    if line.startswith("EQUIVALENCE_JSON "):
                        try:
                            result["checks"] = json.loads(
                                line[len("EQUIVALENCE_JSON ") :]
                            )
                        except json.JSONDecodeError:
                            result["parse_error"] = "malformed simulation summary"
                checks = result.get("checks", {})
                result["ok"] = (
                    simulation["returncode"] == 0
                    and not simulation["timed_out"]
                    and checks.get("ok") is True
                    and checks.get("jobs_completed") == 409
                    and checks.get("resets") == 15
                    and checks.get("valid_writes", 0) > 0
                    and checks.get("stream_stall_cycles", 0) > 0
                )
                result["status"] = (
                    "passed"
                    if result["ok"]
                    else ("timeout" if simulation["timed_out"] else "check_failed")
                )
        else:
            result["status"] = "timeout" if version["timed_out"] else "tool_failed"
    result["elapsed_s"] = time.perf_counter() - started
    (output_dir / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_design_checks(
    candidate_source: Path, output: Path, timeout_s: float = 120
) -> dict:
    """Public integration boundary for the bounded unchanged-RTL oracle check."""
    result = run_sequential_equivalence(candidate_source, output, timeout_s)
    result["source_sha256"] = result["candidate_sha256"]
    result["total_elapsed_s"] = result["elapsed_s"]
    output = Path(output).resolve()
    names = [
        str(path.relative_to(output))
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "receipt.json"
    ]
    result["output_artifacts"] = [
        asdict(Artifact.from_file(output, name)) for name in names
    ]
    result["output_root"] = str(output)
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
