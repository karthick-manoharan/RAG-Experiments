# Spec Delta

## Purpose

Provide an independently runnable backend with predictable configuration and a health response that does not depend on future RAG integrations.

## ADDED Requirements

### Requirement: Dependency-free health endpoint
The backend SHALL expose unauthenticated `GET /health`, returning HTTP 200 with an `application/json` response and exactly `{"status":"ok"}`. Handling this endpoint SHALL NOT contact external services or require service credentials.

#### Scenario: Health response without infrastructure
- **WHEN** a client requests `GET http://localhost:8000/health` with the backend running and no Qdrant, embedding, or generation service available
- **THEN** the response status is 200
- **AND** the JSON body equals `{"status":"ok"}` with no additional fields
- **AND** no external service requests are made

### Requirement: Typed runtime configuration
The backend SHALL load an `APP_NAME` string setting, defaulting to `PaperChat API`, from process environment variables and an optional app-local `.env` file. Process environment values SHALL take precedence over file values. With neither source present, the backend SHALL start using defaults without requiring future provider settings.

#### Scenario: Start with defaults
- **WHEN** the backend starts from `apps/api` without an `.env` file or `APP_NAME` environment variable
- **THEN** the configured application name is `PaperChat API` and `/health` remains available

#### Scenario: Read local configuration
- **WHEN** `apps/api/.env` sets `APP_NAME=Local PaperChat` and the process environment does not set `APP_NAME`
- **THEN** the configured application name is `Local PaperChat`

#### Scenario: Process environment overrides local configuration
- **WHEN** the app-local `.env` sets `APP_NAME=Local PaperChat` and the process environment sets `APP_NAME=Hosted PaperChat`
- **THEN** the configured application name is `Hosted PaperChat`
