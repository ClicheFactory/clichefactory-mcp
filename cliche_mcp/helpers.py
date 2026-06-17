"""
Shared helpers for the ClicheFactory MCP server.

Handles config resolution, client construction, schema parsing,
diagnostics, and error formatting.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from clichefactory import Client, Endpoint, factory
from clichefactory._config import (
    CLIConfig,
    config_file_path,
    load_config,
    resolve_api_key,
    resolve_base_url,
    resolve_model,
    resolve_model_api_key,
    resolve_ocr_api_key,
    resolve_ocr_model,
)
from clichefactory.errors import ClicheFactoryError, ConfigurationError, ErrorInfo


# ---------------------------------------------------------------------------
# Schema resolution
# ---------------------------------------------------------------------------

def resolve_schema(schema: str | dict[str, Any]) -> dict[str, Any]:
    """Accept a file path or an inline dict and return a parsed JSON schema."""
    if isinstance(schema, dict):
        return schema
    p = Path(schema)
    if not p.is_file():
        raise FileNotFoundError(f"Schema file not found: {schema}")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------

_SERVICE_KEY_HINT = (
    "Create a free API key at clichefactory.com → Settings → API Keys, "
    "then set CLICHEFACTORY_API_KEY in your MCP client config "
    'or run "clichefactory configure" in a terminal.'
)


def _resolve_mode(*, mode: str | None, cfg: CLIConfig) -> str:
    """Pick execution mode: explicit param > credentials > config default."""
    if mode:
        return mode
    if resolve_api_key(cli_flag=None, cfg=cfg):
        return "service"
    model_name = resolve_model(cli_flag=None, cfg=cfg)
    model_key = resolve_model_api_key(cli_flag=None, cfg=cfg)
    if model_name and model_key:
        return "local"
    return cfg.default_mode


def build_client(
    *,
    mode: str | None = None,
    model: str | None = None,
    model_api_key: str | None = None,
    ocr_model: str | None = None,
    ocr_api_key: str | None = None,
) -> Client:
    """Build a clichefactory Client using the same config cascade as the CLI.

    Resolution order (highest priority first):
        tool parameter → environment variable → ~/.clichefactory/config.toml → default
    """
    cfg = load_config()
    resolved_mode = _resolve_mode(mode=mode, cfg=cfg)

    if resolved_mode == "service":
        api_key = resolve_api_key(cli_flag=None, cfg=cfg)
        if not api_key:
            raise ConfigurationError(
                ErrorInfo(
                    code="mcp.missing_api_key",
                    message="No ClicheFactory API key configured for service mode.",
                    hint=_SERVICE_KEY_HINT,
                )
            )
        base_url = resolve_base_url(cli_flag=None, cfg=cfg)

        model_name = resolve_model(cli_flag=model, cfg=cfg)
        model_key = resolve_model_api_key(cli_flag=model_api_key, cfg=cfg)

        model_ep = None
        if model_name:
            model_ep = Endpoint(provider_model=model_name, api_key=model_key or None)

        return factory(
            api_key=api_key,
            base_url=base_url,
            mode="service",
            model=model_ep,
        )

    # --- local mode ---
    model_name = resolve_model(cli_flag=model, cfg=cfg)
    model_key = resolve_model_api_key(cli_flag=model_api_key, cfg=cfg)

    if not model_name:
        raise ConfigurationError(
            ErrorInfo(
                code="mcp.missing_model",
                message="No LLM model configured for local mode.",
                hint=(
                    'Try mode="service" instead if a ClicheFactory API key is configured. '
                    "Otherwise set LLM_MODEL_NAME and LLM_API_KEY in the MCP server environment, "
                    'or run "clichefactory configure --local" in a terminal.'
                ),
            )
        )

    model_ep = Endpoint(provider_model=model_name, api_key=model_key or None)

    ocr_name = resolve_ocr_model(cli_flag=ocr_model, cfg=cfg)
    ocr_key = resolve_ocr_api_key(
        cli_flag=ocr_api_key, cfg=cfg, model_api_key=model_key,
    )
    ocr_ep = None
    if ocr_name:
        ocr_ep = Endpoint(provider_model=ocr_name, api_key=ocr_key or None)

    return factory(
        mode="local",
        model=model_ep,
        ocr_model=ocr_ep,
    )


# ---------------------------------------------------------------------------
# Diagnostics (mirrors `clichefactory doctor`)
# ---------------------------------------------------------------------------

def _mask(s: str) -> str:
    if not s:
        return "(not set)"
    if len(s) <= 8:
        return "***"
    return s[:4] + "..." + s[-4:]


def run_doctor() -> str:
    """Run the same diagnostics as ``clichefactory doctor`` and return a text report."""
    lines: list[str] = []
    ok_count = warn_count = err_count = 0

    def ok(msg: str) -> None:
        nonlocal ok_count
        ok_count += 1
        lines.append(f"  [OK]   {msg}")

    def warn(msg: str) -> None:
        nonlocal warn_count
        warn_count += 1
        lines.append(f"  [WARN] {msg}")

    def err(msg: str) -> None:
        nonlocal err_count
        err_count += 1
        lines.append(f"  [ERR]  {msg}")

    lines.append("ClicheFactory Doctor")
    lines.append("")

    cfg = load_config()
    effective_mode = _resolve_mode(mode=None, cfg=cfg)
    api_key = resolve_api_key(cli_flag=None, cfg=cfg)

    # --- Config ---
    lines.append("Configuration:")
    ok(f"Default mode: {effective_mode}")
    cfg_path = config_file_path()
    if cfg_path.is_file():
        ok(f"Config file: {cfg_path}")
    else:
        lines.append("  [INFO] No config file — using env vars or defaults")

    if api_key:
        ok(f"Service API key configured ({_mask(api_key)})")
    elif effective_mode == "service":
        warn("No ClicheFactory API key — create one at clichefactory.com → Settings → API Keys")

    if effective_mode == "local":
        if cfg.local.model:
            ok(f"Local model: {cfg.local.model}")
        else:
            warn("Local mode but no LLM model configured")

    lines.append("")

    # --- Python deps ---
    lines.append("Python dependencies:")

    for name, module in [("httpx", "httpx"), ("pydantic", "pydantic"), ("anyio", "anyio")]:
        try:
            __import__(module)
            ok(name)
        except ImportError:
            err(f"{name} (not installed)")

    if effective_mode == "service" and api_key:
        lines.append("  [INFO] Local parsing deps not required in service mode")
    else:
        local_deps = [
            ("pymupdf", "fitz"),
            ("docling", "docling"),
            ("Pillow", "PIL"),
            ("RapidOCR", "rapidocr"),
            ("pytesseract", "pytesseract"),
            ("openpyxl", "openpyxl"),
            ("python-docx", "docx"),
            ("pypdf", "pypdf"),
        ]
        for name, module in local_deps:
            try:
                __import__(module)
                ok(f"{name} (local)")
            except ImportError:
                warn(f"{name} not installed (needed for local mode)")

    lines.append("")

    # --- System binaries ---
    if effective_mode == "service" and api_key:
        lines.append("System binaries:")
        lines.append("  [INFO] Not required in service mode (parsing runs in the cloud)")
    else:
        lines.append("System binaries:")
        for binary, purpose in [
            ("tesseract", "tesseract OCR engine"),
            ("pandoc", ".odt/.doc conversion"),
            ("soffice", "legacy .doc conversion"),
        ]:
            path = shutil.which(binary)
            if path:
                ok(f"{binary}: {path}")
            else:
                warn(f"{binary} not found on PATH (needed for {purpose})")

    lines.append("")

    # --- Summary ---
    total = ok_count + warn_count + err_count
    lines.append(f"Summary: {ok_count}/{total} checks passed, {warn_count} warnings, {err_count} errors")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Error formatting
# ---------------------------------------------------------------------------

def format_error(exc: Exception) -> str:
    """Turn an exception into an LLM-friendly error string."""
    if isinstance(exc, ClicheFactoryError):
        parts = [f"Error: {exc}"]
        hint = getattr(exc.info, "hint", None) if hasattr(exc, "info") else None
        if hint:
            parts.append(f"Hint: {hint}")
        return "\n".join(parts)

    if isinstance(exc, FileNotFoundError):
        return f"Error: {exc}"

    return f"Error ({type(exc).__name__}): {exc}"
