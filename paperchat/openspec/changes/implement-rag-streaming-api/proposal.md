# Proposal

## Why

PaperChat can ingest and retrieve paper passages but cannot generate contextual answers. Add a streaming backend conversation endpoint over the Phase 02 index so clients can receive grounded answers and inspect their sources.

## What Changes

- Add asynchronous `POST /api/v1/chat/stream` with validated questions and ordered JSON SSE events: `sources`, `token`, `done`, and safe `error`.
- Reuse Phase 02 top-five retrieval, embedding identity, named cosine vectors, and provenance without changing ingestion behavior.
- Add a small reusable chat service using LangChain prompts and the official OpenRouter asynchronous model integration, with typed environment configuration and no hardcoded chat model.
- Ground answers exclusively in retrieved passages, treat passages as untrusted data, acknowledge insufficient context, and prohibit fabricated citations.
- Bound retrieval/generation, handle provider errors and disconnects, close resources, and record safe operational diagnostics.
- Add offline mocked tests and document configuration, startup, ingestion prerequisites, and curl verification.

## Capabilities

### New Capabilities

- `rag-chat-streaming`: Validated, contextual question answering with source provenance, ordered SSE output, and bounded failure/cancellation behavior.

### Modified Capabilities

None. Phase 02 ingestion and CLI search requirements remain unchanged; their completed change artifacts have not yet been archived into main specs.

## Impact

- Backend: `apps/api/app/main.py`, typed chat settings, and a small chat module using `app.ingestion.store` and its existing helpers.
- Dependencies: add a compatible `langchain-openrouter` release to `apps/api/pyproject.toml` and `uv.lock`; retain the existing embeddings integration.
- Tests and documentation: backend tests, `apps/api/.env.example`, `README.md`, and `docs/architecture.md`.
- Existing Qdrant data stays read-only during chat. No frontend, history, agents, LangGraph, evaluation, authentication, additional infrastructure, or alternate embeddings provider is included.
