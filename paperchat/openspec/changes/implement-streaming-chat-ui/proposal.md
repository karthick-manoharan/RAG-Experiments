# Proposal

## Why

PaperChat already retrieves paper passages and streams grounded answers, but users can only access chat through the API. A responsive browser interface will make the existing RAG flow usable with incremental answers and verifiable source metadata.

## What Changes

- Replace the static frontend with a responsive shadcn/ui chat page for “Attention Is All You Need”, including examples, history, keyboard-friendly composer, and compact references.
- Add a typed direct POST streaming client that preserves the existing sources/token/done/error contract and handles arbitrary network boundaries.
- Add incremental rendering, loading/generating/completed/cancelled/failed states, cancellation, duplicate submission protection, retry, and scroll-aware following.
- Keep exchanges in browser-session component state; send only the current question.
- Configure the public API base URL with a localhost default; minimally enable explicit local-origin CORS without exposing service credentials.
- Add frontend tests and local verification documentation.

## Capabilities

### New Capabilities

- `streaming-chat`: Browser-based independent paper questions, incremental answers, actual source references, accessible interactions, cancellation, and failure recovery over the existing streaming endpoint.

### Modified Capabilities

None. The main spec inventory is currently empty; existing API behavior is documented in code, tests, README, and prior change artifacts and remains unchanged.

## Impact

Affected areas: `apps/web/src/app`, new chat presentation/state modules and `src/lib` streaming modules, frontend test tooling and lockfile, `apps/web/.env.example`, `apps/api/app/main.py` CORS integration and backend tests, README and architecture documentation. Existing Next.js App Router, TypeScript, Tailwind, and shadcn/ui setup is retained. No ingestion, retrieval, generation, or endpoint schema redesign; no memory, persistence, authentication, agents, evaluations, WebSockets, API proxy, or cloud deployment.
