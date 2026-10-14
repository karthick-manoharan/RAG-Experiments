# Design

## Context

See proposal.md for motivation. The repository has a Python 3.12 FastAPI app under `apps/api`, managed with uv, pytest, Ruff, and Pydantic Settings. `app/settings.py` deliberately loads only `apps/api/.env` with process environment precedence; root `.env` is ignored. `/health` needs no external services. `docs/architecture.md` plans LangChain and Qdrant but leaves embeddings undecided. There are no main specs; the completed Phase 01 change has not been archived.

## Goals / Non-Goals

**Goals:** Keep the CLI independently executable, preserve page provenance, make retries idempotent, and make collection compatibility and destruction explicit.

**Non-Goals:** Service startup must not require ingestion credentials. There is no API/UI integration, chat model initialization, automatic document replacement, OCR, embedding cache, transaction framework, or Qdrant deployment management.

## Decisions

### 1. Reuse the Python environment with an isolated module

Add `app/ingestion/` with settings, extraction/chunking, embeddings factory, vector-store operations, CLI, and `__main__.py`. Use standard-library argparse. Proposed commands, from `apps/api`:

```sh
uv run python -m app.ingestion ingest ../../data/attention-is-all-you-need.pdf
uv run python -m app.ingestion ingest ../../data/attention-is-all-you-need.pdf --recreate
uv run python -m app.ingestion search "multi-head attention"
```

Resolve input paths relative to the caller's directory; resolve dotenv relative to `apps/api` as Phase 01 does. Instantiate ingestion settings and service clients only in CLI execution. A separate project would duplicate packaging and checks; FastAPI endpoints would exceed scope. Thin composable functions and injected clients suffice instead of orchestration frameworks.

### 2. Separate embeddings settings and a small provider factory

Use `EMBEDDINGS_PROVIDER=openrouter`, `EMBEDDINGS_MODEL=openai/text-embedding-3-small`, and a dedicated `OPENROUTER_API_KEY` containing an OpenRouter key, per the operator's provider selection during apply. Use `langchain_openai.OpenAIEmbeddings` against `https://openrouter.ai/api/v1/embeddings`. OpenRouter documents this supported API and model in its [embeddings API reference](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings). Initially support only this provider; reject unknown values with a supported-provider hint. Provider dispatch is the extension point; implementing additional APIs is unnecessary for this phase. Pass explicit endpoint/key and float encoding; disable OpenAI token-array preprocessing so text strings reach the OpenRouter endpoint. Model choice is configurable. Embeddings settings do not fall back to chat credentials, chat models, or chat endpoints; future chat generation remains separately configured.

Use `QDRANT_URL=http://localhost:6333`, optional `QDRANT_API_KEY`, and `QDRANT_COLLECTION=paperchat-papers`. Cloud uses an HTTPS URL and its API key. Store secret fields as secrets, avoid raw SDK exception dumps, and set bounded service timeouts/retries. Existing FastAPI settings remain independent.

### 3. Deterministic page documents and point IDs

Use PyMuPDF to open the PDF and `page.get_text("text")` for each page. Split nonblank page text independently with `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` using stable default separators and character length. Preserve one-based original page numbers and zero-based page-local indices in LangChain Documents. Skip blank pages; reject a document with no extracted chunks. No OCR is attempted.

Use SHA-256 of PDF bytes as `document_id`, source basename as `source`, and deterministic UUIDv5 point IDs from a fixed namespace and document ID, extraction/chunking version, page, chunk index, and chunk-text hash. IDs exclude the absolute path and source basename, so relocation does not duplicate the paper; source metadata reflects the latest ingestion. Record chunking version and embeddings identity as additional metadata. Chunking version includes parameters and changes whenever extraction/splitting semantics change. Content hashes alone would collapse identical passages from distinct pages; random IDs would duplicate retries.

Changed bytes create a new document; changed chunking versions can add new points. Never remove stale versions automatically. Document that a fresh collection or `--recreate` is required for a clean replacement.

### 4. Explicit collection schema and embedding identity

Use `QdrantClient` for lifecycle/schema checks and `QdrantVectorStore` with dense retrieval for document storage and search. Before any deletion or creation, validate input, extract/split, instantiate embeddings, and obtain a real embedding to determine vector length; reject empty/nonfinite vectors and inconsistent batch dimensions.

Create a named dense vector using `VectorParams(size=measured_dimension, distance=Distance.COSINE)`. Derive its stable name as `dense_<sha256(canonical_embedding_identity)>`; identity includes provider, model, embeddings API endpoint identity, measured dimensions, and an identity-format version, excluding credentials. Pass this vector name explicitly to QdrantVectorStore. Validate vector name, dimension, and distance against collection schema before writes or search. This persists identity even for empty collections and distinguishes models with equal dimensions without sentinel points or a sidecar database. Unknown/unnamed existing schemas are rejected, never adopted silently. A dimension-only check cannot ensure compatible embedding spaces.

For ordinary ingestion, create only if absent and attach to an existing compatible collection otherwise. Upsert through `add_documents` with explicit UUID IDs in bounded batches and acknowledge all writes before reporting success. Reuse the preflight vector when practical; no persistent cache is needed. Failures can leave partially upserted points, so report partial completion and explain rerunning is safe.

Only `ingest --recreate` deletes the target collection. Print its name, sanitized destination, and collection-wide destruction scope before deletion. Preflight limits avoidable destruction but subsequent remote failures cannot be atomic; document this explicitly. Do not add a second interactive approval: the flag is the operator's explicit authorization.

### 5. Search uses existing schema and raw scores

Validate a nonblank query, resolve the same embeddings identity/dimensions, verify the existing collection, and call `QdrantVectorStore.similarity_search_with_score(query, k=5)`. Print numbered results with full text, source, page, document ID, chunk index, and labeled raw cosine similarity scores, ordered highest first. Do not present scores as probabilities. An empty compatible collection reports no results and exits successfully; a missing collection fails with an ingest hint. Search has no collection lifecycle write path and no `--recreate` flag.

The selected integration APIs are documented in [QdrantVectorStore reference](https://reference.langchain.com/python/langchain-qdrant/qdrant/QdrantVectorStore) and [OpenAIEmbeddings reference](https://reference.langchain.com/python/langchain-openai/embeddings/base/OpenAIEmbeddings). Resolve compatible package versions into `uv.lock` during implementation instead of guessing versions in this plan.

### 6. Verification and operator documentation

Add pytest tests with mocked embeddings/Qdrant, fake page readers, and optionally tiny PDFs generated at test time. Exercise metadata, blank pages, splitter boundaries, deterministic UUIDs, repeated upsert behavior, partial retry, dimension and identity mismatch, recreation sequencing, CLI output, and redacted failure diagnostics. No checked-in PDF fixtures or live credentials are needed. Retain Phase 01 health/settings tests and run Ruff plus pytest.

README adds a minimal local Docker command with persistent storage, dashboard URL, cloud configuration, app-local dotenv examples, paper acquisition URL, commands above, destructive flag scope, and point-count/search verification. Add `*.pdf` and local Qdrant storage ignore rules. Update architecture documentation to distinguish implemented CLI ingestion from deferred application RAG. A live paper walkthrough is manual acceptance, not an evaluation system; record unperformed checks if credentials or a service are unavailable.

## Risks / Trade-offs

- PDF layout can produce awkward text → Keep page provenance and inspect the attention passages; OCR and layout reconstruction remain outside scope.
- Embedding calls cost money and repeated upserts recompute embeddings → Document this; batching limits request size, while caching is deferred.
- Partial writes and post-deletion failures are not transactional → Report failures, preserve deterministic IDs, preflight recreation, and document collection-wide rebuild consequences.
- Provider model behavior can change behind an identifier → Persist configured identity and versions; require deliberate rebuilds when the operator changes the embedding space.
- Mock tests cannot prove remote relevance or real credentials → Document the live dashboard/count/query walkthrough separately.
- Named-vector identity prevents using arbitrary existing collections → Reject unknown schemas with clear fresh-collection/rebuild guidance to avoid mixing incompatible data.

## Migration Plan

Add and lock dependencies, implement the isolated CLI, run mocked checks, and update documentation. Acquire the paper locally without committing it; start local Qdrant or configure cloud, ingest, inspect collection count, repeat ingestion, and search the attention query. Existing API startup stays credential-free. Rollback removes CLI additions and dependencies; existing Qdrant data remains unless the operator explicitly removes it. Phase 01 archive/sync is separate work.
