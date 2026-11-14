"""
ClicheFactory MCP server.

Exposes document extraction and conversion tools via the Model Context Protocol.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from cliche_mcp.helpers import build_client, format_error, resolve_schema, run_doctor

mcp = FastMCP(
    "clichefactory-mcp",
    instructions=(
        "ClicheFactory MCP server for structured data extraction from documents.\n\n"
        "Tools:\n"
        "- extract: Pull structured JSON from a document using a schema.\n"
        "- to_markdown: Convert a document to readable markdown.\n"
        "- doctor: Check configuration and dependencies.\n"
        "- balance: Show the credit balance and how many pages it still buys.\n\n"
        "Default execution mode is service (ClicheFactory cloud) — best quality, "
        "requires CLICHEFACTORY_API_KEY from clichefactory.com → Settings → API Keys.\n"
        "Local mode (BYOK) is available via mode=\"local\" for advanced users.\n\n"
        "If extraction fails, call doctor to check credentials. "
        "If extract returns a validation error, try to_markdown first to inspect the "
        "document, then build a better schema from what you see.\n\n"
        "Run doctor when something fails to check what is configured. "
        "Before a large batch, call balance to check there are enough pages left; "
        "pass include_cost=true to extract to see what each call cost."
    ),
)


@mcp.tool()
async def extract(
    file: str,
    schema: str | dict[str, Any],
    mode: str | None = None,
    extraction_mode: str | None = None,
    artifact_id: str | None = None,
    model: str | None = None,
    model_api_key: str | None = None,
    ocr_model: str | None = None,
    ocr_api_key: str | None = None,
    include_cost: bool = False,
) -> str:
    """Extract structured data from a document using a JSON schema.

    Takes a document file (PDF, image, DOCX, XLSX, CSV, EML, etc.) and a JSON
    schema describing the fields to extract. Returns the extracted data as JSON.

    If extraction fails or returns a validation error, try:
    1. Calling doctor to verify the ClicheFactory API key is configured.
    2. Using to_markdown first to inspect the document, then adjusting the schema.
    3. Using extraction_mode="fast" for simpler documents.

    Args:
        file: Absolute path to the document file.
        schema: Either an absolute file path to a JSON schema, or an inline
            JSON schema object. Example inline schema:
            {"type": "object", "properties": {"invoice_number": {"type": "string"}, "total": {"type": "number"}}}
        mode: Execution mode — "service" (ClicheFactory cloud, default) or
            "local" (BYOK, runs on user's machine). Auto-detected from credentials
            when omitted.
        extraction_mode: Extraction strategy. Options:
            - omit for standard OCR + LLM extraction (most reliable).
            - "fast" — send raw bytes to a multimodal LLM, skipping OCR (faster).
            - "trained" — use a trained pipeline artifact (service only, needs artifact_id).
            - "robust" — two-stage extract + verify (service only).
            - "robust-trained" — trained extract + verify (service only, needs artifact_id).
        artifact_id: Trained pipeline artifact ID from ClicheFactory / Emio.
            Required when extraction_mode is "trained" or "robust-trained".
        model: LLM model override (e.g. "gemini/gemini-3-flash-preview", "openai/gpt-4o").
        model_api_key: API key for the model override.
        ocr_model: Separate model for OCR/VLM tasks (optional, defaults to main model).
        ocr_api_key: API key for the OCR model.
        include_cost: Service mode only. When true, the result is wrapped as
            {"result": <extracted data>, "cost": {"pages", "credits_used",
            "credits_per_page"}}. credits_used is 0 when free pages covered it.

    Returns:
        JSON string with the extracted data matching the provided schema
        (wrapped with its cost when include_cost is true).
    """
    try:
        p = Path(file)
        if not p.is_file():
            return f"Error: File not found: {file}"

        schema_dict = resolve_schema(schema)

        client = build_client(
            mode=mode,
            model=model,
            model_api_key=model_api_key,
            ocr_model=ocr_model,
            ocr_api_key=ocr_api_key,
        )

        cliche = client.cliche(schema_dict, artifact_id=artifact_id)
        cost = None
        if include_cost:
            if client.mode != "service":
                return (
                    "Error: include_cost needs service mode. Local (BYOK) extractions "
                    "run on your own model key, so ClicheFactory bills nothing for them."
                )
            result, cost = await cliche.extract_async(
                file=file, mode=extraction_mode, return_cost=True
            )
        else:
            result = await cliche.extract_async(file=file, mode=extraction_mode)

        if hasattr(result, "model_dump"):
            data = result.model_dump(mode="json")
        elif hasattr(result, "raw"):
            data = {"raw": result.raw, "validation_errors": result.validation_errors}
        else:
            data = result

        if cost is not None:
            data = {"result": data, "cost": cost.model_dump(mode="json")}

        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    except Exception as e:
        return format_error(e)


@mcp.tool()
async def to_markdown(
    file: str,
    mode: str | None = None,
    conversion_mode: str | None = None,
    model: str | None = None,
    model_api_key: str | None = None,
    ocr_model: str | None = None,
    ocr_api_key: str | None = None,
) -> str:
    """Convert a document to markdown text.

    Takes any supported document (PDF, image, DOCX, XLSX, CSV, EML, etc.) and
    returns its content as readable markdown. Use this to inspect a document
    before extraction, or when extract fails and you need to see the content
    to build a better schema.

    Args:
        file: Absolute path to the document file.
        mode: Client mode — "service" (default) or "local". Auto-detected from
            credentials when omitted.
        conversion_mode: Conversion mode (service mode only). Options:
            - omit for standard OCR + LLM conversion (most reliable).
            - "fast" — send raw bytes to a multimodal LLM, skipping OCR (faster).
        model: LLM model override (e.g. "gemini/gemini-3-flash-preview").
        model_api_key: API key for the model override.
        ocr_model: Separate model for OCR/VLM tasks.
        ocr_api_key: API key for the OCR model.

    Returns:
        The document content as markdown text.
    """
    try:
        p = Path(file)
        if not p.is_file():
            return f"Error: File not found: {file}"

        client = build_client(
            mode=mode,
            model=model,
            model_api_key=model_api_key,
            ocr_model=ocr_model,
            ocr_api_key=ocr_api_key,
        )

        doc = await client.to_markdown_async(
            file=file,
            conversion_mode=conversion_mode,
        )

        return doc.get_markdown() if hasattr(doc, "get_markdown") else str(doc)

    except Exception as e:
        return format_error(e)


@mcp.tool()
def doctor() -> str:
    """Check ClicheFactory configuration, dependencies, and system binaries.

    Returns a diagnostic report showing:
    - Config file status and API key / model settings
    - Installed Python dependencies (core + local mode)
    - System binaries (tesseract, pandoc, LibreOffice)

    Call this tool first when extraction fails, or to verify the setup is correct.
    """
    return run_doctor()


_BALANCE_FIELDS = {
    "balance_credits",
    "currency",
    "free_extraction_pages_remaining",
    "pages_remaining",
}


@mcp.tool()
async def balance() -> str:
    """Show the ClicheFactory credit balance and how many pages it still buys.

    Call it before a large batch to check there is enough left. Service mode
    only: it reads the account of the configured CLICHEFACTORY_API_KEY.

    Returns:
        JSON with balance_credits, currency, free_extraction_pages_remaining
        (used before credits), and pages_remaining: for each extraction mode
        ("fast", "balanced", "robust", under "extract" and "extract_byok") and
        for "to_markdown", the credits_per_page and the pages the balance
        still buys (null when the rate is 0).
    """
    try:
        client = build_client(mode="service")
        bal = await client.balance_async()
        data = bal.model_dump(mode="json", include=_BALANCE_FIELDS)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return format_error(e)
