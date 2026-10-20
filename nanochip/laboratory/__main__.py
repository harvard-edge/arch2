"""Nanochip: build and inspect a learned architecture-design system."""

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .contracts import Artifact, ContractError

def doctor() -> dict:
    tools = {}
    for name in ("verilator", "make", "c++", "yosys", "openroad", "klayout", "docker"):
        path = shutil.which(name)
        version = None
        if path:
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=4)
                lines = (result.stdout or result.stderr).splitlines()
                version = lines[0] if lines else "version unavailable"
            except (OSError, subprocess.TimeoutExpired):
                version = "version unavailable"
        tools[name] = dict(path=path, version=version)
    return {
        "python": platform.python_version(), "system": platform.system(),
        "machine": platform.machine(), "tools": tools,
        "block_probe_prerequisites_found": all(tools[n]["path"] for n in ("verilator", "make", "c++")),
        "learner_implemented": True, "torch_available": importlib.util.find_spec("torch") is not None,
        "language_model_pretraining_implemented": True,
        "complete_teaching_workload_rtl_implemented": True,
        "physical_backend_implemented": True, "complete_accelerator_physical_flow_implemented": True,
        "physical_acceptance_requires_candidate_receipt": True,
        "note": "Physical acceptance requires a passing receipt for the exact candidate from the configured platform.",
    }


def write_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def run(args) -> int:
    from .adapters import DequantMaterializer, ReferenceProposer, VerilatorBackend, starter_task
    from .evidence import JsonlRecorder
    from .runner import run_campaign
    from .student import StudentProposer

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    task = starter_task()
    write_json(output / "environment.json", doctor())
    policy = StudentProposer() if args.policy == "student" else ReferenceProposer()
    started = time.perf_counter()
    campaign = run_campaign(task, policy, DequantMaterializer(), VerilatorBackend(args.timeout),
                            output / "attempts", JsonlRecorder(output / "events.jsonl"))
    elapsed = time.perf_counter() - started
    report = {
        "schema_version": 1, "policy": args.policy, "learned_policy": False,
        "scope": "one dequantizer block; no complete-workload or physical execution",
        "campaign_wall_seconds": elapsed, "campaign": asdict(campaign),
        "complete_design_eligible": any(o.eligible for o in campaign.observations),
    }
    write_json(output / "campaign.json", report)
    rows = []
    for i, observation in enumerate(campaign.observations):
        if observation.receipt and observation.receipt.output_root:
            receipt_path = Path(observation.receipt.output_root) / "receipt.json"
            artifact = Artifact.from_file(output, receipt_path.relative_to(output).as_posix())
            rows.append(dict(
                record_id=f"dequant-{i}", group_id="dequant-shift-saturation-family-v1",
                split="train", evidence_mode="fresh",
                construction="constructed_fault" if observation.action.name == "teaching_fault" else "reference",
                source="Nanochip development probe; see candidate and raw tool receipts",
                receipt=asdict(artifact),
            ))
    if rows:
        write_json(output / "dataset.json", dict(
            schema_version=1, dataset_id="nanochip-starter-observations-v1", records=rows,
            purpose="Collection example only; no optimal-action labels or independent evaluation partition",
        ))
    failed = any(o.status != "success" for o in campaign.observations)
    print(f"Policy: {args.policy} (no learned model)")
    for observation in campaign.observations:
        name = observation.action.name if observation.action else "no action"
        checks = ", ".join(f"{c.name}={c.status}" for c in observation.checks)
        print(f"  {name}: execution={observation.status}; {checks}")
        if observation.details and observation.status != "success":
            print(f"    {observation.details}")
    print(f"Campaign: {elapsed:.3f} s; report: {output / 'campaign.json'}")
    print("Complete accelerator/GDS: unresolved. No model learning or design speedup claimed.")
    return 1 if failed or not campaign.observations else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    components = {
        "language": (".language_cli", "inspect data, pretrain, adapt, and use a byte language model"),
        "core": (".teaching_core.__main__", "compile and execute the complete teaching workload"),
        "core-feedback": (".exercises.core_feedback", "observe a real numerical failure trigger an authored repair policy"),
        "course": (".course.__main__", "build cumulative student components in one workspace"),
        "system": (".campaign", "run the connected learning and design comparison"),
        "launch": (".launch", "run a cached full container with a retained output directory"),
    }
    if argv and argv[0] in components:
        from importlib import import_module
        try:
            return import_module(components[argv[0]][0], __package__).main(argv[1:])
        except (OSError, ValueError, ContractError, RuntimeError) as exc:
            print(f"nanochip {argv[0]}: {exc}", file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description=__doc__)
    from nanochip import __version__
    parser.add_argument("--version", action="version", version=f"Nanochip {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, description) in components.items():
        sub.add_parser(name, help=description)
    sub.add_parser("doctor", help="inspect installed tools; install nothing")
    sub.add_parser("labs", help="show the cumulative component map")
    demo = sub.add_parser("demo", help="run the earlier block alpha demonstration; use system for the complete workload")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--physical", action="store_true", help="also run the pinned block GDS flow; requires the cached image")
    demo.add_argument("--transformer", choices=("supplied", "student"), default="supplied")
    demo.add_argument("--check-timeout", type=float, default=120)
    demo.add_argument("--physical-timeout", type=float, default=900)
    demo.add_argument("--cores", type=int, default=1)
    for command in ("probe", "run"):
        item = sub.add_parser(command)
        item.add_argument("--output", required=True, type=Path)
        item.add_argument("--timeout", type=float, default=120, help="seconds per candidate build and simulation")
        if command == "probe":
            item.add_argument("--candidate", choices=("reference", "teaching_fault"), default="reference")
        else:
            item.add_argument("--policy", choices=("reference", "student"), default="reference")
    check = sub.add_parser("dataset-check")
    check.add_argument("manifest", type=Path)
    check.add_argument("--split", choices=("train", "dev", "test"), default="train")
    corpus = sub.add_parser("collect", help="execute the constructed diagnostic corpus")
    corpus.add_argument("--output", type=Path, required=True)
    corpus.add_argument("--timeout", type=float, default=120)
    learn = sub.add_parser("learn", help="train, adapt, and evaluate the small diagnostic decoder")
    learn.add_argument("--corpus", type=Path, required=True)
    learn.add_argument("--output", type=Path, required=True)
    learn.add_argument("--context", choices=("none", "keyword"), default="none")
    learn.add_argument("--train-seconds", type=float, default=30)
    learn.add_argument("--adapt-seconds", type=float, default=15)
    diagnosis = sub.add_parser("diagnose", help="execute a decoded diagnostic on retained evidence")
    diagnosis.add_argument("--corpus", type=Path, required=True)
    diagnosis.add_argument("--record", required=True)
    diagnosis.add_argument("--checkpoint", type=Path)
    diagnosis.add_argument("--context", choices=("none", "keyword"), default="none")
    diagnosis.add_argument("--output", type=Path, required=True)
    physical = sub.add_parser("physical", help="run the pinned block RTL-to-GDS flow offline")
    physical.add_argument("--rtl", type=Path)
    physical.add_argument("--output", type=Path, required=True)
    physical.add_argument("--timeout", type=float, default=900)
    design_train = sub.add_parser("design-train", help="train the small design-action proposer on disclosed constructed tasks")
    design_train.add_argument("--output", type=Path, required=True)
    design = sub.add_parser("design", help="execute the learned RTL change through functional checks and GDS")
    design.add_argument("--checkpoint", type=Path, required=True)
    design.add_argument("--output", type=Path, required=True)
    design.add_argument("--transformer", choices=("supplied", "student"), default="supplied")
    design.add_argument("--check-timeout", type=float, default=120)
    design.add_argument("--physical-timeout", type=float, default=900)
    design.add_argument("--cores", type=int, default=1)
    feedback_collect = sub.add_parser("feedback-collect", help="audit prior tool results and derive an explicit exploration preference")
    feedback_collect.add_argument("--baseline-run", type=Path, required=True)
    feedback_collect.add_argument("--prior-run", type=Path, required=True)
    feedback_collect.add_argument("--output", type=Path, required=True)
    feedback = sub.add_parser("feedback", help="adapt from audited tool feedback, then execute control and adapted designs")
    feedback.add_argument("--checkpoint", type=Path, required=True)
    feedback.add_argument("--corpus", type=Path, required=True)
    feedback.add_argument("--feedback", type=Path, required=True)
    feedback.add_argument("--output", type=Path, required=True)
    feedback.add_argument("--check-timeout", type=float, default=120)
    feedback.add_argument("--physical-timeout", type=float, default=900)
    feedback.add_argument("--cores", type=int, default=1, help="CPU cores per physical arm; two arms run concurrently")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            from .demo import run_demo
            transformer = None
            if args.transformer == "student":
                from .exercises.student_design import transform
                transformer = transform
            print("Nanochip: collect tool evidence, train, adapt, infer, and check the selected RTL.", flush=True)
            if args.physical:
                print("Physical mode includes a fresh block implementation; inspect all returned checks.", flush=True)
            result = run_demo(args.output, physical=args.physical, transformer=transformer,
                              check_timeout=args.check_timeout,
                              physical_timeout=args.physical_timeout, cores=args.cores)
            print(f"Status: {result['status']}")
            print(f"Selected action: {result['design']['selected_action']}; source changed: {result['design']['source_changed']}")
            for check in result["checks"]:
                print(f"  {check['name']} [{check['scope']}]: {check['status']}")
            print(f"Elapsed: {result['total_wall_seconds']:.3f} s")
            print(f"Report: {args.output.resolve() / 'report.md'}")
            return 0 if result["success"] else 1
        elif args.command == "doctor":
            print(json.dumps(doctor(), indent=2))
        elif args.command == "labs":
            from .course.registry import LABS
            for lab in LABS:
                print(f"{lab.number}. {lab.title}\n   {lab.student_file}: {lab.component}")
        elif args.command == "dataset-check":
            from .data import load_dataset
            entries = load_dataset(args.manifest, split=args.split)
            print(f"Validated {len(entries)} {args.split} entries. Label quality and coverage are not established.")
        elif args.command == "probe":
            from .adapters import SOURCES
            from .dequant_probe import run_probe
            result = run_probe(SOURCES[args.candidate], args.output, args.timeout)
            print(json.dumps({k: result.get(k) for k in (
                "scope", "mode", "status", "ok", "checks", "total_elapsed_s", "limits",
            )}, indent=2))
            print(f"Receipt: {args.output.resolve() / 'receipt.json'}")
            return 0 if result["ok"] else 1
        elif args.command == "collect":
            from .datasets.dequant_corpus import collect_corpus
            result = collect_corpus(args.output, timeout_s=args.timeout)
            print(json.dumps({k: result[k] for k in ("counts", "action_counts", "total_wall_seconds", "limits")}, indent=2))
        elif args.command == "learn":
            from .experiments import learning_study
            result = learning_study(args.corpus, args.output, context=args.context,
                                    train_seconds=args.train_seconds, adapt_seconds=args.adapt_seconds)
            print(json.dumps({k: result[k] for k in ("base_evaluation", "adapted_evaluation", "majority_baseline", "total_wall_seconds", "limits")}, indent=2))
            print(f"Study: {args.output.resolve() / 'study.json'}")
        elif args.command == "diagnose":
            from .experiments import diagnose
            result = diagnose(args.corpus, args.record, args.output,
                              checkpoint=args.checkpoint, context=args.context)
            print(json.dumps(dict(policy=result["policy"], scope=result["scope"],
                                 actions=[o["action"]["name"] if o["action"] else None
                                          for o in result["campaign"]["observations"]]), indent=2))
            print(f"Report: {args.output.resolve() / 'diagnosis.json'}")
            observations = result["campaign"]["observations"]
            failed = not observations or any(
                o["status"] != "success" or any(c["status"] == "fail" for c in o["checks"])
                for o in observations)
            return 1 if failed else 0
        elif args.command == "physical":
            from .adapters import SOURCES
            from .physical import run_physical
            result = run_physical(args.rtl or SOURCES["reference"], args.output, timeout_s=args.timeout)
            print(json.dumps({k: result[k] for k in ("status", "ok", "boundary", "checks")}, indent=2))
            return 0 if result["ok"] else 1
        elif args.command == "design-train":
            from .design_learning import collect_design_examples, train_design_proposer
            args.output.mkdir(parents=True, exist_ok=False)
            corpus = collect_design_examples(args.output / "corpus")
            result = train_design_proposer(corpus, args.output / "model")
            print(json.dumps(dict(checkpoint=result["checkpoint_dir"], scope=result["scope"],
                diagnostics={split:{key:values[key] for key in
                    ("exact_action_accuracy", "majority_action_accuracy", "per_action_accuracy")}
                    for split,values in result["diagnostics"].items()}), indent=2))
        elif args.command == "feedback-collect":
            from .design_feedback_data import collect_feedback
            result = collect_feedback(args.baseline_run, args.prior_run, args.output)
            print(json.dumps({key:result[key] for key in ("selected_action", "case_count", "accepted", "boundary")}, indent=2))
            print(f"Feedback: {args.output.resolve() / 'manifest.json'}")
        elif args.command == "feedback":
            from .design_feedback import run_feedback_study
            result = run_feedback_study(args.checkpoint, args.corpus, args.feedback, args.output,
                check_timeout=args.check_timeout, physical_timeout=args.physical_timeout, cores=args.cores)
            print(json.dumps(dict(comparison=result["comparison"],
                actions={arm:row["action"] for arm,row in result["outcomes"].items()},
                metrics={arm:row["metrics"] for arm,row in result["outcomes"].items()}), indent=2))
            print(f"Study: {args.output.resolve() / 'feedback-study.json'}")
            return 0 if all(row["complete_design_eligible"] for row in result["outcomes"].values()) else 1
        elif args.command == "design":
            from .design_experiment import run_design_experiment
            transformer = None
            if args.transformer == "student":
                from .exercises.student_design import transform
                transformer = transform
            result = run_design_experiment(args.checkpoint, args.output,
                check_timeout=args.check_timeout, physical_timeout=args.physical_timeout,
                cores=args.cores, transformer=transformer)
            observations = result["campaign"]["observations"]
            print(json.dumps(dict(source_changed=result["source_changed"],
                complete_design_eligible=result["complete_design_eligible"],
                actions=[o["action"] for o in observations],
                checks=[o["checks"] for o in observations],
                details=[o["details"] for o in observations]), indent=2))
            print(f"Report: {args.output.resolve() / 'design-experiment.json'}")
            # Unresolved full-core obligations do not mean the scoped command failed.
            return 1 if not observations or any(o["status"] != "success" or any(
                c["scope"] == "block:msh_deq" and c["status"] != "pass"
                for c in o["checks"] if c["name"] != "rtl_netlist_correspondence") for o in observations) else 0
        else:
            return run(args)
    except (OSError, ValueError, ContractError, RuntimeError) as exc:
        print(f"nanochip laboratory: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
