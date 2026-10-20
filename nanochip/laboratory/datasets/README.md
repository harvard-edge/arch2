# Executed diagnostic corpus

`dequant_corpus` creates 15 independently executed teaching cases from copies of
the frozen `msh_deq` reference. It makes one literal mutation per fault and
checks that every mutation anchor occurs exactly once. The reference and
frozen probe sources are never edited.

```sh
python -m nanochip.laboratory.datasets.dequant_corpus output/nanochip/my-corpus
```

The output directory must be empty. It contains candidate snapshots, Verilator
build logs, finite-vector simulation logs, oracle vectors, raw receipts,
`records.jsonl`, and `manifest.json`. Costs report measured probe wall time;
peak memory is not measured. Failed builds and protocol failures remain in the
corpus. Generated output belongs under the repository's ignored `output/`.

Each canonical record has `record_id`, `group_id`, `split`, `input_text`,
`target_action`, `source_receipt`, `source_sha256`, and `label_origin`.
`source_sha256` identifies the executed RTL snapshot; `source_receipt` is a
relative path and SHA-256 pair. Metadata records the constructed mutation,
common base, artifact hashes, and cost. These fields are provenance, never
learner input. `load_corpus(manifest_path)` validates records and retained
artifacts before returning them.

The hand-authored policy selects one of four diagnostic activities:

| Action | Observation that justifies the teaching label |
| --- | --- |
| `inspect_build` | Compiler/tool failure or an unclassified execution failure |
| `inspect_protocol` | A reported stream, write, or completion protocol error |
| `inspect_numerics` | Completed comparisons contain numerical mismatches |
| `accept_block` | The complete finite block probe passed |

These labels are neither optimal-action annotations nor recovered Kimi
reasoning. Predicting an action requests a diagnostic activity; it does not
apply a repair. `accept_block` is scoped to the finite simulation, with no
whole-KPU correctness or physical implementation claim.

`serialize_observation(receipt, simulation_log="", build_log="")` is the shared
training/inference serializer. It includes only current observed checks,
numeric mismatch tuples, and allowlisted compiler diagnostic categories.
Paths, hashes, source lines, mutation identities, target labels, and later
results are excluded. The full RTL and logs remain available for human audit
through provenance fields.

Train/dev/test partitions contain 6/5/4 cases and separate mutation templates.
No exact candidate or observation can cross partitions. All cases still share
one base design, one harness, and one vector suite, so this does not test
generalization to another design or workload. There is one accepted reference
case, in train only; copying equivalent passing observations into dev/test
would leak evidence. Evaluation must disclose the absence of accepted cases
in those partitions. A small successful run cannot establish transfer to
naturally occurring faults.

The dev tranche may support a later adaptation experiment only through an
explicitly recorded new training view that retains its original dev origin.
The held-out test tranche must remain excluded from all parameter updates.
