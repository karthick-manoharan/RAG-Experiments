# Spec Delta

## Purpose

Enable clients to ask questions about indexed paper passages and receive incremental grounded answers with authentic source provenance and predictable failure behavior.

## ADDED Requirements

### Requirement: Validated streaming question endpoint
The API SHALL accept `POST /api/v1/chat/stream` with JSON `{"question": string}`. It MUST trim surrounding whitespace, reject empty or whitespace-only questions, non-string or missing questions, and questions exceeding 4000 characters with HTTP 422 before external calls. Valid successful requests SHALL return HTTP 200 with `text/event-stream`.

#### Scenario: Valid question
- **WHEN** a client submits a nonblank question of at most 4000 characters with working dependencies
- **THEN** the API returns a streamed answer with the SSE media type

#### Scenario: Invalid input
- **WHEN** a question is missing, null, non-string, blank, longer than 4000 characters, or the request JSON is malformed
- **THEN** the API returns HTTP 422 and performs no vector search or model generation

### Requirement: Compatible read-only top-five retrieval
The endpoint MUST retrieve the five most relevant chunks, or fewer when fewer are available, from the existing configured collection before invoking generation. It SHALL reuse ingestion embedding configuration and schema validation, preserve descending cosine relevance order, and never create, rebuild, or modify the collection.

#### Scenario: Existing Phase 02 index
- **WHEN** the configured collection contains the indexed paper and compatible vectors
- **THEN** up to five relevant passages are retrieved before generation using the same embedding identity as ingestion

#### Scenario: Incompatible index
- **WHEN** the collection is missing or its vector identity, dimensions, or distance is incompatible
- **THEN** retrieval fails before the stream starts without writing or rebuilding data

### Requirement: Authentic source provenance
The first SSE event MUST be `sources` with JSON `{"sources": [...]}`. Each entry SHALL contain `id`, `document_id`, `source`, `page`, `chunk_index`, and `snippet`, retaining actual metadata and retrieval order. IDs MUST identify retrieved chunks; missing metadata SHALL be null, never fabricated. Snippets MUST be excerpts of retrieved text.

#### Scenario: Original metadata available
- **WHEN** passages include point IDs, source filenames, document IDs, original pages, and chunk indices
- **THEN** the sources event exposes those values and an excerpt for each retrieved passage

#### Scenario: Missing page metadata
- **WHEN** a retrieved passage has no page number
- **THEN** its source entry contains `page: null` and no invented page reference

### Requirement: Context-grounded generation
Answers MUST use only retrieved context, treat embedded passage instructions as untrusted data, acknowledge insufficient context, and avoid fabricated citations. Any source references SHALL refer only to supplied source IDs and actual page metadata. An empty retrieval SHALL produce a clear insufficient-context answer without a model call.

#### Scenario: Supported question
- **WHEN** passages contain the facts needed to answer a question
- **THEN** the generated answer is constrained to those passages and available source references

#### Scenario: Unsupported question
- **WHEN** retrieved passages do not support an answer
- **THEN** the response acknowledges insufficient document context instead of inventing an answer

#### Scenario: Empty retrieval
- **WHEN** a compatible collection returns no passages
- **THEN** the stream sends empty sources, a token explaining insufficient context, and done without invoking generation

#### Scenario: Passage injection
- **WHEN** a passage contains instructions to ignore the system prompt or reveal credentials
- **THEN** the generation prompt explicitly treats that text as evidence only and forbids following its instructions

### Requirement: Ordered SSE lifecycle
Each event MUST use `event: <name>\ndata: <JSON>\n\n` framing. `token` events SHALL carry `{"text": string}` in generation order and arrive incrementally. Successful completion SHALL emit exactly one terminal `done` event with `{}`. Failures after streaming starts SHALL emit one terminal `error` with `{"code": string, "message": string}` and no done. No events SHALL follow a terminal event.

#### Scenario: Incremental answer
- **WHEN** the provider yields multiple text deltas
- **THEN** sources precedes ordered token events and done terminates the response without buffering the full answer

#### Scenario: Text with newlines
- **WHEN** a token contains Unicode, quotes, or line breaks
- **THEN** JSON encoding preserves the text without breaking SSE event boundaries

#### Scenario: Streaming failure
- **WHEN** generation fails after sources or tokens have been emitted
- **THEN** one safe structured error terminates the stream without done

### Requirement: Configurable generation and bounded execution
Model ID, temperature, output token limit, and timeout MUST be supplied through validated typed environment settings. No chat model ID SHALL be hardcoded. Retrieval and generation MUST have finite deadlines. Missing chat configuration MUST NOT prevent existing API health or ingestion operations from starting.

#### Scenario: Operator configuration
- **WHEN** the operator configures valid chat parameters
- **THEN** generation uses those parameters while retrieval retains Phase 02 embeddings and collection settings

#### Scenario: Incomplete chat configuration
- **WHEN** chat configuration is absent
- **THEN** health and ingestion remain available and chat requests receive a safe pre-stream configuration error

### Requirement: Safe pre-stream failures
Failures detected before sending response headers MUST return safe JSON HTTP errors: 503 for invalid service configuration or missing/incompatible index, 502 for external dependency failure, and 504 for timeout. Responses and logs MUST omit credentials, remote exception bodies, whole questions, retrieved passages, and complete prompts.

#### Scenario: Retrieval provider failure
- **WHEN** Qdrant or embeddings fails before response headers are sent
- **THEN** the client receives an appropriate non-SSE HTTP error without sensitive upstream content

#### Scenario: Provider initialization failure
- **WHEN** model initialization fails during pre-stream preparation
- **THEN** the API returns a safe HTTP error rather than beginning a successful stream

### Requirement: Disconnect cleanup and safe diagnostics
The API MUST detect client disconnection, cancel pending generation work, stop requesting further tokens, and close streams and request-owned resources on completion, failure, timeout, or cancellation. Diagnostics SHALL record request correlation, stage, elapsed time, result counts, and safe outcome codes without secrets or full content.

#### Scenario: Client disconnects during generation
- **WHEN** a client disconnects while waiting for a token
- **THEN** pending generation is cancelled promptly and resources are cleaned up without attempting terminal events to the disconnected client

#### Scenario: Retrieval is cancelled
- **WHEN** the client disconnects before retrieval completes
- **THEN** generation never starts and any already-running synchronous provider operation is bounded by its configured network timeouts

### Requirement: Offline verification and operator documentation
Tests MUST mock vector search and model streaming without paid provider calls. Documentation SHALL describe app-local environment configuration, ingestion prerequisites, startup, SSE payloads, curl verification, fallback behavior, and failure responses. Existing ingestion and search checks MUST continue passing.

#### Scenario: Offline test suite
- **WHEN** backend tests run without provider credentials or Qdrant
- **THEN** mocks verify validation, ordering, metadata, fallback, failures, timeouts, and cancellation alongside existing ingestion regression tests

#### Scenario: Operator walkthrough
- **WHEN** an operator follows the documentation with the paper ingested and valid configuration
- **THEN** curl displays sources, incremental tokens, and done from the streaming endpoint
