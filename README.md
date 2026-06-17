# clichefactory-mcp

<!-- mcp-name: io.github.ClicheFactory/clichefactory-mcp -->

MCP (Model Context Protocol) server for [ClicheFactory](https://clichefactory.com) — structured data extraction from documents.

This server exposes ClicheFactory's extraction and document conversion capabilities as MCP tools, allowing AI assistants in Cursor, Claude Desktop, OpenClaw, and other MCP-compatible clients to extract structured data from PDFs, images, DOCX, XLSX, CSV, EML, and more.

## Quick start (recommended — service mode)

Service mode uses the ClicheFactory cloud for the best extraction quality. You only need one API key.

1. **Sign up** at [clichefactory.com](https://clichefactory.com) — free pages included, no credit card required.
2. **Create an API key** in [Settings → API Keys](https://clichefactory.com) (format: `cliche-...`).
3. **Install** the MCP server:

   ```bash
   pip install clichefactory-mcp
   ```

4. **Configure** — either paste the key into your MCP client (see below) **or** run once in a terminal:

   ```bash
   pip install clichefactory   # if you don't have the CLI yet
   clichefactory configure
   ```

   The interactive wizard saves credentials to `~/.clichefactory/config.toml`, which the MCP server reads automatically.

That's it — one env var (`CLICHEFACTORY_API_KEY`) or a config file, and you're on hosted extraction.

## Tools

| Tool | Description |
|------|-------------|
| `extract` | Extract structured JSON from a document using a schema |
| `to_markdown` | Convert a document to markdown text |
| `doctor` | Check configuration, dependencies, and system binaries |

### `extract`

The main tool. Pass a document file and a JSON schema — get structured data back.

Supports all extraction modes:

| Mode | Description | Requires |
|------|-------------|----------|
| *(default)* | OCR + LLM extraction | Service API key (recommended) |
| `fast` | Fastest pipeline | Service API key |
| `trained` | Trained pipeline artifact | Service + `artifact_id` |
| `robust` | Two-stage extract + verify | Service only |
| `robust-trained` | Trained extract + verification | Service + `artifact_id` |

The schema can be provided as:
- **File path**: absolute path to a `.json` schema file
- **Inline dict**: the LLM constructs a JSON schema from the conversation (e.g., the user says *"extract the invoice number and total"* and the LLM builds `{"type": "object", "properties": {"invoice_number": {"type": "string"}, "total": {"type": "number"}}}`)

### `to_markdown`

Converts any supported document to markdown. Useful for inspecting document contents or feeding them to the LLM for analysis before deciding on an extraction schema.

### `doctor`

Runs diagnostics on the ClicheFactory setup — config file, API keys, Python dependencies, system binaries. Call this when things aren't working.

## Execution Modes

The server defaults to **service mode** (ClicheFactory cloud). Local mode is available for BYOK / air-gapped use.

- **`service`** *(recommended)* — Uses the ClicheFactory cloud service. Requires a ClicheFactory API key. Supports all extraction modes including trained pipelines and robust verification. Best extraction quality out of the box.

- **`local`** *(advanced)* — Runs extraction on your machine. You bring your own LLM key (BYOK). Requires `pip install "clichefactory-mcp[local]"` (~2 GB of parsing/OCR dependencies) plus system binaries (tesseract, LibreOffice). Quality depends on your local setup.

## Installation

### Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### From PyPI

```bash
pip install clichefactory-mcp
```

For local-mode extraction (BYOK, runs on your machine), install with the local extras:

```bash
pip install "clichefactory-mcp[local]"
```

## Configuration

### Environment Variables

Set these in your MCP client configuration (see below) or in `~/.clichefactory/config.toml` via `clichefactory configure`.

| Variable | Required | Description |
|----------|----------|-------------|
| `CLICHEFACTORY_API_KEY` | **Yes** (service mode) | ClicheFactory API key from Settings → API Keys (`cliche-...`) |
| `CLICHEFACTORY_API_URL` | No | Override the default service URL (`https://api.clichefactory.com`); useful for local development against a self-hosted ClicheFactory backend |
| `LLM_MODEL_NAME` | Local mode only | Model name, e.g. `gemini/gemini-3-flash-preview` |
| `LLM_API_KEY` | Local mode only | API key for the LLM provider |
| `OCR_MODEL_NAME` | No | Separate OCR/VLM model (defaults to main model) |
| `OCR_API_KEY` | No | API key for OCR model (defaults to main key) |

Environment variables take precedence over the config file at `~/.clichefactory/config.toml`.

### Cursor

Add to `.cursor/mcp.json` in your project (or global Cursor settings):

```json
{
  "mcpServers": {
    "clichefactory": {
      "command": "uvx",
      "args": ["clichefactory-mcp"],
      "env": {
        "CLICHEFACTORY_API_KEY": "cliche-your-key-here"
      }
    }
  }
}
```

For local development from a git checkout, replace `uvx` with:

```json
"command": "uv",
"args": ["--directory", "/absolute/path/to/cliche-mcp", "run", "clichefactory-mcp"]
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "clichefactory": {
      "command": "uvx",
      "args": ["clichefactory-mcp"],
      "env": {
        "CLICHEFACTORY_API_KEY": "cliche-your-key-here"
      }
    }
  }
}
```

### OpenClaw

Register the MCP server with your [OpenClaw](https://github.com/openclaw/openclaw) agent:

```bash
openclaw mcp set clichefactory '{"command":"uvx","args":["clichefactory-mcp"],"env":{"CLICHEFACTORY_API_KEY":"cliche-your-key-here"}}'
```

Verify with `openclaw mcp list`. The agent can now use `extract`, `to_markdown`, and `doctor` tools in any conversation.

An OpenClaw skill with agent instructions is also available in [`integrations/openclaw/`](integrations/openclaw/SKILL.md). To install it into your workspace:

```bash
cp -r /path/to/cliche-mcp/integrations/openclaw ~/.openclaw/skills/clichefactory
```

Or, once published to ClawHub:

```bash
openclaw skills install clichefactory
```

### Local mode (advanced)

If you prefer BYOK extraction on your machine, install the local extras and set LLM credentials:

```json
{
  "mcpServers": {
    "clichefactory": {
      "command": "uvx",
      "args": ["clichefactory-mcp"],
      "env": {
        "LLM_MODEL_NAME": "gemini/gemini-3-flash-preview",
        "LLM_API_KEY": "your-gemini-api-key"
      }
    }
  }
}
```

Pass `mode="local"` explicitly in tool calls, or run `clichefactory configure --local` to set local as the default in `~/.clichefactory/config.toml`.

## Supported File Types

PDF, PNG, JPG, JPEG, WebP, GIF, BMP, DOCX, DOC, ODT, XLSX, CSV, EML, TXT, MD.

## Differences from the CLI

This MCP server covers the core extraction and conversion workflows. The following CLI features are **not included** in v1:

| Feature | Reason |
|---------|--------|
| Batch operations (`extract-batch`, `to-markdown-batch`) | MCP tools are typically called one-at-a-time by the LLM. For multiple documents, the LLM calls `extract` in sequence. Batch support may be added in a future version. |
| `configure` | Interactive prompts don't work in MCP. Use env vars or run `clichefactory configure` in a terminal. |
| `--output` / `-o` flag | MCP tools return results directly to the LLM rather than writing to files. |
| `allow_partial` | Not exposed as a tool parameter in v1. |
| OCR engine selection | Uses the SDK defaults (RapidOCR). Configure via `~/.clichefactory/config.toml` or pass parsing options through the SDK if needed. |

## Development

```bash
# Install in development mode
uv sync

# Run the server directly (stdio transport, for testing with MCP clients)
uv run clichefactory-mcp

# Inspect available tools (requires mcp CLI)
uv run mcp dev cliche_mcp/server.py
```

## License

[MIT](LICENSE) — Copyright (c) 2026 Urban Susnik s.p.
