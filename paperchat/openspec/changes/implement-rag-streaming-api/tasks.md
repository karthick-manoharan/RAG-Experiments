# Tasks

## 1. Compatible integration and configuration

- [x] 1.1 Add a compatible official `langchain-openrouter` release to `apps/api/pyproject.toml` and update `uv.lock` with minimal justified changes; verify `uv sync --frozen`, local `ChatOpenRouter` import, async streaming/timeout interfaces, and absence of paid API calls during these checks.
- [x] 1.2 Add lazy typed chat settings composed with existing `IngestionSettings`, requiring `OPENROUTER_MODEL` and validating temperature, token limit, and finite deadlines as defined in design.md; test env precedence, app-local dotenv boundaries, secret redaction, blank model, invalid ranges, and health startup with only Phase 02 configuration.
- [x] 1.3 Extend `apps/api/.env.example` and README environment documentation with model/temperature/token/deadline settings and existing shared OpenRouter key semantics; verify every documented variable maps to a settings field and no concrete model or secret is hardcoded as an application default.

## 2. Retrieval preparation and sources

- [x] 2.1 Implement chat service preparation using existing `app.ingestion.store.search` off the event loop, with bounded retrieval concurrency held until worker completion and caller deadline/disconnect handling; tests must prove retrieval precedes model invocation, top-five ordering/schema reuse, event-loop responsiveness, no collection writes, and no generation after cancelled retrieval.
- [x] 2.2 Add allowlisted safe error categories for configuration, index availability/compatibility, embeddings, and Qdrant; if shared `PipelineError` needs typed subclasses, preserve existing CLI diagnostics. Verify mocked failures produce the planned pre-stream 503/502/504 and existing ingestion/store tests pass without leaking sentinel secrets.
- [x] 2.3 Build sources from actual retrieved metadata, preferring stored point IDs and reusing Phase 02 deterministic IDs when complete, with clearly documented request-local references only when necessary; verify source order, 500-character excerpts, preserved one-based pages, and null missing provenance with unit tests.
- [x] 2.4 Document the configured paper collection prerequisite, retrieval reuse, source field meanings, missing-page behavior, and residual synchronous cancellation limitation in README/architecture docs; verify descriptions match service tests and preserve existing ingestion instructions.

## 3. Contextual model generation

- [x] 3.1 Assemble the context-only untrusted-passage system prompt with `ChatPromptTemplate` and compose it with explicitly configured `ChatOpenRouter` using native async streaming and no generation retries; mocked tests must assert configuration forwarding, proper message roles, literal passage/question handling, and omission of credentials and fabricated page references.
- [x] 3.2 Implement generation text extraction in provider order, excluding reasoning/tool/metadata chunks, with deterministic empty-retrieval fallback and explicit unsupported-question prompt instructions; verify mocked deltas are preserved, empty results never invoke the model, and a mocked unsupported answer reaches the client unchanged.
- [x] 3.3 Apply a total generation deadline, close request-owned iterator/HTTP resources on every exit, and record correlation/stage/timing/count/outcome diagnostics; verify completion, first-read failure, mid-answer failure, timeout, and cancellation cleanup with mocks and assert logs contain no sentinel keys, questions, context, or raw exception bodies.
- [x] 3.4 Update architecture and README with LangChain/OpenRouter generation, fallback limitations, and manual supported/unsupported question examples; verify docs distinguish deterministic no-context behavior from model adherence when nonempty passages are irrelevant.

## 4. HTTP and SSE lifecycle

- [x] 4.1 Add strict request validation for missing/non-string/blank/malformed and over-4000-character questions, checking length before trimming, and register `POST /api/v1/chat/stream` through a small router in `app/main.py`; route tests must verify 422 before external work and sanitize validation responses so full questions are not echoed.
- [x] 4.2 Implement JSON SSE framing, sources-first ordering, incremental token events, exactly one done/error terminal event, safe late error codes, and anti-buffering headers; verify Unicode/newlines/quotes, HTTP media type, fallback ordering, safe construction failures before headers, and no done after provider failure.
- [x] 4.3 Supervise disconnects during preparation and idle generation using one ASGI receive owner, cancel and await pending generation, and clean up without terminal events to disconnected clients; a direct ASGI gated-model test must prove tokens are sent before full completion and a disconnect cancels a pending next-token read without further generation.
- [x] 4.4 Document startup and `curl -N` POST commands for successful supported questions, unsupported questions, invalid questions, and pre-stream versus late failures; verify request bodies and expected SSE JSON match the route contract and include existing ingestion/search prerequisites.

## 5. Integration verification

- [x] 5.1 Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` from `apps/api`; verify all new mocked tests and existing settings, health, extraction, ingestion, and search regression tests pass without network or paid provider calls.
- [x] 5.2 Smoke-test FastAPI startup and `/health` with only Phase 02 configuration, then verify the endpoint through mocked ASGI streaming with full chat configuration; record results and distinguish offline evidence from any optional operator-run live curl verification.
