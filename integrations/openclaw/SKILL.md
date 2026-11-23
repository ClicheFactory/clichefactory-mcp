---
name: clichefactory
description: Extract structured data from documents (PDF, images, DOCX, XLSX, CSV, EML) into validated JSON using ClicheFactory
metadata: {"openclaw": {"requires": {"bins": ["uvx"]}, "primaryEnv": "CLICHEFACTORY_API_KEY", "install": [{"id": "uv", "kind": "uv", "package": "clichefactory-mcp", "bins": ["clichefactory-mcp"], "label": "Install ClicheFactory MCP server (uv)"}]}}
---

# ClicheFactory — Structured Document Extraction

ClicheFactory extracts structured, Pydantic-validated data from documents. Give it a file and a JSON schema — it returns clean JSON.

This skill requires the `clichefactory` MCP server. Register it once:

```bash
openclaw mcp set clichefactory '{"command":"uvx","args":["clichefactory-mcp"],"env":{"CLICHEFACTORY_API_KEY":"cliche-your-key"}}'
```

Get your API key at [clichefactory.com → Settings → API Keys](https://clichefactory.com). Free pages included, no credit card.

Verify with `openclaw mcp list`.

## MCP Tools

### extract

Primary tool. Takes a document file path and a JSON schema, returns structured JSON matching the schema.

**Parameters:**
- `file` — absolute path to the document
- `schema` — JSON schema (inline object or path to a `.json` file)
- `mode` — `"service"` (default, ClicheFactory cloud) or `"local"` (BYOK, advanced)
- `extraction_mode` — omit for default OCR+LLM, or `"fast"` for multimodal LLM without OCR
- `model` — LLM override, e.g. `"openai/gpt-4o"`

A `boolean` field comes back as `true` / `false` (never "yes" / "no"). `enum` limits a string to the listed values, and `pattern`, `minLength` / `maxLength` and `minimum` / `maximum` are checked: a value that breaks one is a validation error naming the field. Fields not in `required` may be `null`.

### draft_model

Drafts a schema from a plain-language description of the fields (any language). Returns `json_schema` (pass it to `extract` unchanged), `model` (send it back as `current_model` to refine), and `summary` / `notes` (what the draft assumed or could not express). Service mode, billed per draft.

**Parameters:**
- `description` — what to extract, or with `current_model`, the change to make
- `current_model` — the `model` from an earlier draft (optional)
- `language` — two-letter code for summary and notes (optional)

### to_markdown

Converts a document to readable markdown. Use this to inspect contents before building a schema, or when extract fails and you need to understand the document structure.

**Parameters:**
- `file` — absolute path to the document
- `mode` — `"service"` (default) or `"local"`

### doctor

Checks configuration, Python dependencies, and system binaries. Call this when extraction fails to diagnose the issue.

### balance

Shows the credit balance and, per extraction mode, how many pages it still buys. Call it before a large batch. To see what one extraction cost, pass `include_cost: true` to `extract`: the output becomes `{"result": ..., "cost": {"pages", "credits_used", "credits_per_page"}}`. Service mode only.

## Workflow

1. If the user describes the fields but has no schema, call `draft_model`, tell them what its `notes` say, and use its `json_schema`.
2. Otherwise, call `to_markdown` to see the document, and build a JSON schema from what you see.
3. Call `extract` with the file and schema (service mode is the default).
4. If extraction returns validation errors, inspect them — the schema may need adjustment (wrong types, missing fields, etc.).
5. If extraction fails entirely, call `doctor` to check whether the API key is configured.

## Local mode (advanced)

For BYOK / on-machine extraction, install local extras and set LLM credentials:

```bash
openclaw mcp set clichefactory '{"command":"uvx","args":["clichefactory-mcp"],"env":{"LLM_MODEL_NAME":"gemini/gemini-3-flash-preview","LLM_API_KEY":"YOUR_KEY"}}'
```

Requires `pip install "clichefactory-mcp[local]"`.

## Supported File Types

PDF, PNG, JPG, JPEG, WebP, GIF, BMP, DOCX, DOC, ODT, XLSX, CSV, EML, TXT, MD.

## Schema Tips

Schemas follow standard JSON Schema. Example for an invoice:

```json
{
  "type": "object",
  "properties": {
    "invoice_number": {"type": "string"},
    "date": {"type": "string", "description": "Invoice date in YYYY-MM-DD format"},
    "vendor": {"type": "string"},
    "line_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": {"type": "string"},
          "quantity": {"type": "number"},
          "unit_price": {"type": "number"},
          "total": {"type": "number"}
        }
      }
    },
    "total_amount": {"type": "number"}
  }
}
```

Use `description` fields in the schema to guide extraction — the LLM reads them.

## More Information

- SDK and CLI: [clichefactory on PyPI](https://pypi.org/project/clichefactory/)
- MCP server: [clichefactory-mcp on PyPI](https://pypi.org/project/clichefactory-mcp/)
- Website: [clichefactory.com](https://clichefactory.com)
