# Architecture 2.0: Foundations for AI Agents in Computer System Design

**Speaker / Author:** Vijay Janapa Reddi
**Topic:** Autonomous AI Agents, Hardware-Software Co-Design, Systems Infrastructure, Open Silicon
**Target Format:** Conference Keynote / Distinguished Lecture

---

## 🎯 Official Keynote Abstract (295 words — Recommended Sweet Spot)

> Modern computing systems have reached unprecedented levels of physical and architectural complexity, pushing traditional human-driven design methodologies past their sustainable scaling limits. With the breakdown of Dennard scaling and the rise of post-Moore specialization, architects must navigate an exponentially expanding design space spanning heterogeneous accelerators, 2.5D/3D multi-die packaging, domain-specific instruction sets, and dynamic machine learning software stacks. While architectural complexity compounds exponentially, engineering team bandwidth scales linearly—creating a widening "scissors gap" where design exploration, physical placement, and verification signoff consume unsustainable cost and time.
>
> This keynote presents **Architecture 2.0**, a new paradigm for computer system design in which autonomous AI agents serve as first-class, collaborative partners across the entire research, specification, implementation, and signoff lifecycle. While machine learning has traditionally influenced computer architecture through isolated point-heuristics and surrogate optimization, agentic design fundamentally transforms this workflow: AI agents actively synthesize architectural variants, invoke compilers and cycle-accurate simulators inside deterministic execution sandboxes, inspect concrete physical and logical feedback, and autonomously iterate through timing and functional repair loops.
>
> Realizing this vision is fundamentally a **systems infrastructure challenge** rather than an AI modeling problem. It demands a shared precompetitive ecosystem: standardized execution harnesses, deterministic simulation sandboxes, verifiable feedback interfaces, and human-in-the-loop signoff governance that avoids moral crumple zones. Drawing inspiration from the 1979 Mead-Conway VLSI revolution that democratized integrated circuit design via ARPANET and multi-project wafers (MPC79), this talk charts a community-driven roadmap to build open datasets, standardized benchmarks, and accessible community shuttles—democratizing physical silicon design and establishing the foundations for the next era of intelligent computer architecture.

---

## 📢 Conference Program Blurb & Key Takeaways (For Website / Schedule)

* **The Complexity Wall:** Why post-Moore specialization and 2.5D/3D multi-die packaging break traditional manual design flows.
* **Agentic Closed Loops:** How autonomous AI agents transcend passive ML surrogates through iterative synthesis, sandboxed tool execution, and automated regression repair.
* **The Infrastructure Challenge:** Why verifiable feedback protocols (qualify-then-claim-then-act) and human signoff authority are required for trustworthy silicon design.
* **The Open Silicon Roadmap:** Democratizing hardware design through open PDKs, standardized simulation benchmarks, and low-cost community fabrication shuttles.

---

## 🔬 Extended Colloquium Edition (450 words — For Departmental Seminars & In-Depth Proposals)

> Computer systems architecture is undergoing a generational inflection point driven by the simultaneous convergence of extreme specialization, physical packaging limits, and the explosive compute demands of foundation models. Modern System-on-Chip (SoC) architectures no longer consist of uniform cores; they are complex heterogeneous ecosystems integrating domain-specific tensor cores, vector units, high-bandwidth memory hierarchies, and multi-die chiplet interconnects. Designing and optimizing these systems requires navigating vast, non-linear, multi-dimensional Pareto frontiers across latency, power, area, thermal dissipation, and software portability. Conventional human-driven methodologies—relying on manual RTL authoring, intuition-driven parameter sweeps, and siloed point-optimization heuristics—cannot scale to meet this combinatorial explosion.
>
> This talk introduces **Architecture 2.0**, an agentic framework that reimagines computer systems research and development by positioning autonomous AI agents as continuous, closed-loop collaborators. Moving beyond passive surrogate models and Bayesian parameter search, Architecture 2.0 empowers AI agents to operate directly on structured intermediate representations (such as MLIR, CIRCT, and high-level HDLs), formulate architectural hypotheses, interact with production-grade EDA toolchains, and autonomously debug and repair functional regressions. By closing the loop between generative reasoning and concrete simulation feedback, agentic workflows compress exploratory architectural timelines from months to hours while uncovering novel microarchitectural topologies that elude human intuition.
>
> However, deploying autonomous agents into high-stakes silicon engineering reveals critical scientific and infrastructural bottlenecks. Hardware design is unforgiving: physical silicon lacks the post-deployment patching mechanisms of software, making hallucinations and uncalibrated proxy metrics fatal to multimillion-dollar tapeouts. This talk examines the foundational infrastructure required to make AI agents trustworthy participants in systems research:
>
> 1. **Deterministic Execution Sandboxes:** Robust containerization and process-level isolation (cgroups v2, ephemeral namespaces) that allow agents to safely invoke unconstrained compilers, linters, and simulators.
> 2. **Verifiable Feedback Protocols:** Formal "qualify-then-claim-then-act" contracts that prevent reward hacking, Goodhart's law failures, and proxy optimizer curses.
> 3. **Nondelegable Commitment Governance:** Clear organizational boundaries and in-order human commitment authority that preserve accountability and avoid "moral crumple zones."
>
> Finally, we explore the democratization imperative of Architecture 2.0. Just as Lynn Conway and Carver Mead catalyzed the VLSI revolution in 1979 through standardized design rules and the MPC79 multi-university multi-project wafer (MPW), the modern architecture community must establish open-source PDKs, standardized agentic benchmark suites, and low-cost community fabrication shuttles (e.g., Tiny Tapeout and OpenTitan). We conclude with an actionable community roadmap for democratizing custom silicon, empowering non-experts to design, verify, and fabricate physical hardware at the velocity of software.

---

## ⚡ Short Program / Flyer Version (150 words — For Pocket Guides & Social)

> Modern computing systems have reached unprecedented complexity, pushing traditional manual design methodologies to their limits as architects navigate vast spaces spanning heterogeneous hardware, advanced packaging, compilers, and dynamic ML workloads. This keynote presents **Architecture 2.0**, a vision for the next era of computer system design in which autonomous AI agents serve as first-class collaborators throughout the architectural lifecycle. Moving beyond traditional ML point-heuristics, AI agents autonomously synthesize designs, execute inside sandboxed simulation environments, interpret verifiable physical feedback, and iteratively repair timing and functional defects. Realizing this vision is fundamentally a systems infrastructure challenge demanding deterministic execution harnesses, rigorous evaluation rubrics, and human-in-the-loop governance. Drawing inspiration from the 1979 Mead-Conway VLSI revolution, this talk outlines the foundational infrastructure required to make AI agents trustworthy partners in systems research and charts a community-driven roadmap for democratizing custom silicon design.
