# Kernel time, occupancy, and DRAM throughput

The figure compares the first retained candidate with the minimum-time candidate among eight retained rounds for each task. It shows the timing ratio, achieved occupancy, and DRAM throughput from associated Nsight Compute records. Every plotted candidate has exactly one profiled kernel; percentages are never summed across kernels.

![Kernel timings and associated hardware counters.](figure.png)

**Placement.** Chapter 7, “Outcome, Mechanism, and Counterfactual Reasoning.” Chapter 4 can refer to the same artifact when motivating the representation of hardware feedback. Keep the main figure in one chapter.

**Why this figure.** MaxPool 3D becomes faster while its achieved occupancy falls from 73.29% to 57.18% and DRAM throughput rises from 33.92% to 66.00% of peak sustained. The matrix–vector candidate follows a different pattern. An agent that maximizes occupancy as its reward can therefore reject useful candidates. The figure motivates diagnosis and measurement of the actual objective; it does not prove which code change caused the improvement.

**Suggested caption.** Lower occupancy can accompany a faster kernel. The first retained candidate and fastest retained candidate differ in timing, achieved occupancy, and DRAM throughput across five curated tasks. Candidate selection uses all eight retained timing records per task. Associated profiler records provide diagnostic signals, not a causal decomposition of runtime; the small RMSNorm timing difference has no reported uncertainty.

**Alt text.** Three aligned dot plots compare the first and fastest retained candidates for five kernel tasks. Kernel time falls while occupancy rises for some tasks and falls for others. MaxPool 3D has lower occupancy and higher DRAM throughput in its faster candidate.

## Reproduction and limits

Run `python3 data/studies/11-kernelagent-feedback/reproduce.py` from the repository root. The folder retains every timing and output-profile record needed to repeat candidate selection, plus the associated source code. `collect.py` copies and verifies this subset from Study 10; Study 10's collector retrieves the original pinned GitHub files. Plotting itself is independent of that folder.

The source is the [same pinned KernelAgent repository](https://github.com/kaiming-cheng/kernelagent-optimization-artifacts/tree/56cf9183b527307538ccbe8f554a88502918d2d1). Hardware identity and toolchain context are author-reported. Profiling records identify Nsight Compute 2025.2.1.0. Raw field names are preserved in `reproduce.py`; `paired_metrics.csv` records the selected paths, kernel names, and values. SHA-256 receipts protect retained bytes, but the original profiler record does not contain a hash of the executed kernel. No GPU run or causal experiment was performed here.

Round 1 is the first optimization round, not the input kernel or a `torch.compile` baseline. Timings here come from the per-round `benchmark_results.json` records, not the upstream README table, and `readme_timing_check.csv` compares the two for all 40 task-rounds. They agree closely except for Transposed conv. 3D, where the README reads about 1.445 times the records in every round although the first-to-best ratio is nearly the same (0.5271 against 0.5269), and RMSNorm, where the README puts the best round at 3 and the records at 8. The per-round records use warmup 25 and upstream `benchmark.py` uses warmup 500; whether that explains the gap was not tested, and the cause is unknown.

Profile elapsed time is not the recorded time. Elapsed time implied by DRAM bytes over DRAM bytes per second runs 0.85 to 2.11 times the recorded `time_ms` across the 40 retained rounds, and about 2 for the fastest matrix–vector and RMSNorm rounds. The cause is not established. The RMSNorm round 8 kernel has four launch sites, one per input-size branch, and the profile records no launch count. Upstream README transposed conv. values 14.839 and 7.821 sit within 0.03 percent of profile elapsed 14.838 and 7.823 (rounds 1 and 5), and 9.836 sits near 9.811 (round 2). These three points may bear on the README gap above but do not settle it.

The runtime environment and source/output hashes are in `build_receipt.json`. SVG, PDF, and PNG use the shared book style. No license file was present in the original tree, so permission to redistribute source code remains unresolved.
