You are the proposal component in a preregistered, bounded computer-architecture
study. Do not use tools, browse, inspect local files, or invent simulator
results. You have only the context below. Your role is to propose three legal
array geometries and a mechanism hypothesis. A separate runner will validate
and evaluate every accepted proposal with SCALE-Sim 3.0.0. You cannot waive a
rejection check, see simulator outputs, choose the final recommendation, or
make the final decision.

Architecture question

Which legal systolic-array shape should advance for the declared compact GEMM
workload under a fixed 1,024-processing-element budget and fixed simulator
configuration, and what mechanism could explain the result?

Workload context

The workload is a compact XR-like slice, not a complete XR application. It has
three dense GEMM layers:

- `xr_projection`: M=128, N=128, K=256
- `xr_attention_tile`: M=64, N=192, K=128
- `xr_head`: M=32, N=128, K=192

The aggregate N dimension is larger than the aggregate M dimension, but layer
sizes and mapping effects can defeat a simple aggregate-aspect-ratio rule.

Fixed environment

- SCALE-Sim 3.0.0 in GEMM mode
- weight-stationary dataflow
- 128 KiB each for IFMAP, filter, and OFMAP SRAM
- 64 words per cycle for each declared interface bandwidth
- 800 MHz clock used only for derived latency
- dense mappings and the same layout file for every candidate
- hard area check: rows multiplied by columns must not exceed 1,024 PEs
- hard deadline check: total simulated cycles must not exceed 90,000
- mandatory baseline: 32 rows by 32 columns; the runner inserts it automatically

Legal nonbaseline shapes

Choose exactly three unique shapes from this closed list:

- 8x8, 8x16, 8x32, 8x64, 8x128
- 16x8, 16x16, 16x32, 16x64
- 32x8, 32x16
- 64x8, 64x16
- 128x8

Candidate identifiers must begin with `ai_` and contain only lowercase letters,
digits, and underscores. Do not propose 32x32 because it is already the
mandatory baseline. Do not repeat a shape or identifier.

Comparison and evidence rules

- The model arm receives exactly four SCALE-Sim evaluations: the baseline plus
  your three proposals.
- A deterministic conventional heuristic receives the same four-evaluation
  budget. Its candidates were fixed before this request and are hidden from
  you.
- The primary selection rule first applies the area and deadline checks, then
  minimizes `total_cycles / (average_layer_utilization_percent / 100)`. This is
  a preregistered local decision score, not a universal architecture metric.
- A separate shared mechanism probe compares 16x64 with 64x16 on both the
  declared workload and a version with M and N transposed. It does not count
  toward either proposal arm's budget.
- Your mechanism hypothesis should make a directional prediction for that
  mirrored/transposed contrast. State what observation would falsify it.
- No result from this study can establish general model superiority, full-XR
  performance, implementation readiness, physical feasibility, power, thermal
  behavior, or product fitness.

Return one JSON object that conforms exactly to the supplied schema. Use
`schema_version` value `arch2-ai-proposal/v1` and `proposal_id` value
`recorded_model_arm`. Return JSON only, with no Markdown fences or commentary.
