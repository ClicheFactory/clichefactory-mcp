# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0: minor for additive features, patch for bugfix / dependency
bump / docs).

## [0.1.9] — 2026-06-16

### Changed

- **Service mode is now the documented default.** README, skills, Smithery
  config, and MCP server instructions all lead with
  `CLICHEFACTORY_API_KEY` instead of local BYOK credentials.
- Added a Quick Start section covering signup, API key creation, and
  `clichefactory configure` as the one-time setup path.
- `build_client()` auto-detects mode from credentials when the `mode`
  tool parameter is omitted (API key → service, LLM key → local).
- Improved missing-API-key error hint with a direct onboarding path
  (clichefactory.com → Settings → API Keys).
- `doctor` is quieter for service-mode users — local parsing deps and
  system binaries are reported as informational instead of warnings.

## [0.1.8] — 2026-05-18

### Added

- Added Open Plugins metadata for cursor.directory discovery, including
  `.plugin/plugin.json`, root `.mcp.json`, and a discoverable
  `skills/clichefactory/SKILL.md`.

### Changed

- Updated Open Plugins description to:
  "Extract structured JSON from PDFs, images, DOCX, XLSX, CSV, EML with
  attachments, train your DSPy pipelines and more using ClicheFactory."
- Updated MCP Registry description with a shorter variant to fit the
  registry's 100-character limit.

## [0.1.7] — 2026-05-18

### Added

- Added MCP Registry verification metadata for
  `io.github.ClicheFactory/clichefactory-mcp`.
- Added `server.json` for publishing `clichefactory-mcp` to the
  official MCP Registry, including discovery metadata for document
  extraction, emails with attachments, and custom DSPy-trained
  pipelines.

## [0.1.6] — 2026-05-14

### Changed

- Bumped `clichefactory` floor to `>=0.6.1` to pick up the SDK's
  parser-registry fixes. `XlsxParser` and `DocxParser` can now be
  instantiated through `MediaParserRegistry` (prior versions raised
  `TypeError: __init__() got an unexpected keyword argument
  'media_parser_registry'` the moment an `.xlsx` or `.docx` went
  through the canonical `MediaRouter` path, so local-mode `extract`
  and `to_markdown` on those formats silently fell out of the
  parser pipeline). Also picks up `.odt` going through LibreOffice
  (`soffice`) instead of pandoc — local-mode users now only need
  `libreoffice-core` on PATH for `.doc` / `.odt` conversion.
  No public MCP tool surface changed.

## [0.1.5] — 2026-05-11

### Changed

- Bumped `clichefactory` floor to `>=0.6.0` to pick up the SDK's
  in-flight 409 polling and the new
  `clichefactory.AlreadyInFlightError` typed error. Service-mode
  `extract` and `to_markdown` calls no longer crash with an opaque
  `ParsingError` / `ExtractionError` when an identical request is
  still being processed by the ClicheFactory service — the SDK now
  polls with a more generous attempt budget (default 6 attempts ×
  60 s cap) until the original attempt finishes and replays. Plain
  client-side 409s (e.g. fingerprint mismatches on a reused
  idempotency key) still fail fast. No public MCP tool surface
  changed.

## [0.1.4] — 2026-05-10

### Changed

- Bumped `clichefactory` floor to `>=0.5.1` to pick up the SDK's
  Docling-adapter page-marker fix. The SDK now emits canonical
  `<!-- cf:page N -->` markers from `to_markdown()`, so
  `PageChunker(pages_per_chunk=N)` actually splits multi-page
  documents on page boundaries instead of falling back to
  `TokenChunker` and producing a single chunk for any multi-page
  document under the token cap. The MCP server's local-mode
  `extract` and `to_markdown` tools route through this code path,
  so fresh installs of the MCP server now pick up the fix
  transparently. No public MCP tool surface changed.

## [0.1.3] — 2026-05-10

### Changed

- Bumped `clichefactory` floor to `>=0.5.0` to track the SDK's latest
  minor. No public MCP tool surface changed — this is purely a
  dependency-floor bump. See the SDK's CHANGELOG for SDK-side details.

## [0.1.2] — 2026-05-10

### Changed

- Bumped `clichefactory` floor to `>=0.4.2` to pick up the SDK's new
  default service base URL. Service-mode MCP installs now talk to
  `https://api.clichefactory.com` out of the box — `CLICHEFACTORY_API_KEY`
  is the only env var most users need. `CLICHEFACTORY_API_URL` remains
  available as the override for local development and
  self-hosted instances.

### Documentation

- Dropped the redundant `"CLICHEFACTORY_API_URL": "https://api.clichefactory.com"`
  from the Cursor and OpenClaw service-mode example snippets — it was
  always equivalent to the SDK default since the floor is now `>=0.4.2`.
- Tightened the env-vars table description for `CLICHEFACTORY_API_URL`
  to make it explicit that it overrides the default rather than enables
  it.

## [0.1.1] — 2026-05-09

### Changed

- Bumped `clichefactory` floor to `>=0.4.0` to pick up the SDK's
  fast-mode MIME degradation. `mode="fast"` extract calls on EML,
  DOCX, XLSX, CSV, ODT and DOC inputs now succeed transparently
  instead of raising the vendor's `400 INVALID_ARGUMENT: Unsupported
  MIME type` (the SDK pre-flights `AIClient.supports_bytes(mime)`
  and parses unsupported types to markdown locally before a single
  `extract(text, schema)` call). PDFs and common image MIMEs keep
  the multimodal raw-bytes path unchanged. No public MCP tool
  surface changed.

## [0.1.0] — 2026-05-05

### Added

- Initial public release. MCP server exposing `extract`,
  `to_markdown` and `doctor` tools backed by the `clichefactory`
  SDK in either local (BYOK) or service (ClicheFactory cloud) mode.
