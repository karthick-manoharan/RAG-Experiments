# Spec Delta

## Purpose

Let operators verify an indexed paper through a standalone text-query command that returns relevant passages, provenance, and dense similarity scores.

## ADDED Requirements

### Requirement: Top-five scored passage search
The search CLI SHALL accept a nonblank text query and return the five most similar chunks, or all available chunks when fewer than five exist, ordered by descending cosine similarity. Each result MUST include chunk text, raw similarity score, document ID, source filename, page number, and chunk index. Scores MUST be identified as cosine similarity with higher values indicating closer matches.

#### Scenario: Verify attention passages
- **WHEN** the documented search command queries `multi-head attention` after the paper has been indexed
- **THEN** up to five scored passages are returned with source and page metadata, including relevant paper passages verified by operator inspection

#### Scenario: Small or empty collection
- **WHEN** the compatible collection contains fewer than five chunks
- **THEN** search prints only the available results, and an empty collection yields a clear no-results message

### Requirement: Compatible non-mutating retrieval
Search MUST use the configured embeddings provider and model and reject incompatible or unverifiable collections before retrieval. Search SHALL NOT create, delete, or write collections or points and SHALL NOT generate LLM answers.

#### Scenario: Existing compatible collection
- **WHEN** search uses the same embedding identity and vector dimensions as ingestion
- **THEN** it queries the configured collection and leaves stored data unchanged

#### Scenario: Same dimensions but different model
- **WHEN** the query model differs from the indexed model despite equal vector dimensions
- **THEN** search fails with a compatibility hint instead of returning misleading matches

### Requirement: Actionable search failures
Blank queries, missing collections, invalid configuration or credentials, embedding failures, and Qdrant connection failures SHALL produce nonzero exit codes and concise corrective diagnostics without leaking secrets.

#### Scenario: Blank query
- **WHEN** an operator supplies an empty or whitespace-only query
- **THEN** search rejects it before contacting external services

#### Scenario: Collection absent
- **WHEN** the configured collection does not exist
- **THEN** search reports its name and instructs the operator to ingest first without creating a collection

#### Scenario: Service failure
- **WHEN** a query embedding or Qdrant request fails
- **THEN** search identifies the service and corrective action, exits nonzero, and exposes no credentials

### Requirement: Search tests without services
Automated tests SHALL verify query validation, a five-result limit, descending scores, metadata output, collection compatibility, and failure diagnostics using mocked external services.

#### Scenario: Offline search tests
- **WHEN** search tests run without a live Qdrant instance or API credentials
- **THEN** mocked embeddings and retrieval results exercise the CLI contract without network requests
