"""draft_model: no network; the HTTP call to /v1/models/draft is replaced."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from cliche_mcp.server import draft_model, mcp

DRAFT = {
    "model": {"root_model": "Vehicle", "definitions": [{"name": "Vehicle", "fields": []}]},
    "json_schema": {
        "type": "object",
        "properties": {
            "vin": {"type": "string"},
            "document_type": {"type": "string", "enum": ["registration", "insurance", "other"]},
            "photo_is_sharp": {"type": "boolean"},
        },
        "required": ["vin"],
    },
    "summary": "Vehicle documents.",
    "notes": [],
    "language": "en",
    "credits_used": 10,
    "cost_summary": {"total_cost_usd": 0.01},
}


@pytest.fixture
def api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))  # no config file
    monkeypatch.setenv("CLICHEFACTORY_API_KEY", "cliche-test")
    monkeypatch.setenv("CLICHEFACTORY_API_URL", "https://api.example.test")


def _fake_post(monkeypatch, status: int, body, calls: list):
    async def post(self, url, json=None, headers=None, **kw):
        calls.append({"url": url, "json": json, "headers": headers})
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


def test_tool_is_registered():
    assert "draft_model" in {t.name for t in asyncio.run(mcp.list_tools())}


def test_draft_returns_the_schema_for_extract(monkeypatch, api_key):
    calls: list = []
    _fake_post(monkeypatch, 200, DRAFT, calls)
    out = json.loads(asyncio.run(draft_model(description="VIN, document type, sharp photo?", language="en")))

    assert out["json_schema"] == DRAFT["json_schema"]
    assert out["model"] == DRAFT["model"]
    assert out["credits_used"] == 10
    assert "cost_summary" not in out  # internal field is not passed on
    (call,) = calls
    assert call["url"] == "https://api.example.test/v1/models/draft"
    assert call["headers"] == {"X-API-KEY": "cliche-test"}
    assert call["json"] == {"description": "VIN, document type, sharp photo?", "language": "en"}


def test_refine_sends_current_model(monkeypatch, api_key):
    calls: list = []
    _fake_post(monkeypatch, 200, DRAFT, calls)
    asyncio.run(draft_model(description="add the owner", current_model=DRAFT["model"]))
    assert calls[0]["json"]["current_model"] == DRAFT["model"]


def test_rejected_draft_lists_the_problems(monkeypatch, api_key):
    body = {"detail": {"detail": "Could not draft a valid model.", "problems": ["field 'x' has type 'y'"]}}
    _fake_post(monkeypatch, 422, body, [])
    out = asyncio.run(draft_model(description="?"))
    assert out.startswith("Error: Could not draft a valid model.")
    assert "field 'x' has type 'y'" in out
    assert "Hint:" in out


def test_low_balance_is_a_readable_error(monkeypatch, api_key):
    _fake_post(monkeypatch, 403, {"detail": {"error": "insufficient_credits"}}, [])
    out = asyncio.run(draft_model(description="invoices"))
    assert "HTTP 403" in out and "balance" in out


def test_missing_key_is_a_readable_error(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLICHEFACTORY_API_KEY", raising=False)
    out = asyncio.run(draft_model(description="invoices"))
    assert out.startswith("Error: draft_model needs a ClicheFactory API key")
