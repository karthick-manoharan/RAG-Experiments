# Production preparation verification

## Scope and repository paths

The owner confirmed that `rag-experiments` is the Git repository and PaperChat
is its `paperchat/` folder. The single discoverable workflow is
`rag-experiments/.github/workflows/ci.yml`. Hosting roots are
`paperchat/apps/web` (Vercel) and `paperchat/apps/api` (Render). Select
`paperchat/render.yaml` as the custom Render Blueprint path. Local README
commands start from PaperChat unless explicitly labelled parent-root commands.

## Local results — 2026-10-15

- Backend frozen install succeeds. All **127 pytest tests pass**, including
  ingestion regressions, configured CORS, lazy startup/configuration safety,
  empty responses, ordered streaming, total deadlines, ASGI delivery and cleanup.
- Ruff lint and format pass for all **23 Python files**. An import-order issue
  found during verification was corrected.
- Backend tests/import were run in `/private/tmp/paperchat-offline-api`, copied
  with only source, tests, pyproject, lockfile and `.python-version`. No dotenv,
  user PDF, provider credentials or running Qdrant were supplied. Tests use mocks
  and generate fixtures. No ingestion or paid calls were performed.
- A separate `uv sync --frozen --no-dev` environment contains production packages
  only. Application import succeeds from the clean source. Its direct Uvicorn
  command starts on `0.0.0.0:18005`; actual local GET `/health` returns 200 and
  `{"status":"ok"}`. It shuts down cleanly afterward.
- Frontend `npm ci`, ESLint, all **47 Vitest tests**, route type generation /
  TypeScript and production build pass on Node **22.19.0**. API configuration
  tests cover missing/blank/malformed/loopback/non-HTTPS URLs and normalization.
  Typecheck and build use only the explicit non-secret URL
  `https://api.example.com`, which is not a deployed service. The local Next
  commands report an existing `.env.local`; the explicit API URL overrides its
  value. No provider credentials are consumed by the frontend checks.
- A blank `NEXT_PUBLIC_API_BASE_URL` production build fails with the actionable
  configuration error as expected. Next type generation also loads the production
  configuration phase, so the documented check command supplies the same URL.
- A sandboxed Turbopack build cached a worker port `Operation not permitted`
  failure. An escalated retry reused that failed cache. Moving generated `.next`
  to a temporary diagnostic directory and rebuilding with local port permission
  succeeded; a subsequent normal build with that permission also passed. No
  bundler switch or application workaround was introduced.
- Local backend Python is **3.12.8**, uv **0.5.9**. Render pins Python **3.12.12**
  and uv **0.12.10**; CI uses the project's Python **3.12** selection and uv
  **0.12.10**. The local macOS checks do not prove the pinned Render runtime or
  Linux wheels; inspect actual CI and host logs after pushing/deploying.
- Neither `actionlint` nor the Render CLI is installed. The YAML parser checks
  workflow triggers, read-only permissions, two jobs, working directories and
  absence of secret references; Blueprint structure/fields were reviewed against
  official Render docs. No Render API or remote workflow validation is claimed.
- Existing npm and uv lockfiles are unchanged. Local installation/checks use them.

## Hosted acceptance — unverified

No deployed Render/Vercel service URLs, authenticated hosting sessions or Git
connections were supplied for this change. Remote GitHub Actions has not been
run by this session; the workflow has only been checked locally. There are no
hosted health, CORS, incremental answer, citation or cancellation results to report.

The owner must connect the parent Git repository to Render and Vercel, supply
backend secrets and original embedding/collection identity, choose the model
and spending limits, set the public API URL in Vercel Production/Preview, and
set exact frontend origins in Render CORS. Follow README's executable hosted
acceptance and rollback instructions, recording deployment/commit IDs and
outcomes without secrets. Do not change collection data while deploying.

The prior live Phase 04 result remains unresolved: five sources, then done,
with zero answer tokens. The new `empty_response` guard now prevents this from
being reported as success, but the model/adapter cause and actual hosted text /
citation quality have not been verified. See `streaming-chat-verification.md`.


## Final diff review

Changes are limited to the parent `.github/workflows/ci.yml`; PaperChat's
`render.yaml`, README and environment examples; backend settings/application
factory and empty-answer stream guard with focused tests; frontend shared API
URL validator, Next config, stream client and validator tests; this verification
record; and the change's planning artifacts/task tracking. No ingestion behavior,
provider/model migration, authentication, data stores or dependencies were added.

Reviewed tracked diffs and every newly authored deployment/code/document file.
Only blank secret placeholders, `sync: false` host prompts and synthetic test
sentinels are present; no actual credentials were found. Dotenv files remain
ignored. `git diff --check` passes and both application lockfiles are unchanged.
Render commands, Vercel settings, required variables and owner actions are in
README. Remote CI and hosted results remain explicitly unverified above.
