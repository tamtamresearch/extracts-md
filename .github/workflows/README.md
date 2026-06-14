# GitHub Actions Workflows

## deploy.yml — Deploy preview to GitHub Pages

This repository **produces** the Markdown in `output/` (the deliverable copied
manually into the production ISO-TC204 site repository). As a convenience, this
workflow also builds the local mkdocs preview and deploys it to **this repo's**
GitHub Pages (`gh-pages` branch) so the conversion result can be reviewed online.

> This is a **preview** only. The production site is built/deployed from a
> separate repository.

### Steps

1. **Checkout repository** — get the latest code.
2. **Install mise** — tool version manager (provides `uv`, Python, `watchexec`).
3. **Run preflight checks** — validate Python dependencies.
4. **Run test suite** — all tests must pass (`mise run test`).
5. **Check documents** — fail early if any `.docx` has unconvertible content
   (e.g. vector EMF/WMF figures); see `mise run check`.
6. **Convert documents** — `input/*.docx` → `output/extracts/<doc>/index.md`.
7. **Generate navigation** — regenerate the mkdocs `nav:` block + landing page.
8. **Build mkdocs site (strict)** — `uv run mkdocs build --strict` to catch
   broken links / config.
9. **Deploy preview** — push `site/` to the `gh-pages` branch (only on `master`).

**If any step fails:** the workflow stops; nothing is deployed.

### Triggers

- **Push to `master`** — runs and deploys.
- **Pull requests** — runs the build/tests only (no deploy).
- **Manual** — via the Actions UI (`workflow_dispatch`).

### Permissions

`contents: write` — required to push the built site to the `gh-pages` branch.

### GitHub Pages settings

In the repo **Settings → Pages**, set the source to **Deploy from a branch**,
branch **gh-pages** / **/ (root)**. The preview is served at
`https://tamtamresearch.github.io/extracts-md/`.

## Troubleshooting

### Tests fail

1. Check the job logs.
2. Reproduce locally: `mise run test`.
3. Fix and push.

### Vector figure rejected

`mise run check` / `mise run convert` fails with a `vector image (EMF/WMF)`
error when a `.docx` contains a vector figure. Open the document, convert the
figure to PNG/JPEG, re-embed it, and rerun. `mise run check` lists every
affected document in one pass.

### Build fails

`uv run mkdocs build --strict` fails on broken links or bad config. Reproduce
locally with `mise run build` (or `uv run mkdocs serve`) and inspect the output.

## Local testing

```sh
mise run preflight
mise run test
mise run check
mise run all      # convert + gen + build (site/)
mise run serve    # preview locally
```
