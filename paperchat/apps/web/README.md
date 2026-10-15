# PaperChat web

Run `npm ci` and `npm run dev` here, then open http://localhost:3000.
Optionally copy `.env.example` to `.env.local`. `NEXT_PUBLIC_API_BASE_URL`
defaults to `http://localhost:8000`; trailing slashes are normalized. Next.js
inlines public variables at build time, so rebuild after changing them.
Never put OpenRouter, embeddings, or Qdrant credentials in the web environment.

The frontend posts directly to FastAPI; start the API separately using the
[root README](../../README.md). Health needs no credentials; real answers require
the indexed paper and configured backend provider settings. Local CORS allows
exactly `http://localhost:3000`. A different frontend origin requires an explicit
backend allowlist change; changing the API URL does not change allowed origins.

Checks: `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`.
Tests use controlled offline streams and make no provider calls.

Enter sends a question, Shift+Enter inserts a newline. Stop generating aborts
an active request. Retry question adds a new attempt of a failed question.
History lasts until reload; each request sends only the current question.
