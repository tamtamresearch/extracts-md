# Agent Instructions

## Project Overview

Converts Word `.docx` extracts of ISO/CEN/EN standards to Markdown with YAML front-matter, then previews them with an mkdocs (Material) static site that mirrors the production ISO-TC204 site. Python scripts orchestrate the pipeline; `mise` manages tooling and tasks.

> **This repo only produces `output/`.** The production site is built/deployed
> from a separate repository; `output/extracts/<doc>/` is copied there manually.
> The local mkdocs build exists so the preview matches production rendering.

## Critical Commands

**Always use `mise run <task>` — never call Python scripts directly.**

```sh
mise install              # first time: install uv + watchexec
mise run setup            # first time: install Python 3.12 + deps (incl. mkdocs)
mise run all              # full pipeline: convert + gen + build
mise run serve            # preview with live reload (mkdocs)
mise run dev              # watch input/*.docx → convert/gen + serve with browser reload
```

### Individual Tasks

```sh
mise run convert          # input/*.docx → output/extracts/<doc>/index.md (+ figures)
mise run gen              # regenerate mkdocs nav + landing page from front-matter
mise run build            # mkdocs build (auto-runs `gen` first)
mise run check            # scan input/*.docx for unconvertible content (e.g. vector figures)
mise run watch            # re-run convert + gen whenever an input .docx changes
```

`mise run dev` is the live-development entry point: it runs `watch` (re-converts
on `.docx` edits) alongside `mkdocs serve --open`, so editing a source document
triggers conversion and the browser reloads automatically.

## Key Architecture

- **Toolchain**: `mise` → `uv` → Python 3.12 + `python-docx` + `Pillow` + `mkdocs-material` + `pymdown-extensions` + `mkdocs-macros-plugin`
- **Input**: `input/*.docx` files (Word extracts)
- **Output**: `output/extracts/<doc>/index.md` (Markdown) + `output/extracts/<doc>/fig-N.png` (extracted images)
- **Build**: `site/` (static mkdocs site; git-ignored)

### Scripts & config

| File                | Purpose                                                            |
|---------------------|--------------------------------------------------------------------|
| `convert_docx.py`   | Parse `.docx`, emit Markdown with YAML + HTML tables + caption blocks |
| `gen_nav.py`        | Regenerate the mkdocs `nav:` block + landing page; copy `theme/extra.css` |
| `macros.py`         | mkdocs-macros: inject the standard-metadata box on extract pages   |
| `mkdocs.yml`        | mkdocs site config (Material, attr_list, md_in_html, blocks.caption) |
| `theme/extra.css`   | Figure/figcaption styling (copied to `output/stylesheets/extra.css`) |

**Never invoke scripts directly**; use `mise run <task>` so the uv-managed environment is active.

## Workflow Conventions

### Adding a New Extract

1. Drop `.docx` in `input/`
2. `mise run all`

File naming: `input/ISO_12345.docx` → `output/extracts/ISO_12345/index.md`

### Front-Matter Structure

Each `output/extracts/<doc>/index.md` begins with:

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
- Figures → `![Figure N](fig-N.png){.figure}` with extracted images
- **Captions** → `pymdownx.blocks.caption` blocks (verbatim docx text, no
  auto-numbering). pymdownx wraps the **preceding** block in a `<figure>`, so the
  caption block is always emitted **after** its object: figures use `/// caption`
  (figcaption renders below the image); tables/table-images use `/// caption | <`
  (figcaption renders above). Caption paragraphs are detected by a
  `Figure N`/`Table N` prefix **and** being centred / all-bold / a caption style
  — so ordinary prose starting with "Table" is left untouched.

At render time, `macros.py` (`on_pre_page_macros`) injects the standard-metadata
box (name + Published/Edition/Pages + annotation) from the YAML front matter.
mkdocs reads the YAML front matter natively.

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

1. **Task dependency**: `mise run build` and `mise run serve` both depend on `gen`, so the nav + landing page are regenerated before building.
2. **Nav generation**: `gen_nav.py` rewrites the `nav:` block in `mkdocs.yml` between the `# >>> GENERATED NAV START` / `# <<< GENERATED NAV END` markers — keep those markers intact.
3. **Czech custom styles**: `convert_docx.py` maps Czech Word styles (`Text normy`, `Seznam v normě`, `Poznámka`, `NadpisTabObr`) to Markdown equivalents.
4. **Vector figures abort conversion**: a `.docx` with EMF/WMF figures fails fast (`VectorFigureError`); convert those figures to raster (PNG/JPEG) first. `mise run check` reports them without aborting.
5. **Captions need mkdocs**: the `/// caption ///` syntax only renders under mkdocs (the production renderer + the local preview). It is plain text in other Markdown viewers.

## File Locations

```
input/                  # source .docx files (add new extracts here)
output/                 # canonical Markdown deliverable (commit these); = mkdocs docs_dir
  index.md              # landing page (generated)
  stylesheets/extra.css # figure/caption styling (copied from theme/extra.css)
  extracts/<STANDARD>/
    index.md            # the extract with YAML front-matter
    fig-N.png           # extracted figures
site/                   # built mkdocs site (git-ignored)
mkdocs.yml              # site config; nav block regenerated by gen_nav.py
macros.py               # metadata-box macro (mkdocs-macros)
theme/extra.css         # source CSS, copied into output/stylesheets/
```

## Common Mistakes to Avoid

- **Don't run Python scripts directly** — always use `mise run <task>`
- **Don't edit `output/index.md` manually** — regenerated by `gen_nav.py`
- **Don't hand-edit the `nav:` block in `mkdocs.yml`** — regenerated by `gen_nav.py`
- **Don't edit front-matter in `output/extracts/<doc>/index.md`** unless fixing a parser bug
- **Don't commit `site/` or `.venv/`** — both git-ignored

## Testing

Pytest-based test suite covering conversion, captions, navigation, and the metadata macro.

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
│   └── test_unit_gen_nav.py
└── fixtures/
    ├── docx/                 # real test extract (ISO_TS_22741-10.docx)
    └── sample_output/        # minimal extracts for gen_nav tests
```

### Key Tests

- **Real extract conversion** (`test_real_extract_iso22741_10`): validates front-matter, figures, caption blocks, tables, heading demotion
- **Navigation generation** (`test_navigation_generation`): validates the mkdocs `nav:` block + landing page generation
- **Metadata macro** (`test_metadata_macro_render`): validates the standard-metadata box rendering
- **Caption detection** (`test_is_caption_*`): validates `Figure N`/`Table N` caption recognition vs. prose
- **Vector figure rejection** (`test_convert_rejects_vector_figure`): validates that EMF/WMF figures fail fast

### Manual Verification

After making changes, also verify:

1. `mise run all` (should complete without errors)
2. `mise run serve` (inspect site; mkdocs serves at http://127.0.0.1:8000)
3. Spot-check a converted extract for correct front-matter, figures, captions, and tables
