# PLAN.md

Active checklist. One running plan for the whole project — check items off as they land, add new steps as they come up. See `PROJECT_BRIEF.md` for the "why" behind each known limitation.

## Repo hygiene

- [x] Remove committed debug/scratch files from git: `backend/chat_log.txt`, `backend/debug_test.txt`, `backend/error_detail_chat.txt`, `backend/debug_ingestion.py`, `backend/debug_upload.py`, `backend/verify_ingestion.py`
- [x] Root-level `test_doc.txt` and `Company Policy - Google Docs.pdf` — verified via `git ls-files` they were never actually tracked (already covered by `.gitignore`); no action needed
- [x] Add a `.env.example` to `backend/` documenting all expected env vars with correct casing — also fixed README's env block, which showed a `DATABASE_URL` var that isn't actually read (it's built from `POSTGRES_*` vars)

## Correctness bugs

- [x] Fix env var casing mismatch in `backend/app/config.py:10-11` — now reads `LLM_MODEL_FAST`/`LLM_MODEL_SMART` (uppercase), matching `.env.example`/README
- [x] Resolve dead code in `backend/app/graph/graph.py` — removed unused `grade_generation_and_documents`; its retry-cap logic is now correctly owned by `hallucination_check` itself
- [x] Give the hallucination-check retry path actual feedback — added `hallucination_feedback` to `GraphState`; `hallucination_check` sets a specific corrective note (different for "ungrounded" vs "doesn't address the question") and `generate` injects it into the prompt on retry. Also fixed a related bug: retries exhausted while still ungrounded used to return `END` with `generation` still `None` (a silent `null` answer to the frontend) — now returns a clear fallback message instead
- [x] Make `/chat`'s response `steps` field reflect the real execution path — added `steps: List[str]` to `GraphState`, each node appends its own name, `server.py` returns the accumulated list instead of a hardcoded placeholder

## Resilience

- [ ] Add a fallback/graceful error response in `retrieve()` when Qdrant is unreachable, instead of letting it re-raise and 500 the whole `/chat` request
- [ ] Review default secrets in `config.py`/`docker-compose.yml` (`SECRET_KEY`, Postgres password) — fine for dev, but confirm there's a documented path to override them before any real deployment
- [ ] Confirm CORS config (currently hardcoded to `http://localhost:3000`) is intentional for current deployment plans

## Future features (not started)

- [ ] Streaming responses for `/chat` (currently a single synchronous `graph_app.invoke()`)
- [ ] Automated test suite (backend: graph nodes/edges, auth; frontend: at least route protection)
- [ ] CI pipeline (build + lint on PR, at minimum)

---
*When starting a new feature not listed here: enter plan mode, propose the steps, get them added to this file, then implement per the loop in `CLAUDE.md`.*
