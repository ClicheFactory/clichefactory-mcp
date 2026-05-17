# Releasing `clichefactory-mcp`

Checklist for cutting a new release of the MCP server to PyPI and GitHub.
Versioning is SemVer (pre-1.0: minor for additive features, patch for
bugfix / dependency bump / docs).

The single source of truth for the version is `cliche_mcp/__about__.py`.
`pyproject.toml` reads it dynamically via `[tool.hatch.version]`.

`clichefactory-mcp` has **no downstream consumers** — it's an end-user
MCP server installed by hand (`pip install clichefactory-mcp` or `uvx
clichefactory-mcp`), so there is no internal floor to bump after
publishing. That's the main reason this checklist is shorter than the
SDK's `RELEASE.md`.

---

## Prerequisites (one-time setup)

- `uv` installed (`brew install uv`)
- PyPI account with API token scoped to the `clichefactory-mcp` project:
  https://pypi.org/manage/account/token/
- Token saved as `UV_PUBLISH_TOKEN` in your shell environment, e.g. in
  `~/.zshrc`:
  ```bash
  export UV_PUBLISH_TOKEN=pypi-AgEI...
  ```

---

## Release checklist

Copy this block into your scratchpad and tick off as you go:

```
- [ ] 1. Pick the new version (X.Y.Z)
- [ ] 2. Bump cliche_mcp/__about__.py
- [ ] 3. (If clichefactory dep changed) bump floor in pyproject.toml + uv lock
- [ ] 4. Update CHANGELOG.md
- [ ] 5. Decide on README.md / other unstaged changes
- [ ] 6. uv build (after wiping dist/)
- [ ] 7. Smoke-test the wheel locally
- [ ] 8. uv publish
- [ ] 9. Commit, tag, push (main + tag)
- [ ] 10. Optional: GitHub release in the UI
```

---

### 1. Pick the new version

| Bump  | When                                                  |
| ----- | ----------------------------------------------------- |
| patch | Bugfix, dep floor bump, docs only, no API change      |
| minor | New tool / new resource / additive surface change     |
| major | Breaking change (post-1.0 only; pre-1.0 use minor)    |

### 2. Bump `cliche_mcp/__about__.py`

```python
__version__ = "X.Y.Z"
```

This is the only place to change it.

### 3. Bump the `clichefactory` floor (if needed)

If this release is being cut to pick up SDK changes, bump the floor in
`pyproject.toml`:

```toml
"clichefactory>=A.B.C",
```

…and refresh the local lock so smoke-tests resolve the new SDK
(note: `uv.lock` is gitignored in this repo — only `pyproject.toml`
ships, so the floor in `pyproject.toml` is what consumers will pin
against):

```bash
uv lock --upgrade-package clichefactory
grep -nE 'name = "clichefactory"|^version = "A\.B\.C"' uv.lock | head
```

### 4. Update `CHANGELOG.md`

Add a new entry at the top following Keep a Changelog style:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added / Changed / Fixed / Removed

- Concise bullet describing the change.
```

### 5. Decide on `README.md` / other unstaged changes

Run `git status`. If unrelated edits are sitting there, either include
them in this release if they're complete, or `git checkout -- <file>`
to revert. Don't ship a half-finished README.

### 6. `uv build` (after wiping `dist/`)

```bash
cd ~/ClicheFactory/cliche-mcp
rm -rf dist/
uv build
ls dist/
```

Expect:
- `clichefactory_mcp-X.Y.Z-py3-none-any.whl`
- `clichefactory_mcp-X.Y.Z.tar.gz`

Wiping `dist/` first prevents `uv publish` from re-uploading old
versions and getting a confusing 400 from PyPI.

### 7. Smoke-test the wheel locally

```bash
uv venv /tmp/cliche-mcp-test
source /tmp/cliche-mcp-test/bin/activate
uv pip install dist/clichefactory_mcp-X.Y.Z-py3-none-any.whl
python -c "import cliche_mcp; print(cliche_mcp.__version__)"
# Entry-point sanity: run it briefly with no stdin and kill, since
# `clichefactory-mcp` boots an MCP stdio server (it has no --help).
timeout 2 clichefactory-mcp </dev/null 2>&1 | head -5 || true
deactivate
rm -rf /tmp/cliche-mcp-test
```

If the version doesn't match, stop and figure out why before publishing.

### 8. `uv publish`

```bash
uv publish
```

Reads `UV_PUBLISH_TOKEN` from the environment. Or pass `--token` inline:

```bash
uv publish --token pypi-AgEI...
```

Confirm on https://pypi.org/project/clichefactory-mcp/ that the new
version shows up.

### 9. Commit, tag, push

```bash
cd ~/ClicheFactory/cliche-mcp

git add cliche_mcp/__about__.py CHANGELOG.md pyproject.toml
# (uv.lock is gitignored in this repo — don't try to add it)
# (also git add README.md if you're keeping those changes)

git commit -m "<type>: <summary>

Bumps version to X.Y.Z.

<bullet list of changes>"

git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

### 10. Optional: GitHub release in the UI

Only useful if you want pretty release notes / downloadable artifacts.
PyPI is the source of truth for `pip install`.

1. https://github.com/ClicheFactory/clichefactory-mcp/releases
2. **Draft a new release**
3. Choose the existing tag `vX.Y.Z`, target `main`
4. Title: `vX.Y.Z`
5. Description: paste the relevant CHANGELOG entry
6. Optionally drag in `dist/clichefactory_mcp-X.Y.Z-py3-none-any.whl`
   and `clichefactory_mcp-X.Y.Z.tar.gz`
7. Keep "Set as the latest release" checked, **Publish release**

---

## Troubleshooting

### `uv publish` fails with 400 / "File already exists"

PyPI does not allow re-uploading a version. You either:
- forgot to bump `__about__.py`, or
- left old artifacts in `dist/` from a previous release.

Fix: bump to the next patch (e.g. `X.Y.(Z+1)`), wipe `dist/`, rebuild,
republish. **Never** try to "fix" a published version in place — cut a
new patch instead.

### `clichefactory-mcp` still resolves the old `clichefactory` after a floor bump

`uv lock --upgrade-package clichefactory` is the magic command.
Without `--upgrade-package`, `uv lock` will keep the existing pinned
version even if the floor moved. After running it, `grep` the lock
file to confirm the new SDK version is actually pinned.

### Token leaked into shell history

Revoke it on PyPI immediately and generate a new one. Prefer
`UV_PUBLISH_TOKEN` in `~/.zshrc` over inline `--token` for this reason.
