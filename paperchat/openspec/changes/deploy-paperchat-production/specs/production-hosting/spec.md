# Spec Delta

## Purpose

Run the existing browser and API applications on their selected hosts with explicit configuration, safe cross-origin access, and reproducible operator verification.

## ADDED Requirements

### Requirement: Reproducible backend service
Deployment configuration SHALL run the existing API from paperchat/apps/api with locked production dependencies, bind to 0.0.0.0 and the host PORT, and use /health for process health checks. Deployment SHALL neither ingest documents nor depend on a local PDF or Qdrant container.

#### Scenario: Configured production startup
- **WHEN** Render starts the service with valid runtime configuration
- **THEN** the API starts gracefully and GET /health returns 200 with {"status":"ok"} without contacting providers

#### Scenario: Credential-free local startup
- **WHEN** local API startup or import occurs without provider configuration
- **THEN** health remains available and chat returns a safe configuration error rather than exposing settings or secrets

### Requirement: Explicit production browser endpoint
The production frontend SHALL require a valid HTTPS NEXT_PUBLIC_API_BASE_URL and reject missing, blank, malformed, or loopback configuration. Local development SHALL retain its localhost default. Client variables SHALL contain no provider credentials.

#### Scenario: Production URL missing
- **WHEN** a production build lacks a valid public backend URL
- **THEN** the build fails with an actionable configuration message and cannot silently ship localhost requests

#### Scenario: Configured browser
- **WHEN** the production app submits a question
- **THEN** it fetches the configured API directly and renders SSE tokens incrementally through the existing App Router interface

### Requirement: Explicit cross-origin allowlist
The API SHALL accept typed explicit frontend origins, retain http://localhost:3000 for development, permit POST and Content-Type preflight, and grant no wildcard or credentialed access.

#### Scenario: Allowed production origin
- **WHEN** the configured Vercel origin sends a preflight or chat request
- **THEN** the response grants that exact origin access including readable validation and service errors and SSE responses

#### Scenario: Unauthorized origin
- **WHEN** another origin attempts cross-origin access
- **THEN** no access-control-allow-origin permission is returned for it

### Requirement: Production configuration reference
Documentation SHALL list existing environment variable names, defaults, limits, shared embedding/generation credentials, and production Cloud settings without secrets. Production instructions SHALL require an existing compatible Qdrant Cloud collection and matching embedding identity without recreating it.

#### Scenario: Owner configures services
- **WHEN** the owner follows the environment reference
- **THEN** they can configure the shared OpenRouter key, chat model, embeddings model, Qdrant HTTPS URL/key/collection, timeouts, output cap, app name, and explicit Vercel origin using host-managed secrets

### Requirement: Public endpoint risk disclosure
Existing question limits, generation caps, deadlines, safe errors, cancellation, and secret-free diagnostics SHALL remain effective. Documentation SHALL disclose lack of distributed request rate limiting and recommend provider spending controls; process-local concurrency bounds SHALL NOT be presented as distributed abuse protection.

#### Scenario: Public API exposure
- **WHEN** the owner deploys the unauthenticated endpoint
- **THEN** instructions explain that direct clients bypass CORS and recommend provider key budgets, usage alerts, monitoring, and an external gateway limit if public traffic warrants it

### Requirement: Executable deployment runbook
README SHALL give local and CI commands, Render commands and health settings, Vercel root and build settings, production CORS setup, live verification, rollback, and troubleshooting. Reports SHALL distinguish local checks from actual hosted acceptance.

#### Scenario: Hosted acceptance
- **WHEN** live URLs and authorized service access are available
- **THEN** verification checks health, allowed and rejected origins, browser network targets, source metadata, incremental answer text with paper citations, completion, and cancellation

#### Scenario: Hosting unavailable
- **WHEN** accounts, credentials, connections, or live URLs are unavailable
- **THEN** reporting identifies remaining manual actions and does not claim deployed health or successful hosted chat
