# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RoundZero is a multimodal AI interview coach using Gemini 2.0 Flash Live API for bidirectional streaming audio. The AI acts as an interviewer, evaluates responses in real-time, and generates performance reports. Built for the Gemini Live Agent Challenge.

## Commands

### Frontend
```bash
cd frontend
npm install          # Install dependencies
npm start            # Dev server on http://localhost:3000
npm run build        # Production build to build/
npm run lint         # ESLint
```

### Backend
```bash
cd backend
uv sync              # Install dependencies
uv run python run.py # Start server (PREFERRED — sets ws="wsproto")
uv run pytest -v     # Run all tests
uv run pytest tests/test_question_engine.py::test_name -v  # Single test
uv run ruff check .  # Lint
uv run ruff format . # Format
```

**Never use `uv run python -m app.main` to start the server** — always use `run.py`, which sets `ws="wsproto"` in Uvicorn. Without this, WebSocket connections return 400 errors.

## Architecture

```
Browser → React App (useGeminiLive hook)
            ↓ HTTP: /session/prepare, /session/start
            ↓ WebSocket: /ws/{userId}/{sessionId}
          FastAPI (ASGI middleware stack)
            ↓
          Google ADK Runner (4-phase lifecycle per connection)
            ↓
          Gemini 2.0 Flash Live API (bidi audio streaming)
            ↓
          External: Pinecone, Neon PostgreSQL, Upstash Redis, Supermemory
```

### WebSocket Protocol
- **Upstream**: binary PCM16 audio at **16kHz** (mic capture)
- **Downstream**: binary PCM16 audio at **24kHz** (AI playback) + JSON events
- Audio contexts must be **separate** — 16kHz for capture, 24kHz for playback — never merged

### Middleware Stack (backend/app/main.py)
Uses direct ASGI wrapping (not `add_middleware()`). Order matters:
```
DiagnosticMiddleware → JWTAuthMiddleware → CORSASGIMiddleware → FastAPI
```

### ADK 4-Phase Lifecycle (backend/app/api/websocket.py)
1. Module load: `InMemorySessionService` + `Runner` factory
2. Per-connection: fresh `RunConfig` + `LiveRequestQueue`
3. Streaming: `asyncio.gather(upstream_task, downstream_task)`
4. Teardown: `queue.close()`

### Frontend Hook (frontend/src/hooks/useGeminiLive.ts)
Core audio/WebSocket logic. Handles mic capture, PCM encoding, AI audio playback, transcript display, and interrupt handling.

## Key Environment Variables

**Backend** (see `backend/.env.example`):
- `GOOGLE_API_KEY` — Gemini API key (Google AI Studio)
- `GEMINI_MODEL` — must be `gemini-2.5-flash-native-audio-latest` (must support Live API)
- `DATABASE_URL` — Neon PostgreSQL connection string
- `JWT_SECRET` — for auth middleware
- `PINECONE_API_KEY`, `PINECONE_INDEX`
- `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

**Frontend** (see `frontend/.env.example`):
- `VITE_BACKEND_URL` — backend URL (dev: `http://localhost:8080`)
- `REACT_APP_NEON_AUTH_URL` — Neon Auth endpoint

## Deployment

- **Backend**: Google Cloud Run via Docker (`backend/Dockerfile`, `backend/cloudbuild.yaml`)
- **Frontend**: Vercel (`frontend/vercel.json` — build output in `build/`)

## Important Reference Docs

- `IMPLEMENTATION_CHECKPOINT.md` — current working state, known issues, critical implementation details
- `backend/QUICK_REFERENCE.md` — troubleshooting WebSocket 400s, Gemini 1008 errors, port conflicts
- `backend/.env.example` — full list of configurable environment variables
