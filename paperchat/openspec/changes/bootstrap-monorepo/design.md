# Design

## Context

See `proposal.md` for motivation and scope, and the three delta specs for acceptance behavior. Read-only inspection found only OpenSpec configuration, editor metadata, and a local root `.env`; there are no application files, tests, main specs, or Git metadata. OpenSpec uses the default spec-driven schema with no additional project rules. Existing Docker/Qdrant setup is user-reported and does not need inspection or modification for this foundation.

## Goals / Non-Goals

**Goals:**
- Keep each application installable and runnable from its own directory, forming a straightforward boundary for later hosting.
- Prove the chosen web and API toolchains with the smallest visible page and endpoint.
- Make configuration and quality commands reproducible without paid services, credentials, or running infrastructure.

**Non-Goals:**
- No shared package framework, task runner, repository-wide Python environment, service/repository layers, or unused API client.
- No browser-to-API wiring, CORS middleware, provider settings, RAG dependencies, or background workers until a feature requires them.
- No deployment, CI, or container orchestration files. Future hosting and streaming belong in explanatory documentation only.

## Decisions

### 1. Two independent application roots

Use `apps/web/package.json` with an app-local `package-lock.json`, and `apps/api/pyproject.toml` with an app-local `uv.lock` and `.python-version` selecting Python 3.12. Use npm for the web app and uv for the API. Do not add a root Node manifest, npm workspaces, pnpm, Turborepo, or shared packages: two independent install commands are sufficient and avoid cross-directory build dependencies. This is a directory-based monorepo, with all commands explicitly scoped to an app.

Proposed structure:

```text
apps/
  web/
    src/app/                  # layout, static page, global styles
    src/components/ui/button.tsx
    src/lib/utils.ts          # shadcn-generated utility only
    components.json
    package.json
    package-lock.json
    .env.example
    ...                       # required Next.js/TS/ESLint configuration
  api/
    app/
      __init__.py
      main.py
      settings.py
    tests/
      test_health.py
      test_settings.py
    pyproject.toml
    uv.lock
    .python-version
    .env.example
docs/architecture.md
README.md
.gitignore
openspec/                     # existing planning system
```

### 2. Minimal web scaffold and component proof

Initialize Next.js App Router with TypeScript, Tailwind CSS, ESLint, `src/`, and the `@/*` import alias. Initialize shadcn/ui against that configuration and add only Button plus its generated dependencies and utility. Render a static page titled PaperChat with a brief foundation message and a labeled button such as “UI configured”; no click handler, chat form, health fetch, or other application feature is needed. Keep the page a server component unless the generated component genuinely requires a client boundary. Use system fonts so production builds do not depend on downloading fonts.

Expose `dev`, `lint`, `typecheck`, `build`, and `start` scripts. Use an explicit ESLint command and `tsc --noEmit`, and make standalone type validation work after installation, including any route type generation the selected Next.js version requires. Resolve compatible framework, Tailwind, and shadcn versions during implementation, record the required Node version in `engines` and the README, and commit the resulting lockfile. Do not add frontend unit-test infrastructure just to test the static scaffold; validate with quality commands and a browser smoke check.

Alternative: a larger component gallery or chat-shaped placeholder would expand UI scope without proving more configuration.

### 3. Small FastAPI application with process health

Use a flat Python `app` package under `apps/api`, with `app.main:app` as the ASGI entry point. Define `GET /health` directly in `main.py`; return a constant JSON object. No router tree, service layer, database client, lifespan resource initialization, or readiness dependency is necessary. The health check establishes process availability, not future Qdrant/provider readiness.

Runtime dependencies are FastAPI, an ASGI server (Uvicorn), and pydantic-settings with its needed environment-file support. Development dependencies are Ruff, pytest, and HTTPX for FastAPI's in-process test client. Define the Python requirement as `>=3.12,<3.13` so uv cannot silently select a different minor version. Configure Ruff for Python 3.12, a small standard lint rule set, and formatting in `pyproject.toml`; configure pytest there too.

Tests assert status 200, JSON content type, and the exact response body without network access. No future integrations are installed or initialized. An application factory is unnecessary for the single endpoint and can be introduced later if needed.

### 4. Settings and environment boundaries

Define a small `BaseSettings` model in `settings.py` with `app_name: str = "PaperChat API"`, read from `APP_NAME`. Load the optional `.env` relative to the API app root rather than the repository root, ignore unrelated dotenv keys, and retain process-environment precedence. Use this value for the FastAPI application title, making the setting useful without changing the health contract. No memoization or dependency injection layer is needed.

`apps/api/.env.example` contains the harmless default `APP_NAME`. `apps/web/.env.example` is comment-only, explaining that the static shell needs no environment variables and public browser settings must never hold secrets. Do not predeclare provider keys, embedding dimensions, or unused API URLs. Runtime defaults allow both apps to start without copying examples. Tests use temporary dotenv files and controlled environment values to verify defaults, file loading, and precedence without reading the user's real `.env`.

Root `.gitignore` excludes `.env` and `.env.*` at all depths with an exception for `.env.example`, `node_modules`, `.next`, `out`, `.venv`, Python bytecode, pytest/Ruff caches, TypeScript build metadata, coverage, and editor/OS artifacts. Keep app lockfiles eligible for tracking. Preserve the existing root `.env` without opening, relocating, or overwriting it. Since Git is not initialized, verify ignore patterns with an isolated temporary Git repository rather than initializing this project as an incidental step.

### 5. Explicit local command contract

The root README uses separate terminals and app directories. Expected commands:

| App | Install | Development | Checks | Production locally |
| --- | --- | --- | --- | --- |
| `apps/web` | `npm ci` | `npm run dev` (3000) | `npm run lint`, `npm run typecheck`, `npm run build` | `npm run start` (3000, after build) |
| `apps/api` | `uv sync --frozen` | `uv run uvicorn app.main:app --reload --port 8000` | `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` |

Document the selected compatible Node runtime, npm, Python 3.12, and uv prerequisites; environment examples; URLs; and `curl http://localhost:8000/health`. Docker/Qdrant are not prerequisites for running this change. Make clear that a future host will supply its own bind port. Avoid scripts that assume a sibling app is installed or active.

### 6. Document the future architecture without introducing it

Create a concise `docs/architecture.md`, linked from the README, distinguishing “implemented in this foundation” from “planned.” Describe:
- Ingestion: “Attention Is All You Need” document → extraction → chunks with source/page metadata → embeddings (provider undecided) → Qdrant vectors and payloads. LangChain is planned for orchestration; the ingestion entry point is deferred.
- Query: browser question → FastAPI → query embedding using a model compatible with indexed vectors → Qdrant retrieval → contextual prompt → OpenRouter generation → HTTP SSE events → browser answer and source references. This is a conceptual flow, not a committed endpoint or event schema.
- Next.js owns the browser experience; FastAPI owns orchestration and private credentials. Qdrant has local Docker and hosted Cloud options already set up separately. Vercel and Render are the planned web/API hosts; GitHub Actions is planned for later CI.

A prose/arrow flow is sufficient; no executable diagrams, SDKs, infrastructure configuration, or mock production services are needed. Separate app roots preserve future deployment boundaries without choosing deployment commands or implementing streaming today.

## Risks / Trade-offs

- [Generated tooling can change] → Resolve compatible versions at implementation time, record prerequisites, keep only necessary generated files, and validate locked installations and production build.
- [Two apps need two terminals and installation commands] → Document both clearly; this modest repetition avoids an unnecessary task runner.
- [Health reports only process availability] → State its meaning explicitly; add dependency readiness only with real integrations.
- [Existing environment files could accidentally influence tests or be tracked] → Use isolated settings tests, safe examples, and explicit ignore checks while preserving the existing root file.
- [Independent deployment is not yet operationally verified] → Keep manifests, lockfiles, and runtime entry points app-local; defer provider-specific testing and configuration to deployment work.

## Migration Plan

This is an additive scaffold with no data migration or production deployment. Implement the app roots, safe configuration, checks, and documentation; run the acceptance commands and smoke checks. Rollback consists of removing the introduced scaffold files while preserving existing local files and OpenSpec history. Do not initialize Git or commit files as a side effect of this change.
