import tempfile
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import sys
import urllib.request
import re
import yaml
import subprocess

# Ensure arch2_labs is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arch2_labs.scale_env import run_example
from arch2_labs.decisions import record_human_decision
from arch2_labs.validators import validate_receipt


def query_ollama() -> list:
    """Queries the local Ollama instance for architecture generation."""
    print("Connecting to local LLM (gemma3:1b via Ollama)...")
    prompt = "You are an AI architect designing a systolic array. The total PE budget is 1024. Return ONLY a valid JSON list containing exactly two objects. Each object must have an 'array_rows' integer and an 'array_cols' integer. Ensure one design is square and one is rectangular. Output no other text."

    data = json.dumps({"model": "gemma3:1b", "prompt": prompt, "stream": False}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            response_text = result.get("response", "")

            # Extract JSON block using regex if there's surrounding text
            match = re.search(r"\[.*\]|\{.*\}", response_text.replace("\n", ""))
            if match:
                candidates = json.loads(match.group(0))
                if isinstance(candidates, dict):
                    candidates = [candidates]
                if not isinstance(candidates, list):
                    raise ValueError("LLM response did not contain a valid JSON list.")
                print(f"[Ollama] Successfully generated {len(candidates)} candidates.")
                return candidates
            else:
                raise ValueError("LLM response did not contain a valid JSON list.")
    except Exception as e:
        print(
            f"[Ollama] LLM call failed ({e}). Falling back to hardcoded heuristic candidates..."
        )
        # Fallback to simulated hallucination
        return [
            {"array_rows": 64, "array_cols": 64},  # Massive over-budget
            {"array_rows": 8, "array_cols": 128},  # Long rectangle
        ]


def run_eda_synthesis(candidate_id: str, rows: int, cols: int, out_dir: Path) -> dict:
    """Level 3: Physical EDA Synthesis. Generates RTL and runs Yosys."""
    print(
        f"\n[EDA Synthesis] Generating Verilog RTL for {candidate_id} ({rows}x{cols} array = {rows*cols} MACs)..."
    )

    # We must write EDA files outside the `out_dir` run archive, otherwise
    # the cryptographic integrity validator will reject the folder!
    eda_dir = Path(tempfile.mkdtemp(prefix="arch2_eda_"))
    rtl_path = eda_dir / f"{candidate_id}.v"
    num_macs = rows * cols

    # Generate a single MAC structural Verilog to evaluate standard cell area
    rtl = f"""
module mac (
    input clk,
    input [7:0] a,
    input [7:0] b,
    input [15:0] p_sum,
    output reg [15:0] out
);
    always @(posedge clk) out <= p_sum + (a * b);
endmodule
"""
    rtl_path.write_text(rtl)

    # Run Yosys
    print(f"[EDA Synthesis] Running Yosys logic synthesis on array primitive...")
    yosys_script = eda_dir / "synth.ys"
    yosys_script.write_text(
        f"""
read_verilog {rtl_path}
hierarchy -check -top mac
synth -top mac
abc -g gates
stat
"""
    )

    cmd = ["yosys", "-s", str(yosys_script)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse gate count from Yosys stat output
    mac_cells = 0
    for line in result.stdout.splitlines():
        if "Number of cells:" in line:
            mac_cells = int(line.split()[-1])
            break

    total_cells = mac_cells * num_macs
    return {
        "status": "success" if result.returncode == 0 else "failed",
        "gate_count": total_cells,
    }


def overwrite_candidates_yaml(generated: list):
    """Dynamically updates the candidates.yaml file with the LLM's choices + baseline."""
    yaml_path = (
        Path(__file__).parent
        / "examples"
        / "scale_proxy_mirage"
        / "configs"
        / "candidates.yaml"
    )

    # Load original to keep the top-level structure
    with open(yaml_path, "r") as f:
        spec = yaml.safe_load(f)

    new_candidates = []

    # Keep the baseline
    baseline = next(
        c for c in spec["candidates"] if c["candidate_id"] == spec["baseline_id"]
    )
    new_candidates.append(baseline)

    # Inject LLM candidates
    for i, c in enumerate(generated):
        r, c_cols = c.get("array_rows", 16), c.get("array_cols", 16)
        new_candidates.append(
            {
                "candidate_id": f"llm_gen_{i}_{r}x{c_cols}",
                "label": f"LLM Generated {r}x{c_cols}",
                "source": "Local Ollama Generation",
                "array_rows": r,
                "array_cols": c_cols,
                "dataflow": "ws",
                "sram_kb": 128,
                "dram_bandwidth_words_per_cycle": 64,
                "clock_mhz": 800,
                "area_budget_pes": 1024,
                "deadline_cycles": 90000,
                "min_layer_util_pct": 35.0,
            }
        )

    spec["candidates"] = new_candidates

    with open(yaml_path, "w") as f:
        yaml.dump(spec, f, sort_keys=False)


def main():
    print("=========================================================")
    print(" ARCHITECTURE 2.0: LIGHTHOUSE CAPSTONE WORKSHOP")
    print("=========================================================")

    print("\n[Phase 1] Setup: Formulating the Lighthouse Request")
    print("We are evaluating cache hierarchy bounds for an XR-class 3W RISC-V SoC.")

    # 2. Run the Loop
    print("\n[Phase 2] The Loop: Generation vs. Verification")

    # 2A. Action (LLM Generation)
    llm_candidates = query_ollama()
    overwrite_candidates_yaml(llm_candidates)

    print("\nInvoking the SCALE-Sim proxy engine to simulate the LLM's outputs...")

    out_dir = Path(tempfile.mkdtemp(prefix="arch2_workshop_")) / "run"

    try:
        summary = run_example("scale_proxy_mirage", out_dir, force=True)
    except RuntimeError as e:
        print(f"\n[Environment] Run halted: {e}")
        print(
            "This means the LLM entirely failed the constraints (e.g. blew past the 1024 PE budget)."
        )
        print(
            "This is the verification imbalance in action: open weights hallucinated an unbuildable chip."
        )
        return

    print(f"\n[Environment] Run complete. Artifacts written to: {out_dir}")

    evidence = json.loads((out_dir / "evidence_record.json").read_text())
    negative_traces = [
        json.loads(line)
        for line in (out_dir / "negative_traces.jsonl").read_text().splitlines()
        if line.strip()
    ]

    print(f"\n>> Results:")
    print(f"Candidates rejected by static constraints: {len(negative_traces)}")
    for trace in negative_traces:
        print(f"  - {trace['candidate_id']}: {trace['reason']}")

    print(f"\nCandidates that passed verification:")
    survivors = []
    for outcome in evidence["candidate_outcomes"]:
        if outcome["accepted"]:
            print(f"  - {outcome['candidate_id']}")
            survivors.append(outcome["candidate_id"])

    # 2C. Physical EDA Synthesis
    print("\n[Phase 2C] The Reality Check: EDA Physical Synthesis")
    if survivors:
        survivor = survivors[0]
        # Find its dimensions from the yaml
        yaml_path = (
            Path(__file__).parent
            / "examples"
            / "scale_proxy_mirage"
            / "configs"
            / "candidates.yaml"
        )
        with open(yaml_path, "r") as f:
            spec = yaml.safe_load(f)
        cand_data = next(c for c in spec["candidates"] if c["candidate_id"] == survivor)

        synth_result = run_eda_synthesis(
            survivor, cand_data["array_rows"], cand_data["array_cols"], out_dir
        )
        gate_count = synth_result.get("gate_count", 0)

        print(f"\n>> EDA Results for {survivor}:")
        print(f"Physical Gate Count: {gate_count} standard cells.")
        if gate_count > 10000:
            print(
                "[WARNING] The architecture passed SCALE-Sim cycle checks, but massively violated physical area budgets in RTL!"
            )
        else:
            print("[SUCCESS] The architecture is physically viable.")

    # 3. Human Decision
    print("\n[Phase 3] The Commitment: Human Verification")
    machine_rec = evidence["machine_recommendation"]
    print(f"Machine Recommendation: {machine_rec}")

    decision_dict = {
        "schema_version": "arch2-human-decision/v0.2",
        "lab_id": "scale_proxy_mirage",
        "human_owner": "Workshop Attendee",
        "authored_at": datetime.now(timezone.utc).isoformat(),
        "selected_candidate_id": machine_rec,
        "governing_objective": "latency_under_declared_gates",
        "objective_override": False,
        "override_reason": None,
        "commitment_level": "next_fidelity_study",
        "rationale": "Accepted baseline/LLM output minimizing latency.",
        "residual_risk": "Without a proprietary Data Moat, actual power draw remains highly uncertain.",
        "would_overturn": "Access to foundry-specific layout data showing thermal hotspots.",
    }

    print("Recording human decision and cryptographically sealing receipt...")
    record_human_decision(out_dir, decision_dict)

    errors = validate_receipt(out_dir)
    if errors:
        print(f"[FATAL] Receipt validation failed: {errors}")
    else:
        print("[SUCCESS] Receipt cryptographically sealed. Audit complete.")


if __name__ == "__main__":
    main()
