# Releasing `clichefactory-mcp`

Releases are published by GitHub Actions (`.github/workflows/release.yml`)
when a version tag is pushed: to PyPI, then (final releases only) to the MCP
registry, then as a GitHub release. Nothing is uploaded from a laptop and no
token is stored anywhere: PyPI trusts this repo's release workflow (trusted
publishing), the MCP registry trusts GitHub's OIDC token for the
`io.github.ClicheFactory` namespace, and the PyPI step waits for the owner's
approval.

Versioning is SemVer (pre-1.0: minor for a new tool or other additive
surface, patch for bugfix / dependency floor / docs). The version lives in
three places, and the release check fails if they disagree:

| File | Field |
| --- | --- |
| `cliche_mcp/__about__.py` | `__version__` (the source of truth; `pyproject.toml` reads it) |
| `server.json` | `version` and `packages[0].version` (published to the MCP registry) |
| `.plugin/plugin.json` | `version` (Claude plugin manifest) |

`clichefactory-mcp` has no downstream consumers: users install it with
`uvx clichefactory-mcp` or `pip install clichefactory-mcp`.

---

## Release checklist

```
- [ ] 1. PR: bump the version in all three files, add the CHANGELOG.md entry
         (and the clichefactory floor, if this release needs a newer SDK)
- [ ] 2. Merge it (tests must be green)
- [ ] 3. Tag main and push the tag
- [ ] 4. Approve the publish job in the Actions tab
- [ ] 5. Check PyPI, the MCP registry and the GitHub release
```

### 1. Version bump and changelog (in a PR)

| Bump  | When                                                  |
| ----- | ----------------------------------------------------- |
| patch | Bugfix, SDK floor bump, docs only, no tool change     |
| minor | New tool / new resource / additive surface change     |
| major | Breaking change (post-1.0 only; pre-1.0 use minor)    |

Set the version in `cliche_mcp/__about__.py`, `server.json` (both fields) and
`.plugin/plugin.json`, and add an entry at the top of `CHANGELOG.md`. The
GitHub release notes are this entry, so the heading must be exactly:

```markdown
## [X.Y.Z] — YYYY-MM-DD
```

If the release needs a newer SDK, raise the floor in `pyproject.toml`
(`"clichefactory>=A.B.C"`). `uv.lock` is gitignored here, so the floor is
what users get.

Check it before pushing (standard library only, no install needed):

```bash
python scripts/release_check.py vX.Y.Z
```

### 2. Merge

`tests.yml` runs on the PR: the tests on Python 3.12 and 3.13, installed
without `[local]` the way `uvx` installs it, plus the release check for the
version on the branch.

### 3. Tag and push

```bash
git fetch origin && git tag -a vX.Y.Z -m vX.Y.Z origin/main && git push origin vX.Y.Z
```

The release workflow then:

1. checks the tag, the three version fields and the changelog agree, and
   that the commit is on `main`;
2. runs the tests, builds, installs the wheel in a clean venv and checks the
   version it reports;
3. **waits for approval**, then publishes to PyPI;
4. waits until PyPI serves the new version, then publishes `server.json` to
   the MCP registry (`mcp-publisher`, pinned, signature verified);
5. creates the GitHub release.

If step 1 or 2 fails, nothing is published. Fix it, delete the tag
(`git push --delete origin vX.Y.Z && git tag -d vX.Y.Z`), and tag again.

### 4. Approve

Actions tab → the `release` run → **Review deployments** → `pypi` → Approve.

### 5. Check

- https://pypi.org/project/clichefactory-mcp/ shows the new version.
- `https://registry.modelcontextprotocol.io/v0/servers?search=clichefactory`
  lists it.
- https://github.com/ClicheFactory/clichefactory-mcp/releases has the release.

---

## Release candidates

A pre-release (`X.Y.ZrcN`, also `aN` / `bN`) goes to PyPI and GitHub (marked
pre-release) but **not** to the MCP registry, so registry users stay on the
last final release. `uvx clichefactory-mcp` ignores pre-releases; try one
with:

```bash
uvx clichefactory-mcp==0.2.0rc1
```

For an rc, only `__about__.py` and the changelog entry need the rc version;
`server.json` and `plugin.json` keep naming the last final release until the
final one. A pre-release may be tagged from a branch.

---

## One-time setup (repo owner)

1. **PyPI → trusted publisher.** On
   https://pypi.org/manage/project/clichefactory-mcp/settings/publishing/, add
   a GitHub publisher:
   - Owner: `ClicheFactory`
   - Repository: `clichefactory-mcp`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
2. **GitHub → environment.** Repo Settings → Environments → New environment
   `pypi`:
   - Required reviewers: yourself ("Prevent self-review" off).
   - Deployment branches and tags: "Selected branches and tags", add the tag
     rule `v*`.
3. **MCP registry:** nothing to set up. `mcp-publisher login github-oidc`
   proves the workflow runs in a `ClicheFactory` repo, which is what the
   `io.github.ClicheFactory/*` namespace requires. The registry also checks
   that the PyPI README contains `mcp-name: io.github.ClicheFactory/clichefactory-mcp`
   (it's at the top of `README.md`; keep it).
4. **After the first release works,** revoke the old PyPI token.

---

## Troubleshooting

### "File already exists" from PyPI

PyPI never accepts the same version twice. Bump to the next patch (or the
next `rcN`) and release that.

### The check job fails

The message lists every mismatch: tag vs `__about__.py`, a missing changelog
entry, `server.json` / `plugin.json` lagging behind (final releases), or a
final release tagged off `main`.

### The registry job fails

- "Package validation failed": PyPI didn't have the version yet, or the
  README lost its `mcp-name:` line. Re-run the failed job from the Actions tab
  once PyPI shows the version.
- Signature verification failed: `MCP_PUBLISHER_VERSION` in `release.yml`
  must be a real release tag of `modelcontextprotocol/registry`.

PyPI and the GitHub release are not affected by a registry failure; re-run
just that job.

### `clichefactory-mcp` still resolves the old `clichefactory` after a floor bump

Locally: `uv lock --upgrade-package clichefactory`. Users get the floor from
`pyproject.toml`, since `uv.lock` isn't shipped.
