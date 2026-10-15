# weights/

Real trained checkpoint weights are **not used by the scored evaluation**.
The nano config uses synthetic int4 tensors derived from the evaluation seed,
so the suite is hermetic and deterministic.

Running a real checkpoint through a passing chip is a natural follow-on
demo: the image format already speaks AWQ/GPTQ-style int4 groups, so a
quantized checkpoint can be packed with `harness/memmap.py` into the
descriptor-table format of `docs/memory_map.md`. It remains a demo, not a
metric — correctness is defined against `reference/model.py` on seeded
weights. If you build it, keep the tooling in your own directory and the
downloaded weights out of git.
