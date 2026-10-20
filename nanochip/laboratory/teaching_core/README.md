# Execute the complete Kimi-derived teaching core

This target runs every workload operation through a serialized RTL engine. It
preserves the frozen nano-KPU mathematical architecture with smaller dimensions,
new control and memory organization, and its own implementation identity. It
does not preserve upstream RTL or performance results.

```bash
python3 -m nanochip.laboratory.teaching_core contract
python3 -m nanochip.laboratory.teaching_core run --action serial_mul1 \
  --output output/nanochip/complete-core-001 --seed 1 --tokens 0,1,2,3
python3 -m unittest discover -s tests -p 'test_nanochip_teaching_core*.py' -v
```

`run` requires a new directory. It materializes a complete candidate, compiles
that exact RTL, and executes its exact external program, packed input image,
and nonlinear tables. The receipt records identities, commands, fresh cycle and
traffic measurements, logs, numerical results, and failed checks. The command
does not run physical tools or establish physical acceptance.

The geometry has two layers (KDA then MLA), model width eight, two KDA heads of
width four, two MLA heads with dk/dr/dv four and compressed width eight, four
routed experts with top-two selection and one shared expert, FF width eight,
vocabulary sixteen, and up to four tokens. Int4 groups contain four input
channels. Kernel-four causal convolutions and residual block size two remain.
The fourth token exercises all convolution taps. The exact geometry is in
`contract.py` and the compiler manifest.

The core fetches 128-bit instructions through its external memory port and
executes them using sixteen signed 128-bit registers, arithmetic/shifts,
comparisons/branches, and explicit load/store operations. A bitserial multiplier
processes one or two multiplier bits per cycle, selected by `serial_mul1` or
`serial_mul2`. These actions change the actual RTL implementation. Both execute
the same program and require identical numerical behavior. A student can add a
new implementation family by extending the materializer and retaining the
checks, rather than supplying a preference label.

Program compilation depends on geometry and declared token count. It reads no
weights, tokens, activations, golden outputs, or selected-expert answers. Packed
tensor descriptors, parameters, tokens, expert selection, and every activation
are processed at runtime. Exact upstream nonlinear tables and the program live
in explicit external memory alongside the packed weights. External program,
data, and table regions are disjoint. Serial instruction/table fetch trades
more cycles and traffic for less on-chip storage; these costs are measured.
This is a custom teaching execution engine, not a RISC-V integration.

Static allocation covers every reachable temporary and all recurrent, causal
convolution, and KV state. The compiler reports its high-water mark and rounds
to a power-of-two scratch capacity. The present allocation requires 399 int32
words and realizes 512 words. The scratch interface has a synchronous read and
explicit execution latency. Its initial implementation maps storage into
standard cells, with no SRAM blackbox or initialization file. The program
clears persistent state and writes temporaries before reading them. A future
SRAM adapter must preserve the verified semantics and supply matched physical
views; no macro is silently assumed here.

`build_fixture(output, seed, prompt_index, tokens=...)` runs both frozen
software references with this geometry and retains packed inputs, logits,
argmax, intermediate arrays, and provenance. `compile_program(seq_len, config)`
returns firmware, exact tables, and allocation/observation manifests.
`interpreter.execute(compiled, image)` independently executes the ISA, checks
bounds and uninitialized scratch, and exposes intermediate observations.

The common laboratory API is `make_task(...)`,
`TeachingCoreMaterializer.materialize(task, action, workspace)`, and
`TeachingCoreBackend.evaluate(task, candidate)`. The task freezes source and
checker identities. The backend uses the same manifested RTL and program at
nominal and stressed memory timing, backpressure, and randomized power-on
initialization. Required checks compare every integer logit and argmax against
the independent frozen integer model; enforce the upstream per-row cosine and
near-tie-aware argmax thresholds against the float model; check status/protocol;
and require identical outputs across reset/timing profiles. It reports actual
cycles, read beats, and write beats at complete-core scope.

Functional receipts do not establish implementation correspondence or checked
GDS. Those require synthesis/netlist verification, mapped storage,
connectivity/LVS, the declared DRC/antenna/electrical checks, extracted timing
with explicit corner coverage, and exact linkage to this accepted candidate.
