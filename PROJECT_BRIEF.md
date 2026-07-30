# PROJECT_BRIEF.md

Source of truth for scope, architecture, and conventions of the **Advanced RAG Chatbot**. `CLAUDE.md` covers *how* to work in the repo; this covers *what the system is*. Update this when the architecture or scope genuinely changes — don't let it go stale, but don't duplicate `CLAUDE.md`'s command/workflow content here either.

## What this is

A corrective RAG (Retrieval-Augmented Generation) chatbot. Users upload documents (PDF/TXT/MD), and a LangGraph-orchestrated pipeline answers questions grounded in those documents — with relevance grading, hallucination checking, and query rewriting when retrieval is weak, rather than a plain "retrieve-then-generate" RAG.

## Architecture

### Backend (`backend/app/`)

**Graph pipeline** (`graph/`) — the core of the system:
- `state.py` — `GraphState` TypedDict: `question`, `generation`, `documents`, `run_web_search`, `retry_count`.
- `nodes.py` — node functions, each with its own `PromptTemplate`:
  - `retrieve` — fetches context from Qdrant.
  - `grade_documents` — evaluates document relevance (fast LLM).
  - `generate` — produces the answer (smart LLM).
  - `rewrite_query` — rewrites the question when retrieval is weak (fast LLM).
  - `hallucination_check` — verifies the answer is grounded in retrieved docs.
- `graph.py` — wires nodes into a `StateGraph`:
  `retrieve → grade_documents → (rewrite_query loop | generate) → hallucination_check → (loop to generate | END)`, capped at 3 retries.

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
- Frontend auth state flows through `middleware.ts` (route-level gating) + `context/auth-context.tsx` (component-level state) — new protected pages need both a middleware rule and to consume the auth context.
- Sample/fixture documents for manual ingestion testing (e.g. `test_doc.txt`) belong outside version control or clearly marked as fixtures — not loose at repo root as committed files.

## Known limitations (current state, not yet fixed)

These aren't roadmap items — they're honest gaps in what exists today. See `PLAN.md` for the active cleanup checklist.

- `grade_generation_and_documents` in `graph.py` is dead code — defined but never wired into the graph.
- `hallucination_check`'s retry path loops back to `generate` with no feedback about *why* the generation failed grounding.
- `/chat`'s response `steps` field is a hardcoded placeholder, not the actual execution path taken.
- `retrieve()` has no fallback on Qdrant errors — it re-raises, and a Qdrant outage 500s `/chat` entirely.
- No streaming — `/chat` uses a synchronous `graph_app.invoke()`.
- No automated tests.
