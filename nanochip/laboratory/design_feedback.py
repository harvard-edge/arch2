"""Compose measured feedback, parameter updates, and fresh design campaigns.

The two prospective arms use the existing design command in separate Python
processes. Training finishes before either arm can obtain new tool feedback.
This is adaptation on an observed case, not held-out physical generalization.
"""

from dataclasses import asdict
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import design_changes, design_experiment, design_learning
from .contracts import (
    Action,
    Artifact,
    Candidate,
    CheckRequirement,
    ContractError,
    Task,
    file_sha256,
)
from .design_changes import design_change_task
from .design_learning import design_proposer
from .physical import flow


def _read(path):
    return json.loads(Path(path).read_text())


def _write(path, payload):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def _finite_metric(metrics, name):
    value = metrics.get(name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ContractError(f"Missing or nonfinite physical metric: {name}")
    return value


def _selected_physical_metrics(stages: dict) -> dict:
    """Use the executing stages selected by the physical checker.

    LibreLane inserts stages when repair settings change. Their numeric
    directory prefixes therefore cannot identify post-route measurements.
    ``collect_checks`` also selects the antenna stage after detailed routing,
    rather than an earlier repair report that may have reached zero.
    """
    sta = stages.get("openroad-stapostpnr", {}).get("metrics", {})
    antenna_stages = [
        value
        for name, value in stages.items()
        if name.startswith("openroad-checkantennas")
    ]
    if len(antenna_stages) != 1:
        raise ContractError("One selected postroute antenna stage is required")
    antenna = antenna_stages[0].get("metrics", {})
    names = dict(
        cell_area_um2="design__instance__area",
        instances="design__instance__count",
        setup_slack_ns="timing__setup__ws",
        hold_slack_ns="timing__hold__ws",
        slew_violations="design__max_slew_violation__count",
        capacitance_violations="design__max_cap_violation__count",
        fanout_violations="design__max_fanout_violation__count",
    )
    result = {name: _finite_metric(sta, key) for name, key in names.items()}
    result["antenna_violations"] = _finite_metric(
        antenna, "route__antenna_violation__count"
    )
    if result["cell_area_um2"] <= 0:
        raise ContractError("Cell area must be positive")
    return result


def inspect_design_run(root: Path) -> dict:
    """Validate a fresh campaign before using its results in a comparison."""
    root = Path(root).resolve()
    report = _read(root / "design-experiment.json")
    observations = report["campaign"]["observations"]
    if len(observations) != 1:
        raise ContractError("Feedback comparison requires exactly one proposal per arm")
    observation = observations[0]
    result = dict(
        action=observation["action"],
        execution_status=observation["status"],
        checks=observation["checks"],
        complete_design_eligible=observation["eligible"],
        report_sha256=file_sha256(root / "design-experiment.json"),
        total_wall_seconds=report["total_wall_seconds"],
        physical_executed=False,
        source_sha256=None,
        metrics=None,
    )
    events = [
        _read_line(line) for line in (root / "events.jsonl").read_text().splitlines()
    ]
    candidates = [
        event["candidate"] for event in events if event["event"] == "candidate"
    ]
    if not candidates:
        return result
    if len(candidates) != 1:
        raise ContractError("Unexpected additional design candidates")
    payload = candidates[0]
    candidate = Candidate(
        **dict(
            payload,
            action=Action(**payload["action"]),
            artifacts=tuple(Artifact(**item) for item in payload["artifacts"]),
        )
    )
    candidate.validate_files()
    raw_task = _read(root / "task.json")
    task = Task(
        **dict(
            raw_task,
            allowed_actions=tuple(raw_task["allowed_actions"]),
            required_checks=tuple(
                CheckRequirement(**c) for c in raw_task["required_checks"]
            ),
        )
    )
    proposal = _read(root / "proposal.json")
    if (
        candidate.task_digest != task.digest
        or candidate.digest != observation["candidate_digest"]
        or proposal["action"] != asdict(candidate.action)
        or set(task.allowed_actions) != set(design_learning.ACTIONS)
    ):
        raise ContractError(
            "Decoded action, candidate, or frozen task identity differs"
        )
    receipt = observation["receipt"]
    if receipt["mode"] != "fresh" or receipt["candidate_digest"] != candidate.digest:
        raise ContractError(
            "Comparison requires fresh evidence for the selected candidate"
        )
    for item in receipt["output_artifacts"]:
        Artifact(**item).validate(receipt["output_root"])
    source = Path(candidate.root) / "msh_deq.v"
    result["source_sha256"] = file_sha256(source)
    result["artifacts_verified"] = len(receipt["output_artifacts"])
    result["checkpoint_sha256"] = proposal["checkpoint_sha256"]
    attempt = Path(candidate.root).parent
    physical_record = attempt / "physical-receipt.json"
    if not physical_record.exists():
        return result
    physical_root = Path(_read(physical_record)["output_root"])
    raw = _read(physical_root / "receipt.json")
    actual_checks, selected_stages = flow.collect_checks(physical_root)
    if actual_checks != raw["checks"]:
        raise ContractError("Physical receipt differs from raw tool checks")
    observed = {(c["name"], c["scope"]): c["status"] for c in observation["checks"]}
    if any(observed.get((c["name"], c["scope"])) != c["status"] for c in actual_checks):
        raise ContractError("Campaign physical checks differ from tool receipt")
    differential = _read(attempt / "differential/receipt.json")
    if not (
        file_sha256(attempt / "tool/candidate.v")
        == differential["source_sha256"]
        == file_sha256(physical_root / "msh_deq.v")
        == raw["candidate_sha256"]
        == result["source_sha256"]
    ):
        raise ContractError("Tool stages evaluated different RTL")
    result.update(
        physical_executed=True,
        physical_status=raw["status"],
        physical_ok=raw["ok"],
        physical_receipt_sha256=file_sha256(physical_root / "receipt.json"),
        physical_elapsed_s=raw["elapsed_s"],
        physical_root=str(physical_root),
        config_sha256=raw["config_sha256"],
        image=raw["image"],
        pdk_revision=raw["pdk_revision"],
        cores=raw["cores"],
        runner_sha256=raw["runner_sha256"],
        coverage_script_sha256=file_sha256(physical_root / "coverage.tcl")
        if (physical_root / "coverage.tcl").exists()
        else None,
    )
    if raw["status"] != "completed":
        return result
    result["metrics"] = _selected_physical_metrics(selected_stages)
    gds = physical_root / "runs/physical/final/gds/msh_deq.gds"
    if gds.exists():
        result.update(gds=str(gds), gds_sha256=file_sha256(gds))
    return result


def _read_line(line):
    return json.loads(line)


def compare_outcomes(control: dict, adapted: dict) -> dict:
    """Keep area preference, complete acceptance, and identical designs distinct."""
    result = dict(
        same_design=bool(
            control["source_sha256"]
            and control["source_sha256"] == adapted["source_sha256"]
        ),
        accepted_design_improvement=False,
        area_change_percent=None,
        exploration_area_improved=False,
    )
    if not control.get("metrics") or not adapted.get("metrics"):
        result["reason"] = "At least one arm has no completed physical measurement"
        return result
    for field in (
        "config_sha256",
        "image",
        "pdk_revision",
        "cores",
        "runner_sha256",
        "coverage_script_sha256",
    ):
        if control[field] != adapted[field]:
            raise ContractError("Comparison arms used different physical settings")
    difference = (
        adapted["metrics"]["cell_area_um2"] / control["metrics"]["cell_area_um2"] - 1
    ) * 100
    failures = lambda row: {
        (c["name"], c["scope"], c["status"])
        for c in row["checks"]
        if c["status"] != "pass"
    }

    def admitted(row):
        checks = {
            c["name"]: c["status"]
            for c in row["checks"]
            if c["scope"] == "block:msh_deq"
        }
        required_pass = {"dequant_vectors", "sequential_rtl_differential"} | (
            set(design_experiment.PHYSICAL_CHECKS)
            - {"electrical_constraints", "postroute_antenna"}
        )
        return all(checks.get(name) == "pass" for name in required_pass) and all(
            checks.get(name) in ("pass", "fail")
            for name in design_experiment.PHYSICAL_CHECKS
        )

    result.update(
        area_change_percent=difference,
        exploration_area_improved=bool(
            not result["same_design"]
            and difference < 0
            and admitted(control)
            and admitted(adapted)
            and failures(control) == failures(adapted)
        ),
        accepted_design_improvement=bool(
            not result["same_design"]
            and difference < 0
            and adapted["complete_design_eligible"]
        ),
        same_failed_or_unresolved_checks=failures(control) == failures(adapted),
        scope="One observed case; objective-specific adaptation, not transfer or model superiority",
    )
    return result


def run_feedback_study(
    base_checkpoint: Path,
    corpus_manifest: Path,
    feedback_manifest: Path,
    output: Path,
    *,
    check_timeout=120,
    physical_timeout=900,
    cores=1,
) -> dict:
    """Finish updates, freeze checkpoints, then execute both selected designs."""
    from . import design_feedback_data, design_feedback_learning
    from .contracts import Budget

    if (
        any(not math.isfinite(t) or t <= 0 for t in (check_timeout, physical_timeout))
        or type(cores) is not int
        or not 1 <= cores <= 8
    ):
        raise ContractError("Use positive finite timeouts and 1..8 CPU cores per arm")
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    feedback = design_feedback_data.load_feedback(feedback_manifest)
    historical_config = feedback["candidates"][0]["configuration"]
    present_config = dict(
        config_sha256=file_sha256(flow.CONFIG),
        image=flow.IMAGE,
        pdk_revision=flow.PDK_REVISION,
        runner_sha256=file_sha256(flow.__file__),
        cores=cores,
        coverage_script_sha256=file_sha256(
            Path(flow.__file__).with_name("coverage.tcl")
        ),
    )
    if any(historical_config[key] != value for key, value in present_config.items()):
        raise ContractError(
            "Prospective physical settings differ from admitted historical feedback"
        )
    sources = {
        "orchestrator": Path(__file__),
        "evidence": Path(design_feedback_data.__file__),
        "adaptation": Path(design_feedback_learning.__file__),
        "design": Path(design_experiment.__file__),
        "transform": Path(design_changes.__file__),
        "physical": Path(flow.__file__),
        "physical_config": flow.CONFIG,
        "cli": Path(__file__).with_name("__main__.py"),
    }
    source_hashes = {name: file_sha256(path) for name, path in sources.items()}
    protocol = dict(
        schema_version=1,
        purpose="one-case tool-feedback parameter adaptation and prospective rerun",
        base_checkpoint=str(Path(base_checkpoint).resolve()),
        base_weights_sha256=file_sha256(Path(base_checkpoint) / "checkpoint.pt"),
        feedback_manifest=str(Path(feedback_manifest).resolve()),
        feedback_sha256=file_sha256(feedback_manifest),
        corpus_manifest=str(Path(corpus_manifest).resolve()),
        corpus_sha256=file_sha256(corpus_manifest),
        code=source_hashes,
        check_timeout=check_timeout,
        physical_timeout=physical_timeout,
        cores_per_arm=cores,
        prospective_arms=["control", "adapted"],
        proposals_per_arm=1,
        attempts_per_arm=1,
        concurrency="Two isolated processes, concurrent one-candidate runs; no runtime speed comparison",
        no_update_control="Frozen initial checkpoint prediction, no additional physical execution",
        conventional_control="Measured-area selection from the same admitted feedback, no model updates",
        no_heldout_physical_claim=True,
        no_checkpoint_selection_from_new_tool_results=True,
    )
    _write(root / "protocol.json", protocol)
    protocol_hash = file_sha256(root / "protocol.json")
    (root / "source_code").mkdir()
    for name, path in sources.items():
        shutil.copyfile(path, root / "source_code" / f"{name}{path.suffix}")
    design_feedback_learning.adapt_from_feedback(
        base_checkpoint, corpus_manifest, feedback_manifest, root / "learning"
    )
    if any(file_sha256(path) != source_hashes[name] for name, path in sources.items()):
        raise ContractError("Study implementation changed during adaptation")
    # Predictions for the two trained arms occur only inside their actual design
    # campaigns. No target decoding selects a checkpoint or controls a retry.
    frozen_model = design_proposer(root / "learning/base")
    frozen_action = frozen_model.propose(design_change_task(), (), Budget(1, 1))
    _write(
        root / "no-update.json",
        dict(
            action=asdict(frozen_action),
            prediction=frozen_model.predictions[-1],
            physical_executed=False,
        ),
    )
    frozen_checkpoints = {
        arm: {
            name: file_sha256(root / f"learning/{arm}" / name)
            for name in design_experiment.CHECKPOINT_FILES
        }
        for arm in ("control", "adapted")
    }
    _write(root / "frozen-checkpoints.json", frozen_checkpoints)
    processes, streams = {}, []
    launch = []
    repository = Path(__file__).resolve().parents[2]
    try:
        for arm in ("control", "adapted"):
            command = [
                sys.executable,
                "-m",
                "nanochip.laboratory",
                "design",
                "--checkpoint",
                str(root / f"learning/{arm}"),
                "--output",
                str(root / arm),
                "--check-timeout",
                str(check_timeout),
                "--physical-timeout",
                str(physical_timeout),
                "--cores",
                str(cores),
            ]
            log = (root / f"{arm}.log").open("x")
            streams.append(log)
            process = subprocess.Popen(
                command, cwd=repository, stdout=log, stderr=subprocess.STDOUT
            )
            processes[arm] = process
            launch.append(dict(arm=arm, command=command, pid=process.pid))
        _write(root / "launch.json", launch)
        # Each child enforces its own tool and training budgets. Do not kill only
        # the Python parent and leave an EDA container running in the background.
        exits = {arm: process.wait() for arm, process in processes.items()}
    finally:
        for stream in streams:
            stream.close()
    outcomes = {}
    for arm in ("control", "adapted"):
        for name, digest in frozen_checkpoints[arm].items():
            if file_sha256(root / f"learning/{arm}" / name) != digest:
                raise ContractError(
                    "A prospective result changed the frozen checkpoint"
                )
        if (root / arm / "design-experiment.json").exists():
            outcomes[arm] = inspect_design_run(root / arm)
            if (
                outcomes[arm].get("checkpoint_sha256") is not None
                and outcomes[arm]["checkpoint_sha256"]
                != frozen_checkpoints[arm]["checkpoint.pt"]
            ):
                raise ContractError(
                    "Executed checkpoint differs from the assigned frozen arm"
                )
            if outcomes[arm].get("physical_status") == "completed" and any(
                outcomes[arm].get(key) != value for key, value in present_config.items()
            ):
                raise ContractError(
                    "Executed physical settings differ from admitted historical feedback"
                )
        else:
            outcomes[arm] = dict(
                action=None,
                execution_status="error",
                metrics=None,
                source_sha256=None,
                complete_design_eligible=False,
                physical_executed=False,
                details="Child did not produce a final campaign; inspect retained log and partial artifacts",
            )
        outcomes[arm]["process_returncode"] = exits[arm]
    if file_sha256(root / "protocol.json") != protocol_hash:
        raise ContractError("Frozen study protocol changed")
    result = dict(
        schema_version=1,
        protocol_sha256=protocol_hash,
        feedback_sha256=protocol["feedback_sha256"],
        learning_report=str(root / "learning/report.json"),
        no_update=_read(root / "no-update.json"),
        conventional_action=feedback["selected_action"],
        outcomes=outcomes,
        comparison=compare_outcomes(outcomes["control"], outcomes["adapted"]),
        total_wall_seconds=time.perf_counter() - started,
        limits=[
            "Feedback case is training data, including when tools are run freshly",
            "Both actions are authored implementations; retention is a valid learned response",
            "Comparison measures a label intervention on one case, not model superiority",
            "Every failed or unresolved physical/core obligation remains binding",
        ],
    )
    _write(root / "feedback-study.json", result)
    return result
