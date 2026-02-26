# RoundZero Backend

FastAPI backend for the RoundZero AI Interview Coach.

## Implemented Flow

1. `POST /session/start` creates an interview session and returns first question + session metadata.
2. `POST /session/{session_id}/answer` evaluates candidate answer and returns next action (`CONTINUE`, `HINT`, `ENCOURAGE`, `NEXT`).
3. `POST /session/{session_id}/end` finalizes the session.
4. `GET /session/{session_id}/report` returns the final report and question breakdown.
5. `GET /health` and `GET /ready` expose liveness/readiness.

## Architecture Notes

- Core AI/session orchestration lives in `backend/agent/interviewer.py`.
- Question retrieval supports:
  - local dataset fallback (`backend/questions_normalized.json`)
  - optional Pinecone + Gemini embedding path (enable with `USE_PINECONE=true`)
- Decision engine supports:
  - heuristic fallback (default)
  - optional Claude decision path (enable with `USE_CLAUDE_DECISION=true`)
- Supabase + Supermemory are mirrored opportunistically when enabled.
- Pinecone: when enabled (`USE_PINECONE=true` + `PINECONE_API_KEY` + `GEMINI_API_KEY`), transcripts and summaries are embedded and upserted for personalization.
- Voice agent: enable with `USE_VISION=true` and provide Stream + Deepgram + ElevenLabs (and Anthropic/Gemini) keys; the interviewer will join Stream calls and converse in audio.
- Auth: backend validates Neon Auth JWTs via JWKS when `NEON_AUTH_URL` or `NEON_AUTH_JWKS_URL` is configured. A local HS256 fallback can stay enabled with `ALLOW_LEGACY_HS256_AUTH=true` for dev-only migration.

## Local Run (uv)

```bash
cd backend
uv sync --dev             # install runtime + dev deps into .venv
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
cd backend
uv run python -m unittest discover -s tests -p "test_*.py"
```
