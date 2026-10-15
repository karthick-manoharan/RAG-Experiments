# Tasks

## 1. Typed streaming transport

- [x] 1.1 Read the relevant installed Next.js guides required by apps/web/AGENTS.md, add Vitest/jsdom/React Testing Library development tooling and an npm test script, update the lockfile, and verify installation and a smoke test succeed.
- [x] 1.2 Define the inspected source/event/error types and implement a pure incremental SSE parser; verify byte-split Unicode, split delimiters and CRLF, comments, multiline data, coalesced frames, unknown events, and malformed recognized payloads with unit tests.
- [x] 1.3 Implement the direct fetch POST client with base URL normalization, JSON question body, streaming TextDecoder/reader, runtime guards, HTTP errors, terminal-event enforcement, AbortSignal, and reader cleanup; verify controlled-stream tests cover incremental delivery before done, errors, missing/non-SSE bodies, premature EOF, and abort before headers and during reading.
- [x] 1.4 Update apps/web/.env.example and frontend setup documentation with NEXT_PUBLIC_API_BASE_URL, localhost default, and browser-secret restrictions; verify documented URL examples match client tests.

## 2. Request lifecycle and session state

- [x] 2.1 Implement exchange state and a dedicated chat hook/controller with loading/generating/completed/cancelled/failed transitions, ordered token accumulation, source association, and session-only history; verify tests observe partial text before completion and multiple requests send only their current question.
- [x] 2.2 Implement synchronous duplicate gating, per-request identity, AbortController cancellation/unmount cleanup, terminal-race protection, and retry as a new attempt of the original failed question; verify tests cover rapid submits, cancellation in loading and generating, late events/finalizers, preserved partial answers, retry body isolation, and new submissions after termination.
- [x] 2.3 Document lifecycle, reload behavior, retry semantics, and the existing residual synchronous retrieval cancellation limit in architecture documentation; verify it matches controller tests and the unchanged backend disconnect behavior.

## 3. Responsive chat presentation

- [x] 3.1 Replace the static page with a small App Router entry and client chat view using existing shadcn/ui plus only needed components; verify title, description, examples, message history, composer, and controls render at narrow and desktop widths.
- [x] 3.2 Add a semantic labelled composer with Enter submit, Shift+Enter newline, IME protection, pre-trim 4000-character/blank validation, active-request disabled submission, cancel and retry actions, and safe focus behavior; verify keyboard and validation component tests pass.
- [x] 3.3 Render incremental text, explicit lifecycle/error states, polite status announcements, and compact actual source references with nullable provenance and inspectable IDs/snippets; verify tests cover actual pages, null metadata, empty sources, escaped text, incomplete answers, and recoverable errors.
- [x] 3.4 Implement near-bottom auto-scroll that pauses when reading earlier messages and resumes at the bottom; verify simulated scroll tests and manually check real scrolling, wrapping, keyboard focus, and mobile composer visibility.
- [x] 3.5 Update README and architecture descriptions from static shell to chat behavior, including keyboard controls and source display; verify documentation describes the delivered UI and no conversational history is sent.

## 4. Local cross-origin integration

- [x] 4.1 Add minimal explicit FastAPI CORS for http://localhost:3000, chat POST and Content-Type with credentials disabled; verify backend tests cover allowed preflight, readable validation/service errors, successful stream headers, and denied unrelated origins without changing the endpoint contract.
- [x] 4.2 Document both local process commands, explicit allowed origin, configured API URL behavior, and the existing ingestion/provider prerequisites; verify instructions distinguish credential-free health startup from configured RAG generation.

## 5. Integrated verification

- [x] 5.1 Run frontend npm test, npm run lint, npm run typecheck, and npm run build; run backend uv run ruff check ., uv run ruff format --check ., and uv run pytest; record outcomes and resolve regressions while preserving ingestion and API functionality.
- [x] 5.2 Verify the complete browser flow with a controlled streaming backend: incremental answer, actual source records, second independent question, cancellation before and after first token, HTTP/SSE failures, and retry; record desktop/mobile and scroll/focus results with no provider credentials exposed.
- [ ] 5.3 Add reproducible local end-to-end verification steps for a configured indexed paper and record a live check when prerequisites are available: confirm retrieval, incremental tokens, sources, independent follow-up, and cancellation; clearly identify unavailable live prerequisites without presenting mocked evidence as a live RAG result.

Verification note: implementation and controlled-stream checks pass. Task 5.3 remains open because the configured live RAG service returned five sources and done but zero token events. See docs/streaming-chat-verification.md; live incremental generation cannot yet be confirmed.
