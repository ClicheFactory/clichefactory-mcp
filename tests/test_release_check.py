"""scripts/release_check.py: the gate the release workflow runs before building."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
_spec = importlib.util.spec_from_file_location("release_check", _SCRIPT)
release_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_check)

CHANGELOG = """# Changelog

## [0.2.0] — 2026-11-20

### Added

- Balance tool.

## [0.2.0rc1] — 2026-11-15

- Balance tool (release candidate).

## [0.1.9] — 2026-06-16

- Older.
"""


@pytest.fixture
def repo(tmp_path: Path):
    def make(about: str, server: str, plugin: str, package: str | None = None) -> Path:
        (tmp_path / "cliche_mcp").mkdir(exist_ok=True)
        (tmp_path / "cliche_mcp" / "__about__.py").write_text(f'__version__ = "{about}"\n')
        (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
        (tmp_path / "server.json").write_text(json.dumps({
            "version": server,
            "packages": [{"registryType": "pypi", "identifier": "clichefactory-mcp",
                          "version": package or server}],
        }))
        (tmp_path / ".plugin").mkdir(exist_ok=True)
        (tmp_path / ".plugin" / "plugin.json").write_text(json.dumps({"version": plugin}))
        return tmp_path

    return make


def test_final_release_with_every_version_in_step(repo):
    root = repo("0.2.0", "0.2.0", "0.2.0")
    version, notes = release_check.check("v0.2.0", root)
    assert version == "0.2.0"
    assert notes == "### Added\n\n- Balance tool."


def test_final_release_lists_every_lagging_field(repo):
    root = repo("0.2.0", "0.1.9", "0.1.8", package="0.1.9")
    with pytest.raises(release_check.ReleaseError) as exc:
        release_check.check("v0.2.0", root)
    msg = str(exc.value)
    assert "server.json version is '0.1.9'" in msg
    assert "server.json packages[pypi].version is '0.1.9'" in msg
    assert ".plugin/plugin.json version is '0.1.8'" in msg


def test_prerelease_ignores_published_files(repo):
    # server.json / plugin.json keep naming the last final release during an rc.
    root = repo("0.2.0rc1", "0.1.9", "0.1.9")
    version, notes = release_check.check("v0.2.0rc1", root)
    assert release_check.is_prerelease(version)
    assert notes == "- Balance tool (release candidate)."


@pytest.mark.parametrize(
    "tag, about, reason",
    [
        ("v0.2.1", "0.2.0", "__about__.py says 0.2.0"),
        ("0.2.0", "0.2.0", "must look like"),
        ("v1.0.0", "1.0.0", "no '## [1.0.0]"),
    ],
)
def test_mismatches_fail_with_the_reason(repo, tag, about, reason):
    root = repo(about, tag.lstrip("v"), tag.lstrip("v"))
    with pytest.raises(release_check.ReleaseError, match=reason.replace("[", r"\[")):
        release_check.check(tag, root)


def test_current_repo_is_releasable_as_is():
    """main must always pass the check for its own version."""
    version = release_check.package_version()
    release_check.check(f"v{version}")
