"""Audit retained outputs when a completed tool flow outlives its driver error."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from ..contracts import Artifact, file_sha256
from . import flow


def audit_retained_run(output: str | Path, driver_error_log: str | Path, driver_exitcode: int,
                       *, requested_timeout_s: float | None = None, requested_cores: int | None = None) -> dict:
    """Preserve the original failure and issue a separately identified audit.

    This is not a successful fresh RunReceipt, and it never grants eligibility.
    Per-stage check results describe retained files, not repaired execution.
    """
    output = Path(output).resolve(strict=True)
    target = output / "audited-receipt.json"
    if target.exists():
        raise FileExistsError(target)
    shutil.copyfile(driver_error_log, output / "original-driver-error.log")
    shutil.copyfile(flow.__file__, output / "audit-validator.py")
    shutil.copyfile(__file__, output / "audit.py")
    checks, stages = flow.collect_checks(output)
    raw_log = output / "runs/physical/flow.log"
    metrics = stages.get("openroad-stapostpnr", {}).get("metrics", {})
    config = json.loads((output / "config.json").read_text())
    coverage_path = output / "coverage-receipt.json"
    result = dict(
        schema="nanochip-retained-physical-audit/v1", mode="retained_audit",
        audit_timestamp=datetime.now(timezone.utc).isoformat(), eligible=False, ok=False,
        original_driver_status="error" if driver_exitcode else "success", original_driver_exitcode=driver_exitcode,
        original_driver_failure="See retained original-driver-error.log; this audit does not repair the original execution status",
        tool_flow_completion_marker_observed="Flow complete." in raw_log.read_text(),
        image=flow.IMAGE, pdk="sky130A", pdk_revision=flow.PDK_REVISION, standard_cell_library="sky130_fd_sc_hd",
        declared_config=config, declared_clock_ns=config["CLOCK_PERIOD"], declared_core_utilization_pct=config["FP_CORE_UTIL"],
        declared_placement_density_pct=config["PL_TARGET_DENSITY_PCT"], requested_timeout_s=requested_timeout_s, requested_cpu_limit=requested_cores,
        source_sha256=file_sha256(output / "msh_deq.v"), original_runner_sha256=file_sha256(output / "runner.py"),
        audit_validator_sha256=file_sha256(output / "audit-validator.py"), checks=checks, stages=stages,
        postroute_metrics={key: metrics.get(key) for key in (
            "timing__setup__ws", "timing__hold__ws", "timing__setup_vio__count", "timing__hold_vio__count",
            "design__max_slew_violation__count", "design__max_cap_violation__count", "design__max_fanout_violation__count",
            "design__instance__area", "design__die__area", "design__core__area", "design__instance__count")},
        coverage_receipt_sha256=file_sha256(coverage_path) if coverage_path.is_file() else None,
        final_gds="runs/physical/final/gds/msh_deq.gds", layout_preview="layout.png",
        boundary=flow.BOUNDARY,
        interpretation="Individual retained stage checks are listed explicitly. Original driver status remains separate. No complete accelerator or manufacturing acceptance.",
    )
    result["artifacts"] = [asdict(Artifact.from_file(output, str(p.relative_to(output))))
                           for p in sorted(output.rglob("*")) if p.is_file() and not p.is_symlink()]
    flow._json(target, result)
    return result
