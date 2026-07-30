# PLAN.md

Active checklist. One running plan for the whole project — check items off as they land, add new steps as they come up. See `PROJECT_BRIEF.md` for the "why" behind each known limitation.

## Repo hygiene

- [ ] Remove committed debug/scratch files from git: `backend/chat_log.txt`, `backend/debug_test.txt`, `backend/error_detail_chat.txt`, `backend/debug_ingestion.py`, `backend/debug_upload.py`, `backend/verify_ingestion.py`
- [ ] Decide what to do with root-level `test_doc.txt` and `Company Policy - Google Docs.pdf` (already gitignored going forward, but still tracked from before) — either untrack them or move to a clearly-labeled `fixtures/` dir
- [ ] Add a `.env.example` to `backend/` documenting all expected env vars with correct casing

## Correctness bugs

- [ ] Fix env var casing mismatch in `backend/app/config.py:10-11` (`os.getenv("llm_model_fast", ...)` / `"llm_model_smart"`) — should match the uppercase names used in README/`.env` examples, or lookups silently no-op on case-sensitive systems
- [ ] Resolve dead code in `backend/app/graph/graph.py`: `grade_generation_and_documents` (lines 21-39) is defined but never wired into the `StateGraph` — either remove it or replace `check_hallucination_edge` with it if it was meant to supersede that logic
- [ ] Give the hallucination-check retry path actual feedback (currently loops back to `generate` blind when grounding fails, with no signal about what to fix)
- [ ] Make `/chat`'s response `steps` field reflect the real execution path instead of a hardcoded placeholder list

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
