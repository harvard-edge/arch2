"""Inventory elaborated upstream memories without synthesizing the core.

Yosys resolves parameters and hierarchy. Only its RTL frontend and hierarchy
pass run; blackboxes are inventoried, never treated as physical memories.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
KPU = ROOT / "nanochip/kpu"
SNAPSHOT = PACKAGE / "target.json"
TOP = "msh_chip_top"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _constant(value: str):
    value = value.strip()
    if value.startswith('"'):
        return json.loads(value)
    bits = re.fullmatch(r"\d+'([01]+)", value)
    if bits:
        return int(bits[1], 2)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    raise ValueError(f"Unsupported elaborated parameter: {value}")


def _modules(rtlil: str) -> dict:
    """Read only module/cell structure from Yosys RTLIL, not Verilog syntax."""
    modules = {}
    for module in re.finditer(r"^module (\S+)\n(.*?)^end$", rtlil, re.M | re.S):
        name, body = module.groups()
        if re.search(r"^  memory ", body, re.M):
            raise ValueError(f"Uninventoried inferred memory in {name}; explicit mapping is required")
        cells = []
        for cell in re.finditer(r"^  cell (\S+) (\S+)\n(.*?)^  end$", body, re.M | re.S):
            kind, instance, content = cell.groups()
            if kind.startswith("$mem"):
                raise ValueError(f"Uninventoried inferred memory cell in {name}")
            params = {}
            for key, value in re.findall(r"^    parameter(?: signed)? \\(\w+) (.+)$", content, re.M):
                params[key] = _constant(value)
            cells.append({"type": kind.lstrip("\\"), "name": instance.lstrip("\\"), "parameters": params})
        modules[name.lstrip("\\")] = cells
    if TOP not in modules:
        raise ValueError("Elaboration did not retain the requested top")
    return modules


def _inventory(modules: dict, source_root: Path = ROOT) -> list[dict]:
    memories = []

    def visit(module: str, path: str, stack: tuple):
        if module in stack:
            raise ValueError("Recursive hardware hierarchy")
        for cell in modules[module]:
            kind = cell["type"]
            location = path + "/" + cell["name"]
            if kind in ("msh_sram", "msh_rom"):
                p = cell["parameters"]
                depth, width = p["DEPTH"], p["WIDTH"]
                if type(depth) is not int or type(width) is not int or depth <= 0 or width <= 0 or width % 8:
                    raise ValueError(f"Unsupported memory dimensions at {location}")
                entry = {"instance": location, "kind": kind, "depth_words": depth,
                         "width_bits": width, "capacity_bits": depth * width,
                         "address_bits": (depth - 1).bit_length(),
                         "physical_realization": "unresolved", "physical_views": {}}
                if kind == "msh_rom":
                    relative = "nanochip/kpu/" + p["INIT_FILE"]
                    rom = source_root / relative
                    words = rom.read_text().split()
                    if len(words) != depth or any(not re.fullmatch(r"[0-9a-fA-F]+", w) or int(w, 16) >= (1 << width) for w in words):
                        raise ValueError(f"ROM content dimensions disagree at {location}")
                    entry["initialization"] = {"path": relative, "sha256": sha256(rom), "word_count": len(words)}
                else:
                    entry["initialization"] = {"kind": "uninitialized; no reset port"}
                memories.append(entry)
            elif kind in modules:
                visit(kind, location, stack + (module,))
            elif not kind.startswith("$"):
                raise ValueError(f"Unresolved module {kind} at {location}")

    visit(TOP, TOP, ())
    if not memories:
        raise ValueError("Empty memory inventory")
    return sorted(memories, key=lambda item: item["instance"])


def derive_target(timeout_s: float = 60) -> dict:
    """Return a fresh, source-hashed inventory; requires local Yosys, no network."""
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("Use a positive finite wall-time budget")
    yosys = shutil.which("yosys")
    if yosys is None:
        raise FileNotFoundError("Local Yosys is required for fresh hierarchy inventory")
    filelist = KPU / "rtl/filelist.f"
    rtl = [KPU / line.strip() for line in filelist.read_text().splitlines() if line.strip()]
    macros = [KPU / "harness/macros" / name for name in ("msh_sram_bb.v", "msh_rom_bb.v")]
    source_paths = set(rtl + macros + [filelist, KPU / "reference/configs.json", KPU / "reference/config.py",
                                      KPU / "harness/macros/msh_sram.v", KPU / "harness/macros/msh_rom.v"])
    source_paths.update((KPU / "rtl/roms").glob("*.hex"))
    source_bytes = {p: p.read_bytes() for p in source_paths}
    # The checked-in paths have no whitespace. Quoted paths support relocated
    # repositories; no shell is used to execute the tool.
    quote = lambda p: '"' + str(p).replace('\\', '\\\\').replace('"', '\\"') + '"'
    with tempfile.TemporaryDirectory(prefix="nanochip-inventory-") as tmp:
        # Tools and the config loader consume copied bytes. Hash those same
        # inputs, rather than hashing potentially changed sources after a run.
        staged_root = Path(tmp)
        staged_kpu = staged_root / "nanochip/kpu"
        for path, contents in source_bytes.items():
            staged = staged_kpu / path.relative_to(KPU)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(contents)
        staged_rtl = [staged_kpu / p.relative_to(KPU) for p in rtl]
        staged_macros = [staged_kpu / p.relative_to(KPU) for p in macros]
        output = Path(tmp) / "hierarchy.il"
        script = ("read_verilog -sv -lib " + " ".join(map(quote, staged_macros)) + "; "
                  "read_verilog -sv " + " ".join(map(quote, staged_rtl)) + "; "
                  f"hierarchy -check -top {TOP}; write_rtlil " + quote(output))
        run = subprocess.run([yosys, "-Q", "-T", "-p", script], cwd=staged_kpu,
                             text=True, capture_output=True, timeout=timeout_s)
        if run.returncode:
            raise ValueError("Yosys hierarchy failed: " + run.stderr[-4000:])
        memories = _inventory(_modules(output.read_text()), staged_root)
        version = subprocess.run([yosys, "-V"], text=True, capture_output=True, check=True, timeout=10).stdout.strip()
        config_json = json.loads((staged_kpu / "reference/configs.json").read_text())["nano"]
        config_py = asdict(runpy.run_path(str(staged_kpu / "reference/config.py"))["CONFIGS"]["nano"])
    if config_json != json.loads(json.dumps(config_py)):
        raise ValueError("Reference config.py and configs.json disagree")
    sources = set(rtl + macros + [filelist, KPU / "reference/configs.json", KPU / "reference/config.py",
                                  KPU / "harness/macros/msh_sram.v", KPU / "harness/macros/msh_rom.v"])
    sources.update(ROOT / m["initialization"]["path"] for m in memories if m["kind"] == "msh_rom")
    totals = Counter()
    for m in memories:
        totals[m["kind"] + "_instances"] += 1
        totals[m["kind"] + "_bits"] += m["capacity_bits"]
    totals["all_memory_bits"] = sum(m["capacity_bits"] for m in memories)
    return {
        "schema": "nanochip-teaching-target/v1", "target_id": "upstream-nano-inventory-v0",
        "scope": "source-derived complete-core memory inventory; not a realized teaching core",
        "top": TOP, "configuration": config_json,
        "source_artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(source_bytes[p]).hexdigest()} for p in sorted(sources)],
        "derivation": {"tool": version, "passes": ["read_verilog", "hierarchy -check", "write_rtlil"],
                       "synthesis": False, "physical_execution": False},
        "contracts": {
            "msh_sram": {"read_ports": 1, "write_ports": 1, "read_latency_cycles": 1,
                         "write_mask_granularity_bits": 8, "same_address_read_write": "old_data",
                         "read_enable_false": "hold_previous_output", "reset": "none",
                         "initial_contents": "unspecified"},
            "msh_rom": {"read_ports": 2, "write_ports": 0, "read_latency_cycles": 0,
                        "initialization": "readmemh at simulation time zero; physical implementation unresolved"}},
        "memories": memories, "totals": dict(sorted(totals.items())),
        "complete_core_ready": False,
        "unresolved": ["SRAM and asynchronous dual-read ROM physical implementations/views",
                       "Complete workload checks with realized memory wrappers and initialization",
                       "Functional correspondence through synthesis and physical integration",
                       "Core constraints, macro-aware coverage, floorplan, routing and extracted timing",
                       "DRC, LVS, connectivity, antenna and electrical closure"],
    }


def validate_target(target: dict, timeout_s: float = 60) -> dict:
    """Compare every field with a fresh derivation; never just trust totals/hashes."""
    fresh = derive_target(timeout_s)
    # Tool revision may differ across prepared environments. All design fields
    # must still agree; return the actual executing version for the receipt.
    expected, observed = dict(target), dict(fresh)
    expected.pop("derivation", None)
    observed.pop("derivation", None)
    if expected != observed:
        raise ValueError("Target snapshot differs from freshly elaborated source inventory")
    if target.get("derivation", {}).get("passes") != fresh["derivation"]["passes"] or target.get("derivation", {}).get("synthesis") is not False or target.get("derivation", {}).get("physical_execution") is not False:
        raise ValueError("Invalid derivation scope")
    return {"schema": "nanochip-target-validation/v1", "status": "pass", "tool": fresh["derivation"]["tool"],
            "scope": fresh["scope"], "totals": fresh["totals"], "complete_core_ready": False}
