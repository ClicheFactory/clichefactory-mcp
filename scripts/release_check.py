"""Check a release tag against the package version, the other version fields and the changelog.

Usage:

    python scripts/release_check.py v0.2.0
    python scripts/release_check.py v0.2.0rc1 --notes-out notes.md

Fails (exit 1, with every reason) unless:

* the tag is ``v`` + the version in ``cliche_mcp/__about__.py``,
* ``CHANGELOG.md`` has a ``## [<version>]`` entry, and
* for a final release (not ``aN`` / ``bN`` / ``rcN`` / ``.devN``), the version
  in ``server.json`` (top-level and the PyPI package entry) and in
  ``.plugin/plugin.json`` is the same. Those two are published as-is (to the
  MCP registry and as the Claude plugin manifest), so they must not lag. A
  pre-release goes to PyPI only, so they may still name the last final
  release.

``--notes-out`` writes the changelog entry, which becomes the GitHub release
notes. In GitHub Actions it also sets the step outputs ``version`` and
``prerelease``.

Uses only the standard library, so it runs before anything is installed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_PRERELEASE = re.compile(r"(a|b|rc|\.dev)\d+$")


class ReleaseError(Exception):
    pass


def package_version(root: Path = ROOT) -> str:
    about = root / "cliche_mcp" / "__about__.py"
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', about.read_text(), re.M)
    if not m:
        raise ReleaseError("no __version__ in cliche_mcp/__about__.py")
    return m.group(1)


def changelog_entry(version: str, root: Path = ROOT) -> str | None:
    """The body of ``## [version] — date``, up to the next ``## [`` heading."""
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", re.M | re.S
    )
    m = pattern.search((root / "CHANGELOG.md").read_text())
    if not m:
        return None
    return m.group(1).strip() or None


def published_versions(root: Path = ROOT) -> dict[str, str | None]:
    """Version fields of the files that are published as they are."""
    server = json.loads((root / "server.json").read_text())
    plugin = json.loads((root / ".plugin" / "plugin.json").read_text())
    pypi = [p for p in server.get("packages", []) if p.get("registryType") == "pypi"]
    return {
        "server.json version": server.get("version"),
        "server.json packages[pypi].version": pypi[0].get("version") if pypi else None,
        ".plugin/plugin.json version": plugin.get("version"),
    }


def is_prerelease(version: str) -> bool:
    return bool(_PRERELEASE.search(version))


def check(tag: str, root: Path = ROOT) -> tuple[str, str]:
    """Return (version, release notes), or raise ReleaseError listing every problem."""
    if not tag.startswith("v"):
        raise ReleaseError(f"tag {tag!r} must look like v1.2.3 or v1.2.3rc1")
    version = tag[1:]
    problems = []
    pkg = package_version(root)
    if version != pkg:
        problems.append(f"cliche_mcp/__about__.py says {pkg}")
    notes = changelog_entry(version, root)
    if notes is None:
        problems.append(f"CHANGELOG.md has no '## [{version}] — YYYY-MM-DD' entry")
    if not is_prerelease(version):
        for field, value in published_versions(root).items():
            if value != version:
                problems.append(f"{field} is {value!r}")
    if problems:
        raise ReleaseError(f"tag {tag} does not match: " + "; ".join(problems))
    return version, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tag", help="the git tag, e.g. v0.2.0")
    parser.add_argument("--notes-out", type=Path, help="write the changelog entry here")
    args = parser.parse_args(argv)

    try:
        version, notes = check(args.tag)
    except ReleaseError as exc:
        print(f"release check failed: {exc}", file=sys.stderr)
        return 1

    if args.notes_out:
        args.notes_out.write_text(notes + "\n")
    prerelease = is_prerelease(version)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"version={version}\nprerelease={str(prerelease).lower()}\n")
    kind = "pre-release (PyPI only)" if prerelease else "release (PyPI + MCP registry)"
    print(f"{args.tag}: {kind} {version}, versions and changelog entry agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
