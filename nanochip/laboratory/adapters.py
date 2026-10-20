"""First supplied checkpoint: a conventional controller and a real RTL tool.

The teaching fault and its reference replacement test the execution machinery.
They do not demonstrate model learning or architectural optimization.
"""

from dataclasses import asdict
import json
from pathlib import Path
import shutil

from . import dequant_probe
from .contracts import (
    Action, Artifact, Budget, Candidate, CheckRequirement, CheckResult,
    ContractError, Cost, Metric, Observation, RunReceipt, Task, file_sha256,
)

NANOCHIP = Path(__file__).resolve().parents[1]
BLOCK_SCOPE = "block:msh_deq"
CORE_SCOPE = "accelerator:msh_chip_top"
SOURCES = {
    "teaching_fault": NANOCHIP / "trajectories/variants/msh_deq_bad_shift.v",
    "reference": NANOCHIP / "kpu/rtl/msh_deq.v",
}


def starter_task() -> Task:
    return Task(
        task_id="nanochip-dequant-integration-v1",
        allowed_actions=tuple(SOURCES),
        required_checks=(
            CheckRequirement("dequant_vectors", BLOCK_SCOPE),
            CheckRequirement("workload_functional", CORE_SCOPE),
            CheckRequirement("rtl_netlist_correspondence", CORE_SCOPE),
            CheckRequirement("routed_timing", CORE_SCOPE),
            CheckRequirement("physical_drc", CORE_SCOPE),
            CheckRequirement("physical_lvs", CORE_SCOPE),
        ),
        max_attempts=2, max_proposals=3,
        specification={
            "purpose": "scoped RTL integration; no learned policy or GDS implementation",
            "source": "https://github.com/MoonshotAI/nano-kpu",
            "workload": "constructed dequant block inputs, not complete model inference",
            "vector_seed": dequant_probe.VECTOR_SEED,
            "candidate_sources": {name: file_sha256(path) for name, path in SOURCES.items()},
            "bench_sha256": file_sha256(dequant_probe.BENCH),
            "probe_sha256": file_sha256(dequant_probe.__file__),
        },
    )


class ReferenceProposer:
    """Supplied rule policy: exercise the fault, then respond to observed failure."""

    def propose(self, task: Task, history: tuple[Observation, ...], budget: Budget) -> Action | None:
        if not history:
            return Action("teaching_fault")
        last = history[-1]
        if last.status != "success":
            return None
        block = next((c for c in last.checks if c.name == "dequant_vectors" and c.scope == BLOCK_SCOPE), None)
        if block and block.status == "fail" and last.action and last.action.name == "teaching_fault":
            return Action("reference")
        return None


class DequantMaterializer:
    def materialize(self, task: Task, action: Action, workspace: Path) -> Candidate:
        if action.name not in SOURCES or action.parameters:
            raise ContractError("The starter accepts only reference/teaching_fault with no parameters")
        source = SOURCES[action.name]
        if file_sha256(source) != task.specification["candidate_sources"][action.name]:
            raise ContractError("Source changed after task construction")
        for path, key in ((dequant_probe.BENCH, "bench_sha256"),
                          (Path(dequant_probe.__file__), "probe_sha256")):
            if file_sha256(path) != task.specification[key]:
                raise ContractError("Checker changed after task construction")
        root = workspace / "candidate"
        root.mkdir()
        shutil.copyfile(source, root / "msh_deq.v")
        shutil.copyfile(dequant_probe.BENCH, root / "dequant_tb.cpp")
        shutil.copyfile(dequant_probe.__file__, root / "probe.py")
        (root / "task.json").write_text(json.dumps(asdict(task), indent=2) + "\n")
        names = ("msh_deq.v", "dequant_tb.cpp", "probe.py", "task.json")
        return Candidate(
            action.name, task.task_id, str(root), action,
            tuple(Artifact.from_file(root, name) for name in names), task_digest=task.digest,
        )


class VerilatorBackend:
    def __init__(self, timeout_s: float = 120):
        self.timeout_s = timeout_s

    def evaluate(self, task: Task, candidate: Candidate) -> RunReceipt:
        root = Path(candidate.root)
        out = root.parent / "tool"
        result = dequant_probe.run_probe(root / "msh_deq.v", out, self.timeout_s,
                                        bench_path=root / "dequant_tb.cpp")
        for output_key, input_name in (("candidate_sha256", "msh_deq.v"),
                                       ("bench_sha256", "dequant_tb.cpp"),
                                       ("probe_sha256", "probe.py")):
            if result[output_key] != file_sha256(root / input_name):
                raise ContractError("Executed input differs from the candidate manifest")
        reported = result.get("checks", {})
        status = result["status"]
        simulation = result.get("simulation", {})
        summary_valid = (
            isinstance(reported, dict) and isinstance(reported.get("ok"), bool)
            and all(type(reported.get(key)) is int and reported[key] >= 0
                    for key in ("rows_completed", "lanes_checked", "mismatches"))
        )
        completed = (
            summary_valid and simulation.get("returncode") in (0, 1)
            and not simulation.get("timed_out", True)
            and (simulation["returncode"] == 0) == reported["ok"]
        )
        execution = "success" if status in ("passed", "check_failed") and completed else (
            "timeout" if status == "timeout" else "not_run" if status == "unavailable" else "error"
        )
        check_status = "pass" if result["ok"] else "fail" if execution == "success" else "not_run"
        metrics = {
            "lanes_checked": Metric(reported["lanes_checked"], "lanes", BLOCK_SCOPE),
            "mismatches": Metric(reported["mismatches"], "lanes", BLOCK_SCOPE),
        } if "lanes_checked" in reported and "mismatches" in reported else {}
        names = ["receipt.json", "candidate.v", "dequant_tb.cpp", "vectors.json", "vectors.txt"]
        names += [name for name in ("version.log", "build.log", "simulation.log", "obj/dequant_probe")
                  if (out / name).is_file()]
        return RunReceipt(
            task.task_id, candidate.digest, "fresh", execution, "Verilator",
            result.get("tool_version", "unavailable"),
            checks=(CheckResult("dequant_vectors", check_status, BLOCK_SCOPE,
                                f"{status}; constructed finite vectors; no workload or physical claim"),),
            metrics=metrics, cost=Cost(result["total_elapsed_s"]),
            details="Only one RTL block executed. Complete workload and physical checks are unresolved.",
            output_root=str(out),
            output_artifacts=tuple(Artifact.from_file(out, name) for name in names),
        )
