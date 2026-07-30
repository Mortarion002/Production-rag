# PROJECT_BRIEF.md

Source of truth for scope, architecture, and conventions of the **Advanced RAG Chatbot**. `CLAUDE.md` covers *how* to work in the repo; this covers *what the system is*. Update this when the architecture or scope genuinely changes — don't let it go stale, but don't duplicate `CLAUDE.md`'s command/workflow content here either.

## What this is

A corrective RAG (Retrieval-Augmented Generation) chatbot. Users upload documents (PDF/TXT/MD), and a LangGraph-orchestrated pipeline answers questions grounded in those documents — with relevance grading, hallucination checking, and query rewriting when retrieval is weak, rather than a plain "retrieve-then-generate" RAG.

## Architecture

### Backend (`backend/app/`)

**Graph pipeline** (`graph/`) — the core of the system:
- `state.py` — `GraphState` TypedDict: `question`, `generation`, `documents`, `run_web_search`, `retry_count`, `hallucination_feedback`, `steps`.
- `nodes.py` — node functions, each with its own `PromptTemplate`, each appending its own name to `steps` so the caller can see the real execution path:
  - `retrieve` — fetches context from Qdrant. On any retrieval error, sets `retrieval_error` instead of raising, so the graph can short-circuit gracefully rather than 500ing.
  - `handle_retrieval_error` — only runs if `retrieve` set `retrieval_error`; returns a fixed apology as `generation` (no LLM call, nothing to ground it in) straight to `END`. Exists so a Qdrant outage can't feed empty docs into the `grade_documents`/`rewrite_query` loop, which has no retry cap of its own.
  - `grade_documents` — evaluates document relevance (fast LLM).
  - `generate` — produces the answer (smart LLM); if `hallucination_feedback` is set (from a prior failed retry), it's injected into the prompt as a corrective note.
  - `rewrite_query` — rewrites the question when retrieval is weak (fast LLM).
  - `hallucination_check` — verifies the answer is grounded in retrieved docs and addresses the question. Owns the retry-cap decision: while retries remain, it sets `hallucination_feedback` and clears `generation` to loop back to `generate`; once `retry_count` hits `MAX_RETRIES` (3), it returns a fallback message as `generation` instead of looping forever or leaving the answer `None`.
- `graph.py` — wires nodes into a `StateGraph`:
  `retrieve → (handle_retrieval_error → END | grade_documents) → (rewrite_query loop | generate) → hallucination_check → (loop to generate | END)`. The conditional edge after `hallucination_check` is a simple `generation is None → loop, else → END`, since the node itself guarantees `generation` is never left `None` once retries are exhausted.

Two-tier LLM strategy: a fast/cheap model for grading and rewriting, a smarter model for generation. Both default to `gpt-4o-mini` (configurable via `LLM_MODEL_FAST` / `LLM_MODEL_SMART`).

**API** (`server.py`):
- `GET /` — health check.
- `POST /auth/token` — login, returns JWT.
- `POST /chat` — JWT-protected, invokes the graph, returns an answer.
- `POST /ingest` — admin-only, ingest raw text.
- `POST /ingest/file` — admin-only, upload + ingest a file.

**Auth** (`auth/`) — JWT-based, two roles: `USER` and `ADMIN`. Admin role gates ingestion endpoints.

**Ingestion** (`services/ingestion.py`) — bootstraps the Qdrant client/collection, chunks documents with `RecursiveCharacterTextSplitter`, exposes `ingest_text`, `ingest_file`, `get_retriever`.

**Storage**: Qdrant for vectors, PostgreSQL (via SQLAlchemy/asyncpg) for user accounts/roles.

### Frontend (`frontend/app/`)

Flat App Router routes: `/` (landing), `/login`, `/signup`, `/dashboard`, `/chat`, `/admin`. `middleware.ts` enforces JWT-based auth and role gating on protected routes. `context/auth-context.tsx` holds client-side auth state; `lib/axios.ts` is the API client.

### Infra

`docker-compose.yml` at repo root runs **only** Qdrant + Postgres — the FastAPI and Next.js apps run natively (Poetry / npm), not containerized.

## Conventions

- Node functions in `graph/nodes.py` stay single-purpose; all control flow (which node runs next, retry logic) lives in `graph.py`'s conditional edges — never inside a node function.
- Config lives in `backend/app/config.py` as a single `Settings` class reading from `.env` via `os.getenv`. Env var names in `.env`/README examples must match the exact case used in the corresponding `os.getenv(...)` call.
- `config.py` prints a startup warning if `SECRET_KEY` or `POSTGRES_PASSWORD` are still their hardcoded dev defaults — don't remove this without another way of flagging unset secrets before a real deployment.
- `CORS_ORIGINS` (comma-separated) controls allowed frontend origins for `server.py`'s `CORSMiddleware`; defaults to `http://localhost:3000`.
- Frontend auth state flows through `middleware.ts` (route-level gating) + `context/auth-context.tsx` (component-level state) — new protected pages need both a middleware rule and to consume the auth context.
- Sample/fixture documents for manual ingestion testing (e.g. `test_doc.txt`) belong outside version control or clearly marked as fixtures — not loose at repo root as committed files.

## Known limitations (current state, not yet fixed)

These aren't roadmap items — they're honest gaps in what exists today. See `PLAN.md` for the active cleanup checklist.

- No streaming — `/chat` uses a synchronous `graph_app.invoke()`.
- No automated tests.
- No CI pipeline.
