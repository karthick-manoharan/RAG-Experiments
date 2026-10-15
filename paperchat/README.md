# PaperChat

A research-paper reading companion. The responsive web app streams answers
about “Attention Is All You Need” and displays retrieved source references. A standalone Python CLI indexes and searches paper PDFs;
a streaming API generates answers grounded in retrieved passages.

## Repository layout

```text
apps/
  web/               # Next.js; package.json and package-lock.json
  api/               # FastAPI; pyproject.toml and uv.lock
docs/architecture.md # Implemented foundation and planned RAG flows
openspec/            # Change planning and specifications
```

Each application installs and runs from its own directory. Use one terminal for
the frontend at port 3000 and a second for the backend at port 8000. No root
package manager or shared environment is needed. The commands below start from
the repository root unless stated otherwise.

## Frontend

Prerequisites: Node.js 20.9 or newer (Node 22 LTS recommended) and npm 10 or newer.

From the repository root:

```sh
cd apps/web
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend starts independently and requires no credentials. Chat calls FastAPI
directly; real answers require the backend chat configuration and indexed paper
described below. Optionally run `cp .env.example .env.local` to set
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). Public values are
inlined at build time; rebuild after changing them. Never store secrets in
`NEXT_PUBLIC_*` values, which are exposed to the browser.

Run checks from `apps/web`:

```sh
npm test
npm run lint
npm run typecheck
npm run build
```

Typecheck generates route types before running TypeScript, so it works before a
production build. To serve the production build locally, stop the development
server and run:

```sh
npm run start
```

Production also uses port 3000. Run `npm run build` before `npm run start`.

## Backend

Prerequisites: Python 3.12 and uv 0.5.9 or newer. The project's Python requirement
is `>=3.12,<3.13`; `.python-version` selects 3.12. uv can install the interpreter
if it is missing.

In a separate terminal, from the repository root:

```sh
cd apps/api
uv sync --frozen
uv run uvicorn app.main:app --reload --port 8000
```

The API runs independently of the frontend. No environment file, Docker, Qdrant,
or provider credentials are required. Optionally run `cp .env.example .env` to
set `APP_NAME`. The API reads only `apps/api/.env`, regardless of the current
directory; process environment values take precedence. The repository's root
`.env` is not loaded.

Verify [http://localhost:8000/health](http://localhost:8000/health):

```sh
curl http://localhost:8000/health
```

Expected response: `{"status":"ok"}`. Health reports process availability;
it does not check chat or external service readiness.

Run checks from `apps/api`:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

To run without development reload, stop the development server and run:

```sh
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

A future hosting service will supply its own bind port.

## Paper ingestion and CLI search

The CLI runs independently of FastAPI and the frontend, using the backend's
Python 3.12/uv environment. It extracts page text with PyMuPDF, splits each page
with LangChain RecursiveCharacterTextSplitter (1000 characters, target overlap
200), and stores dense embeddings through QdrantVectorStore. No answer is generated.

### Configure embeddings and Qdrant

From the repository root, install dependencies and create an app-local environment
file if one does not already exist:

```sh
cd apps/api
uv sync --frozen
cp -n .env.example .env
```

Edit `apps/api/.env` with the following settings. Put your OpenRouter API key in
`OPENROUTER_API_KEY`; never commit it. The same key is shared by embeddings and chat; model settings remain separate.

```dotenv
EMBEDDINGS_PROVIDER=openrouter
EMBEDDINGS_MODEL=openai/text-embedding-3-small
OPENROUTER_API_KEY=
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=paperchat-papers
```

Only `openrouter` is currently supported. The CLI uses OpenRouter's supported
[/api/v1/embeddings endpoint](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings)
through the OpenAI-compatible LangChain integration. It passes the model, key,
endpoint, and text inputs explicitly; chat settings and `OPENAI_BASE_URL` do not
override them. Vector dimensions are measured from actual API output, rather
than assumed from the model name.

The CLI reads only `apps/api/.env`, with process environment taking precedence.
The root `.env` is not automatically loaded: move the relevant Qdrant settings
to `apps/api/.env` or export them in your shell if they currently live at the root.
FastAPI startup and `/health` still need no provider or Qdrant credentials.

If local Qdrant is already running, reuse it. Otherwise, from the repository root:

```sh
docker run -d --name paperchat-qdrant \
  -p 127.0.0.1:6333:6333 -p 127.0.0.1:6334:6334 \
  -v paperchat-qdrant-data:/qdrant/storage qdrant/qdrant
```

The named volume preserves data across container restarts. Start an existing
stopped container with `docker start paperchat-qdrant`. Open the local
[Qdrant dashboard](http://localhost:6333/dashboard).
See the [Qdrant quickstart](https://qdrant.tech/documentation/quickstart/) for setup.

For Qdrant Cloud, change only `QDRANT_URL` to your cluster HTTPS URL (typically
with port 6333), `QDRANT_API_KEY` to a key with collection read/write permissions,
and optionally `QDRANT_COLLECTION`. The commands below are identical. Use the
cluster dashboard from the Qdrant Cloud console to inspect its points.

### Acquire and ingest the paper

From the repository root, download “Attention Is All You Need” locally:

```sh
mkdir -p data
curl -fL https://arxiv.org/pdf/1706.03762 -o data/attention-is-all-you-need.pdf
```

PDFs and dotenv files are ignored. Do not add paper files or credentials to source
control. Ingest with one command from `apps/api`:

```sh
uv run python -m app.ingestion ingest ../../data/attention-is-all-you-need.pdf
```

The command creates an absent cosine collection and prints its name, document ID,
source, and number of chunks after acknowledged writes. Each payload stores text
under `page_content` and provenance under `metadata`: `document_id` (SHA-256 of
PDF bytes), `source` (filename), `page` (one-based original page), and
`chunk_index` (zero-based within that page). Blank pages are skipped; no chunk
crosses page boundaries. PDFs without extractable text fail; OCR is not included.

Collection schema stores a named dense vector derived from the provider/model/
endpoint/dimension identity. Unknown or incompatible schemas fail without
modification, including different models with equal dimensions. Choose a fresh
collection name or deliberately rebuild:

```sh
uv run python -m app.ingestion ingest ../../data/attention-is-all-you-need.pdf --recreate
```

`--recreate` deletes **all points in the configured collection**, including other
documents, and reports the target before deletion. PDF and embedding preflight
must succeed first. A later remote failure can still leave a rebuilt collection
empty or partially populated; this operation is not transactional.

Ordinary ingestion uses deterministic UUID point IDs and upserts. Repeating the
same PDF/configuration preserves the point count, including retries after partial
writes. Moving or renaming the same bytes does not duplicate points; source
metadata updates to the latest filename. Changed bytes or chunking versions can
add new points and retain old versions. Use a fresh collection or `--recreate`
for a clean replacement. Reruns recompute embeddings and incur API usage.

### Search and verify

From `apps/api`:

```sh
uv run python -m app.ingestion search "multi-head attention"
```

Search returns the top five chunks (or fewer for a small collection), with full
text, source, page, chunk index, document ID, and descending raw cosine similarity
scores. Higher scores indicate closer matches; they are not probabilities.
An empty compatible collection reports no results. Search never creates or
rebuilds data and must use the same embeddings settings as ingestion.

For acceptance verification:

1. In the dashboard, open `QDRANT_COLLECTION` and confirm a positive point count;
   inspect payloads for source and page metadata.
2. Run the ingest command again and confirm the exact point count is unchanged.
3. Run the attention query and inspect passages describing multiple attention
   heads, such as the paper's multi-head attention section. Confirm page/source
   metadata accompanies each result.
4. Repeat with cloud URL/key configuration to verify the same commands work there.

CLI failures return nonzero with corrective hints: check the PDF path/permissions,
`OPENROUTER_API_KEY` and model/quota for embedding failures, or Qdrant URL/key,
network access, and collection permissions for Qdrant failures. Missing collections
require ingestion first; incompatible ones require matching settings or an explicit
rebuild. Diagnostics avoid dumping credential-bearing remote exceptions. After
partial ingestion, rerun without `--recreate` to retry safely.

Automated tests mock external embeddings and Qdrant, generate PDF fixtures at
runtime, and cover metadata, repeatability, compatibility, recreation, CLI output,
and failures. No live services or credentials are needed:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Planned architecture and hosting

See [the architecture document](docs/architecture.md) for ingestion, retrieval,
generation, and streaming behavior. Frontend rendering and API health require no
external services; ingestion/search and grounded chat require embeddings and Qdrant,
and chat generation additionally requires a configured OpenRouter model. Future Vercel hosting
will use `apps/web` as its app root; Render will
use `apps/api`. Deployment configuration and CI are deferred.

## Streaming chat configuration

Chat uses the same `OPENROUTER_API_KEY` as embeddings. Set these additional
fields in `apps/api/.env`; exported environment values take precedence and the
root dotenv is never loaded. Chat configuration is validated on requests, so
startup, health, and ingestion work without a chat model.

| Variable | Default | Allowed values |
| --- | --- | --- |
| `OPENROUTER_MODEL` | Required | Nonblank OpenRouter chat model ID |
| `OPENROUTER_TEMPERATURE` | 0 | Finite number from 0 to 2 |
| `OPENROUTER_MAX_TOKENS` | 1024 | Integer from 1 to 32768 |
| `OPENROUTER_TIMEOUT_SECONDS` | 60 | Finite seconds greater than 0, at most 600 |
| `RAG_RETRIEVAL_TIMEOUT_SECONDS` | 60 | Finite seconds greater than 0, at most 600 |

The generation timeout bounds both the network request and total generation;
retrieval has a separate caller deadline. No chat model is selected by default.
The official `langchain-openrouter` 0.2.9 integration adds only its OpenRouter SDK
and JSONPath dependency to the existing lock; existing locked versions remain.

### Retrieval and sources

First ingest and CLI-search “Attention Is All You Need” using the commands above.
The configured `QDRANT_COLLECTION` must contain that paper with the same embedding
identity, dimensions, and cosine schema. Choose an existing paper-specific
collection if your other collection contains unrelated papers. Chat does not
filter by guessed title, create collections, write points, or rebuild data.
It calls the existing read-only `app.ingestion.store.search`, retaining its top
five results in descending similarity order and its schema validation.

The first SSE payload is `{"sources": [...]}`. Each source has `id` (stored
Qdrant `_id`, or the deterministic Phase 02 chunk ID), `document_id` (PDF byte
hash), `source` (basename), `page` (original one-based page), `chunk_index`
(zero-based within the page), and `snippet` (up to 500 characters of actual text).
Missing metadata stays JSON null, including missing pages. When metadata cannot
support a deterministic ID, `S1`, `S2`, etc. are request-local prompt references,
not stored point IDs. The model receives full passages, not just snippets.

Search runs off the event loop. At most four retrieval workers are admitted;
timed-out or disconnected requests keep their slot occupied until their worker
finishes. Cancellation cannot interrupt an already running synchronous embedding
or Qdrant call. Existing 30-second network timeouts and embedding retries still
bound that residual work; cancelled retrieval never starts generation.

### Grounding and generation

LangChain composes a `ChatPromptTemplate` with the official `ChatOpenRouter`
model and uses native async streaming with retries disabled. The system prompt
restricts answers to retrieved evidence, treats passage instructions as untrusted,
and allows only supplied source IDs and known pages as references. No key enters
the prompt. Text deltas are forwarded in provider order; reasoning, tool calls,
and metadata are excluded.

Empty retrieval deterministically returns:
`I don't have enough information in the retrieved document context to answer that question.`
It makes no model call. With nonempty but irrelevant passages, the model is
instructed to acknowledge insufficient context; prompts and offline mocks cannot
guarantee real model adherence. No similarity cutoff is used to guess relevance.
Try a supported question such as “How does multi-head attention work?” and an
unsupported one such as “What was the weather in Paris yesterday?” after ingestion.
Inspect actual answers and source references during operator verification.

### Run and verify the stream

After configuring the app-local dotenv, ingesting the paper, and checking CLI
search, start the API from `apps/api`:

```sh
uv sync --frozen
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal, ask a supported question (provider usage may incur charges):

```sh
curl -N http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"question":"How does multi-head attention work?"}'
```

SSE frames use `event: <name>`, followed by `data: <JSON>` and a blank line.
A successful response has sources, incremental tokens, and exactly one done.
For example (source identifiers and text depend on retrieval):

```text
event: sources
data: {"sources": [{"id": "actual-point-id", "document_id": "actual-document-hash", "source": "attention-is-all-you-need.pdf", "page": 3, "chunk_index": 0, "snippet": "Actual passage excerpt..."}]}

event: token
data: {"text": "Multi-head attention"}

event: token
data: {"text": " uses..."}

event: done
data: {}

```

Try an unsupported question and confirm an insufficient-context answer:

```sh
curl -N http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"question":"What was the weather in Paris yesterday?"}'
```

With empty retrieval, sources is `{"sources": []}`, one token contains the
fallback text above, then done. With nonempty irrelevant passages, inspect model
adherence manually. The API does not buffer the full answer. Headers include
`Cache-Control: no-cache` and `X-Accel-Buffering: no`; deployment proxies may still
need separate operator configuration.

Invalid questions return safe JSON HTTP 422 before retrieval or generation:

```sh
curl -i -N http://localhost:8000/api/v1/chat/stream \
  -H 'Content-Type: application/json' -d '{"question":"   "}'
```

Missing, non-string, blank, malformed, and over-4000-character questions are
rejected; length is checked before trimming. The body does not echo the question:
`{"detail":{"code":"invalid_question","message":"Provide a nonblank string of at most 4000 characters."}}`.

Before streaming, invalid/missing configuration or a missing/incompatible index
returns HTTP 503; external dependencies or model construction failures return
502; a caller deadline returns 504. All use `{"detail":{"code":"...","message":"..."}}`
with allowlisted messages. To verify a configuration failure in a separate test
process, set a blank model without changing the dotenv:

```sh
OPENROUTER_MODEL='' uv run uvicorn app.main:app --port 8001
# In another terminal:
curl -i -N http://localhost:8001/api/v1/chat/stream \
  -H 'Content-Type: application/json' -d '{"question":"How does attention work?"}'
```

That request returns 503 `configuration_unavailable`; health remains available.
After sources is sent, provider failures use a terminal SSE error even if the
first provider read fails. A partial answer followed by error is incomplete:

```text
event: error
data: {"code": "generation_failed", "message": "Unable to generate an answer. Please try again."}

```

Other late codes are `generation_timeout` and `stream_failed`; no done follows
an error. Disconnect cancels pending generation and closes request-owned streams
and HTTP clients without sending a terminal event. Safe logs record correlation,
stage, elapsed time, retrieval/delta counts, first-token time, and outcome; they
omit questions, passages, keys, prompts, and raw exceptions.

Automated verification is offline: mocks cover configuration, read-only retrieval,
SSE ordering/framing, provider failure, total deadlines, and direct ASGI delivery
before completion/disconnect cleanup. These checks make no paid calls. The live
curl commands above are optional operator checks of provider behavior and grounding.

## Browser chat verification

Start the frontend with `cd apps/web && npm ci && npm run dev` and the API in
a separate terminal with `cd apps/api && uv sync --frozen && uv run uvicorn app.main:app --reload --port 8000`.
Use http://localhost:3000: CORS explicitly allows this origin, POST and Content-Type,
without credentials. Other frontend origins require a deliberate allowlist change;
there is no wildcard production access and no Next.js API proxy.

1. Configure backend chat/embedding settings, ingest the paper, and verify CLI search
   using the existing instructions. Health alone does not establish RAG readiness.
2. Open the chat and select an example or type a question. Enter sends; Shift+Enter
   inserts a newline. Observe Loading, Generating, and Completed, with text arriving
   before completion. Expand retrieved sources to inspect supplied IDs and snippets.
   Pages are actual one-based backend metadata; missing pages stay unknown.
3. Ask another question and confirm both exchanges remain. Network request bodies
   contain only the current question, never previous history. Reload clears history.
4. Stop generating while loading and during generation. The request is aborted and
   any partial text remains marked incomplete. An already running synchronous
   retrieval call may finish under backend timeouts, but cancelled retrieval never
   starts generation. Submit another question after cancellation.
5. Scroll upward during streaming; the page should let you read previous answers.
   Return to the bottom to resume following. Test at desktop and mobile widths.
6. Stop the API to see a connection error; restart it and retry the original question.
   Missing backend configuration produces a readable service error. Late SSE errors
   retain partial text with Failed status. Duplicate submissions are blocked.

Automated frontend tests use controlled streams for parsing, incremental rendering,
HTTP/SSE errors, cancellation, retry, keyboard and scroll behavior. Backend checks
include explicit CORS preflight, successful streams, errors, and rejected origins.
Live retrieval/provider verification requires configured services and may incur usage.
