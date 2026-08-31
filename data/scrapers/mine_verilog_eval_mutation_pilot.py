#!/usr/bin/env python3
"""Run a deterministic mutation-testing pilot on pinned VerilogEval RTL.

The pilot uses the benchmark's retained reference RTL and testbench. Each
single-site mutant is compiled with Icarus Verilog and executed against the
reference-comparison testbench. A dynamic mismatch is a concrete witness that
a mutant is non-equivalent under the exercised input sequence. The primary rate
is the fraction of all generated mutants with such a witness; every non-witness,
including a timeout or Yosys-reported equivalent mutant, remains in the
denominator. Yosys equivalence results are retained as a separate diagnostic,
and failed proofs are never treated as proof of non-equivalence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = (
    Path(__file__).resolve().parent / ".cache" / "ast-corpus" / "verilog-eval"
)
DEFAULT_STUDY_DIR = (
    REPO_ROOT / "data" / "studies" / "08-testbench-vacuity-and-judge-bias"
)
VERILOG_EVAL_COMMIT = "c498220d0a52248f8e3fdffe279075215bde2da6"
VERILOG_EVAL_URL = "https://github.com/NVlabs/verilog-eval"

MISMATCH_PATTERN = re.compile(r"Mismatches:\s*(\d+)\s+in\s+(\d+)\s+samples")
HARNESS_TIMEOUT_PATTERN = re.compile(r"\bTIMEOUT\b", re.IGNORECASE)


@dataclass(frozen=True)
class MutationSpec:
    name: str
    pattern: re.Pattern[str]
    replacement: str


MUTATION_SPECS = (
    MutationSpec("logical_and_to_or", re.compile(r"&&"), "||"),
    MutationSpec("logical_or_to_and", re.compile(r"\|\|"), "&&"),
    MutationSpec("equality_to_inequality", re.compile(r"(?<![=!])==(?!=)"), "!="),
    MutationSpec("inequality_to_equality", re.compile(r"!=(?!=)"), "=="),
    MutationSpec("left_shift_to_right", re.compile(r"(?<!<)<<(?!<|=)"), ">>"),
    MutationSpec("right_shift_to_left", re.compile(r"(?<!>)>>(?!>|=)"), "<<"),
    MutationSpec("bitwise_and_to_or", re.compile(r"(?<![&])&(?![&=])"), "|"),
    MutationSpec("bitwise_or_to_and", re.compile(r"(?<![|])\|(?![|=])"), "&"),
    MutationSpec("bitwise_xor_to_and", re.compile(r"\^(?!=)"), "&"),
    MutationSpec("addition_to_subtraction", re.compile(r"(?<![+])\+(?![+=])"), "-"),
    MutationSpec("subtraction_to_addition", re.compile(r"(?<![-])-(?![-=>])"), "+"),
    MutationSpec("one_bit_zero_to_one", re.compile(r"1\s*'\s*b0\b", re.I), "1'b1"),
    MutationSpec("one_bit_one_to_zero", re.compile(r"1\s*'\s*b1\b", re.I), "1'b0"),
    MutationSpec("unsized_zero_to_one", re.compile(r"(?<![A-Za-z0-9_$])'0\b"), "'1"),
    MutationSpec("unsized_one_to_zero", re.compile(r"(?<![A-Za-z0-9_$])'1\b"), "'0"),
)


@dataclass
class BaselineRecord:
    problem_id: str
    reference_path: str
    testbench_path: str
    reference_sha256: str
    testbench_sha256: str
    adapted_testbench_sha256: str
    testbench_adaptation: str
    compile_returncode: int
    simulation_returncode: int
    mismatch_count: int | None
    sample_count: int | None
    harness_timeout_detected: int
    candidate_mutation_sites: int
    selected_mutants: int
    hit_mutant_cap: int
    status: str
    compile_stderr: str
    simulation_stdout: str
    extraction_timestamp: str


@dataclass
class MutationRecord:
    problem_id: str
    mutation_id: str
    mutation_operator: str
    source_line: int
    source_column: int
    source_offset: int
    original_text: str
    replacement_text: str
    reference_sha256: str
    testbench_sha256: str
    adapted_testbench_sha256: str
    mutated_sha256: str
    compile_returncode: int
    simulation_returncode: int
    mismatch_count: int | None
    sample_count: int | None
    harness_timeout_detected: int
    formal_result: str
    formal_returncode: int
    classification: str
    compile_stderr: str
    simulation_stdout: str
    formal_stderr: str
    extraction_timestamp: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact(text: str, limit: int = 1800) -> str:
    normalized = " ".join(text.split())
    return normalized[:limit]


def run_tool(command: list[str], cwd: Path, timeout: int = 20) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        )
        return 124, stdout, stderr + " timeout"


def comment_and_string_mask(text: str) -> str:
    chars = list(text)
    state = "code"
    i = 0
    while i < len(chars):
        pair = text[i : i + 2]
        if state == "code" and pair == "//":
            state = "line_comment"
            chars[i] = chars[i + 1] = " "
            i += 2
            continue
        if state == "code" and pair == "/*":
            state = "block_comment"
            chars[i] = chars[i + 1] = " "
            i += 2
            continue
        if state == "code" and chars[i] == '"':
            state = "string"
            chars[i] = " "
            i += 1
            continue
        if state == "line_comment":
            if chars[i] == "\n":
                state = "code"
            else:
                chars[i] = " "
            i += 1
            continue
        if state == "block_comment":
            if pair == "*/":
                chars[i] = chars[i + 1] = " "
                state = "code"
                i += 2
            else:
                if chars[i] != "\n":
                    chars[i] = " "
                i += 1
            continue
        if state == "string":
            if chars[i] == "\\" and i + 1 < len(chars):
                chars[i] = chars[i + 1] = " "
                i += 2
                continue
            if chars[i] == '"':
                state = "code"
            if chars[i] != "\n":
                chars[i] = " "
            i += 1
            continue
        i += 1
    return "".join(chars)


def mutation_candidates(
    text: str, limit: int | None = None
) -> list[tuple[MutationSpec, int, str]]:
    mask = comment_and_string_mask(text)
    header_end = mask.find(");")
    if header_end >= 0:
        mask = " " * (header_end + 2) + mask[header_end + 2 :]

    matches_by_spec: list[list[tuple[MutationSpec, int, str]]] = []
    for spec in MUTATION_SPECS:
        matches_by_spec.append(
            [
                (spec, match.start(), match.group(0))
                for match in spec.pattern.finditer(mask)
            ]
        )

    selected: list[tuple[MutationSpec, int, str]] = []
    round_index = 0
    while limit is None or len(selected) < limit:
        added = False
        for matches in matches_by_spec:
            if round_index < len(matches):
                selected.append(matches[round_index])
                added = True
                if limit is not None and len(selected) == limit:
                    break
        if not added:
            break
        round_index += 1
    return selected


def as_dut(reference: str) -> str:
    dut, replacements = re.subn(
        r"\bmodule\s+RefModule\b", "module TopModule", reference, count=1
    )
    if replacements != 1:
        raise ValueError(
            "Reference source does not define exactly one leading RefModule"
        )
    return dut


def adapt_testbench_for_iverilog(testbench: str) -> str:
    """Remove waveform-only system tasks that Icarus elaborates strictly.

    VerilogEval testbenches sometimes reference ``tb_mismatch`` in ``$dumpvars``
    before the signal declaration. Waveform dumping is not part of the oracle;
    removing only ``$dumpfile`` and ``$dumpvars`` preserves the stimulus,
    reference comparison, mismatch accounting, and final report.
    """

    kept_lines = [
        line
        for line in testbench.splitlines(keepends=True)
        if "$dumpfile" not in line and "$dumpvars" not in line
    ]
    return "".join(kept_lines)


def compile_and_simulate(
    reference: str,
    dut: str,
    testbench: str,
    workdir: Path,
) -> tuple[int, int, int | None, int | None, str, str, str]:
    (workdir / "reference.sv").write_text(reference, encoding="utf-8")
    (workdir / "dut.sv").write_text(dut, encoding="utf-8")
    (workdir / "testbench.sv").write_text(testbench, encoding="utf-8")
    compile_rc, compile_out, compile_err = run_tool(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            "simulation.vvp",
            "reference.sv",
            "dut.sv",
            "testbench.sv",
        ],
        cwd=workdir,
    )
    if compile_rc != 0:
        return compile_rc, -1, None, None, compile_out, compile_err, ""
    sim_rc, sim_out, sim_err = run_tool(
        ["vvp", "simulation.vvp"], cwd=workdir, timeout=20
    )
    matches = MISMATCH_PATTERN.findall(sim_out)
    mismatch_count = int(matches[-1][0]) if matches else None
    sample_count = int(matches[-1][1]) if matches else None
    return (
        compile_rc,
        sim_rc,
        mismatch_count,
        sample_count,
        compile_out,
        compile_err,
        sim_out + "\n" + sim_err,
    )


def formal_equivalence(reference: str, dut: str, workdir: Path) -> tuple[str, int, str]:
    (workdir / "formal_reference.sv").write_text(reference, encoding="utf-8")
    (workdir / "formal_dut.sv").write_text(dut, encoding="utf-8")
    script = (
        "read_verilog -sv formal_reference.sv formal_dut.sv; "
        "proc; memory; opt; "
        "equiv_make RefModule TopModule equiv; "
        "prep -top equiv; equiv_simple -undef -seq 8; equiv_status -assert"
    )
    rc, stdout, stderr = run_tool(["yosys", "-q", "-p", script], cwd=workdir)
    combined = stdout + "\n" + stderr
    if rc == 0:
        return "equivalent", rc, combined
    if "unproven $equiv cells" in combined:
        return "unproved", rc, combined
    return "inconclusive", rc, combined


def write_records(path: Path, records: list[object], record_type: type) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(record_type.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def git_commit(checkout: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def tool_version(command: list[str]) -> str:
    rc, stdout, stderr = run_tool(command, cwd=REPO_ROOT)
    return compact(stdout + " " + stderr, 500) if rc in {0, 1} else "unavailable"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STUDY_DIR)
    parser.add_argument("--max-modules", type=int, default=156)
    parser.add_argument("--max-mutants-per-module", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for tool in ("iverilog", "vvp", "yosys"):
        if shutil.which(tool) is None:
            raise SystemExit(f"Required executable is not available: {tool}")
    if git_commit(args.corpus) != VERILOG_EVAL_COMMIT:
        raise SystemExit(
            f"VerilogEval checkout must be pinned to {VERILOG_EVAL_COMMIT}: {args.corpus}"
        )

    dataset = args.corpus / "dataset_spec-to-rtl"
    references = sorted(dataset.glob("*_ref.sv"))[: args.max_modules]
    timestamp = datetime.now(timezone.utc).isoformat()
    baseline_records: list[BaselineRecord] = []
    mutation_records: list[MutationRecord] = []

    with tempfile.TemporaryDirectory(prefix="arch2-mutation-pilot-") as temp:
        root = Path(temp)
        for module_index, reference_path in enumerate(references, start=1):
            problem_id = reference_path.name.removesuffix("_ref.sv")
            testbench_path = dataset / f"{problem_id}_test.sv"
            if not testbench_path.exists():
                continue
            reference = reference_path.read_text(encoding="utf-8")
            testbench = testbench_path.read_text(encoding="utf-8")
            adapted_testbench = adapt_testbench_for_iverilog(testbench)
            reference_hash = sha256_text(reference)
            testbench_hash = sha256_text(testbench)
            adapted_testbench_hash = sha256_text(adapted_testbench)
            original_dut = as_dut(reference)
            module_dir = root / problem_id
            module_dir.mkdir()

            (
                compile_rc,
                sim_rc,
                mismatches,
                samples,
                _,
                compile_err,
                sim_output,
            ) = compile_and_simulate(
                reference, original_dut, adapted_testbench, module_dir
            )
            baseline_harness_timeout = int(
                HARNESS_TIMEOUT_PATTERN.search(sim_output) is not None
            )
            if compile_rc == 0 and sim_rc == 0 and mismatches == 0:
                baseline_status = (
                    "pass_at_harness_timeout" if baseline_harness_timeout else "pass"
                )
            else:
                baseline_status = "fail"
            accepted_baseline = baseline_status in {
                "pass",
                "pass_at_harness_timeout",
            }
            all_candidates = (
                mutation_candidates(original_dut) if accepted_baseline else []
            )
            candidates = all_candidates[: args.max_mutants_per_module]
            baseline_records.append(
                BaselineRecord(
                    problem_id=problem_id,
                    reference_path=reference_path.relative_to(args.corpus).as_posix(),
                    testbench_path=testbench_path.relative_to(args.corpus).as_posix(),
                    reference_sha256=reference_hash,
                    testbench_sha256=testbench_hash,
                    adapted_testbench_sha256=adapted_testbench_hash,
                    testbench_adaptation=(
                        "removed waveform-only $dumpfile/$dumpvars lines for "
                        "Icarus compatibility"
                    ),
                    compile_returncode=compile_rc,
                    simulation_returncode=sim_rc,
                    mismatch_count=mismatches,
                    sample_count=samples,
                    harness_timeout_detected=baseline_harness_timeout,
                    candidate_mutation_sites=len(all_candidates),
                    selected_mutants=len(candidates),
                    hit_mutant_cap=int(
                        len(all_candidates) > args.max_mutants_per_module
                    ),
                    status=baseline_status,
                    compile_stderr=compact(compile_err),
                    simulation_stdout=compact(sim_output),
                    extraction_timestamp=timestamp,
                )
            )
            if not accepted_baseline:
                continue
            for mutation_index, (spec, offset, original) in enumerate(
                candidates, start=1
            ):
                mutated = (
                    original_dut[:offset]
                    + spec.replacement
                    + original_dut[offset + len(original) :]
                )
                line = original_dut.count("\n", 0, offset) + 1
                line_start = original_dut.rfind("\n", 0, offset)
                column = offset - line_start
                mutant_dir = module_dir / f"mutant-{mutation_index:02d}"
                mutant_dir.mkdir()

                (
                    mutant_compile_rc,
                    mutant_sim_rc,
                    mutant_mismatches,
                    mutant_samples,
                    _,
                    mutant_compile_err,
                    mutant_sim_output,
                ) = compile_and_simulate(
                    reference, mutated, adapted_testbench, mutant_dir
                )
                if mutant_compile_rc == 0:
                    formal_result, formal_rc, formal_output = formal_equivalence(
                        reference, mutated, mutant_dir
                    )
                else:
                    formal_result, formal_rc, formal_output = "not_run", -1, ""

                mutant_harness_timeout = int(
                    HARNESS_TIMEOUT_PATTERN.search(mutant_sim_output) is not None
                )

                if mutant_compile_rc != 0:
                    classification = "compile_killed"
                elif mutant_mismatches is not None and mutant_mismatches > 0:
                    classification = (
                        "dynamically_killed_formal_conflict"
                        if formal_result == "equivalent"
                        else "dynamically_killed"
                    )
                elif mutant_sim_rc == 124:
                    classification = "simulation_timeout"
                elif mutant_mismatches is None:
                    classification = "simulation_inconclusive"
                elif formal_result == "equivalent":
                    classification = "no_dynamic_witness_formal_equivalent"
                elif mutant_harness_timeout:
                    classification = "survived_harness_timeout"
                else:
                    classification = "survived_unresolved"

                mutation_records.append(
                    MutationRecord(
                        problem_id=problem_id,
                        mutation_id=f"{problem_id}-M{mutation_index:02d}",
                        mutation_operator=spec.name,
                        source_line=line,
                        source_column=column,
                        source_offset=offset,
                        original_text=original,
                        replacement_text=spec.replacement,
                        reference_sha256=reference_hash,
                        testbench_sha256=testbench_hash,
                        adapted_testbench_sha256=adapted_testbench_hash,
                        mutated_sha256=sha256_text(mutated),
                        compile_returncode=mutant_compile_rc,
                        simulation_returncode=mutant_sim_rc,
                        mismatch_count=mutant_mismatches,
                        sample_count=mutant_samples,
                        harness_timeout_detected=mutant_harness_timeout,
                        formal_result=formal_result,
                        formal_returncode=formal_rc,
                        classification=classification,
                        compile_stderr=compact(mutant_compile_err),
                        simulation_stdout=compact(mutant_sim_output),
                        formal_stderr=compact(formal_output),
                        extraction_timestamp=timestamp,
                    )
                )
            print(
                f"{module_index:03d}/{len(references):03d} {problem_id}: "
                f"baseline {baseline_status}, {len(candidates)} mutants"
            )

    baseline_csv = args.output_dir / "verilog_eval_mutation_pilot_baselines.csv"
    mutation_csv = args.output_dir / "verilog_eval_mutation_pilot.csv"
    summary_json = args.output_dir / "verilog_eval_mutation_pilot_summary.json"
    write_records(baseline_csv, baseline_records, BaselineRecord)
    write_records(mutation_csv, mutation_records, MutationRecord)

    classifications: dict[str, int] = {}
    for record in mutation_records:
        classifications[record.classification] = (
            classifications.get(record.classification, 0) + 1
        )
    dynamic_witnesses = sum(
        record.mismatch_count is not None and record.mismatch_count > 0
        for record in mutation_records
    )
    baseline_statuses: dict[str, int] = {}
    for record in baseline_records:
        baseline_statuses[record.status] = baseline_statuses.get(record.status, 0) + 1
    accepted_baselines = sum(
        status in {"pass", "pass_at_harness_timeout"}
        for status in (record.status for record in baseline_records)
    )
    total_candidate_sites = sum(
        record.candidate_mutation_sites for record in baseline_records
    )
    summary = {
        "study_status": "executed bounded pilot",
        "source": {
            "repository": VERILOG_EVAL_URL,
            "commit": VERILOG_EVAL_COMMIT,
            "module_limit": args.max_modules,
            "mutants_per_module_limit": args.max_mutants_per_module,
        },
        "tool_versions": {
            "iverilog": tool_version(["iverilog", "-V"]),
            "yosys": tool_version(["yosys", "-V"]),
        },
        "execution": {
            "python_version": platform.python_version(),
            "operating_system": platform.system(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
            "miner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "extraction_timestamp": timestamp,
        },
        "testbench_adaptation": (
            "removed waveform-only $dumpfile/$dumpvars lines for Icarus "
            "compatibility; stimulus and mismatch oracle retained"
        ),
        "stimulus_seed_control": (
            "retained VerilogEval testbench with Icarus default implicit random "
            "state; no explicit simulator seed supplied"
        ),
        "baseline_modules": len(baseline_records),
        "baseline_statuses": baseline_statuses,
        "accepted_baseline_modules": accepted_baselines,
        "modules_with_selected_mutants": sum(
            record.selected_mutants > 0 for record in baseline_records
        ),
        "modules_without_selected_mutants": sum(
            record.status in {"pass", "pass_at_harness_timeout"}
            and record.selected_mutants == 0
            for record in baseline_records
        ),
        "candidate_mutation_sites_before_cap": total_candidate_sites,
        "modules_hitting_mutant_cap": sum(
            record.hit_mutant_cap for record in baseline_records
        ),
        "selection_fraction": (
            len(mutation_records) / total_candidate_sites
            if total_candidate_sites
            else None
        ),
        "selection_method": (
            f"at most {args.max_mutants_per_module} sites per accepted module; "
            "mutation operators are "
            "visited round-robin and sites within an operator follow source order"
        ),
        "generated_mutants": len(mutation_records),
        "classifications": classifications,
        "dynamic_mismatch_witnesses": dynamic_witnesses,
        "dynamic_mismatch_witness_rate": (
            dynamic_witnesses / len(mutation_records) if mutation_records else None
        ),
        "dynamic_rate_definition": (
            "generated mutants with mismatch_count > 0 / all generated mutants; "
            "equivalent, surviving, timed-out, inconclusive, and compile-invalid "
            "mutants remain in the denominator"
        ),
    }
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for path in (baseline_csv, mutation_csv, summary_json):
        print(f"generated: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
