# Streaming chat verification

Verified on 2026-10-14 on branch `implement-streaming-chat-ui`.

## Automated checks

- Frontend: 28 Vitest tests pass, covering arbitrary byte/frame boundaries,
  UTF-8, CRLF, comments, multiline data, nullable sources, incremental tokens,
  HTTP/SSE/protocol errors, unexpected EOF, cancellation, request isolation,
  duplicate submissions, retry, keyboard controls, focus and scroll following.
- Frontend ESLint, generated route types/TypeScript, and production build pass.
- `npm ci --ignore-scripts --offline` succeeds from the committed lockfile.
- Backend: all 110 tests pass, including ingestion regressions and three new
  CORS tests. Ruff lint and format checks pass for all 23 Python files.
- Backend checks used the existing `.venv/bin` executables because the runner
  sandbox cannot read uv's global cache. No backend dependency changes were needed.
- The first sandboxed Turbopack build cached a local worker port permission
  failure. Isolating that generated build cache and allowing local worker ports
  produced a passing build; a subsequent normal `npm run build` invocation with
  those permissions also passed. Application build configuration is unchanged.

## Browser checks

Used the browse skill and a local Chrome session at localhost:3000. Desktop
(1288 × 711) and mobile (390 × 844) layouts were visually inspected. At mobile
width the document width equals the viewport width and the composer remains
visible. Example selection focuses the composer; real keyboard typing and Enter
submit. No focus is taken during streamed text updates.

Controlled in-browser ReadableStreams established text visible before done,
actual fixture page/source labels, completion, abort before response headers,
abort after text, preserved partial answers, HTTP/SSE errors, and retry bodies
containing only the original question. Fixture provenance is synthetic and was
used only for UI verification.

A separate temporary FastAPI HTTP fixture on the default API port confirmed
cross-origin network streaming with two text frames separated by two seconds,
source disclosures, completion, a 503 error, cancellation, and late SSE failure.
The real RAG server used for the live check was stopped before this fixture was
started; no existing user server was replaced. No fixture code or network
interception is part of the application.

With a long controlled answer, scrolling upward held scrollTop at zero while
more tokens arrived. Returning to the bottom resumed following; after a further successful HTTP
exchange the measured distance from the bottom was zero. Component tests cover
the same pause/resume behavior.
History retains multiple independent questions and failed/cancelled attempts.

## Live service result and limitation

The configured backend was started and asked “How does multi-head attention
work?” through its actual HTTP SSE endpoint. Retrieval returned five nonempty
source snippets with real page metadata [5, 4, 5, 2, 4]. The service emitted
sources followed by done, with **zero token events**. A browser request also
rendered actual retrieved references but received no answer text. Thus real
retrieval and browser source display were verified, but live provider text
output and live incremental generation were not established in this session.
The frontend correctly displays “No answer received.” for an empty completed
stream. The existing RAG service, model configuration, and generation behavior
were preserved; investigate provider/model output separately before claiming
full live end-to-end answer acceptance. Controlled stream results do not stand
in for this missing live-provider evidence.

## Reproduce

Follow the root README's backend configuration, paper ingestion and CLI search
steps. Start FastAPI on port 8000 and Next.js on port 3000, then follow the
“Browser chat verification” section for live questions, source inspection,
multiple exchanges, cancellation, retry and responsive scrolling. Inspect the
Network response to distinguish absent upstream token events from UI rendering
failures. Never copy provider credentials into frontend environment variables.
