# Spec Delta

## Purpose

Validate both applications reproducibly before deployment without provider credentials, document ingestion, or running external services.

## ADDED Requirements

### Requirement: Pull request and main validation
One CI workflow SHALL run frontend and backend checks on pull requests and pushes to main, using committed lockfiles, compatible runtimes, and dependency caching.

#### Scenario: Frontend checks
- **WHEN** CI runs for a pull request or main push
- **THEN** it installs with npm ci and runs ESLint, TypeScript checks, existing tests, and the Next.js production build from paperchat/apps/web

#### Scenario: Backend checks
- **WHEN** CI runs for a pull request or main push
- **THEN** it uses the configured Python 3.12 version and frozen uv lockfile from paperchat/apps/api and runs Ruff lint and format checks, pytest, and application import validation

### Requirement: Offline validation boundary
CI SHALL require no OpenRouter or Qdrant credentials, perform no ingestion, and make no paid provider calls. Production build configuration SHALL use a non-secret explicit HTTPS backend URL.

#### Scenario: Clean runner
- **WHEN** checks run without dotenv files, a PDF, provider secrets, or Qdrant
- **THEN** mocked tests and application import succeed without external service access
