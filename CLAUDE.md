# CLAUDE.md

How to work in this repo. See `PROJECT_BRIEF.md` for what the system does and its architecture. See `PLAN.md` for the active checklist of work in progress.

## Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph + LangChain, OpenAI (`gpt-4o-mini` default), Qdrant (vectors), PostgreSQL + SQLAlchemy/asyncpg (users), JWT auth (python-jose + passlib/bcrypt). Dependency manager: **Poetry**.
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Shadcn/UI (radix-ui), Axios, `jose` (JWT verification in middleware).
- **Infra**: `docker-compose.yml` runs Qdrant + Postgres only — the app itself runs locally via Poetry/npm, not in Docker.

## Commands

Backend (from `backend/`):
- `poetry install` — install deps
- `poetry run uvicorn app.server:app --reload` — run dev server
- `poetry run pytest` — run backend tests (graph nodes/edges, auth) — no live Qdrant/Postgres needed, DB is an in-memory SQLite fixture and LLM calls are mocked
- `docker-compose up -d` (from repo root) — start Qdrant + Postgres

Frontend (from `frontend/`):
- `npm install`
- `npm run dev` — dev server (localhost:3000)
- `npm run build` — production build
- `npm run lint` — eslint
- `npm run test` — run frontend tests (currently: `middleware.ts` route-protection logic)

CI (`.github/workflows/ci.yml`) runs `pytest` (backend) and `lint`/`build`/`test` (frontend) on every PR to `main` and every push to `main`. Treat a clean `npm run build`, a passing `pytest`/`npm run test`, and a successful manual exercise of the changed flow as the bar for "done" — CI is the safety net, not a substitute for checking locally first.

## Folder conventions

- `backend/app/graph/` — LangGraph core: `state.py` (GraphState schema), `nodes.py` (node functions, one per pipeline stage), `graph.py` (StateGraph wiring + conditional edges). Keep node functions single-purpose; wire control flow only in `graph.py`.
- `backend/app/auth/` — JWT auth: models, schemas, router, token logic.
- `backend/app/services/` — external integrations (Qdrant ingestion/retrieval today).
- `backend/app/server.py` — FastAPI routes only; no business logic here, call into `graph/` or `services/`.
- `frontend/app/<route>/page.tsx` — flat App Router routes (`/`, `/login`, `/signup`, `/dashboard`, `/chat`, `/admin`), no nested route groups yet.
- `frontend/middleware.ts` — JWT-based route protection and role gating. Any new protected route must be added here.
- `frontend/context/`, `frontend/lib/` — auth context and the Axios client.

## Hard rules

- Never commit directly to `main` — always branch for new features/fixes.
- One commit per completed step (see the per-feature loop below).
- Run `npm run build` (frontend) and confirm the backend imports/starts cleanly before marking a step done.
- Never commit debug scratch files, logs, or sample ingestion docs to the repo. `.gitignore` already lists `test_doc.txt` and `*.log`, but check `git status` before committing — several such files (`chat_log.txt`, `debug_*.py`, `error_detail_chat.txt`, `verify_ingestion.py`) were committed in the past before the ignore rules existed; don't reintroduce the pattern.
- Backend env vars are read with exact case in `config.py` (e.g. `os.getenv("llm_model_fast", ...)`, lowercase) — when adding new settings, match the exact casing used in `os.getenv(...)` in both `config.py` and `.env`/README examples, since env var lookups are case-sensitive.
- Never hardcode secrets (API keys, `SECRET_KEY`, DB passwords) as anything other than the existing dev-only fallback defaults in `config.py` — real values always come from `.env` (gitignored), never committed.
- New LangGraph nodes/edges: wire them into `graph.py`'s `StateGraph` immediately. Don't leave a node or decision function defined but unwired — this repo has drifted that way before (see `PLAN.md`).

## Workflow loop (per feature/fix)

1. New branch.
2. Enter plan mode for anything non-trivial → read `PROJECT_BRIEF.md` + relevant existing files → propose a plan → user reviews/approves.
3. Exit plan mode → implement.
4. Run the build/lint (frontend) and a manual smoke test of the changed endpoint or page; show the output, don't just claim it works.
5. Check off the step in `PLAN.md`.
6. Commit with a clear message.
7. Repeat until the feature is done → push branch → merge.
