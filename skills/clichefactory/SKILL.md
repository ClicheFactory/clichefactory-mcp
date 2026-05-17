---
name: clichefactory
description: Extract structured JSON from PDFs, images, DOCX, XLSX, CSV, EML with attachments, train DSPy pipelines, and convert documents to markdown using ClicheFactory.
---

# ClicheFactory Document Intelligence

Use ClicheFactory when the user needs structured data extracted from documents, emails with attachments, scanned files, spreadsheets, or images.

The plugin provides the `clichefactory` MCP server with these tools:

- `extract`: Extract structured JSON from a document using a JSON schema.
- `to_markdown`: Convert a document to readable markdown before building a schema or debugging extraction.
- `doctor`: Check configuration, dependencies, credentials, and system binaries.

## Configuration

ClicheFactory supports two execution modes:

- `service`: Uses ClicheFactory cloud and requires `CLICHEFACTORY_API_KEY`.
- `local`: Runs extraction locally and requires an LLM model/API key, such as `LLM_MODEL_NAME` and `LLM_API_KEY`.

The server also reads `~/.clichefactory/config.toml` created by `clichefactory configure`. Environment variables take precedence.

## Workflow

1. If the user gives a document and no schema, call `to_markdown` first to inspect the contents.
2. Build a JSON schema from the user's requested fields and the document contents.
3. Call `extract` with the file path, schema, and appropriate mode.
4. If extraction returns validation errors, adjust the schema or field descriptions and retry.
5. If extraction fails entirely, try the other mode when credentials are available, then call `doctor`.

## Schema Tips

Schemas follow standard JSON Schema. Add clear `description` fields for ambiguous values, normalized dates, totals, currencies, and line items.

Example invoice schema:

```json
{
  "type": "object",
  "properties": {
    "invoice_number": {
      "type": "string"
    },
    "date": {
      "type": "string",
      "description": "Invoice date in YYYY-MM-DD format"
    },
    "vendor": {
      "type": "string"
    },
    "line_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": {
            "type": "string"
          },
          "quantity": {
            "type": "number"
          },
          "unit_price": {
            "type": "number"
          },
          "total": {
            "type": "number"
          }
        }
      }
    },
    "total_amount": {
      "type": "number"
    }
  }
}
```

Supported file types include PDF, PNG, JPG, JPEG, WebP, GIF, BMP, DOCX, DOC, ODT, XLSX, CSV, EML, TXT, and MD.
