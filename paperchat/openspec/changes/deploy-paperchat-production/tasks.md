# Tasks

## 1. Production settings and CORS

- [x] 1.1 Add typed CORS_ALLOWED_ORIGINS JSON-list settings and wire explicit origins into application construction; verify configured Vercel plus localhost preflights, POST/Content-Type, rejected origins, invalid wildcard/URL settings, and readable SSE/HTTP errors with focused backend tests.
- [x] 1.2 Preserve lazy provider configuration and credential-free import/health; verify valid configured startup, absent provider settings, and safe chat configuration errors without logging secrets or raw validation values.
- [x] 1.3 Update backend environment example and README settings reference with actual names/defaults/ranges, JSON CORS syntax, shared OpenRouter key, and existing Qdrant Cloud collection identity; verify examples match typed settings and contain no credentials.

## 2. Production browser configuration

- [x] 2.1 Read installed Next.js deployment/environment guides required by apps/web/AGENTS.md; add production API URL validation and matching client resolution while retaining development default and current direct SSE client; verify focused tests cover missing/blank/malformed/loopback/non-HTTPS URLs, valid HTTPS URLs and trailing slash normalization.
- [x] 2.2 Document Vercel Hobby Root Directory paperchat/apps/web, Node 22, npm ci, npm run build, framework output defaults, Production/Preview environment scopes, and rebuild semantics in README and frontend environment example; verify production build fails without a URL and succeeds with a non-secret explicit HTTPS URL.

## 3. Streaming answer integrity

- [x] 3.1 Add non-whitespace answer detection to existing generation stream and a safe empty_response terminal error with no done; verify no-chunk, metadata-only, whitespace-only and normal answers, sources-first ordering, and iterator/client cleanup with focused tests.
- [x] 3.2 Retain incremental tokens, timeout errors, cancellation, safe logging and no-retrieval fallback; run existing direct-ASGI streaming tests and frontend stream/UI tests, and document empty-response troubleshooting and the unresolved prior live symptom.

## 4. Render service configuration

- [x] 4.1 Add paperchat/render.yaml using native Python, rootDir paperchat/apps/api, supported pinned Python 3.12/uv configuration, uv sync --frozen --no-dev, direct venv Uvicorn with 0.0.0.0 and $PORT, and /health; verify Blueprint syntax against current official docs and production-only dependency import/start locally without ingestion or local Qdrant.
- [x] 4.2 Document manual Render Git connection, secret entry, HTTPS Qdrant Cloud URL/key/collection, original embeddings identity, liveness semantics and exact build/start commands; verify commands from apps/api and confirm no PDF, Docker, or pre-deploy ingestion requirement.
- [x] 4.3 Document unauthenticated endpoint residual risk, CORS limitations, existing input/time/output bounds, provider budgets/alerts and optional external gateway mitigation; verify wording never presents in-memory concurrency as distributed rate protection.

## 5. GitHub Actions

- [x] 5.1 Add one parent-repository .github/workflows/ci.yml for pull requests and main pushes with read-only permissions, frontend/backend jobs, npm/uv lockfile caches, compatible configured runtimes, all existing checks and import validation; validate with actionlint or report its unavailability and inspect parsed workflow structure.
- [x] 5.2 Document executable CI-equivalent commands and run them without live provider credentials, PDFs, or Qdrant; verify frontend production build uses only an explicit non-secret API URL and backend tests rely on mocks, with no ingestion or paid calls.

## 6. Integrated verification and handoff

- [x] 6.1 Run all existing backend pytest and frontend tests plus Ruff lint/format, ESLint, TypeScript and production build; resolve regressions and record actual results, preserving existing ingestion/local commands and lockfile consistency.
- [x] 6.2 Add executable deployed health, allowed/denied CORS, curl -N and browser verification instructions, including incremental text before done, citations, cancellation, safe failures and no localhost requests; include rollback of both services and matching environment settings without changing collection data, and review commands against implemented config.
- [x] 6.3 Perform external deployment checks only with available live URLs and authorized access; record actual streamed answer/source/citation and health results, or explicitly document owner-supplied account/secret/connection/URL blockers and leave hosted acceptance unverified.
- [x] 6.4 Review diff for accidental secrets and scope expansion; report changed files, local check results versus remote CI results, Render commands, Vercel settings, required variables, manual actions and remaining blockers with evidence.
