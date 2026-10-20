"""Candidate-linked complete workload execution through the common lab protocol."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil
import struct
import time
import uuid

from ..contracts import (Action, Artifact, Candidate, CheckRequirement, CheckResult,
                         ContractError, Cost, Metric, RunReceipt, Task, file_sha256)
from .contract import CONFIG, contract
from .fixtures import build_fixture
from .rtl import BENCH, CORE, implementation_source, run_rtl

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
SCOPE = "accelerator:nanochip_teaching_core"
ACTIONS = ("serial_mul1", "serial_mul2")
CHECKS = ("exact_integer_logits", "exact_argmax", "float_numerical", "protocol", "runtime_program", "reset_latency_independence")
PROFILES = (
    {"latency": 24, "stall_permille": 0, "reset_seed": 0, "jitter": 12},
    {"latency": 48, "stall_permille": 50, "reset_seed": 19, "jitter": 24},
    {"latency": 24, "stall_permille": 0, "reset_seed": 71, "jitter": 12},
)


def default_physical_config():
    """One source for the manifested teaching-core implementation profile."""
    return {"DESIGN_NAME": "nanochip_teaching_core", "VERILOG_FILES": ["dir::core.v"], "CLOCK_PORT": "clk",
            "CLOCK_PERIOD": 100, "FP_CORE_UTIL": 35, "PL_TARGET_DENSITY_PCT": 45, "RUN_LINTER": False,
            "SYNTH_STRATEGY": "AREA 3", "meta": {"flow": "NanochipClockRepair"},
            "CTS_SINK_CLUSTERING_SIZE": 8, "CTS_DISTANCE_BETWEEN_BUFFERS": 200,
            "CTS_CLK_MAX_WIRE_LENGTH": 200, "NANOCHIP_CLOCK_BRANCH_SIZE": 4,
            "NANOCHIP_CLOCK_BRANCH_CELL": "sky130_fd_sc_hd__clkbuf_8",
            "NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE": 0.06,
            "NANOCHIP_CLOCK_BUFFER_INPUTS": True, "NANOCHIP_POST_CTS_HOLD_REPAIR": True,
            "RUN_POST_CTS_RESIZER_TIMING": False, "RUN_POST_GRT_DESIGN_REPAIR": False,
            "RUN_POST_GRT_RESIZER_TIMING": False,
            "NANOCHIP_SIGNAL_WORKING_TRANSITION": ".25",
            "NANOCHIP_SIGNAL_WORKING_CAPACITANCE": ".06",
            "NANOCHIP_SIGNAL_RESIDUAL_MAX_WIRE_LENGTH": 50,
            "GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH": 100,
            "GRT_DESIGN_REPAIR_MAX_SLEW_PCT": 0, "GRT_DESIGN_REPAIR_MAX_CAP_PCT": 0}


def _source_manifest():
    sources = set(PACKAGE.glob("*.py")) | {CORE, BENCH}
    kpu = ROOT / "nanochip/kpu"
    sources.update(kpu / name for name in ("reference/config.py", "reference/model.py", "reference/gen_weights.py",
                   "reference/prng.py", "harness/memmap.py", "harness/scoring.py", "rtl/selfmodel/fxmodel.py", "rtl/selfmodel/fxluts.py"))
    sources.update((kpu / "rtl/roms").glob("*.hex"))
    return {str(p.relative_to(ROOT)): file_sha256(p) for p in sorted(sources)}


def make_task(seed: int = 1, prompt_index: int = 0, split: str = "development", tokens: list[int] | None = None) -> Task:
    if type(seed) is not int or seed < 0 or type(prompt_index) is not int or prompt_index not in range(len(CONFIG.seq_lens)):
        raise ContractError("Invalid workload seed/prompt")
    if split not in ("development", "test"):
        raise ContractError("Use development or test split")
    if tokens is not None and (not isinstance(tokens, list) or not 1 <= len(tokens) <= CONFIG.max_seq or any(type(t) is not int or not 0 <= t < CONFIG.vocab for t in tokens)):
        raise ContractError("Invalid token override")
    spec = {"target": contract(), "seed": seed, "prompt_index": prompt_index, "split": split,
            "tokens": tokens, "token_count": len(tokens) if tokens is not None else CONFIG.seq_lens[prompt_index],
            "profiles": list(PROFILES), "source_artifacts": _source_manifest(),
            "action_parameters": {"serial_mul1": {"multiplier_bits_per_cycle": 1}, "serial_mul2": {"multiplier_bits_per_cycle": 2}},
            "acceptance_boundary": "complete mathematical teaching derivative; no upstream RTL/performance identity or physical acceptance"}
    return Task(f"nanochip-teaching-core-{split}-seed{seed}-p{prompt_index}-n{spec['token_count']}", ACTIONS,
                tuple(CheckRequirement(name, SCOPE) for name in CHECKS), max_proposals=2, max_attempts=2, specification=spec)


def _validate_sources(task):
    for relative, expected in task.specification["source_artifacts"].items():
        if file_sha256(ROOT / relative) != expected:
            raise ContractError(f"Source changed after task construction: {relative}")


class TeachingCoreMaterializer:
    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        if action.name not in ACTIONS or action.parameters or action.name not in task.allowed_actions:
            raise ContractError("Teaching core accepts only serial_mul1/serial_mul2 without parameters")
        _validate_sources(task)
        from .compiler import compile_program
        compiled = compile_program(seq_len=task.specification["token_count"], config=task.specification["target"]["configuration"])
        root = Path(workspace) / "candidate"
        root.mkdir(parents=True, exist_ok=False)
        build_fixture(root / "reference", seed=task.specification["seed"], prompt_index=task.specification["prompt_index"], tokens=task.specification["tokens"])
        bits = 1 if action.name == "serial_mul1" else 2
        scratch = compiled.manifest["minimum_power_of_two_words"]
        (root / "core.v").write_text(implementation_source(bits, scratch))
        shutil.copyfile(BENCH, root / "core_tb.cpp")
        shutil.copyfile(PACKAGE / "rtl.py", root / "rtl.py")
        shutil.copyfile(Path(__file__), root / "backend.py")
        (root / "program.bin").write_bytes(compiled.program)
        (root / "tables.bin").write_bytes(compiled.tables)
        (root / "program.json").write_text(json.dumps(compiled.manifest, indent=2, sort_keys=True) + "\n")
        (root / "task.json").write_text(json.dumps(asdict(task), indent=2, sort_keys=True) + "\n")
        config = default_physical_config()
        (root / "physical-config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
        _validate_sources(task)
        return Candidate(action.name, task.task_id, str(root), action,
                         tuple(Artifact.from_file(root, str(p.relative_to(root))) for p in sorted(root.rglob("*")) if p.is_file()),
                         task_digest=task.digest)


class TeachingCoreBackend:
    def __init__(self, timeout_s: float = 180, max_cycles: int = 300_000_000):
        self.timeout_s, self.max_cycles = timeout_s, max_cycles

    def evaluate(self, task: Task, candidate: Candidate) -> RunReceipt:
        started = time.monotonic()
        _validate_sources(task)
        candidate.validate_files()
        if candidate.task_id != task.task_id or candidate.task_digest != task.digest:
            raise ContractError("Candidate belongs to a different frozen task")
        root = Path(candidate.root)
        for current, manifested in ((PACKAGE / "rtl.py", "rtl.py"), (Path(__file__), "backend.py")):
            if file_sha256(current) != file_sha256(root / manifested):
                raise ContractError("Executed checker differs from candidate-manifested checker")
        out = root.parent / ("rtl-" + uuid.uuid4().hex[:12])
        result = run_rtl(root / "core.v", root / "program.bin", root / "reference/image.bin", root / "tables.bin", out,
                         bench=root / "core_tb.cpp", timeout_s=self.timeout_s, max_cycles=self.max_cycles,
                         profiles=tuple(task.specification["profiles"]))
        expected_inputs = {"core.v": "core.v", "core_tb.cpp": "core_tb.cpp", "program.bin": "program.bin", "image.bin": "reference/image.bin", "tables.bin": "tables.bin"}
        for artifact in result["inputs"]:
            if artifact["sha256"] != file_sha256(root / expected_inputs[artifact["path"]]):
                raise ContractError("Executed RTL/program/image/table differs from manifested candidate")
        execution = {"completed": "success", "timeout": "timeout", "unavailable": "not_run"}.get(result["status"], "error")
        statuses = {name: "not_run" for name in CHECKS}
        details = {}
        metrics = {}
        if result["ok"]:
            import numpy as np
            with np.load(root / "reference/goldens.npz") as golden:
                fixed, fixed_argmax, floating = (golden[k].copy() for k in ("fixed_logits", "fixed_argmax", "float_logits"))
            rows = []
            dumps = []
            for profile in result["profiles"]:
                image = (out / profile["dump"]).read_bytes()
                header = struct.unpack_from("<64I", image)
                logits = np.asarray([struct.unpack_from(f"<{header[17]}i", image, header[25] + pos * header[30]) for pos in range(header[19])])
                argmax = np.asarray(struct.unpack_from(f"<{header[19]}I", image, header[26]))
                f = floating.astype(np.float64); a = logits.astype(np.float64)
                denom = np.linalg.norm(f, axis=1) * np.linalg.norm(a, axis=1)
                cos = np.sum(f * a, axis=1) / np.maximum(denom, 1e-30)
                valid_argmax = bool(np.all((argmax >= 0) & (argmax < f.shape[1])))
                hits = f[np.arange(len(f)), np.clip(argmax, 0, f.shape[1]-1)] >= f.max(axis=1) - 0.01 * f.std(axis=1)
                rows.append({"exact_integer_logits": bool(np.array_equal(logits, fixed)),
                             "exact_argmax": bool(np.array_equal(argmax, fixed_argmax)),
                             "float_numerical": bool(np.all(cos >= 0.98) and valid_argmax and hits.mean() >= 0.99),
                             "cosine_min": float(cos.min()), "near_tie_argmax_rate": float(hits.mean()),
                             "status_word": struct.unpack_from("<I", image, header[27])[0]})
                dumps.append(image)
            for name in ("exact_integer_logits", "exact_argmax", "float_numerical"):
                statuses[name] = "pass" if all(row[name] for row in rows) else "fail"
            statuses["protocol"] = "pass" if all(p["result"]["protocol_errors"] == 0 for p in result["profiles"]) and all(row["status_word"] == 0x600DD00D for row in rows) else "fail"
            statuses["runtime_program"] = "pass" if all(p["result"]["read_beats"] > 0 for p in result["profiles"]) else "fail"
            statuses["reset_latency_independence"] = "pass" if all(data == dumps[0] for data in dumps) else "fail"
            primary = result["profiles"][0]["result"]
            metrics = {name: Metric(primary[key], unit, SCOPE) for name, key, unit in (
                ("cycles", "cycles", "cycles"), ("read_beats", "read_beats", "beats"), ("write_beats", "write_beats", "beats"))}
            metrics["cosine_min"] = Metric(min(row["cosine_min"] for row in rows), "cosine", SCOPE)
            details["profiles"] = rows
        details.update(status=result["status"], physical_execution=False,
                       boundary="Complete mathematical teaching derivative; no physical or upstream performance acceptance")
        (out / "checks.json").write_text(json.dumps({"checks": statuses, "details": details}, indent=2, sort_keys=True) + "\n")
        candidate.validate_files()
        _validate_sources(task)
        names = [artifact["path"] for artifact in result["outputs"]] + ["receipt.json", "checks.json"]
        return RunReceipt(task.task_id, candidate.digest, "fresh", execution, "Verilator", result.get("tool_version", "unavailable"),
                          checks=tuple(CheckResult(name, status, SCOPE, json.dumps(details, sort_keys=True)) for name, status in statuses.items()),
                          metrics=metrics, cost=Cost(time.monotonic() - started), details=details["boundary"], output_root=str(out),
                          output_artifacts=tuple(Artifact.from_file(out, name) for name in names))
