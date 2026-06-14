# ITS Standard Extracts

<!-- Add this badge once pushed to GitHub:
[![Deploy to GitHub Pages](https://github.com/<username>/<repository>/actions/workflows/deploy.yml/badge.svg)](https://github.com/<username>/<repository>/actions/workflows/deploy.yml)
-->

Convert Microsoft Word *"Extract from the Technical Standard"* documents into
clean Markdown — with YAML front-matter, extracted figures and faithful tables —
for the ISO/TC 204 website. The Markdown in `output/` is the deliverable (copied
into the production [mkdocs](https://www.mkdocs.org/) site repository); a local
[mkdocs Material](https://squidfunk.github.io/mkdocs-material/) build mirrors the
production rendering for preview.

> An *extract* summarises selected chapters of a source standard and retains the
> original chapter numbering. It is **informative only** and does not replace the
> standard itself.

---

## What it does

- **`.docx` → Markdown.** Parses each extract, emits one `index.md` per standard
  with structured front-matter and the body starting at *Introduction*.
- **Inline formatting.** Preserves **bold**, *italic*, and `code` formatting from
  Word documents. Monospace fonts (Courier New, etc.) are converted to inline code.
  Smart space handling ensures clean Markdown output.
- **Figures.** Extracts embedded raster images. Vector EMF/WMF figures are
  rejected; convert them to PNG/JPEG inside the `.docx` first.
- **Tables.** Renders Word tables as HTML `<table>` with `colspan`/`rowspan`, so
  merged cells survive and the text stays selectable, searchable and translatable.
- **Captions.** Figure/table captions are emitted as `pymdownx.blocks.caption`
  blocks (`/// caption`) — verbatim docx text, no auto-numbering. Figure captions
  render **below** the image; table captions **above** the table. They are
  centred/styled by the mkdocs Material theme.
- **Site.** Builds a local mkdocs Material site (full-text search) that mirrors
  the production ISO-TC204 site; `gen_nav.py` regenerates the nav and a landing
  page, and `macros.py` injects the standard-metadata box from front matter.
- **Reproducible toolchain.** [`mise`](https://mise.jdx.dev) pins the tools;
  [`uv`](https://docs.astral.sh/uv/) manages Python and dependencies.

## Repository layout

```
extracts-md/
├── input/                       # source .docx files
├── output/                      # generated Markdown — the canonical deliverable; mkdocs docs_dir
│   ├── index.md                 # landing page             (generated)
│   ├── stylesheets/extra.css    # figure/caption styling   (generated copy)
│   └── extracts/<STANDARD>/
│       ├── index.md             # the extract, with YAML front-matter
│       └── fig-N.png            # extracted figures
├── site/                        # built mkdocs site (git-ignored)
├── tests/                       # pytest test suite
│   ├── test_preflight.py        # environment validation
│   ├── test_integration.py      # end-to-end tests
│   ├── unit/                    # function-level tests
│   └── fixtures/                # test data (real .docx + expected output)
├── convert_docx.py              # docx → output/extracts/<doc>/index.md (+ figures, captions, tables)
├── gen_nav.py                   # regenerate mkdocs nav + landing page; copy theme/extra.css
├── macros.py                    # mkdocs-macros: standard-metadata box
├── mkdocs.yml                   # mkdocs site config (docs_dir = output/)
├── theme/extra.css              # source CSS for figure/caption styling
├── pytest.ini                   # pytest configuration
├── pyproject.toml               # Python dependencies (python-docx, Pillow, mkdocs-material, …)
├── .python-version              # Python version, provisioned by uv
└── mise.toml                    # tool + task definitions
```

## Prerequisites

- [**mise**](https://mise.jdx.dev) — installs and runs everything else.
  Native Apple-Silicon binary:
  ```sh
  curl -fsSL https://github.com/jdx/mise/releases/latest/download/mise-macos-arm64 \
    -o ~/.local/bin/mise && chmod +x ~/.local/bin/mise
  # or: brew install mise   |   curl https://mise.run | sh
  ```

`mise` provides `uv` and `watchexec`; `uv` provides Python (`.python-version`)
and the packages in `pyproject.toml` (including mkdocs Material). No external
binaries need to be installed by hand.

## Quick start

```sh
mise install      # install pinned tools: uv + watchexec
mise run setup    # uv installs Python + dependencies (incl. mkdocs)
mise run all      # convert  →  generate nav  →  build site into site/
mise run serve    # local preview with live reload (mkdocs)
mise run dev      # watch input/*.docx → convert/gen + serve with browser reload
```

## Publishing

This repository **only produces `output/`**. The production ISO-TC204 site is
built and deployed from a separate repository; the `output/extracts/<doc>/`
folders are copied there manually. The local mkdocs build (`mise run build` →
`site/`) exists so the preview matches the production Material rendering.

### Tasks

| Task                   | Description                                               |
|------------------------|-----------------------------------------------------------|
| `mise run setup`       | `uv sync` — install Python and dependencies               |
| `mise run convert`     | `input/*.docx` → `output/extracts/<doc>/index.md` (+ figures) |
| `mise run gen`         | regenerate the mkdocs nav + landing page                  |
| `mise run build`       | build the static mkdocs site into `site/`                 |
| `mise run serve`       | serve locally with live reload (mkdocs)                   |
| `mise run all`         | `convert` + `gen` + `build`                               |
| `mise run check`       | scan `input/*.docx` for unconvertible content (vector figures) |
| `mise run watch`       | re-run `convert` + `gen` whenever an input `.docx` changes |
| `mise run dev`         | watch `.docx` + serve with browser reload (live dev)      |
| `mise run preflight`   | validate environment (dependencies)                       |
| `mise run test`        | run full test suite (35 tests)                            |
| `mise run test-integration` | run core end-to-end tests (implementation-agnostic) |
| `mise run test-unit`   | run function-level tests (implementation-specific)        |

Adding a new extract is just: drop the `.docx` in `input/` and run `mise run all`.

## Features

### Inline Formatting Support

The converter preserves Word inline formatting in Markdown:

- **Bold text** → `**bold text**`
- *Italic text* → `*italic text*`
- `Code/verbatim` → `` `code` ``
- ***Bold+italic*** → `***text***`

**Smart handling:**
- Monospace fonts (Courier New, Consolas, Monaco) are converted to inline code
- Code formatting takes precedence: monospace text with bold/italic is rendered as plain code
- Consecutive runs with identical formatting are merged (prevents `**word** **by** **word**`)
- Leading/trailing spaces are moved outside formatting markers (prevents `**text **`)

**Example from ISO 14823-1:**

Before (Word): `{joint-iso-itut(2) its(28) gdd(5)}` in Courier New font  
After (Markdown): `` `{joint-iso-itut(2) its(28) gdd(5)}` ``

## How conversion works

### Front-matter

Each `output/extracts/<doc>/index.md` begins with YAML front-matter:

```yaml
---
published: 2025
edition: 2
pages: 269
title: "ISO/TS 22726-1 - Extract"
standard: "ISO/TS 22726-1"
name: "Intelligent transport systems – Dynamic data and map database … – Part 1: …"
name_1: "Intelligent transport systems"
name_2: "Dynamic data and map database specification for connected and automated driving system applications"
name_3: "Part 1: Architecture and logical data model for harmonization of static map data"
annotation: "This Extract does not replace the technical standard itself; it is only informative material about the standard."
note: "Note: This Extract presents selected chapters of the described document and retains the original chapter numbering."
---
```

`standard` and `name` come from the title table; `name_1..n` is the title split
on the en-dash; `published`/`edition`/`pages` are parsed from the *“Published …”*
line (`edition`/`pages` are omitted when absent).

### Body

- Starts at the **Introduction**; original clause numbering is preserved.
- Word `Heading 1` is demoted to `##`. mkdocs reads the YAML front matter
  natively, and `macros.py` injects the standard-metadata box (name +
  Published/Edition/Pages + annotation) at the top of each extract page.
- **Inline formatting preserved:**
  - Bold text → `**text**`
  - Italic text → `*text*`
  - Monospace/code → `` `text` ``
  - Code formatting takes precedence (monospace text ignores bold/italic)
  - Consecutive runs with identical formatting are merged for clean output
- Tables → HTML; figures → `![Figure N](fig-N.png){.figure}`.
- **Captions** → `pymdownx.blocks.caption` blocks. Figure captions are appended
  (below the image, `/// caption`); table captions are prepended (above,
  `/// caption | <`). Caption text is kept verbatim from the docx.

## Customisation

- **Metadata box.** Edit `render_standard_metadata` in `macros.py`.
- **Figure/caption styling.** Edit `theme/extra.css` (copied to
  `output/stylesheets/extra.css` by `gen_nav.py`).
- **mkdocs theme / extensions / search.** Configure in `mkdocs.yml`. The `nav:`
  block between the `GENERATED NAV` markers is regenerated by `gen_nav.py`.
- **Tool versions.** Pin in `mise.toml` (`uv`, `watchexec`) and `.python-version`.

## Testing

A pytest-based test suite covers conversion, captions, navigation, and the
metadata macro:

```sh
mise run preflight        # validate environment (dependencies)
mise run test             # full test suite (~2s)
mise run test-integration # core end-to-end tests (implementation-agnostic)
mise run test-unit        # function-level tests (implementation-specific)
```

### Test Coverage

- **Pre-flight tests**: environment validation, dependency checks
- **Integration tests**: real extract conversion (figures, captions, tables),
  navigation generation, metadata macro
- **Unit tests**: `clean()`, `yaml_q()`, inline formatting, caption detection
  (`is_caption`/`caption_kind`/`caption_block`), vector-figure rejection

The integration tests use a real extract (`ISO_TS_22741-10.docx`) and validate:
- Front-matter structure and all required fields
- Figure extraction (2 PNG files) with `{.figure}` references
- Caption blocks: figure caption appended, table caption prepended (once each)
- Table rendering as HTML with `colspan`/`rowspan`
- Heading demotion (H1 → H2)
- mkdocs nav block + landing page generation

## Troubleshooting

- **`VectorFigureError: ... is a vector image (EMF/WMF)`** — a `.docx` contains a
  vector figure, which cannot be embedded. Open the document, convert the figure
  to PNG/JPEG, re-embed it, and rerun. Run `mise run check` to list every
  affected document at once.
- **`uv` resolves a newer Python than pinned** — run `uv python pin 3.12 && uv sync`
  to lock the exact interpreter.
- **Tests failing** — run `mise run preflight` first to validate your environment.

## License

The tooling in this repository may be licensed as you choose (add a `LICENSE`
file). The extract *content* is informative material about the referenced ISO /
CEN / EN standards and does not reproduce or replace those standards.
