# Spec Delta

## Purpose

Give contributors a reproducible, understandable local workflow for independently installing, configuring, running, and verifying both PaperChat applications.

## ADDED Requirements

### Requirement: Independent application workflows
The repository SHALL contain `apps/web` and `apps/api`, each with its own dependency manifest and committed lockfile. Documented installation and startup commands SHALL work from each application's directory without installing or running the other application. The backend SHALL use Python 3.12.

#### Scenario: Install the applications independently
- **WHEN** a contributor follows each application's locked installation procedure
- **THEN** the frontend dependencies are installed without a Python environment
- **AND** the backend dependencies are installed without frontend dependencies

### Requirement: Safe environment configuration
Each application SHALL provide a tracked `.env.example` with safe values or comments explaining that no variables are required. Root ignore rules SHALL exclude real environment files at all repository depths, dependency directories, caches, and generated build output while permitting `.env.example` and lockfiles. Existing local environment files SHALL be preserved.

#### Scenario: Local configuration remains private
- **WHEN** a contributor creates app-local environment files from the examples
- **THEN** the ignore rules exclude those local files and the existing root `.env`
- **AND** the examples and dependency lockfiles remain eligible for tracking
- **AND** the examples contain no credentials

### Requirement: Backend quality commands
The backend SHALL expose documented lint, format-check, and test commands. The test suite SHALL verify the health response and runtime settings behavior without cloud access or external service credentials.

#### Scenario: Verify the backend locally
- **WHEN** a developer installs backend development dependencies and runs the documented lint, format-check, and test commands
- **THEN** all commands exit successfully without a running frontend or external infrastructure
- **AND** tests cover the health status/body and settings defaults, file loading, and environment precedence

### Requirement: Contributor documentation
The root README SHALL document prerequisites, installation, environment setup, development commands, expected frontend port 3000 and backend port 8000, health verification, and quality/production commands. It SHALL identify app-directory deployment boundaries for future frontend and backend hosting without requiring deployment configuration.

#### Scenario: Follow the README from a clean checkout
- **WHEN** a contributor with the stated prerequisites follows the root README
- **THEN** both applications can be installed and run in separate terminals
- **AND** the contributor can open the frontend and verify `/health` at the documented URLs
- **AND** the contributor can run all documented checks without RAG credentials

### Requirement: Planned architecture documentation
A concise architecture document SHALL describe planned paper ingestion and retrieval-augmented query flows, application responsibilities, future streaming transport and hosting, and the undecided embedding provider. It SHALL clearly distinguish planned integrations from the implemented foundation.

#### Scenario: Understand the future RAG architecture
- **WHEN** a contributor reads the architecture document linked from the README
- **THEN** they can follow ingestion from the paper through extraction, chunking, embedding, and vector storage
- **AND** they can follow queries through retrieval, prompt construction, generation, and streamed answers
- **AND** they can identify which features are deferred and that existing Docker/Qdrant setup is outside this change
