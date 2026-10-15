# Design

## Context

See proposal.md for motivation. Discovery found independent applications: apps/web uses npm lockfile v3, Next.js 16.4.0, React 19.3.0 and existing lint/typecheck/test/build scripts; apps/api uses uv.lock, Python >=3.12,<3.13 and .python-version 3.12. No published main specs or CI/deploy configuration exists. Existing tests mock retrieval and generation. Phase 04's final live check remains open because it produced sources and done without text.

The API has lazy ChatSettings/IngestionSettings, app-local dotenv loading, credential-free import/health, a 4000-character question limit, 1024 default output tokens (maximum 32768), retrieval/generation deadlines, safe outcome logging, four bounded retrieval workers, and explicit ASGI disconnect ownership. CORS is fixed to localhost. The browser streams fetch responses directly but defaults to localhost in every environment. No rate limiter exists.

## Goals / Non-Goals

**Goals:** Small changes around existing entry points; preserve local/ingestion behavior, offline tests, direct cross-origin streaming, and existing cloud collection contents.

**Non-Goals:** New RAG behavior, ingestion during deployment, authentication, Redis/PostgreSQL, new hosting providers, orchestration abstractions, or distributed rate limiting implemented in process memory.

## Repository layout

The owner confirmed deployment from the parent `rag-experiments` repository.
PaperChat remains its `paperchat/` subdirectory. GitHub discovers the single CI
workflow at repository `.github/workflows/ci.yml` (one directory above this
OpenSpec project); this parent-level file is explicitly authorized by the owner.
Host root directories and CI cache/working paths use `paperchat/apps/...`.
Keep the Blueprint at `paperchat/render.yaml` and select that custom Blueprint
path in Render. Local instructions continue to start at the PaperChat directory.

## Decisions

### CI uses existing application commands

Create .github/workflows/ci.yml with pull_request and push/main triggers, read-only contents permission, two jobs and dependency caches keyed to their lockfiles. Frontend uses Node 22, npm ci, npm run lint, npm run typecheck, npm test, npm run build. Backend installs Python from paperchat/apps/api/.python-version, pins the uv action/tool version, uses uv sync --frozen, runs uv run --frozen ruff check ., ruff format --check ., pytest, and python -c 'from app.main import app; assert app'. Set a non-secret HTTPS placeholder backend URL for the frontend production build; no CI provider secrets. Validate workflow syntax with actionlint when available. Separate deploy workflows are unnecessary because owners configure host Git connections.

### Native Render Python with uv

Add paperchat/render.yaml with runtime python, rootDir paperchat/apps/api, buildCommand `uv sync --frozen --no-dev`, startCommand `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and healthCheckPath /health. Explicitly select Python 3.12 consistently with the project and pin a supported uv version for reproducibility when authoring the Blueprint. Use host-managed environment secrets (sync:false entries where useful), never real values. No pre-deploy command, disk, PDF, local Qdrant, or ingest command. Direct venv executable avoids runtime dependency synchronization. Native runtime supports the existing lockfile; Docker adds no identified value. Confirm Linux wheel installation in CI and actual Render logs; do not claim hosted compatibility from macOS alone.

Render references: https://render.com/docs/deploys and https://render.com/docs/monorepo-support document uv.lock and app root support; https://render.com/docs/health-checks documents HTTP checks.

### Preserve lazy startup and typed explicit CORS

Extend app Settings with CORS_ALLOWED_ORIGINS as a JSON list of validated exact HTTP(S) origins, defaulting to ["http://localhost:3000"]. Reject wildcard, credentials, paths, queries, and fragments; document that production lists its exact HTTPS Vercel origin plus localhost if local access is desired. Build application through a small factory if needed for isolated settings tests. Keep POST, Content-Type and allow_credentials=False. Do not add global eager provider validation: it conflicts with existing health/ingestion guarantees. Missing/invalid chat configuration continues to return the existing safe 503; runbook identifies specific required variables without printing values or raw validation errors. /health is liveness, never RAG readiness.

### Production frontend requires its API URL at build time

Read installed Next.js environment/deployment guides before coding as required by apps/web/AGENTS.md. Validate NEXT_PUBLIC_API_BASE_URL during production build in existing Next config and use matching client resolution: require HTTPS, reject blank/malformed/loopback URLs and embedded credentials/query/fragment, normalize trailing slash. Development retains http://localhost:8000. Keep direct fetch/AbortController/TextDecoder parsing and existing App Router; no Next proxy or full-answer buffering. Test the validator with production and development cases and verify missing URL build failure and valid URL build success. A placeholder domain is only build validation, never live connectivity evidence.

Vercel: Root Directory paperchat/apps/web, framework Next.js, Node 22, install npm ci, build npm run build, framework-managed output. Set NEXT_PUBLIC_API_BASE_URL to the HTTPS Render origin for Production, and separately for Preview if used. Rebuild after changes because Next inlines public variables. No vercel.json is needed unless a demonstrated framework issue requires one. References: https://vercel.com/docs/monorepos and https://nextjs.org/docs/app/guides/environment-variables.

### Detect empty answers without delaying tokens

Keep sources first and text forwarding unchanged. Track whether any emitted model text contains non-whitespace characters; after provider exhaustion, emit an allowlisted `empty_response` error instead of done when none did. Close iterators and clients via existing finally blocks. Preserve empty-retrieval fallback. Add focused no-chunk, metadata-only, whitespace-only, valid-text, and cleanup regression cases. Investigate the recorded live zero-token symptom only within the existing adapter/text extraction path if reproducible; do not switch models/providers or broaden RAG features to mask it.

### Document actual configuration and public abuse limits

Reference APP_NAME; new CORS_ALLOWED_ORIGINS; OPENROUTER_API_KEY (shared by embeddings and generation); OPENROUTER_MODEL; OPENROUTER_TEMPERATURE (0); OPENROUTER_MAX_TOKENS (1024); OPENROUTER_TIMEOUT_SECONDS (60); RAG_RETRIEVAL_TIMEOUT_SECONDS (60); EMBEDDINGS_PROVIDER (openrouter only); EMBEDDINGS_MODEL (openai/text-embedding-3-small); QDRANT_URL; QDRANT_API_KEY; QDRANT_COLLECTION (paperchat-papers). Separate platform PORT/Python/uv settings and public NEXT_PUBLIC_API_BASE_URL. Correct stale .env.example comments implying separate embedding/chat keys.

Require the owner's existing HTTPS Qdrant Cloud cluster, key, collection, and original embedding identity; use collection-scoped read access for runtime when available. Never recreate or re-embed on deploy. Document that CORS does not stop direct clients and the retrieval semaphore is only local resource control. Recommend restricted OpenRouter key budgets, available account spending controls and alerts, usage monitoring, and external gateway rate limiting for sustained exposure. State explicitly that this phase has no reliable distributed request rate limiter.

## Risks / Trade-offs

- Unauthenticated paid endpoint → output/time limits reduce per-request cost; provider budgets and monitoring remain required; direct abusive traffic remains a residual risk.
- Process health does not prove provider readiness → verify real chat separately and distinguish missing settings, unavailable collection, provider quota, and empty model response.
- Host cold starts or proxy buffering → measure first text before done in real browser and curl -N; inspect host logs without dumping remote responses.
- Public build variables freeze URLs → rebuild when changing backend address; exact preview origins need deliberate allowlisting.
- Existing empty-response issue → error guard prevents false success; actual answer/citations remain a live acceptance gate.
- Current remote platform/tool availability may differ → validate Blueprint/action versions and platform settings during implementation; report unavailable validators explicitly.

## Migration Plan

1. Implement and run offline suites/checks and both valid/missing production URL build checks; no data migration.
2. Owner connects Render repository/service and supplies backend secrets and existing collection settings; verify deployed /health.
3. Owner connects Vercel Hobby with paperchat/apps/web root and backend public URL; set its exact origin in Render CORS settings and redeploy as needed.
4. Verify allowed and denied preflight, error readability, curl sources/tokens/done, real browser token arrival before completion, source/citation correctness, cancellation and absence of localhost requests. Record tested URLs, commit and outcomes without secrets; otherwise record manual blockers.
5. Roll back each host to a known working deployment/commit, restore matching environment settings, rebuild frontend if URL changed, and recheck health and chat. Do not modify the Qdrant collection during rollback.

## Open Questions

The owner's actual service URLs, model ID, existing collection identity, hosting plan details, and key budgets are supplied manually. Their values do not change this design; no live deployment success can be reported until those services are tested.
