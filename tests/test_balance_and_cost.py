"""The balance tool and extract(include_cost=True), against a fake client (no network)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from clichefactory import Balance, ExtractionCost

import cliche_mcp.server as server

# The shape aio-server returns for GET /v1/billing/balance.
BALANCE_RESPONSE = {
    "tenant_id": "42",
    "balance_credits": 1240,
    "currency": "EUR",
    "low_balance_threshold_credits": 100,
    "free_extraction_pages_remaining": 0,
    "pages_remaining": {
        "extract": {
            "fast": {"credits_per_page": 10, "pages": 124},
            "balanced": {"credits_per_page": 30, "pages": 41},
            "robust": {"credits_per_page": 50, "pages": 24},
        },
        "extract_byok": {"fast": {"credits_per_page": 1, "pages": 1240}},
        "to_markdown": {"credits_per_page": 20, "pages": 62},
        "to_markdown_byok": {"credits_per_page": 0, "pages": None},
    },
    "balance_usd": 12.4,  # deprecated; the tool leaves it out
}


class _FakeCliche:
    def __init__(self, calls: list):
        self.calls = calls

    async def extract_async(self, **kwargs):
        self.calls.append(kwargs)
        data = {"invoice_number": "INV-1"}
        if kwargs.get("return_cost"):
            return data, ExtractionCost(credits_used=30, pages=3, credits_per_page=10)
        return data


class _FakeClient:
    def __init__(self, mode: str = "service"):
        self.mode = mode
        self.calls: list = []

    def cliche(self, schema, artifact_id=None):
        return _FakeCliche(self.calls)

    async def balance_async(self):
        return Balance.model_validate(BALANCE_RESPONSE)


@pytest.fixture
def fake_client(monkeypatch):
    def install(mode: str = "service") -> _FakeClient:
        client = _FakeClient(mode)
        monkeypatch.setattr(server, "build_client", lambda **kw: client)
        return client

    return install


@pytest.fixture
def doc(tmp_path: Path) -> str:
    p = tmp_path / "mail.eml"
    p.write_bytes(b"Subject: invoice\n\nbody")
    return str(p)


SCHEMA = {"type": "object", "properties": {"invoice_number": {"type": "string"}}}


def test_balance_tool_is_registered():
    tools = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert "balance" in tools


def test_balance_returns_the_useful_fields(fake_client):
    fake_client()
    data = json.loads(asyncio.run(server.balance()))
    assert data["balance_credits"] == 1240
    assert data["currency"] == "EUR"
    assert data["free_extraction_pages_remaining"] == 0
    assert data["pages_remaining"]["extract"]["fast"] == {"credits_per_page": 10, "pages": 124}
    assert data["pages_remaining"]["to_markdown_byok"]["pages"] is None
    assert "balance_usd" not in data and "tenant_id" not in data


def test_balance_without_an_api_key_explains_what_to_do(monkeypatch):
    monkeypatch.setattr("cliche_mcp.helpers.resolve_api_key", lambda **kw: None)
    out = asyncio.run(server.balance())
    assert out.startswith("Error: No ClicheFactory API key")
    assert "Hint:" in out


def test_extract_output_is_unchanged_by_default(fake_client, doc):
    client = fake_client()
    data = json.loads(asyncio.run(server.extract(file=doc, schema=SCHEMA)))
    assert data == {"invoice_number": "INV-1"}
    assert "return_cost" not in client.calls[0]


def test_extract_include_cost_wraps_result_and_cost(fake_client, doc):
    client = fake_client()
    out = asyncio.run(server.extract(file=doc, schema=SCHEMA, include_cost=True))
    data = json.loads(out)
    assert data["result"] == {"invoice_number": "INV-1"}
    assert data["cost"] == {"credits_used": 30, "pages": 3, "credits_per_page": 10}
    assert client.calls[0]["return_cost"] is True


def test_extract_include_cost_in_local_mode_is_a_clear_error(fake_client, doc):
    client = fake_client(mode="local")
    out = asyncio.run(server.extract(file=doc, schema=SCHEMA, include_cost=True))
    assert out.startswith("Error: include_cost needs service mode")
    assert client.calls == []
