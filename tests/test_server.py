"""Smoke tests for the MCP server: no network, no LLM, no ClicheFactory key.

The live, keyed checks are in clichefactory-test-suite (test_mcp.py).
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from cliche_mcp import __version__
from cliche_mcp.server import doctor, extract, mcp, to_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_tools_are_registered():
    tools = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"extract", "to_markdown", "doctor"} <= tools


def test_extract_missing_file_is_a_readable_error():
    out = asyncio.run(extract(file="/no/such/file.pdf", schema={"type": "object"}))
    assert out.startswith("Error: File not found")


def test_to_markdown_missing_file_is_a_readable_error():
    out = asyncio.run(to_markdown(file="/no/such/file.pdf"))
    assert out.startswith("Error")


def test_doctor_reports_without_raising():
    report = doctor()
    assert isinstance(report, str) and report.strip()


def test_server_json_names_this_package():
    server = json.loads((ROOT / "server.json").read_text())
    (pypi,) = [p for p in server["packages"] if p["registryType"] == "pypi"]
    assert pypi["identifier"] == "clichefactory-mcp"
    # The registry checks the PyPI README for this marker to prove ownership.
    readme = (ROOT / "README.md").read_text()
    m = re.search(r"mcp-name:\s*(\S+)", readme)
    assert m and m.group(1) == server["name"]


def test_version_is_importable():
    assert re.fullmatch(r"\d+\.\d+\.\d+((a|b|rc)\d+)?", __version__)
