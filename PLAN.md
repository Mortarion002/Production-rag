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

- [x] Add a fallback/graceful error response in `retrieve()` when Qdrant is unreachable — it now catches the error, sets `retrieval_error`, and a new `handle_retrieval_error` node short-circuits straight to a fallback answer instead of feeding empty docs into the (uncapped) rewrite loop or 500ing
- [x] Review default secrets — `.env.example` documents the override path; `config.py` now prints a startup warning if `SECRET_KEY`/`POSTGRES_PASSWORD` are still the hardcoded defaults
- [x] CORS — confirmed with the user there's no deployment target yet, so `http://localhost:3000` stays the default, but it's now env-configurable (`CORS_ORIGINS`) so a future deploy is a one-line `.env` change, not a code change

## Future features

- [ ] Streaming responses for `/chat` (currently a single synchronous `graph_app.invoke()`)
- [x] Automated test suite — `backend/tests/` (pytest: graph nodes/edges, auth, `/chat`/`/ingest` role gating), `frontend/middleware.test.ts` (vitest: route protection). Found and fixed two real bugs along the way:
  - `ingestion.py` connected to Qdrant at *module import time*, meaning `app.server` — and the whole app — would fail to boot if Qdrant was down at startup, not just fail gracefully mid-request as the resilience PR intended. Now lazily initialized on first use.
  - `frontend/context/auth-context.tsx` used Python type names (`str`, `bool`) in TypeScript annotations — present since the very first commit, meaning `npm run build` has never actually succeeded on this repo until now. Fixed to `string`/`boolean`.
- [x] CI pipeline — `.github/workflows/ci.yml`: backend (`pytest`) and frontend (`lint`/`build`/`test`) jobs on every PR to `main` and push to `main`. No live services needed (SQLite fixture, mocked LLM calls, lazy Qdrant init from the tests PR). Found and fixed two more pre-existing lint errors while making sure CI would ship green: an `any` cast in `admin/page.tsx` (replaced with `undefined`, the standard axios way to unset a default header) and a `react-hooks/set-state-in-effect` violation in `auth-context.tsx` (the token-decode was moved from a mount effect into a lazy `useState` initializer, so `loading` is no longer needed as real state — the effect that only flipped it to `false` was removed entirely).

---
*When starting a new feature not listed here: enter plan mode, propose the steps, get them added to this file, then implement per the loop in `CLAUDE.md`.*
