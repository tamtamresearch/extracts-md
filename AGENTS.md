# Agent Instructions

## Project Overview

Converts Word `.docx` extracts of ISO/CEN/EN standards to Markdown with YAML front-matter, then builds an mdBook static site. Three Python scripts orchestrate the pipeline; `mise` manages tooling and tasks.

## Critical Commands

**Always use `mise run <task>` — never call Python scripts directly.**

```sh
mise install              # first time: install uv + mdbook
mise run setup            # first time: install Python 3.12 + deps
mise run all              # full pipeline: convert + gen + build
mise run serve            # preview with live reload
mise run dev              # watch input/*.docx → convert/gen + serve with browser reload
```

### Individual Tasks

```sh
mise run convert          # input/*.docx → output/<doc>/index.md (+ figures)
mise run gen              # regenerate SUMMARY.md + landing page from front-matter
mise run build            # mdbook build (auto-runs `gen` first)
mise run check            # scan input/*.docx for unconvertible content (e.g. vector figures)
mise run watch            # re-run convert + gen whenever an input .docx changes
```

`mise run dev` is the live-development entry point: it runs `watch` (re-converts
on `.docx` edits) alongside `mdbook serve --open`, so editing a source document
triggers conversion and the browser reloads automatically.

## Key Architecture

- **Toolchain**: `mise` → `uv` → Python 3.12 + `python-docx` + `Pillow`; `mdbook` for site build
- **Input**: `input/*.docx` files (Word extracts)
- **Output**: `output/<doc>/index.md` (Markdown) + `output/<doc>/fig-N.png` (extracted images)
- **Build**: `book/` (static site; git-ignored)

### Scripts

| Script                         | Purpose                                                   |
|--------------------------------|-----------------------------------------------------------|
| `convert_docx.py`              | Parse `.docx`, emit Markdown with YAML + HTML tables     |
| `gen_nav.py`                   | Generate `SUMMARY.md` + landing page from front-matter   |
| `frontmatter_preprocessor.py`  | mdBook preprocessor: strip YAML, inject title header     |

**Never invoke scripts directly**; use `mise run <task>` so the uv-managed environment is active.

## Workflow Conventions

### Adding a New Extract

1. Drop `.docx` in `input/`
2. `mise run all`

File naming: `input/ISO_12345.docx` → `output/ISO_12345/index.md`

### Front-Matter Structure

Each `output/<doc>/index.md` begins with:

```yaml
---
published: 2025
edition: 2
pages: 269
title: "ISO/TS 22726-1 - Extract"
standard: "ISO/TS 22726-1"
name: "Full standard title"
name_1: "Part 1 of title"
name_2: "Part 2 of title"
annotation: "This Extract does not replace..."
note: "Note: This Extract presents selected chapters..."
---
```

**Parsed from the Word doc**; do not edit manually unless fixing a parsing bug in `convert_docx.py`.

### Markdown Body

- Starts at **Introduction** heading; original clause numbering preserved
- Word `Heading 1` → `##` (H2); `Heading 2` → `###`, etc.
- Tables → HTML `<table>` with `colspan`/`rowspan` (merged cells preserved)
- Figures → `![caption](fig-N.png)` with extracted images

At build time, `frontmatter_preprocessor.py` strips YAML and injects H1 title from `name` field.

## Dependencies

No external binaries are required. (LibreOffice was previously needed to
rasterise EMF/WMF figures; the converter now rejects vector figures instead — see
the vector-figure note below.)

### Python Packages

Managed by `uv`; defined in `pyproject.toml`:
- `python-docx` — parse Word documents
- `Pillow` — image handling

### Vector (EMF/WMF) figures

`convert_docx.py` only embeds raster images. If a `.docx` contains a vector
EMF/WMF figure, `mise run convert` **stops** with a `VectorFigureError` naming
the offending document and figure. Fix it by opening the `.docx`, converting the
figure to PNG/JPEG, re-embedding it, and rerunning. Use `mise run check` to list
every problematic document in one pass.

## Quirks & Gotchas

1. **Task dependency**: `mise run build` and `mise run serve` both depend on `gen`, so SUMMARY.md is always regenerated before building.
2. **Preprocessor execution**: `book.toml` calls `uv run python frontmatter_preprocessor.py` to ensure the venv is active.
3. **Czech custom styles**: `convert_docx.py` maps Czech Word styles (`Text normy`, `Seznam v normě`, `Poznámka`, `NadpisTabObr`) to Markdown equivalents.
4. **Vector figures abort conversion**: a `.docx` with EMF/WMF figures fails fast (`VectorFigureError`); convert those figures to raster (PNG/JPEG) first. `mise run check` reports them without aborting.

## File Locations

```
input/           # source .docx files (add new extracts here)
output/          # canonical Markdown deliverable (commit these)
  index.md       # landing page (generated)
  SUMMARY.md     # mdBook TOC (generated)
  <STANDARD>/
    index.md     # the extract with YAML front-matter
    fig-N.png    # extracted figures
book/            # built static site (git-ignored)
```

## Common Mistakes to Avoid

- **Don't run Python scripts directly** — always use `mise run <task>`
- **Don't edit `output/SUMMARY.md` or `output/index.md` manually** — regenerated by `gen_nav.py`
- **Don't edit front-matter in `output/<doc>/index.md`** unless fixing a parser bug
- **Don't commit `book/` or `.venv/`** — both git-ignored

## Testing

Pytest-based test suite with 26 tests covering conversion, navigation, and preprocessing.

### Test Commands

```sh
mise run preflight        # validate environment (dependencies)
mise run test             # full test suite (preflight → integration → unit)
mise run test-integration # core tests (implementation-agnostic)
mise run test-unit        # function-level tests (implementation-specific)
```

### Test Structure

```
tests/
├── test_preflight.py         # environment validation
├── test_integration.py       # end-to-end tests (safe during refactoring)
├── unit/                     # implementation-specific tests
│   ├── test_unit_convert.py
│   ├── test_unit_gen_nav.py
│   └── test_unit_preprocessor.py
└── fixtures/
    ├── docx/                 # real test extract (ISO_TS_22741-10.docx)
    └── sample_output/        # minimal extracts for gen_nav tests
```

### Key Tests

- **Real extract conversion** (`test_real_extract_iso22741_10`): validates front-matter, figures, tables, heading demotion
- **Navigation generation** (`test_navigation_generation`): validates SUMMARY.md and index.md generation
- **Preprocessor transform** (`test_preprocessor_transform`): validates YAML stripping and H1 injection
- **Vector figure rejection** (`test_convert_rejects_vector_figure`): validates that EMF/WMF figures fail fast

### Manual Verification

After making changes, also verify:

1. `mise run all` (should complete without errors)
2. `mise run serve` (inspect site at http://localhost:3000)
3. Spot-check a converted extract for correct front-matter, figures, and tables
