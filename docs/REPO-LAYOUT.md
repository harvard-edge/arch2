# Architecture 2.0 repository layout

Plan of record for how this monorepo is organized. Implementation
proceeds in phases; Phase 1 (book `contents/`) is the first structural
move under this plan.

## 1. Principles

1. **Surfaces, not a monoproject.** Each public product is a peer
   top-level directory with its own build root. Do not fold hub, book,
   tools, labs, and slides into one Quarto project.
2. **Config vs manuscript.** Under each surface, separate “how it
   builds” from “what is written.” For the book, all reader-facing
   `.qmd` (and chapter-local figures) live under `contents/`.
3. **One home URL per published product.** Stable public paths (`/`,
   `/book/`, `/tools/`) are product contracts; internal renames may not
   break them without an explicit redirect policy.
4. **Shared objects stay shared.** Card templates, schemas, figure
   receipts, CLI, tests, and compliance are **not** nested inside
   `book/` or `www/`.
5. **Singular until plural.** Keep `book/` (not `books/`) until there
   is a second volume. Keep `labs/` as the folder name unless a public
   rename is intentional.
6. **Mechanical moves before renames.** Path rewrites must update
   `_quarto.yml`, CLI contracts, tests, and prepare scripts in the same
   change.

## 2. Top-level map

```text
Arch2/
├── book/                 # Synthesis lecture (Quarto book)
├── www/                  # Hub site (Quarto website)
├── tools/                # Tool registry
├── labs/                 # Companion practice / tutorials
├── slides/               # Talk and workshop decks
├── design-loop-card/     # Human templates
├── schemas/              # Machine contracts
├── examples/             # Filled cards / demo artifacts
├── data/                 # Figure source receipts
├── cli/ + arch2          # Build, validate, release tooling
├── tests/
├── compliance/
├── constraints/
├── _global/
├── .github/
└── README, LICENSE, …
```

**Site assembly contract:**

| Source | Assembled under |
| --- | --- |
| `www/` | `_site/` (site root) |
| `book/_build/` | `_site/book/` |
| `tools/_site/` | `_site/tools/` |
| shared assets | `_site/images/`, `_site/schemas/`, … |

## 3. Surfaces

| Surface | Role | Build | Author/content root |
| --- | --- | --- | --- |
| **book** | Synthesis lecture | Quarto book via `arch2` | `book/contents/` |
| **www** | Hub site | Quarto website | `www/*.qmd` (optional later: `www/contents/`) |
| **tools** | Tool registry | Quarto + `registry/` | page at project root; data in `registry/` |
| **labs** | Practice tracks | Python + notebooks | `tutorial/`, `notebooks/`, `full_course/`, `arch2_labs/` |
| **slides** | Decks | LaTeX / Makefile | `slides/` |
| **card** | Study record | templates + schema | `design-loop-card/`, `schemas/`, `examples/` |

## 4. Book project

```text
book/
  _quarto.yml
  filters/  _extensions/  _styles/  _includes/  _python/  scripts/  config/
  tex/  csl/  SNmono.cls …
  images/                  # shared chrome + global figures
  references/              # bibliography (project root, not under parts)
  index.qmd                # thin home shim → include preface (URL: /book/index.html)
  contents/
    frontmatter/
      preface.qmd          # sole preface body
      acknowledgments.qmd
      about-the-author.qmd
      disclosure.qmd
    parts/
    chapters/
    backmatter/
```

### Locked decisions

| Topic | Record |
| --- | --- |
| One preface source | `contents/frontmatter/preface.qmd` only |
| Other front matter | Separate pages under `contents/frontmatter/` |
| Quarto YAML keys | Keep `book.chapters` / `book.appendices`; folders may be named frontmatter/backmatter |
| Art | Chapter-local under `contents/chapters/…/images/`; global under `book/images/` |
| Bibliography | `book/references/` at project root |
| Home URL | Public `/book/index.html` preserved via thin root `index.qmd` that includes the preface |

### Outside `contents/`

Render machinery: `_quarto.yml`, filters, extensions, styles, includes, TeX, CSL, scripts, shared Python plot helpers, build/freeze dirs.

## 5. Anti-patterns

- Repo-root `contents/` for all surfaces
- Nesting www/tools/labs inside `book/`
- Dual full preface copies
- Renaming the Quarto `appendices:` key for aesthetics
- Casual `labs` → `tutorials` path rename
- Premature `books/` plural tree

## 6. Phases

| Phase | Scope | Status |
| --- | --- | --- |
| **0** | This document | Done |
| **1** | `book/contents/` + single preface; update contracts; keep `/book/` URLs | Done (2026-08) |
| **2** | README / guide alignment | Partial (README points here) |
| **3** | Optional www/tools `contents/` tidy | Future |
| **4** | Optional product renames; multi-volume only when real | Future |

Out of scope for layout: receipt CSV hygiene, labs track consolidation, permissions-ledger tombstones.

## 7. Open implementation detail (Phase 1)

- **Home technique:** thin root `index.qmd` with Quarto `include` of `contents/frontmatter/preface.qmd` (preferred; preserves `/book/index.html`).
- **References:** stay at `book/references/`.
- **Global images:** stay at `book/images/` for shared use by www/tools.
