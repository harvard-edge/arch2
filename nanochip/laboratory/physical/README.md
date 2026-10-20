# Physical implementation and retained block runs

The shared physical runner uses a pinned, offline LibreLane flow with Yosys,
OpenROAD, Magic, KLayout, and Netgen. The complete teaching core has its own
configuration and correspondence checks, described in the [system guide](../../docs/SYSTEM_GUIDE.md).
Its primary implementation realizes registers and scratch storage with standard
cells. An SRAM macro is an optional alternative that must supply the functional
and physical views required by the declared checks.

A retained complete-core layout has passed detailed-router DRC, Magic DRC,
KLayout DRC, and Netgen LVS. Extracted setup/hold checks and explicit constraint
coverage also passed at all nine declared corners. These results came from
checkpoint continuations, including an isolated LEF retry with the same geometry
and writer settings under a 7 GiB memory limit. The unchanged layout still fails
post-route antenna and electrical checks. Complete-core physical acceptance
remains unfinished; the system guide links the exact receipts and their limits.

The complete-core profile now requires a successful Magic subprocess exit for
streamout, LEF generation, DRC, and SPICE extraction. LEF generation also
requires the writer's completion marker and a nonempty file containing the
complete top-level macro and library terminators. These producer checks prevent
an interrupted tool from returning a successful stage; the following physical
checks still determine whether its output is correct.

The profile also maps KLayout invocation parameter names to those required by
the pinned SKY130 rule deck. It preserves the deck bytes, selected rules,
top-cell name, and requested thread count, and rejects an unexpected deck or
command. A [native compatibility exercise](../../../output/nanochip/complete-core-physical-20261018/native-klayout-arguments-smoke-1/receipt.json)
accepted a clean cell, rejected a cell with design-rule violations, and refused
a changed deck. That exercise checks the adapter; the corrected invocation
still needs execution in the final complete-core flow.

The commands and retained experiments below concern the earlier `msh_deq`
dequantization block. Their measurements and layouts apply to that block;
they cannot satisfy checks for the complete teaching core.

The run uses cached image
`hpretl/iic-osic-tools@sha256:ae380e2b0b96bd57b91f5864623ed488d00f78eaf58caf7f7d9d3754d315df38`.
The inspected image is ARM64, contains LibreLane 2.4.12, OpenROAD
`26Q1-990-g15af3a5c0`, Yosys 0.62 (`7326bb7d6`), and SKY130A revision
`54435919abffb937387ec956209f9cf5fd2dfbee`. The runner checks the bundled
PDK path before execution. It never pulls an image, installs a PDK, or
uses a network. Docker Desktop must already be running and the pinned image
must be present. Missing prerequisites produce an explicit unavailable receipt.

Run from the repository root:

```bash
python3 -m nanochip.laboratory.physical \
  --rtl nanochip/kpu/rtl/msh_deq.v \
  --output output/dequant-physical-001 \
  --timeout-s 900 --cores 1
```

The output directory must be new. A timeout kills the named ephemeral
container and preserves partial results. Only the output directory is mounted
into the container, which runs with no network and a CPU limit. No frozen
source is changed. Allow at least several hundred megabytes for intermediate
databases, raw logs, extracted parasitics, layout, and reports. The image and
PDK are separate prerequisites with much larger storage requirements.

The Python API is `run_physical(rtl, output, timeout_s=900, cores=1)`. Its
structured result is also written to `receipt.json`. `OpenRoadBackend` provides
`evaluate(task, candidate) -> RunReceipt`, matching the laboratory backend
protocol. It requires a candidate-manifested `msh_deq.v`, validates the task
identity, and binds the copied execution input to the candidate hash. It
reports all checks at `block:msh_deq`; it cannot satisfy checks at
`accelerator:msh_chip_top`.

`config.json` sets a deliberately loose 100 ns clock, 35% core utilization,
and 45% placement density with the SKY130 HD standard-cell library. The flow
uses the pinned bundle's default input/output delays and load assumptions.
The resolved configuration and generated SDC files remain in the output.
Linter execution is disabled in this physical flow. Functional simulation
and RTL/netlist equivalence are separate obligations. The 100 ns clock is an
implementation starting point, not an accelerator performance claim.

The current repair trial also enables post-global-route design repair, sets
CTS sink clustering to 8 and maximum capacitance characterization to 0.16,
and allows 10 global-route antenna repair iterations with margin 30. These
settings change implementation effort; the acceptance checks still require
zero electrical and post-route antenna violations.

The receipt retains copied RTL/config/runner hashes, exact commands, image
inspection, tool version output, raw flow logs, intermediate stage states,
and hashes of every produced regular file. It preserves errors and partial
executions. `status=completed` records a zero process return code;
`ok=true` additionally requires every declared physical check to pass.
Missing metrics remain unresolved. A file called GDS is evidence of generated
bytes only. The adapter distinguishes detailed-router DRC, Magic DRC,
KLayout DRC, and Netgen LVS, and accepts timing metrics only from the
post-route STA stage. Timing requires the explicit supplementary constraint
coverage check to pass for every configured corner, with its retained inputs,
script, environments, logs, and post-route state hash verified. A native
unconstrained-path count is diagnostic only and cannot replace missing, failed,
or invalid explicit coverage. When post-route STA
completes within the run budget, `run_physical` reloads every configured corner's
retained netlist, SDC, SPEF, and configured Liberty library through the same
pinned OpenSTA bundle. It checks
unconstrained endpoints, input/output delays, clocks, loops, and generated
clocks using the Boolean return from `check_setup`, and requires a nonempty
clock and register set. `run_coverage(output, timeout_s=120)` can execute this
check separately on an existing run, preserving the original flow receipt.
The supplementary receipt hashes the checked inputs, environments, script,
and raw logs. Positive slack alone is insufficient.
A separate post-route antenna check uses the antenna checker after detailed
routing; a clean pre-route check cannot satisfy it. An additional
electrical-constraint check requires zero maximum slew,
capacitance, and fanout violations at post-route STA. Clean setup/hold timing
does not override electrical violations. None of these checks establishes
foundry signoff, manufacturing readiness,
full workload correctness, or RTL/netlist equivalence.

The earlier Study 06 ORFS image is a different execution path. Its retained
AMD64-on-ARM failure at clock-tree synthesis does not establish anything about
this native ARM64 flow. Results from other blocks and earlier flows are never
imported into this adapter's receipt.

Configuration syntax and flow semantics follow the official
[LibreLane configuration reference](https://librelane.readthedocs.io/en/latest/reference/configuration.html)
and [built-in flows reference](https://librelane.readthedocs.io/en/latest/reference/flows.html).


## Retained block execution on October 17, 2026

The local run produced actual final layout at
`output/nanochip-physical-api/runs/physical/final/gds/msh_deq.gds`, with a
visually inspected KLayout overview at
`output/nanochip-physical-api/layout.png`. Its separately identified audit is
`output/nanochip-physical-api/audited-receipt.json`. These are ignored local
artifacts, not bundled measurements.

The declared configuration stayed at SKY130 HD, a 100 ns clock, 35% core
utilization, and 45% placement density. Detailed-router, Magic, and KLayout
DRC counts were zero; Netgen LVS errors were zero. Post-route worst setup
slack was 54.819201 ns and worst hold slack was 0.106118 ns, with zero
setup/hold violations. A separate explicit OpenSTA check returned success in
all nine configured corners, each with one clock and 1,350 registers.

The design still had 11 post-route antenna violations, 22 maximum slew
violations, one maximum capacitance violation, and 83 maximum fanout
violations. Those remain failures. The original host driver also failed when
serializing an inherited infinite timing metric after the tool reported
`Flow complete.` Its traceback, original runner, raw stages, and generated
layout remain retained. The corrected parser has regression coverage; this
run's audit retains `original_driver_status=error` and `eligible=false`.
The failed first coverage attempt is retained in `coverage-attempt-01/`.
No clean rerun or physical repair is claimed from the audit.

## Local alpha execution on October 18, 2026

The integrated `demo --physical` run at
`output/nanochip/v0-physical-run/report.json` trained its design decoder,
selected `stream_quantized_row`, and materialized changed RTL. Its
`execution-link.json` records the same source hash for the candidate,
functional execution, and physical execution. The complete demo took
707.567 seconds on the development machine with two physical-tool CPU cores.
This is one observed execution, not a laptop runtime guarantee.

The run generated GDSII and passed finite numerical and differential RTL
checks, detailed-router DRC, Magic DRC, KLayout DRC, Netgen LVS, and routed
setup/hold timing with explicit constraint coverage. Electrical checks
retained 98 slew violations, 38 fanout violations, and one capacitance
violation. The final antenna check found seven violating nets. The run
therefore remains physically ineligible. RTL-to-netlist correspondence is
also unresolved.

Antenna repair reached zero in its own iteration report, but subsequent
independent checks found violations after routing. The next repair should
inspect those routed nets and their diode placement/connectivity, together
with the clock branches that still exceed capacitance and fanout limits.
Increasing the iteration allowance again is not supported by this result.
The trial changed flow settings, so differences from earlier runs cannot be
attributed to the learned design action.
