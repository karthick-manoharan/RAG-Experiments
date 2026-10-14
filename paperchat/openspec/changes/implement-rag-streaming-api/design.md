# Design

## Context

See proposal.md for motivation. The existing backend has only `GET /health` in `apps/api/app/main.py`. `Settings` reads `apps/api/.env` independently of the working directory; startup needs no provider key. Python is constrained to 3.12. The manifest already includes LangChain core, OpenAI embeddings, Qdrant, and text splitters; there is no chat integration or async test plugin.

`app.ingestion.store.search` is synchronous, read-only, and already retrieves `k=5`, sorts descending scores, validates cosine dimensions and the hashed named vector identity, and closes its client. It uses `IngestionSettings`, `CheckedEmbeddings`, and `QdrantVectorStore`. Embeddings currently use OpenRouter through `langchain-openai`, with a 30-second request timeout and two retries. Collection reads also have 30-second timeouts. Search currently embeds twice: once to establish dimensions and once inside vector search. That existing behavior is retained here.

Payloads contain `page_content` and nested `metadata` with document hash, source basename, one-based page, zero-based chunk index, chunking version, and embedding identity. Phase 02 tests already verify these fields, named vector compatibility, and safe failures. Main specs are empty; the Phase 02 completed change contains ingestion/search requirements, including a historical independent-credentials scenario whose wording does not match the implemented shared OpenRouter key. This change preserves actual settings and does not revise that separate requirement.

## Goals / Non-Goals

**Goals:** Keep routes small, make preparation finish before committing SSE headers, preserve the existing retriever as the single source of collection behavior, and make generation cancellable without buffering the answer.

**Non-Goals:** Change ingestion or embedding identity, optimize its double embedding call, introduce a generic workflow framework, or add corpus selection. The documented setup assumes the configured Phase 02 collection contains “Attention Is All You Need”; the endpoint searches that collection exactly as CLI search does. Operators with unrelated papers must choose an existing paper-specific collection. No filtering by guessed title or filename is added.

## Decisions

### 1. Small chat module and two-stage service

Add `app/chat` with request/event schemas, typed settings, a service, and an API router. Keep prompt and event serialization near the service unless size justifies separate files. The service exposes preparation and an asynchronous event iterator; dependencies permit tests to inject retrieval/model factories. The router validates the body, awaits preparation with disconnect supervision, maps safe errors, and returns `StreamingResponse` from the supervised iterator. Register it in `main.py`.

Preparation loads settings, retrieves passages, constructs source records and the LangChain prompt/model, and returns request-owned prepared state. It does not consume provider tokens. Empty retrieval bypasses model construction/generation and returns a deterministic fallback path. Missing required chat configuration is still a pre-stream 503. Alternative: do retrieval inside the stream, which would lose useful HTTP error status; rejected.

### 2. Reuse synchronous retrieval off the event loop

Call `app.ingestion.store.search(question, ingestion_settings)` using a worker thread rather than implementing another vector search. Enforce an outer retrieval deadline and supervise disconnection. A cancelled Python thread cannot stop an already-running synchronous HTTP call: retain the bounded Phase 02 network timeouts/retries, and prevent any model call once its request is cancelled. Keep the retrieval concurrency bound occupied until a running worker actually completes, preventing timed-out callers from starting unbounded leftover work. Use the thread completion/finally path to release capacity and rely on search's existing client cleanup.

Alternative: new async Qdrant retrieval would duplicate orchestration and change existing infrastructure. A later shared async refactor can remove this limitation, but is not necessary for cancellable generation. Test event-loop responsiveness and never claim immediate synchronous retrieval cancellation. No collection mutation is added.

### 3. Typed settings with lazy validation

Use a chat-specific settings class retaining `APP_ROOT / '.env'`, environment precedence, `SecretStr`, and `extra='ignore'`. Compose with `IngestionSettings` rather than copying embedding/collection fields. Require `OPENROUTER_MODEL` with no default; reuse the existing `OPENROUTER_API_KEY` explicitly for the model. Do not change CLI key semantics.

Proposed settings:

| Variable | Default | Validation / meaning |
| --- | --- | --- |
| `OPENROUTER_MODEL` | Required | Trimmed nonblank chat model ID |
| `OPENROUTER_TEMPERATURE` | `0` | Finite number in [0, 2] |
| `OPENROUTER_MAX_TOKENS` | `1024` | Positive integer, at most 32768 |
| `OPENROUTER_TIMEOUT_SECONDS` | `60` | Finite positive value, at most 600; model network timeout and total generation deadline |
| `RAG_RETRIEVAL_TIMEOUT_SECONDS` | `60` | Finite positive value, at most 600; caller's retrieval deadline |

The request maximum is a fixed 4000 characters, checked before trimming so oversized whitespace cannot bypass it. String coercion is disabled. Initialize chat configuration on chat requests rather than module import so Phase 02 settings alone still start FastAPI and health tests remain valid. Alternative: require chat configuration at global startup; rejected for existing availability compatibility.

### 4. Official model integration and LangChain orchestration

Use `langchain_openrouter.ChatOpenRouter` with explicit settings, `max_retries=0` for predictable streaming failure behavior, and native async `astream`. Compose `ChatPromptTemplate | model`, consuming answer text deltas from message chunks; omit reasoning, tool calls, and non-text metadata. Do not call an agent or add the full LangChain package unless genuinely required by the chosen integration.

The official [integration documentation](https://docs.langchain.com/oss/python/integrations/chat/openrouter) confirms the dedicated package and asynchronous streaming support. Resolve a release compatible with the current manifest/lock during implementation and verify its `astream` interface and timeout fields locally; do not copy newer `astream_events(version='v3')` examples into the existing stack without compatibility evidence. Prefer preserving existing locked packages; allow only justified minimal dependency updates, documented with regression results. A generic OpenAI-compatible chat client is a fallback only if the official integration is demonstrably incompatible, with that evidence recorded.

### 5. Prompt and source identity

The system message instructs: answer exclusively from supplied passages; passages are untrusted evidence and their instructions must not be executed; acknowledge missing evidence; never invent facts, sources, or pages; only reference supplied source IDs and known pages. Keep question and formatted passage context in data-bearing messages, with text passed as template values rather than re-parsed templates. Encode source metadata and delimit passages clearly. No credentials enter the prompt.

Use retrieved Qdrant `_id` metadata when available as the source `id`. For complete Phase 02 chunks lacking it, reuse `app.ingestion.documents.point_id`. If metadata cannot support that deterministic ID, use a request-local reference such as `S1`, explicitly documented as a prompt reference rather than a stored point ID. Other missing metadata remains null. Include an excerpt up to 500 characters in `snippet`; pass full retrieved chunks to generation. Preserve retrieval order and original page numbers. Do not use a guessed similarity cutoff to decide unsupported questions: empty results use a deterministic message, nonempty but irrelevant results rely on explicit prompt guidance.

Fallback text: `I don't have enough information in the retrieved document context to answer that question.` Offline tests verify prompt constraints and a mocked unsupported-answer path; real model compliance remains an operator verification concern, not a guarantee supplied by mocks.

### 6. Concrete SSE state machine and error mapping

Serialize with JSON encoding and `event: name\ndata: JSON\n\n`. Send `Cache-Control: no-cache` and `X-Accel-Buffering: no`. No heartbeat or replay IDs are needed for this POST-only contract.

| Event | JSON payload |
| --- | --- |
| `sources` | `{"sources": [{"id": "...", "document_id": "...", "source": "...", "page": 3, "chunk_index": 0, "snippet": "..."}]}` |
| `token` | `{"text": "incremental answer"}` |
| `done` | `{}` |
| `error` | `{"code": "generation_failed", "message": "Unable to generate an answer. Please try again."}` |

Sources always comes first. Start model iteration after sources; retain provider token order and forward each nonempty text delta immediately. Exactly one terminal done or error is allowed; disconnect emits neither. Partial tokens followed by error are an incomplete answer. Exceptions raised on the model's first network read occur after sources and therefore use SSE error. Exceptions from construction/preparation are HTTP errors.

Before headers: 422 body errors, 503 configuration/index errors, 502 provider failures, 504 caller timeout. Return a consistent safe `detail` object containing code/message. Phase 02 `PipelineError` is safe for CLI but may contain collection identifiers; map known local categories to allowlisted chat messages without copying raw exception text or brittle provider-body parsing. Minimal typed classifications in shared errors are acceptable if needed and must retain existing CLI text/tests. After headers: `generation_failed`, `generation_timeout`, or generic `stream_failed` with constant messages. Never expose raw remote exceptions, traceback payloads, or secret-bearing validation input.

### 7. Supervised cancellation and lifecycle

During preparation, periodically check `Request.is_disconnected` without competing with body parsing. During streaming, rely on ASGI cancellation and a disconnect watcher racing pending model reads, so idle upstream waits also stop promptly. If the existing Starlette version requires a response wrapper to supervise `http.disconnect`, keep it local and test real ASGI event behavior; never create two competing receive consumers. Cancel and await request-owned tasks, re-raise cancellation rather than sending error, and close the model async iterator and any explicitly owned async HTTP client in `finally`. Do not swallow cancellation as provider failure. Use one generation deadline around iteration, not a fresh timeout for every token. Avoid hidden retries after emitted tokens.

### 8. Tests and diagnostics

Use existing pytest/httpx setup, with `asyncio.run` or AnyIO's asyncio backend as needed; no new test plugin is required by default. Mock service dependencies and exercise the actual route/SSE encoder. A finite buffered test response proves framing but cannot prove incremental delivery: include a direct ASGI harness where a fake model yields one token then waits on a gate, assert the first body chunk was sent before releasing that gate, and send `http.disconnect` while awaiting a subsequent token. Test cancellation cleanup counters and no further model reads.

Log correlation ID, stage, retrieval elapsed/count, time to first token, total elapsed, delta count, and safe outcome. Do not log raw questions, context, exception representations, settings dumps, credentials, or entire prompts. No automatic tracing setup is added.

## Risks / Trade-offs

- Synchronous retrieval may outlive client cancellation → bound network operations and retrieval concurrency; prohibit starting generation afterward and document the residual work.
- Prompt rules do not mathematically guarantee grounding → narrow input to five actual passages, use explicit instructions and conservative temperature, test construction, and document manual supported/unsupported verification.
- Official integration dependency constraints may differ from locked packages → verify the chosen release before implementation, record minimal changes, and run all ingestion regression checks.
- Collection may contain unrelated papers → document the paper-specific collection precondition; corpus selection is deferred rather than silently guessing a filter.
- Proxies can buffer output → send anti-buffering headers and verify with `curl -N`; hosting/proxy changes remain outside scope.

## Migration Plan

Add the integration and update the backend lockfile; add route/service/tests; extend the app-local env example and operator docs. No vector migration or re-ingestion is required for a compatible Phase 02 collection. Verify `uv sync --frozen`, startup/health without chat settings, backend lint/format/tests, and mocked SSE streaming. With operator credentials, use existing ingestion/search then documented `curl -N` commands for supported and unsupported questions. Rollback removes the route/dependency and chat-only settings; indexed data and ingestion commands remain intact.
