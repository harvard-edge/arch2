"""Bounded EQY proof of exact retained RTL against the final mapped netlist."""

from dataclasses import asdict
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from ..contracts import Artifact, ContractError, file_sha256
from . import flow


def classify_proof(returncode, raw, status):
    """A process exit alone, an empty workdir, or a bounded trace cannot pass."""
    if (
        returncode == 0
        and status == "PASS"
        and "Successfully proved designs equivalent" in raw
    ):
        return "pass"
    if status == "FAIL":
        return "fail"
    return "unresolved"


def run_correspondence(
    physical_output: str | Path,
    output: str | Path,
    *,
    timeout_s=180,
    cores=2,
    mode=None,
) -> dict:
    """Use Liberty functional models and induction/PDR; retain every proof file.

    This establishes only the declared digital RTL/netlist relation. It does
    not establish extracted layout correspondence, workload correctness,
    analog behavior, or manufacturing readiness. Macros need a separate model
    adapter and remain unresolved here.
    """
    if type(cores) is not int or not 1 <= cores <= 8 or timeout_s <= 0:
        raise ValueError("Use positive proof bounds and 1..8 CPU cores")
    physical_output = Path(physical_output).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    mode = flow._runtime_mode(mode)
    config = json.loads((physical_output / "config.json").read_text())
    stages = sorted((physical_output / "runs/physical").glob("*-openroad-stapostpnr"))
    # A synthesis-only preflight can independently exercise the same proof adapter.
    if not stages:
        stages = sorted((physical_output / "runs/physical").glob("*-yosys-synthesis"))
    output.mkdir(parents=True)
    result = {
        "schema": "nanochip-rtl-netlist-correspondence/v1",
        "status": "unresolved",
        "eligible": False,
        "image": flow.IMAGE,
        "runtime_mode": mode,
        "runtime_image_id": os.environ.get("NANOCHIP_RUNTIME_IMAGE_ID")
        if mode == "native"
        else None,
        "design_name": config["DESIGN_NAME"],
        "timeout_s": timeout_s,
        "cores": cores,
        "commands": [],
        "inputs": [],
        "physical_root": str(physical_output),
        "boundary": "Digital RTL/final-netlist proof only; separate physical, workload, and layout checks remain required",
    }
    started = time.monotonic()
    name = "nanochip-equivalence-" + uuid.uuid4().hex[:12]
    try:
        if len(stages) != 1 or config.get("MACROS") or config.get("VERILOG_DEFINES"):
            raise ContractError(
                "Exactly one retained producer and standard-cell RTL without extra defines are required"
            )
        stage = stages[0]
        final = "openroad-stapostpnr" in stage.name
        statefile = stage / ("state_in.json" if final else "state_out.json")
        state = json.loads(statefile.read_text())
        resolved_config = json.loads((stage / "config.json").read_text())
        physical_cells = set()
        for key in ("FILL_CELL", "DECAP_CELL", "WELLTAP_CELL", "ENDCAP_CELL"):
            values = resolved_config.get(key) or []
            physical_cells.update(values if isinstance(values, list) else [values])
        diode = resolved_config.get("DIODE_CELL")
        physical_models = []
        for cell in sorted(physical_cells):
            if not re.fullmatch(
                r"sky130_(fd|ef)_sc_hd__(fill|decap|tapvpwrvgnd)_[0-9]+", cell
            ):
                raise ContractError(
                    "Unrecognized physical-only cell; no empty functional model will be invented"
                )
            physical_models.append(f"module {cell}(); endmodule")
        physical_types = sorted(physical_cells)
        if diode:
            cell, pin = diode.split("/")
            if (
                not re.fullmatch(r"sky130_fd_sc_hd__diode_[0-9]+", cell)
                or pin != "DIODE"
            ):
                raise ContractError("Unrecognized antenna-cell digital model")
            physical_models.append(f"module {cell}(input DIODE); endmodule")
            physical_types.append(cell)
        # These pinned PDK cells have no digital outputs. Every logic cell is
        # modeled by its Liberty function; omitted logic fails hierarchy/check.
        (output / "physical-cells.v").write_text("\n".join(physical_models) + "\n")
        result["physical_only_models_sha256"] = file_sha256(output / "physical-cells.v")
        result["inputs"].append(
            asdict(
                Artifact.from_file(
                    physical_output,
                    str((stage / "config.json").relative_to(physical_output)),
                )
            )
        )
        netlist = physical_output / flow._retained_relative(
            physical_output, state["nl"]
        )
        shutil.copyfile(netlist, output / "gate.v")
        result.update(
            netlist_sha256=file_sha256(netlist),
            producer_state_path=str(statefile.relative_to(physical_output)),
            producer_state_sha256=file_sha256(statefile),
            final_mapped_netlist=final,
        )
        result["inputs"].append(
            asdict(
                Artifact.from_file(
                    physical_output, str(netlist.relative_to(physical_output))
                )
            )
        )
        manifest_path = physical_output / "source-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        gold = []
        for item in manifest:
            path = item["path"]
            if file_sha256(physical_output / path) != item["sha256"]:
                raise ContractError(
                    "Physical source manifest no longer matches retained input"
                )
            target = output / "gold" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(physical_output / path, target)
            result["inputs"].append(item)
            patterns = [
                value.removeprefix("dir::") for value in config["VERILOG_FILES"]
            ]
            if any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
                gold.append(path)
        if not gold:
            raise ContractError("No manifested RTL sources matched VERILOG_FILES")
        runroot = str(output) if mode == "native" else "/proof"
        # Copied proof filenames and module identifiers are constrained before script generation.
        top = config["DESIGN_NAME"]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top) or any(
            not re.fullmatch(r"[A-Za-z0-9_./-]+", path) for path in gold
        ):
            raise ContractError("Unsupported EQY filename/top syntax")
        script = output / "correspondence.eqy"
        script.write_text(
            "[gold]\nread_verilog -formal -sv "
            + " ".join(runroot + "/gold/" + path for path in gold)
            + "\n"
            + "[gate]\nread_liberty -ignore_miss_func "
            + runroot
            + "/standard-cells.lib\nread_verilog -noblackbox -overwrite -formal "
            + runroot
            + "/physical-cells.v\nread_verilog -formal -sv "
            + runroot
            + "/gate.v\ndelete "
            + " ".join("t:" + cell for cell in physical_types)
            + " "
            + " ".join(physical_types)
            + "\n"
            + "[script]\nhierarchy -check -top "
            + top
            + "\nproc\nprep -top "
            + top
            + " -flatten\nmemory -nomap\nasync2sync\ncheck -assert\n"
            + "[strategy sat]\nuse sat\ndepth 5\n"
            + "[strategy pdr]\nuse sby\nengine abc pdr -rfi\n"
        )
        # The bundle's LibreLane EQY helper is absent. Import the exact PDK
        # Liberty functions as behavioral modules (never read_liberty -lib).
        # Missing-function cells are omitted; hierarchy -check then rejects
        # any omitted cell that the final digital netlist actually uses.
        liberty = "/foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        commands = [
            ["cp", liberty, runroot + "/standard-cells.lib"],
            [
                "/foss/tools/yosys/bin/eqy",
                "-j",
                str(cores),
                "-d",
                runroot + "/proof-work",
                runroot + "/correspondence.eqy",
            ],
        ]
        result["functional_model_kind"] = "pinned-liberty-functions"
        result["script_sha256"] = file_sha256(script)
        result["commands"] = commands
        if mode == "native":
            if os.environ.get("NANOCHIP_PHYSICAL_IMAGE") != flow.IMAGE:
                raise ContractError(
                    "Native proof requires the pinned tool-image identity"
                )
            codes = []
            for index, command in enumerate(commands):
                remaining = timeout_s - (time.monotonic() - started)
                with (output / f"command-{index}.log").open("w") as stream:
                    codes.append(flow._execute(command, stream, max(0.01, remaining)))
                if codes[-1]:
                    break
            code = codes[-1]
            raw = (
                (output / "command-1.log").read_text()
                if (output / "command-1.log").exists()
                else ""
            )
        else:
            command = [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "--network",
                "none",
                "--cpus",
                str(cores),
                "--name",
                name,
                "--entrypoint",
                "/bin/bash",
                "-v",
                f"{output}:/proof",
                flow.IMAGE,
                "-lc",
                "set -e; " + " && ".join(" ".join(command) for command in commands),
            ]
            result["container_command"] = command
            with (output / "eqy.log").open("w") as stream:
                code = flow._execute(
                    command, stream, max(0.01, timeout_s - (time.monotonic() - started))
                )
            raw = (output / "eqy.log").read_text()
        markers = [
            value
            for value in ("PASS", "FAIL", "UNKNOWN", "TIMEOUT", "ERROR")
            if (output / "proof-work" / value).is_file()
        ]
        status = markers[0] if len(markers) == 1 else ""
        result.update(
            status="unresolved",
            tool_reported_status=classify_proof(code, raw, status),
            returncode=code,
            eqy_status=status,
            details="Experimental EQY strategy acceptance disabled: the negative-control model/clock audit is not yet validated",
        )
        if (output / "standard-cells.lib").is_file():
            result["functional_model_sha256"] = file_sha256(
                output / "standard-cells.lib"
            )
    except subprocess.TimeoutExpired:
        if mode == "docker":
            subprocess.run(
                ["docker", "rm", "-f", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
        result.update(
            status="unresolved",
            execution_status="timeout",
            details="Proof process tree killed at the declared bound",
        )
    except (OSError, ValueError, KeyError, ContractError) as exc:
        result.update(status="unresolved", details=str(exc))
    result["elapsed_s"] = time.monotonic() - started
    result["artifacts"] = [
        asdict(Artifact.from_file(output, str(path.relative_to(output))))
        for path in sorted(output.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]
    flow._json(output / "receipt.json", result)
    return result
