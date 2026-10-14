# Proposal

## Why

PaperChat needs a runnable, verifiable application foundation before adding RAG for “Attention Is All You Need.” Independent frontend and backend applications will support local development now and separate Vercel and Render deployments later without introducing unused services.

## What Changes

- Establish a minimal monorepo with `apps/web` and `apps/api`, with independent dependency manifests and lockfiles.
- Initialize Next.js App Router with TypeScript, Tailwind CSS, ESLint, and shadcn/ui; render one Button on a static foundation page to demonstrate the configuration.
- Initialize FastAPI on Python 3.12 with uv, typed `pydantic-settings` configuration, Ruff, and pytest.
- Expose `GET /health`, returning HTTP 200 and exactly `{"status":"ok"}` without external dependencies.
- Supply safe app-specific `.env.example` files and root ignore rules, preserving the existing local `.env`.
- Document installation, development ports and commands, checks, and the planned ingestion/query architecture.
- Defer ingestion, embeddings/provider selection, LangChain, Qdrant integration, OpenRouter calls, SSE implementation, chat UI, authentication, additional infrastructure, Docker Compose, CI, and deployment configuration.

## Capabilities

### New Capabilities

- `web-shell`: A runnable, buildable frontend foundation with a minimal shadcn/ui demonstration.
- `api-health`: An independently runnable backend with typed runtime settings and a dependency-free health response.
- `local-development`: Reproducible installation, app-specific configuration, quality commands, and documentation for the two applications.

### Modified Capabilities

None. There are no existing main specs or application implementations.

## Impact

- Adds frontend application files and Node dependencies under `apps/web`, backend application files and Python dependencies under `apps/api`, plus root documentation and ignore rules.
- Introduces a single application API endpoint: `GET /health`.
- Adds no cloud resources or calls to external services. The user reports Docker and local/cloud Qdrant setup are already complete; this change neither configures nor requires them.
- Existing OpenSpec files, local `.env`, and editor configuration are preserved. No source migration is required: inspection found no application code and no Git repository metadata in this directory.
