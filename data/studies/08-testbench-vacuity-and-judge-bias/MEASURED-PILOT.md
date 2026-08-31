# Executed VerilogEval mutation pilot

This candidate preserves the original
`testbench_vacuity_and_judge_calibration.csv`, README, plot script, and figure
assets unchanged. It provides an independently named executed pilot for review
before any manuscript integration.

## Evidence status

- The source RTL and testbenches come from VerilogEval at the full commit
  recorded in `verilog_eval_mutation_pilot_summary.json`.
- Source and testbench SHA-256 hashes, mutation locations, replacement tokens,
  tool return codes, mismatch counts, and compact tool output are retained per
  row.
- Each retained baseline is compiled with Icarus Verilog and compared with an
  identical DUT copy before mutation. A single token-level mutation is then
  compiled and executed against the same reference-comparison testbench.
- VerilogEval's waveform-only `$dumpfile` and `$dumpvars` calls are removed for
  Icarus compatibility. The stimulus, reference instance, comparison logic,
  mismatch counters, and final report remain unchanged. Both original and
  adapted testbench hashes are recorded.
- A dynamic mismatch is a concrete non-equivalence witness for the exercised
  sequence. A failed or inconclusive equivalence proof is never treated as
  proof of non-equivalence. The Yosys diagnostic uses `equiv_simple -undef`
  with a bounded sequential depth of eight.
- The primary rate is the number of generated mutants with an observed dynamic
  mismatch divided by all generated mutants. Formally equivalent,
  zero-mismatch, timed-out, inconclusive, and compile-invalid outcomes remain
  in the denominator.
- VerilogEval stimulus uses the Icarus default implicit random state. The pilot
  supplies no explicit simulator seed and does not claim cross-seed stability.

## Current measured result

Of 156 retained reference/testbench pairs, 152 pass the unmutated baseline
without a harness timeout, three report zero mismatches only when their own
testbench timeout fires, and one has a retained interface mismatch under
Icarus. The 155 accepted baselines contain 475 matching mutation sites. The
bounded sampler selects 338 sites (71.2%) across 107 modules; 48 accepted
modules have no matching site, and 14 modules reach the eight-mutant cap.

The testbenches produce a dynamic mismatch for 328 of 338 generated mutants,
or 97.0%. Four zero-mismatch mutants are reported equivalent by Yosys, four
survive with equivalence unresolved, one survives at a testbench-reported
timeout, and one simulation reaches the process timeout. The 97.0% value is a
mutant-weighted mismatch-witness rate for this bounded sample, not coverage and
not a universal testbench-quality estimate.

## Scope boundary

This pilot measures retained VerilogEval reference testbenches only. It does not
measure line or branch coverage, CV32E40P, BaseJump STL, AI-generated
testbenches, or LLM judges. It therefore cannot substantiate the original
coverage-gap, 67,140-mutant, judge-bias, or formal-detection claims. Those claims
require separately executed studies.

## Reproduction

```bash
python3 data/scrapers/mine_verilog_eval_mutation_pilot.py \
  --corpus data/scrapers/.cache/ast-corpus/verilog-eval \
  --max-modules 156 \
  --max-mutants-per-module 8
uv run --with matplotlib --with numpy \
  python data/studies/08-testbench-vacuity-and-judge-bias/plot_verilog_eval_mutation_pilot.py
```

The corpus checkout must be pinned to the commit recorded by the script. The
miner requires `iverilog`, `vvp`, and `yosys` on `PATH`.
