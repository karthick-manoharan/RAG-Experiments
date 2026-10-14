# Spec Delta

## Purpose

Provide a minimal browser-facing foundation that can run and build independently before PaperChat adds its research-paper chat experience.

## ADDED Requirements

### Requirement: Frontend foundation page
The frontend SHALL serve a static PaperChat foundation page at `/` with a visible, keyboard-focusable demonstration button. The page SHALL require no backend connection or external service credentials and SHALL NOT expose chat controls or imply working RAG functionality.

#### Scenario: Standalone frontend development
- **WHEN** a developer starts the frontend using the documented development command with the backend stopped and no service credentials configured
- **THEN** `http://localhost:3000/` renders the PaperChat foundation page and its styled demonstration button
- **AND** the button can receive keyboard focus without triggering backend requests

### Requirement: Frontend validation commands
The frontend SHALL provide documented commands for linting, TypeScript validation, production build, and serving the production build. These commands SHALL operate from `apps/web` without running the backend or configuring RAG services.

#### Scenario: Validate and serve a production build
- **WHEN** a developer installs the locked frontend dependencies and runs the lint, typecheck, and build commands
- **THEN** each command exits successfully
- **AND** the production start command serves the foundation page at `http://localhost:3000/`
