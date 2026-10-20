# Contributing to Architecture 2.0

Architecture 2.0 is a public research and teaching project built around a
synthesis lecture, a versioned design-loop card, and maintainer-reviewed
registries. Contributions of all sizes are welcome. Please also read our [Code
of Conduct](CODE_OF_CONDUCT.md).

## Use or extend the design-loop card

The [30-minute start workflow](https://arch2.mlsysbook.ai/start.html) helps a
reader draft and validate the context profile of a schema 2.0 card. It also
links the canonical YAML and Markdown templates, JSON Schema, complete v2
example, and non-inventive v1.1 migration command. Validate any completed card
from a repository clone.

```bash
python3 -m venv .venv-card
.venv-card/bin/python -m pip install pip==26.1.2
.venv-card/bin/python -m pip install -r requirements-card.txt
.venv-card/bin/python cli/arch2.py validate card path/to/card.yaml
```

The schema rejects unknown contract versions and fields. Review profiles are
independent, not cumulative. Mark a profile complete only when its required
bindings exist, and list missing bindings for every partial profile.

## Ways to contribute

### Add a tool to the registry

Built an open simulator, proxy model, verification harness, dataset, benchmark,
design loop, or agentic workflow?

1. Open the [Submit](https://arch2.mlsysbook.ai/submit.html) page, or use the
   [Submit a tool](https://github.com/harvard-edge/arch2/issues/new?template=submit_tool.yml)
   GitHub template directly.
2. Fill in the name, URL, artifact type, one primary category, a short public
   summary, and a brief note explaining why the item belongs in Architecture
   2.0. The summary is limited to 220 characters because it appears directly on
   the registry card.
3. Optionally add tags, authors, institutions, submitter credit, paper/preprint
   link, documentation link, artifact link, license, citation, inputs, outputs,
   evidence, limitations, and artifact status. The public card shows the concise
   summary, credit, category, and tags; the rest is preserved in the source
   artifact record.
4. New submissions enter as `unverified`. A maintainer records the observed
   artifact availability and verification date only after checking the links.
5. On submit, an automated check parses the form and opens a pull request adding
   one source file under `tools/registry/` and regenerating `tools/tools.yml`.
   A maintainer reviews it for fit and category, then merges. It appears on the
   site shortly after.

Categories are a fixed set (Simulation, Proxy Models, Agentic Workflows, Data
Representations, Verification, Benchmarks and Datasets, Physical Design) so the
registry filter stays coherent. Use tags for secondary labels. If none of the
categories fit, choose **Not sure / suggest a category** in the issue form and
add the suggested category. The generated pull request will be marked
`Needs Triage` until a maintainer maps it to the final category.

The registry is not meant to be a general tool directory. A tool should explain
what it contributes to an architecture design loop: state, actions, simulation
feedback, proxy feedback, verification, datasets, benchmarks, evidence,
physical design, or agent workflow infrastructure.

You can validate the registry locally with:

```bash
arch2 validate registries
```

### Add a workshop or venue

Organizing a workshop, special session, or recurring venue relevant to
Architecture 2.0, ML for systems, agentic AI, or AI-assisted computer
architecture?

1. Open the [Submit a workshop](https://arch2.mlsysbook.ai/submit-workshop.html) page.
2. Fill in the workshop name, website, venue or host, start and end dates,
   primary topic, and a short description.
3. Optionally add location, organizers, institutions, CFP/submission URL, and
   deadline so the card is useful to potential submitters.
4. The workflow opens a pull request adding one source file under
   `www/workshops/` and regenerating `www/workshops.yml`.

Validate the workshop registry locally with:

```bash
arch2 validate registries
```

### Add a reading or resource

Submitting a paper, SIGARCH post, podcast, talk, dataset, or other reference
that helps readers orient around Architecture 2.0?

1. Open the [Submit a resource](https://arch2.mlsysbook.ai/submit-resource.html) page.
2. Fill in the resource title, URL, type, primary topic, and short description.
3. Optionally add venue/source, date, authors, and DOI so the card is easy to
   cite and evaluate.
4. The workflow opens a pull request adding one source file under
   `www/readings/` and regenerating `www/readings.yml`.

Validate the reading list locally with:

```bash
PYTHONPATH=.github/scripts python .github/scripts/validate_readings.py
```

### Suggest a book correction

Found a typo, a broken cross-reference, an unclear passage, or a wrong citation?
Open an issue with the **Suggest a book correction** template, or, for a small
fix, open a pull request directly. Book source lives under `book/` as Quarto
Markdown (`.qmd`).

### Report a broken link

Use the **Report a broken link** template. A weekly job also scans for link rot
and files issues automatically.

## Building the site locally

The site is three Quarto projects (`www/`, `tools/`, `book/`) assembled into one.
Install Quarto 1.9.36 and EPUBCheck 5.3.0 separately, then make `quarto` and
`epubcheck` available on `PATH`. On macOS, `brew install epubcheck` installs the
EPUB validator. Then create and activate the Python environment:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install pip==26.1.2
.venv/bin/python -m pip install -e .
source .venv/bin/activate
```

CI uses Python 3.11.15 and Quarto 1.9.36. The reviewed Linux dependency
resolution is recorded in `.github/constraints/py311-linux.txt`; local environments may
resolve platform-specific wheels from the direct requirements.

```bash
# Landing page + registries only (fast, no LaTeX needed):
SKIP_BOOK=1 .github/scripts/build_site.sh
python3 -m http.server 8757 --directory _site   # then open http://localhost:8757/

# Or render a single project:
quarto render www
quarto render tools
```

Rendering the book requires the `arch2` CLI and a LaTeX toolchain; a full build is
`.github/scripts/build_site.sh`. Workflow-owned scripts live under `.github/scripts/`.

## Pull requests

- Keep changes focused and describe what and why.
- Site and registry PRs are checked automatically (registry schema + render).
- Be kind in review. We are all here to build the same thing.

## Branch and release flow

- `dev` is the integration branch. Every push to `dev` runs the pre-commit and
  root test gates, registry validation, site renders, the full book build, and
  the Python 3.10/3.11 lab matrix.
- `main` is the release branch. Updating `main` runs the same pre-commit gate
  first, then performs the full site/book build and GitHub Pages publish.
- Do not promote `dev` to `main` until the `Validate site` workflow is green.
- An exact `vMAJOR.MINOR.PATCH` tag is the only stable release identity. Untagged
  builds carry the current commit ID as `vMAJOR.MINOR.PATCH+g<sha>` and remain
  development builds. Keep `CITATION.cff` aligned with the latest release tag.
- Local pre-commit and GitHub preflight intentionally run the same hooks:

```bash
pre-commit run --all-files
```

## Contributor recognition

Accepted tools, resources, workshops, corrections, and artifact submissions are
community contributions. Maintainers can credit contributors in the README using
the [All Contributors](https://allcontributors.org/) convention after a PR is
merged.

Thank you for helping build Architecture 2.0.
