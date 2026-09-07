import re

with open("book/contents/chapters/04-representations/04-representations.qmd", "r") as f:
    text = f.read()

target1 = r"As the foundational entry to Part II \(Technical Building Blocks\), representation defines the semantic boundary between physical semiconductor realities and automated design algorithms\."
replacement1 = r"Representation defines the semantic boundary between physical semiconductor realities and automated design algorithms."
text = text.replace(target1, replacement1)

target2 = r"Architecture 1\.0 workflows tracked design state through fragmented spreadsheets, unindexed simulation logs, and isolated Verilog files, treating tool returns as ephemeral checks\. Architecture 2\.0 unifies live project state, multi-fidelity surrogate models, and formal design provenance in machine-usable representation graphs\."
replacement2 = r"Conventional exploration workflows historically tracked design state across disconnected simulation logs and static HDL trees, treating tool returns as ephemeral pass/fail checks rather than structured search collateral. An AI-native approach links live project state, multi-fidelity surrogate models, and formal design provenance into machine-usable representation graphs."
text = text.replace(target2, replacement2)

target3 = r"The six life-cycle stages established in @sec-architecture-20-ontology impose distinct representation requirements across the design loop\. Stage 1 \(\*Formulate\*\) operates on natural language specifications, business contracts, and unconstrained engineering aspirations\. Stage 2 \(\*Explore\*\) requires structural and parametric representations of the candidate design space\. Stage 3 \(\*Implement\*\) demands executable tool scripts, verifiable property assertions, and valid compilation artifacts\. Stage 4 \(\*Evaluate\*\) produces unstructured logs, timing reports, and massive waveform traces\. Stage 5 \(\*Interpret\*\) requires normalized scorecards and condensed diagnostic subsets\. Finally, Stage 6 \(\*Commit\*\) extracts residual risk declarations and cryptographically signed organizational decisions\. No single representation format satisfies all six responsibilities\."
replacement3 = r"Because design exploration moves from high-level architectural specifications down to physical signoff, no single format satisfies all representations: exploratory parameter sweeps demand continuous feature vectors, while logic synthesis and timing signoff require discrete, synthesizable ASTs and netlists."
text = text.replace(target3, replacement3)

target4 = r"For design reviews, trade-off evaluations, and architectural approvals to remain reusable across project revisions, records must capture the exact evidence presented to the expert, applied criteria, evaluator role, confidence level, and limiting technical context\."
replacement4 = r"Architectural approvals and expert trade-offs function as conditioned data only when bound to explicit evidence: recorded signoff criteria, tool logs, constraint waivers, and the technical assumptions behind them. Schedule-driven compromises and heuristic overrides must be versioned explicitly in waiver files rather than silently hardening into unverified project assumptions."
text = text.replace(target4, replacement4)

target5 = r"This structured progression divides acquisition and governance into three operational stages: the first four steps shape acquisition budgets and source selection, the next three protect identities, lineage, and evaluation splits, and the final step records collection limits and nonclaims\."
replacement5 = r"The structured progression enforces state comparators, matches operating conditions, preserves lineage, and enforces evaluation splits by coarsest shared ancestor."
text = text.replace(target5, replacement5)

# Footnote
target6 = r"Architecture world models solve this by carrying $s = \langle s_{design}, s_{env} \rangle$ as a state representation, explicitly separating the static candidate features ($s_{design}$) from the temporal and dynamic simulator context ($s_{env}$)."
replacement6 = r"Architecture world models solve this by carrying $s = \langle s_{design}, s_{env} \rangle$ as a state representation, explicitly separating the static candidate features ($s_{design}$) from the temporal and dynamic simulator context ($s_{env}$).[^fn-world-model-ml-compilation-c04]"
footnote6 = r"""
[^fn-world-model-ml-compilation-c04]: **Architectural world models and semantic preservation**: Hardware architects are justifiably skeptical of learned transition models: unlike continuous robotics, digital circuits exhibit discontinuous cliff edges where a single unconstrained clock-domain crossing invalidates the entire design. A similar dilemma paralyzed machine learning compilation: determining optimal operator fusion requires knowing post-scheduling register pressure, but instruction scheduling cannot proceed without fixed buffer layouts. Modern ML compilers solved this compounding-error deadlock through equality saturation (e-graphs) and progressive lowering [@TateEtAl2009EqualitySaturation; @WillseyEtAl2021Egg]. Rather than allowing a learned model to execute unconstrained generative leaps, compilers represent the entire equivalence class of legal program transformations simultaneously. Learned search heuristics navigate which paths to prioritize, while the underlying symbolic intermediate representation guarantees that every intermediate state remains mathematically sound and physically realizable.
"""
text = text.replace(target6, replacement6)
if "[^fn-world-model-ml-compilation-c04]" in text and footnote6.strip() not in text:
    text += "\n" + footnote6.strip() + "\n"

with open("book/contents/chapters/04-representations/04-representations.qmd", "w") as f:
    f.write(text)
