import os

def replace_in_file(filepath, old_text, new_text):
    with open(filepath, 'r') as f:
        content = f.read()
    if old_text not in content:
        print(f"Warning: Could not find text in {filepath}")
        return
    content = content.replace(old_text, new_text)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Updated {filepath}")

# CHAPTER 1 FIXES
ch1 = "synthesis/book/chapters/01-moonshot/index.qmd"

# Fix Sandbox Prompt (Shao)
replace_in_file(ch1,
    "> **Sandbox Prompt:** Design a matrix multiplication systolic array in Chisel,\n> verify its correctness against a software model, sweep its dimensions to find\n> the optimal tradeoff between latency and area for a $16\\times16$ workload,\n> and produce a reviewable evidence ledger explaining why suboptimal variants\n> were rejected.",
    "> **Sandbox Prompt:** Design a matrix multiplication systolic array in Chisel and integrate it into a full SoC via a standard NoC (e.g., TileLink or AXI) with DMA engines. Verify its correctness against a software model, sweep its dimensions to find the optimal system-level tradeoff between latency, area, and memory stalls for a $16\\times16$ workload, and produce a reviewable evidence ledger explaining why suboptimal variants were rejected."
)

# Fix Moonshot Prompt (Mutlu, Olukotun)
replace_in_file(ch1,
    "vector-capable\n> CPU, accelerator, or SoC block under a 3 W TDP",
    "vector-capable CPU, fixed-function accelerator, reconfigurable spatial array (CGRA/RDA), or Processing-in-Memory (PIM) data-centric block under a 3 W TDP"
)

# Fix Table 1 (Mutlu, Martonosi)
replace_in_file(ch1,
    "| Compute subsystem | Target vector CPU, accelerator, or heterogeneous SoC block; explicitly excludes pure scalar or monolithic CPU designs. |",
    "| Compute subsystem | Target vector CPU, fixed-function accelerator, reconfigurable spatial array (CGRA), or Processing-in-Memory (PIM) block; explicitly includes dynamic power management (DVFS, power domains, thermal sensors) as part of the hardware-software contract. |"
)
replace_in_file(ch1,
    "| 3 W TDP target in 3 nm LP | Sets the physical-design envelope. | The evidence ledger and rejection gate: To claim 3 W in 3 nm LP, the loop must produce synthesis, timing, and area estimates, not just architectural counters. It requires independent physical-design feedback. |",
    "| 3 W TDP target in 3 nm LP | Sets the physical-design envelope. | The evidence ledger and rejection gate: To claim 3 W in 3 nm LP, the loop must produce synthesis, timing, thermal, and area estimates. It also requires explicit rejection gates for memory disturbance faults (e.g., RowHammer) and verification of runtime throttling policies. |"
)
replace_in_file(ch1,
    "| XRBench-class real-time XR | Sets the workload scope. | The evidence ledger and rejection gate: The loop must evaluate against a specific benchmark suite with real-time latency deadlines, rejecting candidates that optimize average throughput but miss the deadline. |",
    "| XRBench-class real-time XR | Sets the workload scope. | The evidence ledger and rejection gate: The loop must evaluate against statistically rigorous phase clustering (e.g., SimPoint) and real-time latency deadlines, rejecting candidates that over-optimize for a single hot loop or miss the deadline. |"
)

# Fix Datacenter Prompt (Kozyrakis)
replace_in_file(ch1,
    "and guarantee recovery from synchronous faults.",
    "guarantee recovery from synchronous faults, and tolerate cloud multi-tenancy overheads (cold starts, cache pollution, memory disaggregation latencies)."
)

# CHAPTER 6 FIXES
ch6 = "synthesis/book/chapters/06-methods-generation-prediction-optimization/index.qmd"
replace_in_file(ch6,
    "writing direct code; for hardware, searching the High-Level Synthesis (HLS) pragma space (e.g., pipeline depths, unroll factors) is often a richer, more verifiable generative target than raw RTL synthesis.",
    "writing direct code; for hardware, searching the High-Level Synthesis (HLS) pragma space or mutating programmatic generator source code (e.g., Chisel/Scala templates) is often a richer, more verifiable generative target than static configuration sweeps or raw RTL synthesis."
)

# CHAPTER 7 FIXES
ch7 = "synthesis/book/chapters/07-feedback-verification-trust/index.qmd"
replace_in_file(ch7,
    "3. **Physical Limits:** Rejection occurs because the candidate fails timing, power, or area synthesis.",
    "3. **Physical Limits:** Rejection occurs because the candidate fails timing, power, or area synthesis.\n4. **Security/Structural Limits:** Rejection occurs because the candidate fails fast structural checks (e.g., FIRRTL compilation passes) or information-flow/timing-channel security boundaries (e.g., GLIFT)."
)

print("Finished applying Round 3 changes.")
