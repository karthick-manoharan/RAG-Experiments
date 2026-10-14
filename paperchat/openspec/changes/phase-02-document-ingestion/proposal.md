# Proposal

## Why

Phase 01 provides a working Next.js and FastAPI foundation, but no paper can yet be indexed or retrieved. Phase 02 establishes a repeatable standalone ingestion and CLI verification path for “Attention Is All You Need” before application RAG integration.

## What Changes

- Extract page text with PyMuPDF and split each page with LangChain RecursiveCharacterTextSplitter (1000 characters, 200 overlap), preserving document, source, page, and chunk metadata.
- Add separately configured API embeddings and dense Qdrant storage through QdrantVectorStore, usable against local Docker or Qdrant Cloud.
- Create cosine collections using measured embedding dimensions, validate collection compatibility, and upsert deterministic point IDs without duplicates on repeat runs.
- Add explicit collection rebuilding with `--recreate`, actionable CLI failures, and top-five similarity search with metadata and scores.
- Add mocked service tests and README setup, ingestion, search, and manual verification instructions; exclude PDFs and secrets from version control.

## Capabilities

### New Capabilities

- `document-ingestion`: Page-aware extraction, chunking, embedding configuration, safe repeatable Qdrant indexing, and operator documentation.
- `cli-similarity-search`: Standalone dense similarity search with compatible query embeddings, scored passages, and CLI failure behavior.

### Modified Capabilities

None. No main specs exist yet; Phase 01 remains a completed, unarchived change.

## Impact

Add an independent `app.ingestion` Python module and tests in `apps/api`, using its existing Python 3.12/uv environment. Extend its manifest, lockfile, and example environment; update the root README, architecture document, and ignore rules. Add PyMuPDF, langchain-text-splitters, langchain-core, langchain-qdrant, langchain-openai, and qdrant-client; reuse argparse, Pydantic Settings, pytest, and Ruff. Qdrant and a separately authenticated embeddings API are external prerequisites for CLI operations only. No LlamaIndex, frontend changes, FastAPI RAG endpoints, answer generation, SSE, evaluation framework, agents, deployment, or new orchestration frameworks are included.
