# Architecture 2.0: Chapter-by-Chapter Empirical Data Wishlist

This document serves as the master backlog for future data-mining pipelines. Each chapter has one "killer" empirical plot or dataset proposed by domain experts. These proposals are strictly grounded in reality (no hallucinations) and can be mined from public APIs, SEC filings, GitHub repositories, or academic datasets.

## Part I: The Genesis of AI-Native Hardware (Chapters 1-3)
### Chapter 1: The AI-Native Moonshot
**The Productivity Asymmetry: Software Generation vs. Silicon Generation**
*   **The Insight:** Software GenAI is scaling exponentially, while Hardware RTL GenAI is bottlenecked by a lack of high-quality training data.
*   **Data Sources:** HuggingFace datasets (`bigcode/the-stack-v2`) for exact byte counts of Python/C++ vs. Verilog/SystemVerilog; HuggingFace Open LLM Leaderboard (HumanEval) vs. RTLLM / VerilogEval leaderboards.
*   **Axes:**
    *   *X-axis:* Timeline (Release dates of foundational models).
    *   *Y-axis (Left):* Pass@1 Accuracy (%) on benchmarks.
    *   *Y-axis (Right):* Total deduplicated training tokens (Log scale).

### Chapter 2: The Physical & Economic Pressures
**The Collapse of Moore's Cost-Scaling (EUV Capital vs. Yielded Transistor Cost)**
*   **The Insight:** Demonstrates the "R&D Wall" where physical scaling no longer strictly yields economic scaling.
*   **Data Sources:** SEC EDGAR API (10-K/10-Q) for TSMC, Intel, and Samsung CapEx; ASML Financials for EUV ASP; WikiChip for transistor densities (MTr/mm²).
*   **Axes:**
    *   *X-Axis:* Process Node (nm/Å).
    *   *Y1-Axis (Bar):* Foundry CapEx per Node Transition (Billions USD).
    *   *Y2-Axis (Line):* Cost per Billion Transistors (USD).

### Chapter 3: The Hardware Lifecycle
**The Silicon CI Compute Heatmap: Simulation Bottlenecks vs. Implementation Scaling**
*   **The Insight:** Traditional simulation scales catastrophically with design changes compared to software CI.
*   **Data Sources:** GitHub REST API (`/actions/runs`) for flagship repos (`lowRISC/opentitan`, `ucb-bar/chipyard`). Parse CI logs to extract execution times for Lint, Simulation, and PnR.
*   **Axes:**
    *   *X-Axis:* PR Complexity (SV/Chisel lines changed, Log Scale).
    *   *Y-Axis:* CI Pipeline Execution Time (CPU Hours, Log Scale).
    *   *Z-Axis (Color):* Stage of CI Pipeline (Simulation vs. Lint vs. PnR).

## Part II: State Spaces and Synthesis (Chapters 4-6)
### Chapter 4: Hardware as Graph
**The Topological Explosion of Open-Source RTL (Rent's Rule & Graph Entropy)**
*   **The Insight:** Modern hardware state spaces are exploding topologically, not just linearly.
*   **Data Sources:** Major open-source GitHub repos. Run automated synthesis via Yosys (SkyWater 130nm) to JSON netlists. Parse into NetworkX to calculate Rent's exponent.
*   **Axes:**
    *   *X-Axis:* Total Gate Count (Log Scale).
    *   *Y-Axis:* Rent's Exponent (p) or Graph Entropy.
    *   *Bubble Size:* Chronological year of IP release.

### Chapter 5: Agentic Generation Methods
**The Agentic Sweet Spot: Inference Throughput vs. Autonomous Capability**
*   **The Insight:** For agentic workflows, the ratio of coding capability to token generation throughput (Time-to-Thought) is critical. High latency breaks agentic loops.
*   **Data Sources:** Artificial Analysis API for tokens/sec and TTFT; Aider LLM Leaderboard / SWE-bench Lite leaderboard for Agentic Coding Scores.
*   **Axes:**
    *   *X-axis:* Token Generation Throughput (Output Tokens / Second, Log scale).
    *   *Y-axis:* Agentic Coding Score.
    *   *Bubble Size:* Context Window Size. *Color:* Cost per 1M output tokens.

### Chapter 6: Environments
**Cloud-Native EDA and the CI/CD Silicon Loop**
*   **The Insight:** The shift from monolithic, local tapeouts to continuous integration and API-driven silicon submissions.
*   **Data Sources:** GitHub GraphQL API for `efabless/caravel_user_project` CI/CD workflows; Efabless Open MPW API for public submission metadata.
*   **Axes:**
    *   *X-Axis:* Time (2020 - Present).
    *   *Y1-Axis:* Cumulative Open-Source CI/CD EDA workflow runs per month.
    *   *Y2-Axis:* Number of API-submitted designs per MPW shuttle.

## Part III: Verification and Grounding (Chapters 7-9)
### Chapter 7: Grounding & Feedback
**The RTL Mutation Survival Curve: Compute Investment vs. Structural Resilience**
*   **The Insight:** Shows how long mathematically injected faults survive, proving the diminishing returns of blind randomized testing.
*   **Data Sources:** OpenTitan’s nightly coverage dashboards (`.ucdb` exports); `mcy` (Mutation Coverage with Yosys) repos. GitHub Issues API for bug discovery timestamps vs CPU hours.
*   **Axes:**
    *   *X-Axis:* Cumulative Simulation Compute Investment (CPU Hours).
    *   *Y-Axis:* Mutation Survival Rate (% of faults undetected).
    *   *Overlay:* Real-world bugs discovered.

### Chapter 8: The Loop
**RL Convergence vs. Human Heuristics in Macro Placement**
*   **The Insight:** Direct empirical comparison of RL agents optimizing PPA vs baseline human/heuristic placers.
*   **Data Sources:** Google Research `circuit_training` TensorBoard event logs (protobuf files) for RL; OpenROAD / OpenLane analytic placers (RePlAce) proxy costs.
*   **Axes:**
    *   *X-Axis:* Agent Training Steps / Compute Hours (Log Scale).
    *   *Y-Axis:* Proxy PPA Cost (HPWL + Congestion).
    *   *Baselines:* Dashed lines for SoTA analytic and manual placement.

### Chapter 9: The Patterns of AI-Native Architecture
**The Interconnect Wall: Bandwidth Density vs. Energy Efficiency**
*   **The Insight:** The defining metric is no longer transistor density, but communication energy and bandwidth density (Scale-up fabrics).
*   **Data Sources:** OCP UCIe spec logs; MLPerf Training System json metadata; IEEE ISSCC open hardware databases (pJ/bit metrics).
*   **Axes:**
    *   *X-axis:* Energy Efficiency (pJ/bit, reversed Log scale).
    *   *Y-axis:* Bandwidth Density (Tbps/mm of beachfront edge, Log scale).
    *   *Data Points:* Interconnect generations (PCIe, NVLink, UCIe, TPU ICI).

## Part IV: Evaluation and Ecosystems (Chapters 10-12)
### Chapter 10: Evaluation & Benchmarking
**The Utilization Paradox: Benchmark Saturation vs. Real Hardware MFU**
*   **The Insight:** Real hardware MFU drops precipitously due to memory-bound auto-regressive decoding in LLM-as-a-judge setups.
*   **Data Sources:** MLPerf Inference GitHub repo (`summary.json`); calculated MFU from sustained FLOPs vs spec sheets.
*   **Axes:**
    *   *X-axis:* Model Parameter Count (Log scale).
    *   *Y-axis:* Peak Hardware MFU (%).
    *   *Trend Line:* Exponential decay of MFU as sequence lengths (KV cache) grow.

### Chapter 11: Ownership & Trust
**The Hardware Attack Surface (Silicon CVEs by Taxonomy)**
*   **The Insight:** The nature of hardware vulnerabilities is shifting from physical access to microarchitectural state extraction.
*   **Data Sources:** NVD REST API; MITRE CWE Mapping (CWE-1194, CWE-1037, CWE-1254, CWE-1300).
*   **Axes:**
    *   *X-Axis:* Year of CVE Publication.
    *   *Y-Axis:* Number of reported Hardware CVEs (Stacked Area by CWE type).

### Chapter 12: The Architecture 2.0 Ecosystem
**The Open Silicon Dependency Matrix: Tapeout Provenance and IP Reuse**
*   **The Insight:** Ecosystem evolution from isolated monolithic cores to highly fragmented, reusable micro-packages ("Silicon Standard Library").
*   **Data Sources:** Efabless OpenMPW repositories; FuseSoC / Edalize Package Managers YAML registry files.
*   **Axes:**
    *   *Nodes:* IP Modules, EDA Tools, Physical Tapeouts.
    *   *Size:* In-degree centrality (dependencies).
    *   *Edges:* Weighted by co-occurrence.
