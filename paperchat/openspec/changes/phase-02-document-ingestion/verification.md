# Verification

## Automated checks

From `apps/api`, all checks passed:

- `uv sync --frozen`: dependencies installed from the updated lockfile.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 16 files already formatted.
- `uv run pytest -q`: 56 passed. PyMuPDF emits upstream SWIG deprecation warnings.
- Module, ingest, and search help commands: passed.
- `openspec validate phase-02-document-ingestion --strict`: passed.

Tests include real LangChain/QdrantVectorStore integration against mocked service
boundaries, stateful mocked upserts/retries, and a mock HTTP transport verifying
the OpenRouter embeddings endpoint, text inputs, model, credential, and float
encoding. They require no live credentials.

## Paper and service preflight

Downloaded the requested paper from arXiv into the ignored `data/` directory.
PyMuPDF extraction produced 52 chunks spanning 15 pages. All chunks fit the
1000-character maximum, deterministic IDs are unique, and the literal phrase
“multi-head attention” appears in chunks from pages 2, 4, and 5.

Read-only checks against local Qdrant and the cloud destination configured in
the existing root dotenv both succeeded; both initially contained zero collections.
No credentials were printed and no remote collections were changed by these checks.

## Live ingestion and similarity search

The configured OpenRouter key successfully embedded the requested paper with
`openai/text-embedding-3-small`. Local Qdrant created `paperchat-papers` with 52
points and cosine vectors of measured dimension 1536. Repeating the documented
ingest command preserved the exact point count at 52.

Cloud verification used the existing root dotenv's Qdrant URL/key/collection
as process environment overrides for the same CLI commands; no code changes or
persistent configuration changes were needed. Cloud collection `rag-experiments`
contained 52 points before and after repeat ingestion.

Both destinations returned these five passages for `multi-head attention`:

| Rank | Page | Chunk index | Cosine similarity | Passage topic |
| --- | --- | --- | --- | --- |
| 1 | 5 | 0 | 0.615625 | Parallel heads and joint attention across representation subspaces |
| 2 | 4 | 0 | 0.586763 | Multi-head attention figure and scaled dot-product attention |
| 3 | 4 | 2 | 0.532071 | Section 3.2.2: learned projections and parallel attention functions |
| 4 | 5 | 1 | 0.514027 | Applications of multi-head attention in the Transformer |
| 5 | 2 | 3 | 0.503447 | Multi-head attention and self-attention motivation |

Every result included `source=attention-is-all-you-need.pdf`, the original page,
chunk index, document ID, full passage text, and raw similarity score. No
`--recreate` command or collection deletion was used during these checks.

## Dashboard inspection and operator confirmation

The operator confirmed that the local Qdrant dashboard displays `paperchat-papers`
with 52 points, then confirmed the repeat-ingestion and search checks. Combined
with the recorded API counts and live search results, tasks 5.2 and 5.3 are complete.
All 20 implementation and acceptance tasks are complete.

The CLI loads only app-local dotenv or process environment, as designed. The
existing root dotenv is not automatically used by ingestion/search. The provider
design/tasks reflect the user's selection of OpenRouter, and its credential is
named `OPENROUTER_API_KEY` per the user's requested rename.
