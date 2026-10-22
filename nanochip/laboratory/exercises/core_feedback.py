"""Fresh complete-core failure, feedback-directed restoration, and control.

This is an explicitly authored teaching fault and conventional feedback policy.
It demonstrates inference-time control after a failed check, not model training,
model-discovered repair, architectural optimization, or physical acceptance.
"""

from dataclasses import asdict, replace
import difflib
import json
import math
from pathlib import Path
import shutil
import struct
import time

from ..contracts import Action, Artifact, Candidate, ContractError, file_sha256
from ..evidence import JsonlRecorder
from ..runner import run_campaign
from ..teaching_core.backend import (
    ACTIONS as CORE_ACTIONS,
    ROOT,
    SCOPE,
    TeachingCoreBackend,
    TeachingCoreMaterializer,
    make_task,
)


FAULT = "construct_store_bit_fault"
REPAIR = "restore_exact_store"
ACTIONS = (FAULT, REPAIR)
ANCHOR = "mem_req_wdata={96'd0,store_value} << {data_address[3:0],3'b0};"
MUTATION = "mem_req_wdata={96'd0,(store_value ^ ((data_address >= 36'd__START__ && data_address < 36'd__END__) ? 32'd1 : 32'd0))} << {data_address[3:0],3'b0};"
PROVENANCE = "author-constructed logit-store low-bit fault; not an upstream Kimi bug or model discovery"


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _check(observation, name):
    return next(
        (
            check
            for check in observation.checks
            if check.name == name and check.scope == SCOPE
        ),
        None,
    )


def _logit_range(root):
    image = (root / "reference/image.bin").read_bytes()
    if len(image) < struct.calcsize("<64I"):
        raise ContractError("Teaching fault requires the canonical packed-image header")
    header = struct.unpack_from("<64I", image)
    base = json.loads((root / "program.json").read_text())["data_base"]
    start, end = header[25], header[25] + struct.calcsize("<i") * header[17]
    if (
        header[19] != 1
        or header[17] < 1
        or start < struct.calcsize("<64I")
        or end > len(image)
        or start % struct.calcsize("<i")
        or any(
            start < offset + struct.calcsize("<I") and offset < end
            for offset in (header[26], header[27])
        )
    ):
        raise ContractError(
            "Teaching fault requires one isolated logit output region, excluding argmax/status"
        )
    return base + start, base + end


class CoreFeedbackPolicy:
    """Choose restoration only after a fresh, completed exact-numerical failure."""

    def propose(self, task, history, budget):
        if not history:
            return Action(FAULT)
        last = history[-1]
        failed = _check(last, "exact_integer_logits")
        if (
            last.action
            and last.action.name == FAULT
            and last.status == "success"
            and last.receipt
            and last.receipt.mode == "fresh"
            and failed
            and failed.status == "fail"
        ):
            return Action(REPAIR)
        return None


class HiddenFeedbackPolicy:
    """Keep action/turn identity but withhold every returned measurement."""

    def propose(self, task, history, budget):
        masked = tuple(
            replace(
                item,
                checks=(),
                receipt=None,
                eligible=False,
                details="Measurements withheld for the negative control",
            )
            for item in history
        )
        return CoreFeedbackPolicy().propose(task, masked, budget)


class CoreFaultMaterializer:
    """Reuse the normal core builder, then transform only a private RTL copy.

    Both authored exercise actions map to the same serial_mul2 implementation.
    The canonical builder's task is retained, while the executed candidate is
    explicitly rebound to the exercise task/action and its mutation provenance.
    The ordinary complete-workload backend and oracle remain unchanged.
    """

    def materialize(self, task, action, workspace):
        if action.name not in ACTIONS or action.parameters:
            raise ContractError(
                "Use only the two declared teaching actions, without parameters"
            )
        source = Path(__file__).resolve()
        relative = str(source.relative_to(ROOT))
        if file_sha256(source) != task.specification["source_artifacts"][relative]:
            raise ContractError("Teaching transformation changed after task freeze")
        canonical_task = replace(task, allowed_actions=CORE_ACTIONS)
        canonical = TeachingCoreMaterializer().materialize(
            canonical_task, Action("serial_mul2"), workspace
        )
        root = Path(canonical.root)
        shutil.copyfile(
            root / "task.json", root / "canonical-materialization-task.json"
        )
        reference = (root / "core.v").read_text()
        if reference.count(ANCHOR) != 1:
            raise ContractError("Teaching store-data anchor must occur exactly once")
        logit_start, logit_end = _logit_range(root)
        mutation = MUTATION.replace("__START__", str(logit_start)).replace(
            "__END__", str(logit_end)
        )
        changed = (
            reference.replace(ANCHOR, mutation, 1)
            if action.name == FAULT
            else reference
        )
        (root / "reference-core.v").write_text(reference)
        (root / "core.v").write_text(changed)
        (root / "task.json").write_text(json.dumps(asdict(task), indent=2) + "\n")
        (root / "change.diff").write_text(
            "".join(
                difflib.unified_diff(
                    reference.splitlines(keepends=True),
                    changed.splitlines(keepends=True),
                    fromfile="canonical/core.v",
                    tofile=f"{action.name}/core.v",
                )
            )
        )
        shutil.copyfile(source, root / "teaching-transformation.py")
        _write(
            root / "teaching-transformation.json",
            dict(
                action=asdict(action),
                canonical_action="serial_mul2",
                provenance=PROVENANCE,
                reference_sha256=file_sha256(root / "reference-core.v"),
                candidate_sha256=file_sha256(root / "core.v"),
                transformer_sha256=file_sha256(source),
                mutation=dict(
                    old=ANCHOR,
                    new=mutation,
                    absolute_logit_start=logit_start,
                    absolute_logit_end_exclusive=logit_end,
                )
                if action.name == FAULT
                else None,
                policy="authored feedback-aware conventional controller; no model checkpoint",
            ),
        )
        return Candidate(
            action.name,
            task.task_id,
            str(root),
            action,
            tuple(
                Artifact.from_file(root, str(path.relative_to(root)))
                for path in sorted(root.rglob("*"))
                if path.is_file()
            ),
            task_digest=task.digest,
        )


def _fresh_failure(observation):
    check = _check(observation, "exact_integer_logits")
    return bool(
        observation.status == "success"
        and observation.receipt
        and observation.receipt.mode == "fresh"
        and check
        and check.status == "fail"
    )


def run_core_feedback(output, *, seed=7, timeout=180, policy=None):
    """Run two feedback-directed candidates plus a fresh hidden-feedback control."""
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ContractError("Use a finite positive complete-core timeout")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    task = make_task(seed=seed, prompt_index=0, split="development", tokens=[1])
    sources = dict(task.specification["source_artifacts"])
    sources[str(Path(__file__).resolve().relative_to(ROOT))] = file_sha256(__file__)
    task = replace(
        task,
        task_id=task.task_id + "-constructed-store-feedback",
        allowed_actions=ACTIONS,
        max_attempts=2,
        max_proposals=3,
        specification=dict(
            task.specification,
            source_artifacts=sources,
            teaching_fault=dict(
                provenance=PROVENANCE,
                old=ANCHOR,
                new=MUTATION,
                canonical_action="serial_mul2",
            ),
            check_timeout=timeout,
        ),
    )
    _write(output / "task.json", asdict(task))
    try:
        materializer, backend = CoreFaultMaterializer(), TeachingCoreBackend(
            timeout_s=timeout
        )
        observed = run_campaign(
            task,
            policy or CoreFeedbackPolicy(),
            materializer,
            backend,
            output / "feedback",
            JsonlRecorder(output / "feedback-events.jsonl"),
        )
        hidden = run_campaign(
            task,
            HiddenFeedbackPolicy(),
            materializer,
            backend,
            output / "hidden-feedback",
            JsonlRecorder(output / "hidden-feedback-events.jsonl"),
        )
        observations = observed.observations
        paths = [
            output / "feedback" / f"attempt-{index:04d}" / "candidate"
            for index in range(1, observed.attempts_used + 1)
        ]
        unchanged_names = (
            "program.bin",
            "tables.bin",
            "reference/image.bin",
            "core_tb.cpp",
            "rtl.py",
            "backend.py",
            "reference-core.v",
        )
        inputs = {
            name: [
                file_sha256(path / name) for path in paths if (path / name).is_file()
            ]
            for name in unchanged_names
        }
        same_workload_and_oracles = len(paths) == 2 and all(
            len(set(values)) == 1 for values in inputs.values()
        )
        changed_action = (
            len(observations) == 2
            and observations[0].action == Action(FAULT)
            and observations[1].action == Action(REPAIR)
        )
        repaired = bool(len(observations) == 2 and observations[1].eligible)
        control_stopped = (
            len(hidden.observations) == 1
            and hidden.observations[0].action == Action(FAULT)
            and _fresh_failure(hidden.observations[0])
            and hidden.stop_reason == "proposer_stopped"
        )
        demonstrated = bool(
            changed_action
            and _fresh_failure(observations[0])
            and repaired
            and same_workload_and_oracles
            and control_stopped
        )
        report = dict(
            schema_version=1,
            status="completed" if demonstrated else "engineering_failed",
            success=demonstrated,
            scope=SCOPE,
            provenance=PROVENANCE,
            policy="authored conventional feedback controller; no model trained or loaded",
            workload=dict(
                seed=seed,
                tokens=[1],
                layers=task.specification["target"]["configuration"]["layer_pattern"],
                profiles=task.specification["profiles"],
            ),
            feedback_campaign=asdict(observed),
            hidden_feedback_campaign=asdict(hidden),
            changed_action=changed_action,
            repair_passed_all_required_checks=repaired,
            hidden_feedback_prevented_repair=control_stopped,
            same_workload_and_oracles=same_workload_and_oracles,
            input_hashes=inputs,
            total_wall_seconds=time.perf_counter() - started,
            limits=[
                "Constructed store-data fault, not an original Kimi defect or learned repair",
                "One token executes the complete two-layer teaching derivative; no multi-token transfer claim",
                "Same unchanged complete-core check suite and three memory/reset profiles; finite simulation only",
                "Hidden-feedback control uses the same candidate budget but stops without a repair; actual costs differ",
                "No physical implementation or GDS/closure claim; this complements the separate weight-update campaign",
            ],
        )
        _write(output / "report.json", report)
        lines = [
            "# Complete-core feedback exercise",
            "",
            f"Status: **{report['status']}**.",
            "",
            "An authored controller first runs a constructed store-data fault. A fresh exact-logit failure triggers restoration of the canonical store path.",
            "",
            "| Arm | Action | Execution | Exact logits | Eligible for declared functional checks |",
            "| --- | --- | --- | --- | --- |",
        ]
        for arm, campaign in (
            ("feedback visible", observed),
            ("feedback hidden", hidden),
        ):
            for item in campaign.observations:
                check = _check(item, "exact_integer_logits")
                lines.append(
                    f"| {arm} | {item.action.name if item.action else 'none'} | {item.status} | "
                    f"{check.status if check else 'unresolved'} | {item.eligible} |"
                )
        lines += [
            "",
            f"Same workload/oracle hashes: {same_workload_and_oracles}. Hidden feedback prevented restoration: {control_stopped}.",
            "",
            "[Raw campaigns and checks](report.json), [frozen task and authored fault](task.json), [visible-feedback events](feedback-events.jsonl), [negative-control events](hidden-feedback-events.jsonl).",
            "",
            "This demonstrates inference-time feedback control. It does not demonstrate model discovery, parameter adaptation, or physical acceptance.",
        ]
        (output / "report.md").write_text("\n".join(lines) + "\n")
        return report
    except Exception as exc:
        _write(
            output / "failure.json",
            dict(
                error_type=type(exc).__name__,
                error=str(exc),
                total_wall_seconds=time.perf_counter() - started,
            ),
        )
        raise


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", default=7, type=int)
    parser.add_argument("--timeout", default=180, type=float)
    args = parser.parse_args(argv)
    report = run_core_feedback(args.output, seed=args.seed, timeout=args.timeout)
    print(f"Constructed complete-core feedback exercise: {report['status']}")
    print(
        f"Failure changed action: {report['changed_action']}; repaired checks passed: {report['repair_passed_all_required_checks']}"
    )
    print(
        f"Hidden-feedback control prevented repair: {report['hidden_feedback_prevented_repair']}"
    )
    print(
        "Authored fault and conventional policy; no model discovery or physical execution."
    )
    print(f"Retained report: {args.output.resolve() / 'report.md'}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
