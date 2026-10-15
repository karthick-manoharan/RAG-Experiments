# Proposal

## Why

PaperChat works locally but lacks reproducible hosting configuration and automated checks. Phase 05 prepares the existing application for Vercel and Render while addressing production configuration and a demonstrated empty-answer streaming failure.

## What Changes

- Add one GitHub Actions workflow for credential-free frontend and backend validation using existing lockfiles.
- Add native Python Render configuration with app-local root, frozen uv installation, Uvicorn port binding, and `/health` checks; never ingest during deploy.
- Require an explicit production browser API URL while preserving the development localhost default and App Router streaming UI.
- Add typed explicit CORS origins, retain localhost development access, and document production Qdrant Cloud and shared OpenRouter configuration.
- Preserve existing limits, deadlines, cancellation, safe diagnostics, and SSE framing; terminate empty model answers as errors.
- Document deployment, verification, rollback, and residual public-endpoint abuse risk without claiming distributed rate limiting.

## Capabilities

### New Capabilities

- `deployment-validation`: Credential-free CI using the repository's existing checks and lockfiles.
- `production-hosting`: Reproducible monorepo hosting, explicit production configuration, restricted browser access, and operational verification.
- `streaming-answer-integrity`: Successful streams require answer text while preserving ordering and cleanup.

### Modified Capabilities

None: main `openspec/specs` contains no published capabilities. Earlier change artifacts remain context; this change narrows their localhost fallback to development and fixes empty model success without rewriting them.

## Impact

Affected areas: parent-repository `.github/workflows/ci.yml`, `paperchat/render.yaml` with repository-relative hosting paths, backend settings/application assembly and chat service, frontend API URL configuration, focused tests, environment examples, README, and verification documentation. Existing npm and uv lockfiles remain authoritative; no RAG framework, authentication, data service, ingestion pipeline, or provider migration is added. Hosting accounts, secrets, connections, and live verification remain owner-operated prerequisites. Phase 04 currently records an unresolved live stream with sources and done but zero tokens; deployment readiness must not conceal that failure.
