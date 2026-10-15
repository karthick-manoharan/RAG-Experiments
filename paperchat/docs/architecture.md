# PaperChat architecture

## Implemented foundation

`apps/web` is a Next.js App Router application with TypeScript, Tailwind CSS,
and shadcn/ui components for a responsive streaming chat page. It calls FastAPI directly.
`apps/api` is a Python 3.12 FastAPI application with typed app-name settings and
`GET /health`, which reports process availability with `{"status":"ok"}`.
Each app has its own manifest and lockfile and can run independently.

## Implemented standalone ingestion and search

“Attention Is All You Need” document → text extraction → chunks with source and
page metadata → embeddings → Qdrant vectors and metadata payloads.

`uv run python -m app.ingestion` runs from `apps/api`, independently of FastAPI.
PyMuPDF extracts each page; RecursiveCharacterTextSplitter splits page-local text
at 1000 characters with 200 target overlap. Metadata carries byte-hash document
ID, source basename, one-based page, and zero-based page-local chunk index.
Deterministic UUID point IDs make repeated upserts safe without duplicate chunks.

OpenRouter's supported embeddings API serves `openai/text-embedding-3-small`
through a separately configured LangChain OpenAI-compatible embeddings client.
The CLI reads `apps/api/.env` and process environment, never root `.env` or chat
settings. `QdrantVectorStore` performs dense indexing and top-five scored search.
Qdrant collection vectors use cosine distance, measured embedding dimensions,
and a stable vector name encoding embedding identity. Incompatible collections
are rejected; only `ingest --recreate` deletes and rebuilds a collection.

Qdrant can run locally through Docker or in Qdrant Cloud with URL/key/collection
environment changes. CLI search returns passages, raw cosine scores, and provenance;
it generates no answer and does not modify stored data. See the root README for
commands and acceptance checks. API startup and `/health` remain independent of
these services. CLI failures can leave partial upserts; deterministic IDs allow
safe retries without implicit deletion.

## Implemented streaming queries

Client POST question → FastAPI validation → read-only Phase 02 retrieval →
LangChain `ChatPromptTemplate | ChatOpenRouter` → async JSON SSE.

The backend uses the official `langchain-openrouter` 0.2.9 integration, with an
explicit model, shared OpenRouter API key, temperature, output limit, timeout in
milliseconds, and no SDK/generation retries. A system message limits answers to
retrieved passages, treats them as untrusted evidence, requires acknowledgement
of insufficient evidence, and prohibits invented source IDs and pages. Template
values carry literal questions and full passages with actual metadata; no
credentials enter messages. Native `astream` forwards answer text deltas and
omits reasoning, tools, and non-text metadata.

Empty retrieval bypasses model construction and returns the deterministic
insufficient-context message documented in README. Nonempty irrelevant passages
rely on model adherence to prompt rules; offline tests prove construction and a
mocked unsupported answer, not real-world grounding. Operator checks should ask
“How does multi-head attention work?” and “What was the weather in Paris
yesterday?” against the indexed paper. No guessed similarity threshold is used.

Chat settings load on requests, preserving credential-free startup and health.
The web app consumes this endpoint directly; the API is also usable through the
documented curl commands.

## Future hosting and automation

Vercel is planned for the web app, with `apps/web` as its app root. Render is
planned for the API, with `apps/api` as its app root. Independent installations
preserve these boundaries. Hosting configuration and deployment commands are
deferred. GitHub Actions is planned for later quality checks and CI; no workflow
is included in this foundation.

## Implemented chat retrieval

`app.chat.service.prepare` composes lazy chat and ingestion settings and calls the
existing `app.ingestion.store.search` in a bounded four-worker executor. Search
owns schema checks, top-five descending cosine ranking, and Qdrant client cleanup;
chat performs no collection writes. The configured collection must already hold
“Attention Is All You Need” with the ingestion embedding identity. Collections
with unrelated papers need operator selection of a paper-specific collection.
There is no guessed filename/title filter or schema migration.

Retrieval deadlines include waiting for worker capacity. A running synchronous
call survives caller cancellation until the existing provider/network limits
expire; its slot is released only when the worker exits. Generation is never
started for a cancelled retrieval. Source records preserve actual metadata,
original one-based pages and zero-based chunk indices, with 500-character
excerpts. IDs prefer Qdrant `_id`, then the existing deterministic chunk UUID;
incomplete metadata gets request-local `S1` references. Missing provenance,
including pages, is null. Full retrieved passages feed the prompt.

## HTTP lifecycle and operational boundaries

`POST /api/v1/chat/stream` validates a strict question string up to 4000 characters
before trimming. Invalid JSON/shape/content returns sanitized 422 without external
work. Preparation finishes configuration, retrieval, sources, and model/prompt
construction before response headers: safe configuration/index errors are 503,
dependency errors 502, and caller deadlines 504. Responses contain only constant
allowlisted code/message fields, preserving CLI diagnostics separately through
minimal `PipelineError` subclasses.

The SSE iterator sends JSON `sources`, ordered incremental `token` frames, and
one terminal `done` or safe `error`; disconnect sends no terminal event. First
provider reads occur after sources and therefore fail through SSE rather than
HTTP status. Generation has one total deadline, not a fresh timeout per delta.
One ASGI receive watcher transfers from preparation to a local streaming response,
cancelling and awaiting the stream on disconnect even during an idle upstream
read. Iterators and both SDK HTTP clients close on all exit paths. Cache and
proxy anti-buffering headers accompany responses; deployment proxy behavior is
outside this change.

Safe diagnostics record correlation, stage, timings, counts, and outcome without
question, context, secret, prompt, or raw exception content. Offline tests mock
providers and exercise actual HTTP/ASGI framing and gated incremental delivery.
Real model grounding and proxy behavior remain optional operator checks using
the README's supported/unsupported questions and `curl -N` walkthrough.

### Offline verification record

Implementation verification on 2026-10-14 passed frozen dependency sync, Ruff
lint, Ruff format check (22 files), and all 107 backend tests, including the
existing ingestion/search regressions. A FastAPI TestClient lifespan smoke check
with explicit Phase 02-only settings and dotenv disabled confirmed startup,
`/health` 200, and safe chat 503 without a model. Full chat settings with mocked
retrieval and generation passed direct ASGI incremental-token and idle-disconnect
tests, plus HTTP framing, failure, timeout, and cleanup checks. No Qdrant network
requests or paid provider calls were made. Live curl/provider grounding checks
remain optional operator verification, separate from this offline evidence.

## Browser streaming chat

A server page renders a client chat view. `src/lib/chat/stream.ts` owns runtime
contract checks, incremental SSE parsing and fetch with a JSON question body. A
streaming TextDecoder preserves split Unicode; incomplete lines/frames remain
buffered across reads. Only done completes an answer. HTTP errors, SSE errors and
unexpected EOF fail the request without losing history or partial text.

`use-chat.ts` owns session exchanges, an AbortController and a synchronous request
lock. Loading precedes first text, generating appends text deltas, and completed,
failed and cancelled are terminal. Request identity prevents stale updates after
cancel/retry. Retry appends the original question as a new attempt. History lives
only in mounted state and clears on reload; earlier messages never reach the API.
Unmount and Stop generating abort fetch and reader consumption. The existing
backend limitation on interrupting synchronous retrieval remains unchanged.

The view uses escaped text, actual nullable source metadata and compact disclosures.
It preserves keyboard focus and only follows new text while near the bottom.
The public API base defaults to localhost:8000; no provider secrets enter the
browser. FastAPI permits only localhost:3000 cross-origin requests, without
credentials. No conversational memory, API proxy or deployment changes are added.
