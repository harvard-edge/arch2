# Architecture 2.0

*AI-Assisted Computer Architecture*

<p align="center">
  <a href="https://arch2.mlsysbook.ai/start.html"><b>Start with the card</b></a> ·
  <a href="https://arch2.mlsysbook.ai"><b>Website</b></a> ·
  <a href="https://arch2.mlsysbook.ai/book/"><b>Synthesis lecture</b></a> ·
  <a href="https://github.com/harvard-edge/arch2/tree/main/labs"><b>Labs</b></a> ·
  <a href="https://arch2.mlsysbook.ai/tools/"><b>Tool registry</b></a> ·
  <a href="https://arch2.mlsysbook.ai/readings.html"><b>Readings</b></a> ·
  <a href="https://arch2.mlsysbook.ai/workshops.html"><b>Workshops</b></a> ·
  <a href="https://github.com/harvard-edge/arch2/discussions"><b>Discussions</b></a>
</p>

<p align="center">
  <a href="https://github.com/harvard-edge/arch2/actions/workflows/publish-site.yml"><img src="https://img.shields.io/github/actions/workflow/status/harvard-edge/arch2/publish-site.yml?branch=main&label=site&logo=githubactions" alt="Site workflow"></a>
  <a href="https://arch2.mlsysbook.ai"><img src="https://img.shields.io/badge/site-arch2.mlsysbook.ai-1f6f8b" alt="Architecture 2.0 site"></a>
</p>

**Architecture 2.0** is the engineering discipline of using AI, grounded in
architectural representations, tools, and experiments, to formulate, explore,
implement, evaluate, explain, and defend computer architecture decisions. This
public research and teaching project develops that discipline through a
synthesis lecture, companion labs, community resources, and a versioned
design-loop card.

> [!IMPORTANT]
> **Work in progress.** This material is under active development.
> Arguments, terminology, examples, labs, and machine-readable interfaces may
> change as evidence and reader feedback improve. Tagged releases are stable
> snapshots; if you cite or build on the project, record the version you used.
> Corrections and technically grounded disagreement are welcome.

AI can assist across an architecture study, from framing a question and
constructing alternatives to testing mechanisms and defending a bounded
recommendation. A design loop organizes that work around architectural state,
tool feedback, evidence, and human judgment. The card records the question,
inputs, tool runs, results, and decision for one study; it does not define the
field.

Architecture 2.0 is part of the [mlsysbook.ai](https://mlsysbook.ai) family.

## Start Here

| If you want to... | Go here |
| --- | --- |
| Draft and validate a context-profile design-loop card in 30 minutes | [Start workflow](https://arch2.mlsysbook.ai/start.html) |
| Run a tool-backed student study and inspect its run archive | [Companion labs](https://github.com/harvard-edge/arch2/tree/main/labs) |
| Download the machine-checkable blank card | [YAML template](https://arch2.mlsysbook.ai/design-loop-card/template.yaml) |
| Read the core argument | [Architecture 2.0 synthesis lecture](https://arch2.mlsysbook.ai/book/) |
| Find tools, simulators, benchmarks, datasets, and loop infrastructure | [Tool registry](https://arch2.mlsysbook.ai/tools/) |
| Orient yourself with papers, posts, talks, and datasets | [Reading list](https://arch2.mlsysbook.ai/readings.html) |
| Find venues where this work is being discussed | [Workshops](https://arch2.mlsysbook.ai/workshops.html) |
| Submit a tool, dataset, benchmark, or artifact | [Submit](https://arch2.mlsysbook.ai/submit.html) |
| Ask questions or propose ideas | [GitHub Discussions](https://github.com/harvard-edge/arch2/discussions) |

## Participate

The project accepts proposed tools, readings, workshops, corrections, and
examples through structured GitHub forms. Maintainers review each proposal
before it becomes part of a public registry.

| Contribution | Submit |
| --- | --- |
| Tool, dataset, benchmark, model, or workflow | [Submit an artifact](https://arch2.mlsysbook.ai/submit.html) |
| Paper, post, talk, dataset, or reference | [Submit a resource](https://arch2.mlsysbook.ai/submit-resource.html) |
| Workshop, tutorial, CFP, or venue | [Submit a workshop](https://arch2.mlsysbook.ai/submit-workshop.html) |
| Correction or clarification | [Suggest a correction](https://github.com/harvard-edge/arch2/issues/new?template=suggest_book_correction.yml) |
| Broken link | [Report a link](https://github.com/harvard-edge/arch2/issues/new?template=report_broken_link.yml) |

Accepted contributions can be credited in this README through the
[All Contributors](https://allcontributors.org/) convention.

## Project Surfaces

The public site connects the following maintained surfaces.

| Surface | Role |
| --- | --- |
| **Synthesis lecture** | Develops the discipline of using AI to formulate, explore, implement, evaluate, explain, and defend computer architecture decisions. |
| **Design-loop card** | A versioned twelve-field review record with machine-checkable claims, evidence, independent profiles, replay, and decision rights. |
| **Companion labs** | A separate tool-backed practice path for producing evidence and replayable run archives without replacing the synthesis lecture's executed study. |
| **Tool registry** | A maintained index of simulators, proxy models, verification harnesses, benchmarks, datasets, and data representations, each tied to a role in an architecture design loop. |
| **Reading list** | A curated path through papers, SIGARCH posts, talks, datasets, and workshop writeups. |
| **Workshop archive** | Verified active calls when available, with prior events retained as an archive. |
| **Discussions** | A public place to propose questions and ideas when durable discussion is useful. |

## Repository Guide

| Path | What it contains |
| --- | --- |
| [`book/`](book/) | Quarto source for the synthesis lecture, including chapters, appendices, figures, and references. |
| [`labs/`](labs/) | Tool-backed exercises, the executed study, replay support, and tests. |
| [`design-loop-card/`](design-loop-card/) and [`schemas/`](schemas/) | Human-readable templates and machine-checkable contracts for recording a study. |
| [`examples/`](examples/) | Completed cards and supporting evidence that show how the contracts are used. |
| [`www/`](www/) and [`tools/`](tools/) | Source for the project site, community resources, and tool registry. |
| [`data/source-receipts/`](data/source-receipts/) and [`compliance/`](compliance/) | Source notes, permissions records, and publication checks. |

The repository is developed in public so that claims, examples, interfaces,
and teaching material can be inspected and improved together. A tagged release
captures a reviewed snapshot; work on the development branch may change before
the next tag.

## Reading Formats

Use the HTML or EPUB edition for reflowable reading and screen-reader semantics.
The current Springer-layout PDF is untagged and may not work reliably with
screen readers.

## Contributors

People who contribute tools, readings, workshops, corrections, examples,
datasets, or artifact pointers help make Architecture 2.0 useful to the field.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

## Development

Contributor guidance, environment setup, local build commands, branch policy,
and validation checks live in [CONTRIBUTING.md](CONTRIBUTING.md). The public
site is published at [arch2.mlsysbook.ai](https://arch2.mlsysbook.ai).

## Citation

Cite the tagged version you used rather than the development branch. The
repository carries a [`CITATION.cff`](CITATION.cff) entry, which GitHub renders
through the **Cite this repository** control in the sidebar. Tagged snapshots
are listed under [Tags](https://github.com/harvard-edge/arch2/tags).

## License

Copyright 2026 Vijay Janapa Reddi. The manuscript, figures, and supporting
materials are readable in public so that claims and teaching material can be
inspected, but that visibility is not a grant of reuse rights. See
[LICENSE.md](LICENSE.md) for the terms that currently apply before copying,
redistributing, or building on this material.
