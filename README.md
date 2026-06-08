# ITS Standard Extracts

Convert Microsoft Word *“Extract from the Technical Standard”* documents into
clean Markdown — with YAML front-matter, extracted figures and faithful tables —
and publish them on website for ISO/TC 204. Optionally a searchable [mdBook](https://rust-lang.github.io/mdBook/)
website can be generated.

> An *extract* summarises selected chapters of a source standard and retains the
> original chapter numbering. It is **informative only** and does not replace the
> standard itself.

---

## What it does

- **`.docx` → Markdown.** Parses each extract, emits one `index.md` per standard
  with structured front-matter and the body starting at *Introduction*.
- **Figures.** Extracts embedded images; converts vector EMF/WMF to PNG (via
  LibreOffice) and trims page whitespace.
- **Tables.** Renders Word tables as HTML `<table>` with `colspan`/`rowspan`, so
  merged cells survive and the text stays selectable, searchable and translatable.
- **Site.** Generates the mdBook navigation and builds a static, full-text-search
  website. A preprocessor strips the YAML front-matter and injects a title header
  so pages render cleanly.
- **Reproducible toolchain.** [`mise`](https://mise.jdx.dev) pins the tools;
  [`uv`](https://docs.astral.sh/uv/) manages Python and dependencies.

## Repository layout

```
extracts-md/
├── input/                       # source .docx files
├── output/                      # generated Markdown — the canonical deliverable
│   ├── index.md                 # landing page          (generated)
│   ├── SUMMARY.md               # mdBook table of contents (generated)
│   └── <STANDARD>/
│       ├── index.md             # the extract, with YAML front-matter
│       └── fig-N.png            # extracted figures
├── book/                        # built static site (git-ignored)
├── convert_docx.py              # docx → output/<doc>/index.md (+ figures, HTML tables)
├── gen_nav.py                   # regenerate SUMMARY.md + landing index.md
├── frontmatter_preprocessor.py  # mdBook preprocessor: strip front-matter, add H1
├── book.toml                    # mdBook configuration (src = output/)
├── pyproject.toml               # Python dependencies (python-docx, Pillow)
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
- **LibreOffice** on `PATH` — only used to rasterise vector (EMF/WMF) figures.
  ```sh
  brew install --cask libreoffice      # provides the `soffice` command
  ```
  Override the binary location with `SOFFICE_BIN=/path/to/soffice` if needed.

`mise` provides `uv` and `mdbook`; `uv` provides Python (`.python-version`) and
the packages in `pyproject.toml`. Nothing else to install by hand.

## Quick start

```sh
mise install      # install pinned tools: uv + mdbook
mise run setup    # uv installs Python + dependencies
mise run all      # convert  →  generate nav  →  build site into book/
mise run serve    # local preview with live reload
```

### Tasks

| Task              | Description                                               |
|-------------------|-----------------------------------------------------------|
| `mise run setup`  | `uv sync` — install Python and dependencies               |
| `mise run convert`| `input/*.docx` → `output/<doc>/index.md` (+ figures)      |
| `mise run gen`    | regenerate `SUMMARY.md` and the landing page              |
| `mise run build`  | build the static site into `book/`                        |
| `mise run serve`  | serve locally with live reload                            |
| `mise run all`    | `convert` + `gen` + `build`                               |

Adding a new extract is just: drop the `.docx` in `input/` and run `mise run all`.

## How conversion works

### Front-matter

Each `output/<doc>/index.md` begins with YAML front-matter:

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
- Word `Heading 1` is demoted to `##`, so each page has a single H1 — injected
  from `name` by the preprocessor at build time (the front-matter never appears
  on the rendered page).
- Tables → HTML; figures → `![…](fig-N.png)` with their captions.

## Customisation

- **Page title.** The injected H1 uses the full `name`. To use the shorter
  `{standard} — Extract` instead, edit `transform()` in
  `frontmatter_preprocessor.py`.
- **mdBook theme / search / folding.** Configure in `book.toml`.
- **Tool versions.** Pin in `mise.toml` (`uv`, `mdbook`) and `.python-version`.

## Troubleshooting

- **`FileNotFoundError: 'libreoffice'` / `'soffice'`** — install LibreOffice
  (`brew install --cask libreoffice`) or set `SOFFICE_BIN`. Only the documents
  containing EMF/WMF figures need it.
- **`uv` resolves a newer Python than pinned** — run `uv python pin 3.12 && uv sync`
  to lock the exact interpreter.

## License

The tooling in this repository may be licensed as you choose (add a `LICENSE`
file). The extract *content* is informative material about the referenced ISO /
CEN / EN standards and does not reproduce or replace those standards.
