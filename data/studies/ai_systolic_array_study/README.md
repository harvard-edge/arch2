# Recorded AI-Assisted SCALE-Sim Study

This example supplies the executed study used in Chapters 5 and 7. It records one model
interaction, compares it with a weak fixed aspect-ratio heuristic at the same
simulator-call budget, evaluates every candidate with SCALE-Sim 3.0.0, tests
the proposed directional prediction, and stops at an evidence-bounded
recommendation.

The example is deliberately narrow. The three-layer GEMM workload is a
synthetic XR-like stand-in, not a trace extracted from a spatial-tracking
implementation. It does not establish that a model is generally better at
architecture search, that the slice represents a complete XR application, or
that any candidate is ready for RTL, physical design, or product use.

## Frozen protocol

The preregistration in
[`context/pre_registration.yaml`](context/pre_registration.yaml) was frozen
before the model call or any study simulation. It declares:

- the three-layer XR-like GEMM slice and its transposed mechanism probe;
- the legal array dimensions, 1,024-PE budget, and 32x32 baseline;
- three model candidates and three fixed-heuristic candidates, with four
  SCALE-Sim evaluations per arm after inserting the baseline;
- a deterministic aggregate-aspect-ratio heuristic fixed before the call;
- the local decision score, `cycles / (average utilization / 100)`;
- a 1 percent support margin; and
- a shared four-run mirrored/transposed mechanism test outside both arm
  budgets.

The retained model prompt, response schema, complete recorded response, and
recorded provenance are in `context/` and `recorded/model/`. The recorded
call produced a valid response without repair. The runtime did not report a
currency cost, seed, temperature, or provider revision, so those values are
recorded as unavailable rather than inferred.

One provenance gap was discovered after the study. The retained
`context/model_prompt.md` hashes to
`36e0167aa338c6b13087314b768e4f313a8b72ebce5d2c7b7bff5af968376971`,
while the preregistration and model provenance record
`ec12df200a134532942ce0120bbb5694bc657c0e13cf88654631db42aa76fbca`.
No matching prompt copy survives in the package. The complete response and
simulator inputs remain retained, but the exact generation context cannot be
verified. The frozen records are not rewritten to hide the mismatch.

## Recorded outcome

Cycles and utilization below are computed by SCALE-Sim for the frozen inputs.
The historical runner computed the local score and dispositions; the
standalone [`replay.py`](replay.py) now checks those records and recomputes
their metrics. None of the values are measurements from silicon.

The score uses the sum of the report's `Total Cycles` column, which excludes
prefetch, divided by the **unweighted arithmetic mean** of the three layers'
`Overall Util %` values, expressed as a fraction. These are compute-window
cycles, not complete application latency. The separately retained
`Total Cycles (incl. prefetch)` column sums to 17,371 for the 32x32 baseline
and 17,500 for 16x64. Their exact score tie applies to the preregistered
excluding-prefetch metric. Including prefetch would make 16x64 about 0.743
percent worse with the same utilization denominator, still inside the
preregistered 1 percent tolerance. This sensitivity check does not change
the historical metric or establish end-to-end latency across layers.

| Arm | Shape | Cycles excluding prefetch | Unweighted mean layer utilization | Local score | Disposition |
| --- | ---: | ---: | ---: | ---: | --- |
| Model | 32x32 baseline | 13,917 | 41.196% | 33,782.40 | Tied best |
| Model | 16x64 | 13,917 | 41.196% | 33,782.40 | Tied best |
| Model | 8x128 | 19,405 | 29.704% | 65,327.45 | Ranked worse |
| Model | 32x16 | 25,277 | 45.438% | 55,629.61 | Ranked worse |
| Heuristic | 32x32 baseline | 13,917 | 41.196% | 33,782.40 | Tied best |
| Heuristic | 16x64 | 13,917 | 41.196% | 33,782.40 | Tied best |
| Heuristic | 8x128 | 19,405 | 29.704% | 65,327.45 | Ranked worse |
| Heuristic | 64x16 | 17,757 | 32.294% | 54,985.25 | Ranked worse |

The architecture-outcome claim is null at the preregistered margin because no
nonbaseline candidate improves on 32x32 by at least 1 percent. The
two arms return the same best score at the same four-run budget. With a weak
comparator, substantial proposal overlap, and unknown total human effort, this
is a local non-demonstration of AI advantage rather than evidence that the
proposers are equally capable.

The model predicted that 16x64 would beat 64x16 on the original workload and
that the winner would reverse after transposing M and N. The first prediction
held by 38.56 percent on the local score. The transposed result did not reverse,
and 16x64 still won by 7.57 percent. The directional prediction therefore
fails its recorded criterion. The surviving prompt copy omits the mapping
between GEMM dimensions and array dimensions, and the hash mismatch prevents
the package from establishing whether the recorded call did. The contrast
also did not isolate orientation, so the result establishes no replacement
mechanism.

The machine-readable result in
[`recorded/reference/study_results.json`](recorded/reference/study_results.json)
recommends retaining the 32x32 baseline and stopping this bounded search. Its
accountable decision status remains `awaiting_author_confirmation`.

## Verification and replay

The former `arch2_labs.study` package is retired. The standalone runner in
this directory supports this frozen experiment only. It neither calls a
model nor uses the network. It does not rewrite the original records,
repair the missing prompt, or claim to reproduce the model interaction.

From the repository root, verification needs only Python's standard library:

```bash
python3 data/studies/ai_systolic_array_study/replay.py verify
```

Verification checks the complete 75-file reference manifest, file sizes and
SHA-256 hashes, model-response and schema hashes, twelve evaluation records,
input identities, raw report schemas and layer counts. It recomputes the
metrics, local scores, gates and reported outcomes. The known prompt mismatch
is printed as a limitation. A different prompt modification, missing report,
changed metric, or broken hash fails verification. These internal consistency
checks do not authenticate the historical model call or its preregistration.

Replay requires SCALE-Sim 3.0.0. Python 3.11 matches the historical execution
environment; the runner was also checked with Python 3.14. Install the
simulator in a separate environment if needed (installation requires package
access; verification and replay themselves do not):

```bash
python3 -m venv /tmp/arch2-systolic-env
/tmp/arch2-systolic-env/bin/python -m pip install -r data/studies/ai_systolic_array_study/requirements.txt
/tmp/arch2-systolic-env/bin/python data/studies/ai_systolic_array_study/replay.py replay \
  --output /tmp/arch2-systolic-replay
```

The output directory must not already exist and must be outside this study
directory. Choose a new output name for each replay. Each of the twelve runs
gets a log and three summary CSV reports. `replay_summary.json` records the
current interpreter and simulator versions, run results and completion
status. Failed runs leave their new outputs for inspection and exit with an
error; no baseline is replaced. Large access-trace files are not exported by
this runner.

Comparison requires exact report headers, three ordered layers, integer
counts, cycle values, `Overall Util %`, bandwidth/access values and decision
scores. Only `Compute Util %`, a diagnostic unused by the decision score,
allows an absolute difference of at most `1e-12` percentage points. Independent
Python 3.11/3.14 replays differed there by at most approximately `2.14e-14`.
The runner preserves the original left-to-right aggregation order because
Python changed floating-point `sum` after version 3.11. No tolerance is used
to excuse a changed decision or a missing/extra run.

The regression tests include corrupted records, a missing report, metrics
that disagree with raw data despite refreshed hashes, malformed report
schemas, strict cycle comparisons and refusal to overwrite output paths:

```bash
python3 -m pytest -q tests/test_systolic_replay.py
```

The full twelve-run replay test requires SCALE-Sim 3.0.0; the remaining tests
do not. A new model proposal would be a separate study requiring its own
exact prompt, model response, provenance and output directory. There is no
live model adapter in this package.
