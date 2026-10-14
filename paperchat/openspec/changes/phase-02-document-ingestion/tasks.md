# Tasks

## 1. CLI environment and configuration

- [x] 1.1 Add PyMuPDF, langchain-core, langchain-text-splitters, langchain-qdrant, langchain-openai, and qdrant-client to `apps/api/pyproject.toml` and resolve `uv.lock`; verify Python 3.12 installation with `uv sync --frozen` and integration imports.
- [x] 1.2 Add isolated `app/ingestion` package, module entry point, argparse ingest/search subcommands, and ingestion-only settings; verify CLI help and tests for app-local dotenv, environment precedence, defaults, unsupported provider, blank query, and missing credentials without importing service clients into FastAPI startup.
- [x] 1.3 Implement the supported OpenRouter embeddings factory with explicit dedicated credentials, model selection, explicit embeddings endpoint, bounded requests, and redacted diagnostics; verify mocked configuration/authentication tests and that chat/OpenAI environment values cannot redirect embedding requests.
- [x] 1.4 Extend `apps/api/.env.example` and README with provider/model/key, Qdrant URL/key/collection, app-local loading, and local/cloud configuration; verify placeholders contain no secrets and align with settings tests.

## 2. Page extraction and deterministic chunks

- [x] 2.1 Implement PyMuPDF page extraction and independent RecursiveCharacterTextSplitter chunking at 1000/200; verify tests for multiple pages, blank pages, character limits/overlap, and one-based page plus zero-based page-local chunk metadata.
- [x] 2.2 Implement byte-hash document identity and UUIDv5 point IDs with versioned chunking parameters and text hash; verify stable IDs across retries/relocation, distinct IDs for repeated text on different pages, and distinct identities for changed PDFs.
- [x] 2.3 Add missing/unreadable/corrupt/no-text PDF diagnostics before remote writes; verify CLI failure tests assert nonzero status and no Qdrant mutations.
- [x] 2.4 Add PDF and local Qdrant storage ignore rules and document paper acquisition/path/metadata conventions; verify tests generate any PDF fixtures at runtime and no PDF or secret is introduced into tracked source artifacts.

## 3. Safe dense Qdrant ingestion

- [x] 3.1 Implement real-vector dimension preflight, embedding identity-derived named cosine vectors, and collection schema checks; verify mocked tests for measured dimensions, empty/nonfinite/inconsistent embeddings, wrong distance, wrong size, same-size different models, and unknown schemas.
- [x] 3.2 Connect local/cloud QdrantClient settings and QdrantVectorStore dense storage with explicit IDs and bounded batches; verify stateful mocked upserts preserve point count on identical reruns and recover partial ingestion without duplicates.
- [x] 3.3 Implement absent-collection creation and explicit collection-wide `--recreate` after successful input/embedding preflight; verify delete/create ordering, reported target/scope, no deletion on preflight failure, and no destructive calls on default ingestion or incompatibility.
- [x] 3.4 Implement safe service-specific connection/authentication/embedding/write diagnostics and success summaries only after acknowledged writes; verify mocked failures hide secrets, return nonzero, and report partial completion with retry guidance.
- [x] 3.5 Document local Docker startup/persistence/dashboard, the single ingest command, repeat-run point-count inspection, embedding costs, changed-document behavior, and recreation limitations; verify examples match the CLI help and environment variables.

## 4. Scored CLI retrieval

- [x] 4.1 Implement compatible existing-collection search using QdrantVectorStore `similarity_search_with_score` with `k=5`; verify mocked tests assert provider/model compatibility, missing-collection guidance, and zero lifecycle or point writes.
- [x] 4.2 Format descending raw cosine scores, full text, document ID, source, page, and chunk index; verify captured output tests for five results, fewer results, empty collections, and required provenance fields.
- [x] 4.3 Handle query embedding and Qdrant search/authentication failures with redacted actionable messages; verify mocked CLI failure tests and rejection of `--recreate` on search.
- [x] 4.4 Document `uv run python -m app.ingestion search "multi-head attention"`, score semantics, no-results behavior, and corrective hints; update `docs/architecture.md` to mark CLI ingestion/search as implemented while application RAG remains deferred, and verify commands against CLI help.

## 5. Integration acceptance

- [x] 5.1 Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` from `apps/api`; verify all checks pass without live service credentials, including Phase 01 health/settings regressions.
- [x] 5.2 With an operator-provided embeddings key and local Qdrant, follow README to ingest the uncommitted paper, inspect a populated dashboard collection, rerun and confirm unchanged point count, then inspect relevant `multi-head attention` results with source/page/scores; record command results and counts, or explicitly leave this check incomplete if prerequisites are unavailable.
- [x] 5.3 With an operator-provided Qdrant Cloud endpoint/key, repeat the documented ingest/search commands using environment-only changes; verify populated cloud collection and returned metadata, or explicitly leave this check incomplete if cloud access is unavailable.
