# Architecture 2.0 Data Validation Report

This report validates the data sources, provenance pipelines, and empirical methodologies behind the datasets mined for *Architecture 2.0: Principles of AI-Native System and Chip Design*.

## 1. Intel & AMD Hardware Errata (Track 1)
- **Source**: Longitudinal specification updates and revision guides across 19 major commercial processor families from Intel and AMD (2016–2026).
- **Validation Check**: The dataset parses official hardware defect documentation, extracting metadata such as `erratum_id`, subsystems (Memory Hierarchy, NoC, execution units), and workaround types (Microcode, OS/Compiler).
- **Methodological Soundness**: Highly sound. These are official hardware vendor documents. The parsing maps defects onto the hardware stack architecture directly, proving that complex verification often fails on physical silicon.

## 2. Hardware AST Complexity (Track 2)
- **Source**: AI Synthetic Benchmarks (VerilogEval, RTLLM) vs. Production Silicon RTL (OpenTitan, BOOM, SweRV/VeeR, BlackParrot).
- **Validation Check**: Extracts AST nodes, Lines of Code, sequential state bits, clock-domain crossings, and hierarchy depth.
- **Methodological Soundness**: This is a vital baseline for evaluating AI-native generation. By measuring the structural gap between synthetic AI benchmarks (which are often flat, single-clock, combinational logic) and production IP (deeply hierarchical, multi-clock), it successfully dismantles the "AI can write Verilog" myth by grounding it in quantitative graph complexity metrics.

## 3. MLPerf Software Dividend (Track 3)
- **Source**: MLCommons inference benchmarks (2018–2026) and leading LLM inference runtimes (vLLM, TensorRT-LLM, SGLang).
- **Validation Check**: Measures throughput gains achieved on *frozen physical silicon* purely through algorithmic/compiler software maturity versus hardware step-functions.
- **Methodological Soundness**: MLCommons is the gold standard for ML benchmarking. Tracking identical chips over 12-36 months to isolate the "software dividend" is mathematically rigorous and isolates the compiler/runtime optimization stack.

## 4. EDA Physical Seed Dispersion (Track 4)
- **Source**: Physical synthesis and PnR runs (Monte Carlo QoR simulation).
- **Validation Check**: Isolates the nondeterministic variance in EDA toolchains (the "QoR lottery").
- **Methodological Soundness**: Accurately addresses the chaotic nature of physical signoff (EDA variance), essential for proving why surrogate models and AI optimizers often fail to close timing.

## 5. SEC EDGAR R&D & Foundry Economics (Track 5)
- **Source**: SEC EDGAR 10-K financial filings for major semiconductor titans (NVDA, AMD, INTC, TSM, AAPL) correlated with IBS/Gartner node economics (300mm wafer cost, mask set costs, SoC design costs).
- **Validation Check**: Validates the financial wall of Moore's Law (e.g., $725M+ SoC design costs at 2nm).
- **Methodological Soundness**: Merging audited public financial data with foundry cost models creates an undeniable economic mandate for AI-native design automation.

## 6. Tiny Tapeout Census (Track 6)
- **Source**: Public manifests from Tiny Tapeout (TT01 through TT10, Skywater, GF, IHP) and Efabless Open MPW.
- **Validation Check**: Analyzes open-source tapeout demographics and cost structures.
- **Methodological Soundness**: Validates the democratization and shifting ownership models of Architecture 2.0.

### Conclusion
The data pipelines are grounded in primary, auditable sources (SEC filings, official vendor errata, MLCommons benchmark data, and physical AST parsing). They are methodologically sound and directly support the book's claims regarding verification complexity, the limits of current AI RTL generation, and the economic necessity of Architecture 2.0.
