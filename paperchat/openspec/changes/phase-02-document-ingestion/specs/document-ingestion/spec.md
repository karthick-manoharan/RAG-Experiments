# Spec Delta

## Purpose

Enable operators to index a local research-paper PDF into a dense vector collection reproducibly, with traceable page metadata and explicit control over rebuilding stored data.

## ADDED Requirements

### Requirement: Page-aware extraction and chunk metadata
The ingestion CLI SHALL accept a local PDF path, extract text page by page, and split each nonempty page independently using an initial chunk size of 1000 characters and overlap of 200. Each chunk MUST retain `document_id`, `source`, `page`, and `chunk_index`; pages SHALL be one-based and chunk indices SHALL be zero-based within each page.

#### Scenario: Paper extraction
- **WHEN** an operator ingests a readable text PDF
- **THEN** chunks contain only text from their originating page and include the source basename, stable document ID, original page number, and page-local chunk index

#### Scenario: Empty pages
- **WHEN** a PDF contains blank pages
- **THEN** those pages produce no chunks and later page metadata retains the original page numbers

### Requirement: Independent embeddings configuration
The CLI MUST support an explicitly configured supported embeddings API provider and model with dedicated credentials independent of OpenRouter chat settings. Ingestion and search MUST use the same embedding configuration. Unsupported providers and missing required credentials SHALL fail clearly.

#### Scenario: Separate credentials
- **WHEN** valid embeddings credentials are configured and OpenRouter credentials are absent
- **THEN** ingestion can generate embeddings without chat configuration

#### Scenario: Unsupported provider
- **WHEN** an unsupported embeddings provider is selected
- **THEN** the CLI exits nonzero with a supported-provider configuration hint before storing points

### Requirement: Configurable Qdrant destination
The CLI SHALL configure Qdrant URL, optional API key, and collection name through environment variables. Local Docker and Qdrant Cloud MUST use the same ingestion and retrieval commands with only configuration changes.

#### Scenario: Switch destination
- **WHEN** the operator replaces a local URL with a cloud URL and API key
- **THEN** the same command indexes the configured cloud collection without code changes

### Requirement: Compatible cosine collections
Ingestion SHALL create absent collections with cosine similarity and dimensions measured from actual embeddings. Existing collections MUST match vector dimensions, cosine distance, and stored embedding identity before writes; incompatibility SHALL fail without deleting or modifying points.

#### Scenario: New collection
- **WHEN** a model returns vectors of dimension D and the collection is absent
- **THEN** ingestion creates a cosine collection of dimension D and stores the generated chunks

#### Scenario: Incompatible collection
- **WHEN** the collection has different dimensions, distance, model identity, or unverifiable embedding identity
- **THEN** ingestion exits nonzero with instructions to choose a compatible collection or explicitly rebuild

### Requirement: Repeatable non-destructive ingestion
The system SHALL generate deterministic valid point IDs and upsert chunks. Re-ingesting identical PDF bytes with the same extraction, chunking, and embedding configuration MUST preserve the point count, including after a partially failed run. Default ingestion MUST NOT delete existing data. Changed PDF bytes SHALL have a distinct document identity.

#### Scenario: Repeat ingestion
- **WHEN** the same paper is ingested twice into a compatible collection
- **THEN** the second run overwrites the same point IDs and creates no duplicate chunks

#### Scenario: Retry partial write
- **WHEN** a write fails after some batches and the operator reruns ingestion
- **THEN** successfully written chunks retain their IDs and missing batches can complete without duplicates

#### Scenario: Changed document
- **WHEN** PDF bytes change
- **THEN** ingestion treats the PDF as a new document and retains earlier points unless explicitly rebuilding

### Requirement: Explicit collection recreation
Only ingestion with `--recreate` SHALL delete and rebuild the configured collection. The CLI MUST identify the target and collection-wide deletion scope. Input extraction and embedding preflight MUST succeed before deletion; search MUST never recreate collections.

#### Scenario: Authorized rebuild
- **WHEN** a valid ingestion command includes `--recreate` and preflight succeeds
- **THEN** the CLI reports that all points in the named collection will be removed and rebuilds it with the configured embedding schema

#### Scenario: Failed preflight
- **WHEN** `--recreate` is supplied with a missing PDF or invalid embeddings credentials
- **THEN** the command fails without deleting the existing collection

### Requirement: Actionable ingestion failures
Missing or unreadable PDFs, PDFs without extractable text, invalid credentials, embedding errors, and Qdrant connection or write failures MUST produce nonzero exit codes and actionable diagnostics without exposing secrets. Success SHALL only be reported after all writes complete, with document, collection, and chunk count.

#### Scenario: Missing PDF
- **WHEN** the specified file does not exist
- **THEN** the CLI reports the missing path and exits nonzero before remote writes

#### Scenario: Remote service failure
- **WHEN** embeddings or Qdrant rejects authentication or cannot complete a request
- **THEN** the CLI identifies the failing service, provides a corrective hint, redacts credentials, and does not report successful ingestion

### Requirement: Documented and testable operator workflow
The README SHALL document dependencies, separate credentials, local and cloud configuration, PDF acquisition without committing it, ingest/search commands, recreation scope, dashboard inspection, and repeat-run verification. Automated tests MUST mock external services and run without credentials or a live Qdrant instance. PDFs and secrets MUST be excluded from version control.

#### Scenario: Acceptance walkthrough
- **WHEN** an operator follows the documented paper ingestion command with valid configuration
- **THEN** the Qdrant dashboard shows a populated collection and a repeat run leaves its point count unchanged

#### Scenario: Offline automated checks
- **WHEN** automated tests run without external credentials or services
- **THEN** extraction, metadata, repeatability, compatibility, recreation, and failure behaviors are exercised with mocked external dependencies
