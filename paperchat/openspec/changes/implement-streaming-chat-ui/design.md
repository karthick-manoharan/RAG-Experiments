# Design

## Context

See proposal.md for motivation. `apps/web/src/app/page.tsx` is a static shell. The frontend already has Next.js 16.4, React 19.3, Tailwind 4, shadcn configuration, and a Base UI Button; no frontend test script exists. Read relevant installed Next.js guides under `node_modules/next/dist/docs/` before implementation, as required by `apps/web/AGENTS.md`.

Inspection of `apps/api/app/chat/router.py`, `service.py`, and `tests/test_chat.py` establishes the contract:

| Event | JSON data |
| --- | --- |
| sources | `{sources: Source[]}` |
| token | `{text: string}` |
| done | `{}` |
| error | `{code: string, message: string}` |

A Source carries `id: string`, `document_id: string | null`, `source: string | null`, `page: number | null`, `chunk_index: number | null`, and `snippet: string`. Pages are already one-based. IDs can be stored point IDs, deterministic chunk IDs, or request-local S1-style references; they are not document URLs. Successful streams start with sources and end with done; failures after headers end with error without done. Before headers, failures use `{detail: {code, message}}` with 422/502/503/504 statuses. The question limit is 4000 characters before trimming. `app/main.py` currently has no CORS middleware. No main specs exist yet.

## Goals / Non-Goals

**Goals:** Preserve the wire contract, isolate streaming from rendering, make request ownership explicit, and verify incremental behavior offline with controlled streams.

**Non-Goals:** No changes to ingestion or RAG internals, persistent history, conversational memory, authentication, agents, evaluations, deployment, WebSockets, Next.js proxy, or browser provider credentials. Plain text rendering is sufficient; Markdown rendering and citation link resolution are not required.

## Decisions

### Separate transport, state, and view

Keep the App Router page as a small server entry rendering a client chat component. Use `src/lib/chat/` for types, a pure SSE parser, and a fetch client; use a dedicated chat hook/controller for request lifecycle and session messages, with presentation in `src/components/chat/`. This supports direct transport/state tests without coupling fetch parsing to JSX. A separate chat framework would add unnecessary dependencies and could assume a different contract.

### Direct typed POST streaming

Resolve `NEXT_PUBLIC_API_BASE_URL ?? http://localhost:8000`, normalize trailing slashes, and append the existing route. POST `{question}` with JSON content type, accept SSE, and the caller's AbortSignal. Validate HTTP status before reading the body; safely decode the documented error envelope and fall back to a local message for unexpected bodies. Reject missing bodies or non-SSE successful responses. Use narrow runtime guards for known event payloads alongside TypeScript discriminated types; no new schema dependency is necessary.

Use a streaming TextDecoder and ReadableStream reader. Buffer incomplete lines and frames; support LF and CRLF (including split CRLF), comments, multiple data lines joined with newline, and multiple frames per read. Ignore unknown event types for forward compatibility. Decode only complete frames and validate recognized payloads. Flush the decoder at EOF; an incomplete unterminated frame or absence of a terminal event is a failed stream, never implicit success. Stop on the first done/error and cancel/release the reader in cleanup. EventSource cannot issue this JSON POST, so it is unsuitable.

### One owned request and explicit terminal states

Represent each exchange with stable identity, original question, assistant text, sources, status, and optional safe error. Append the user question and assistant placeholder atomically. A synchronous active-request ref prevents rapid duplicate submits before React renders. Loading covers retrieval and waiting for text; the first token moves to generating, done to completed, SSE/HTTP/transport/protocol errors to failed, and user abort to cancelled. Preserve partial text and source records on failure/cancel.

Each request has an AbortController and identity. Guard every event and finally update against that identity; terminal transitions happen once. Abort on cancel and unmount. Check the signal before processing buffered events so cancellation is not overwritten by already queued data. Release the active lock only for its owner. Retry appends a new attempt using the exact original question, preserving failed context, and uses the same duplicate gate. Earlier exchanges never enter request bodies. State lasts for the mounted browser page; reload clears it.

### Small accessible shadcn/ui composition

Reuse Button and add only needed shadcn components such as Textarea and Badge. Use a centered responsive page, clear paper header, readable message widths, bottom composer, and compact source list with optional native disclosure for snippets. Render source/text values as escaped React text; no raw HTML. Show known filename and page unchanged, otherwise supplied ID and unknown provenance; never construct PDF links. Keep source IDs inspectable because the model can reference them.

Enter submits through a semantic form unless Shift or IME composition is active; enforce blank/length validation before trimming. Expose status via a polite live region and errors via accessible notification without announcing every token. Label controls and roles, preserve focus during updates, and restore composer focus only when appropriate after the user's send/cancel/retry action, without pulling focus from another control.

Track whether the scroll container is near its bottom using a small pixel threshold. Follow streamed updates only in that state; user upward scrolling disables follow until they return to the bottom. Avoid smooth-scroll queues on each token. Use wrapping and mobile viewport-aware sizing so references and composer do not overflow.

### Minimal explicit CORS

Wrap FastAPI with CORSMiddleware permitting `http://localhost:3000`, POST, and Content-Type, with credentials disabled. Keep origins explicit and add no wildcard or speculative production origin. Apply middleware so documented HTTP errors are readable cross-origin. Do not add deployment configuration; any future origin must be deliberately allowlisted. Add preflight, error-path, and rejected-origin tests while preserving health and route behavior. A Next.js proxy would obscure the existing direct service boundary and is unnecessary.

### Focused offline tests

Add Vitest, jsdom, and React Testing Library as development-only test tooling with a reproducible npm test command and updated lockfile. Exercise pure parsing and fetch with byte-controlled ReadableStreams; exercise the controller/UI using deferred streams. Tests must prove a token becomes visible before done, not merely assert final concatenation. Include Unicode byte splits, delimiter splits, coalesced events, CRLF/comments, actual nullable sources, HTTP/SSE/malformed/EOF failures, AbortSignal propagation before headers and mid-stream, stale event suppression, terminal races, retry body isolation, and duplicate submissions. Add keyboard and scroll behavior coverage where DOM simulation is reliable; manually verify real responsive layouts and scrolling.

## Risks / Trade-offs

- [Abort cannot instantly stop an already running synchronous retrieval call] → Document the existing backend limit; abort terminates the browser request and backend disconnect cancels generation, while a worker can finish under existing timeouts.
- [Malformed or truncated responses could look complete] → Require done and retain explicit failed/cancelled badges on partial text.
- [Source metadata can be missing or IDs lengthy] → Preserve null values, wrap labels, and disclose full supplied IDs without guessing provenance.
- [DOM tests cannot establish mobile layout or real scroll behavior] → Verify desktop and narrow viewport interaction manually in addition to unit/component tests.
- [Live RAG checks need configured services and may incur provider charges] → Keep automated tests offline; record live verification separately and report unavailable prerequisites honestly.

## Migration Plan

No data migration or deployment work. Install frontend dependencies, set the optional public base URL, run existing backend setup/ingestion instructions, and start both local processes. Update README and architecture docs to replace static-shell claims and document CORS, lifecycle, tests, cancellation limits, and live checks. Rollback restores the static page and removes frontend-only modules/test tooling and local CORS addition; stored vectors and API contract remain intact.
