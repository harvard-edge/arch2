"""Explicit, hash-bound reuse of completed CTS views for engineering trials."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil

from ..contracts import Artifact, ContractError, file_sha256
from .clock_flow import PROFILE, STEP_ID


STRATEGY_KEYS = {
    "meta",
    "NANOCHIP_CLOCK_BRANCH_SIZE",
    "NANOCHIP_CLOCK_BRANCH_CELL",
    "NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE",
    "NANOCHIP_SIGNAL_WORKING_TRANSITION",
    "NANOCHIP_SIGNAL_WORKING_CAPACITANCE",
    "NANOCHIP_SIGNAL_RESIDUAL_MAX_WIRE_LENGTH",
    "NANOCHIP_CLOCK_BUFFER_INPUTS",
    "NANOCHIP_POST_CTS_HOLD_REPAIR",
    "RUN_POST_CTS_RESIZER_TIMING",
    "PL_RESIZER_SETUP_SLACK_MARGIN",
    "PL_RESIZER_HOLD_SLACK_MARGIN",
    "PL_RESIZER_GATE_CLONING",
}


def prepare_cts_checkpoint(parent, output, *, runtime_root, image, pdk_revision):
    """Copy exact parent views into an existing new run; never edit the parent.

    The child must declare the clock-repair profile. Only its engineering
    strategy settings may differ; source, geometry and acceptance constraints
    retain their identities. This is explicit checkpoint reuse, never fresh P&R.
    """
    parent, output = Path(parent).resolve(strict=True), Path(output).resolve(
        strict=True
    )
    raw_path = parent / "receipt.json"
    raw = json.loads(raw_path.read_text())
    if raw.get("image") != image or raw.get("pdk_revision") != pdk_revision:
        raise ContractError("Checkpoint tool/PDK identities differ")
    if (
        raw.get("design_name") != "nanochip_teaching_core"
        or raw.get("scope") != "accelerator:nanochip_teaching_core"
    ):
        raise ContractError(
            "CTS continuation currently requires the complete teaching core"
        )
    manifest = {item["path"]: item["sha256"] for item in raw["artifacts"]}
    for item in raw["artifacts"]:
        Artifact(**item).validate(parent)

    def parent_artifact(relative):
        path = parent / relative
        if manifest.get(relative) != file_sha256(path):
            raise ContractError(
                "Checkpoint input is not bound to its producer: " + relative
            )
        return path

    parent_config = json.loads(parent_artifact("config.json").read_text())
    config = json.loads((output / "config.json").read_text())
    if config.get("meta", {}).get("flow") != PROFILE:
        raise ContractError(
            "CTS continuation requires the manifested clock-repair profile"
        )
    if {k: v for k, v in config.get("meta", {}).items() if k != "flow"} != {
        k: v for k, v in parent_config.get("meta", {}).items() if k != "flow"
    }:
        raise ContractError(
            "Checkpoint metadata changes are limited to the declared flow identity"
        )
    if {k: v for k, v in config.items() if k not in STRATEGY_KEYS} != {
        k: v for k, v in parent_config.items() if k not in STRATEGY_KEYS
    }:
        raise ContractError(
            "Checkpoint reuse cannot change source geometry or acceptance configuration"
        )
    core = parent_artifact("core.v")
    if file_sha256(core) != file_sha256(output / "core.v") or raw.get(
        "source_manifest"
    ) != [asdict(Artifact.from_file(parent, "core.v"))]:
        raise ContractError("Checkpoint and child RTL sources differ")
    stages = sorted((parent / "runs/physical").glob("*-openroad-cts"))
    if len(stages) != 1:
        raise ContractError("Exactly one completed CTS checkpoint is required")
    stage_relative = str((stages[0] / "state_out.json").relative_to(parent))
    state_path = parent_artifact(stage_relative)
    state = json.loads(state_path.read_text())
    if not state.get("odb") or not state.get("sdc"):
        raise ContractError("CTS database and constraints must both be retained")
    checkpoint = output / "checkpoint"
    checkpoint.mkdir(exist_ok=False)
    (checkpoint / "parent").mkdir()
    result = {
        "schema": "nanochip-physical-checkpoint/v1",
        "upstream_evidence_mode": "reused_checkpoint",
        "start_at": STEP_ID,
        "parent_stage_state_path": stage_relative,
        "config_patch": {
            key: value
            for key, value in config.items()
            if parent_config.get(key) != value
        },
        "copied_views": [],
    }

    def retain(source, target, label):
        path = output / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
        result[label + "_path"] = target
        result[label + "_sha256"] = file_sha256(path)

    retain(raw_path, "checkpoint/parent/receipt.json", "parent_receipt")
    retain(core, "checkpoint/parent/core.v", "parent_core")
    retain(parent / "config.json", "checkpoint/parent/config.json", "parent_config")
    retain(state_path, "checkpoint/original-state.json", "original_state")
    if (parent / "engineering-cancellation.json").is_file():
        retain(
            parent / "engineering-cancellation.json",
            "checkpoint/parent/cancellation.json",
            "parent_cancellation",
        )
    copied = {}

    def rewrite(value):
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if not isinstance(value, str):
            return value
        # All nonmetric state strings are design-view paths.
        if value.startswith("/work/"):
            relative = value.removeprefix("/work/")
        elif "/runs/physical/" in value:
            relative = "runs/physical/" + value.split("/runs/physical/", 1)[1]
        else:
            raise ContractError("Unsupported checkpoint view path: " + value)
        source = parent_artifact(relative)
        target = "checkpoint/views/" + relative
        if target not in copied:
            path = output / target
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
            item = {
                "path": target,
                "sha256": file_sha256(path),
                "parent_path": relative,
            }
            result["copied_views"].append(item)
            copied[target] = item
        return runtime_root.rstrip("/") + "/" + target

    rewritten = {
        key: state[key] if key == "metrics" else rewrite(value)
        for key, value in state.items()
    }
    (checkpoint / "state.json").write_text(
        json.dumps(rewritten, indent=2, sort_keys=True) + "\n"
    )
    result.update(
        rewritten_state_path="checkpoint/state.json",
        rewritten_state_sha256=file_sha256(checkpoint / "state.json"),
    )
    path = checkpoint / "checkpoint.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return {
        "manifest_path": "checkpoint/checkpoint.json",
        "manifest_sha256": file_sha256(path),
    }
