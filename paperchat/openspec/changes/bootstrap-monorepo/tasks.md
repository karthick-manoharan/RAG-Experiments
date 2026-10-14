# Tasks

## 1. Repository layout and safe configuration

- [x] 1.1 Create `apps/web` and `apps/api` as independent application roots, preserving existing OpenSpec, editor files, and root `.env`; verify the directory layout matches the design and no existing local files were overwritten.
- [x] 1.2 Add root ignore rules for environment files, dependencies, caches, build output, and editor artifacts, with `.env.example` and lockfile exceptions; verify representative root/nested paths using `git check-ignore --no-index` in an isolated temporary repository without initializing Git here.

## 2. Frontend foundation

- [x] 2.1 Initialize Next.js App Router with TypeScript, Tailwind CSS, ESLint, `src/`, and `@/*`, using npm and compatible dependency versions; record the Node requirement in `engines`, retain `apps/web/package-lock.json`, and verify `npm ci` succeeds from `apps/web` independently of the backend.
- [x] 2.2 Initialize shadcn/ui, add only Button and required generated support, and replace starter content with the static PaperChat foundation page using system fonts; verify in the browser at port 3000 that styles apply, the button receives keyboard focus, and there are no chat controls or backend calls.
- [x] 2.3 Configure `dev`, `lint`, `typecheck`, `build`, and `start` scripts, including generated route types if needed; verify `npm run lint`, `npm run typecheck` before any production build, and `npm run build` succeed, then confirm `npm run start` serves `/` on port 3000.
- [x] 2.4 Add the comment-only frontend `.env.example` and frontend sections of the root README covering Node/npm prerequisites, `npm ci`, optional environment setup, development/production commands, and checks; verify every documented command matches `package.json` and the shell runs without an environment file.

## 3. Backend foundation and tests

- [x] 3.1 Initialize the Python `app` package and uv project with Python `>=3.12,<3.13`, `.python-version`, FastAPI, Uvicorn, pydantic-settings, Ruff, pytest, and HTTPX; generate `uv.lock` and verify `uv sync --frozen` succeeds from `apps/api` without frontend dependencies.
- [x] 3.2 Add typed `APP_NAME` settings with a safe default, optional app-root `.env` loading, and process-environment precedence; use the setting as the FastAPI title and add isolated pytest coverage for defaults, dotenv loading, and environment overrides; verify those tests pass without reading the repository's root `.env`.
- [x] 3.3 Implement unauthenticated `GET /health` directly in `app/main.py` without external clients; add an in-process test asserting status 200, JSON content type, and exactly `{"status":"ok"}`, and verify it passes without infrastructure or credentials.
- [x] 3.4 Configure Ruff lint/format rules and pytest in `pyproject.toml`; verify `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` all succeed from `apps/api`.
- [x] 3.5 Add the backend `.env.example` and backend README sections covering Python 3.12/uv prerequisites, `uv sync --frozen`, optional environment setup, startup on port 8000, health verification, and quality commands; verify startup without `.env` and confirm the documented `curl` command returns the expected health response.

## 4. Architecture and repository documentation

- [x] 4.1 Add concise `docs/architecture.md` covering the planned ingestion and query flows, LangChain, Qdrant local/Cloud, OpenRouter, undecided embeddings, SSE, future Vercel/Render hosting, and later GitHub Actions; verify it clearly separates the implemented shell/health endpoint from deferred work and introduces no endpoint/event contracts or runtime integrations.
- [x] 4.2 Finish the root README with the repository layout, separate-terminal workflow, expected local URLs/ports, and architecture link; verify its relative links resolve and its hosting notes identify independent app roots without deployment configuration.

## 5. Integrated acceptance review

- [x] 5.1 Follow the complete README workflow with the app-local locked installations, run both apps concurrently on ports 3000/8000, and verify the static page and exact health response without provider credentials; confirm frontend lint/typecheck/build and backend Ruff/pytest checks pass, reusing successful checks unless subsequent changes require rerunning them.
- [x] 5.2 Review the resulting file tree, manifests, examples, and ignore behavior against the proposal exclusions; verify there is no ingestion/chat implementation, provider SDK, unused infrastructure, Docker Compose, CI/deployment configuration, hardcoded credential, or generated artifact intended for tracking, and that the existing root `.env` was preserved.
