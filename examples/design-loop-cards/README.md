# Design-Loop Card Examples

`array-study-v2.yaml` is the canonical schema 2.0 example. It follows one
constructed accelerator-array comparison and keeps six review profiles
independent: context, inspectability, replay, independent review, disclosure,
and decision-right completeness. A profile marked `complete` asserts only that
its required bindings are present. It does not assert that the evidence is
high-fidelity or adequate for a larger commitment.

The card separates its architecture-outcome claim from any possible
AI-contribution claim. Its two evidence records are labeled `illustrative`,
bind their producer, tool version, inputs, outputs, limitations, and hashes,
and support only the synthetic estimator result stated in the claim.

Validate the v2 card and then execute its recorded replay command.

```console
./arch2 validate card examples/design-loop-cards/array-study-v2.yaml
cd examples/design-loop-cards
python3 replay.py verify-all
```

The replay packet uses a declared deterministic array estimator and a synthetic
layer set, not SCALE-Sim or a published benchmark. The estimator tiles each
matrix layer over the declared array. Each tile costs
`k + array_rows + array_columns - 2` cycles, exposing pipeline fill and drain
overhead. It does not estimate memory stalls, timing, energy, area, or physical
design.

## Legacy v1.1 Fixtures

The five files whose names contain `level` are frozen schema 1.1 compatibility
fixtures. They show the former cumulative Level 0–3 contract and remain
readable for one public release:

- `level-0-context.yaml`
- `level-1-auditable.yaml`
- `level-2-replayable.yaml`
- `level-3-independent.yaml`
- `redacted-level-0.yaml`

Do not use those levels for a new study. Cumulative levels incorrectly suggest
that independent review follows replay and that a single rank can summarize
different review needs. Schema 2.0 replaces that ladder with independent
profiles and strengthens claims, evidence, rejection checks, replay, and
decision rights.

Create a deterministic migration draft without inventing missing semantics.

```console
./arch2 migrate card examples/design-loop-cards/level-3-independent.yaml \
  --output /tmp/array-study.v2-migration-draft.yaml
```

The draft intentionally does not validate as a v2 card. It preserves fields
that map directly and lists author decisions still needed, including claim and
evidence status, typed rejection checks, replay validation, and decision
rights.

## Next Step

These synthetic packets teach the schema, provenance, and replay contract. They
do not replace empirical lab work with tool-produced evidence. Continue with
the [simulator-backed Architecture 2.0 labs](https://github.com/harvard-edge/arch2/tree/main/labs)
to generate evidence, inspect raw outputs, preserve failed runs and rejected
alternatives, and submit a replayable run archive for review.

The synthetic fixture, simulator-backed lab, and executed systolic array study have different
jobs. Neither synthetic fixture replaces the empirical executed systolic array study.
