# GitHub Actions Workflows

## deploy.yml — CI (validate, no deploy)

> Despite the filename, this workflow **does not deploy** anything. This
> repository only produces the Markdown in `output/`. The production ISO-TC204
> site is built and deployed from a separate repository; the
> `output/extracts/<doc>/` folders are copied there manually.

The workflow validates the conversion pipeline on every push to `master`, on
pull requests, and on manual dispatch.

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
9. **Upload artifact** — the built `site/` is uploaded for inspection.

**If any step fails:** the workflow stops; nothing is published.

### Triggers

- **Push to `master`** and **pull requests** — runs automatically.
- **Manual** — via the Actions UI (`workflow_dispatch`).

### Permissions

`contents: read` only — the workflow never writes to the repository.

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
