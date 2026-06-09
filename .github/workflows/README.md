# GitHub Actions Workflows

## deploy.yml - Deploy to GitHub Pages

This workflow automatically builds and deploys the mdBook site to GitHub Pages whenever changes are pushed to the `master` branch.

### Workflow Steps

The workflow runs as a single job with sequential steps:

**Steps:**
1. **Checkout repository** - Get the latest code
2. **Install LibreOffice** - Required for EMF/WMF image conversion
3. **Install mise** - Tool version manager (provides uv, mdbook, Python)
4. **Run preflight checks** - Validates LibreOffice, Python dependencies
5. **Run test suite** - All 35 tests must pass
6. **Convert documents** - Word `.docx` → Markdown with figures
7. **Generate navigation** - Create `SUMMARY.md` and landing page
8. **Build mdBook** - Generate static site in `book/` directory
9. **Deploy to gh-pages** - Push `book/` contents to `gh-pages` branch

**If any step fails:** The workflow stops and no deployment occurs.

### Triggers

- **Push to master:** Automatically runs on every push
- **Manual trigger:** Can be run manually via GitHub Actions UI (workflow_dispatch)

### Permissions

The workflow requires:
- `contents: write` - Push to `gh-pages` branch

### Concurrency

Only one deployment can run at a time (`group: "pages"`). If a new deployment starts while one is running, the old one is cancelled.

## Setup Instructions

### 1. Push to Master

The workflow will run automatically on the next push to `master` and create a `gh-pages` branch with the built site.

### 2. Enable GitHub Pages

1. Go to repository **Settings** → **Pages**
2. Under "Source", select **Deploy from a branch**
3. Select branch: **gh-pages**
4. Select folder: **/ (root)**
5. Click **Save**

### 3. Monitor Workflow

1. Go to the **Actions** tab in GitHub
2. Click on the latest workflow run
3. View logs for the deployment

### 4. Access the Site

Once deployed, the site will be available at:
```
https://<username>.github.io/<repository>/
```

## Troubleshooting

### Tests Fail

**Problem:** The test job fails, preventing deployment.

**Solution:**
1. Check the test job logs in GitHub Actions
2. Run tests locally: `mise run test`
3. Fix any failing tests
4. Push the fix

### Build Fails

**Problem:** The build job fails to convert documents or build the site.

**Solution:**
1. Check the build job logs
2. Verify all Word documents are valid: `mise run convert`
3. Test the build locally: `mise run all`
4. Check for missing dependencies or configuration issues

### Deploy Fails

**Problem:** The deploy step fails to push to `gh-pages` branch.

**Solution:**
1. Check workflow has `contents: write` permission (already configured)
2. Verify no branch protection rules on `gh-pages`
3. Check the Actions logs for specific error messages

### LibreOffice Not Found (in CI)

**Problem:** Tests fail with "LibreOffice not found" error.

**Solution:**
The workflow uses Ubuntu runners which don't have LibreOffice pre-installed. Tests marked with `@pytest.mark.requires_libreoffice` should be skipped in CI, or LibreOffice should be installed in the workflow.

**Current behavior:** Tests requiring LibreOffice will fail if the fixtures contain EMF/WMF images. Consider:
1. Marking these tests to skip in CI
2. Adding LibreOffice installation step to the workflow
3. Using pre-converted PNG fixtures for CI

## Local Testing

Before pushing, test the workflow steps locally:

```sh
# Run what the test job does
mise run preflight
mise run test

# Run what the build job does
mise run convert
mise run gen
mise run build

# Preview the result
mise run serve
```

## Workflow Customization

### Change Branch

To deploy from a different branch, edit `deploy.yml`:

```yaml
on:
  push:
    branches:
      - main  # Change from 'master' to 'main'
```

### Add Slack/Discord Notifications

Add a notification step at the end of the deploy job:

```yaml
- name: Notify on deployment
  if: success()
  run: |
    curl -X POST ${{ secrets.WEBHOOK_URL }} \
      -d '{"text":"Deployed to GitHub Pages!"}'
```

### Cache Dependencies

Speed up the workflow by caching mise tools:

```yaml
- name: Cache mise tools
  uses: actions/cache@v3
  with:
    path: ~/.local/share/mise
    key: ${{ runner.os }}-mise-${{ hashFiles('mise.toml') }}
```

## Security

- **Secrets:** No secrets are required for basic deployment
- **Permissions:** Minimal permissions are granted (read contents, write pages)
- **Isolation:** Each job runs in a fresh Ubuntu container

## Monitoring

View deployment status:
1. **Actions tab:** See all workflow runs
2. **Commit badges:** Green checkmark = tests passed and deployed
3. **Environment:** Settings → Environments → `github-pages` shows deployment history
