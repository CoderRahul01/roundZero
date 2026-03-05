# roundZero — AI Interview Coach (Development Guide)

## 🏗️ Architecture Overview

roundZero is a high-performance AI Interview Coach built using the **Google ADK** and **Gemini 2.0 Flash Live API**.

- **Backend**: FastAPI with async/await discipline.
- **Database**: Neon (Postgres) for persistent session and profile storage.
- **Caching**: Upstash Redis for high-speed session context and profile metadata.
- **Persistent Memory**: Supermemory AI for cross-session candidate progress tracking.
- **WebRTC**: GetStream (or local PCM streaming via WebSocket).

## 🚀 Getting Started

### Prerequisites

- `uv` (Python package manager)
- Environment variables configured in `.env` (see `.env.example`)

### Local Setup

```bash
cd backend
uv sync
uv run main.py
```

## 🛠️ Key Components

### 1. Interviewer Agent (`app/agents/interviewer/agent.py`)

Standard ADK Agent configured with multimodal speech/video support. Ingests user profiles and past feedback into its system prompt for a personalized experience.

### 2. WebSocket Implementation (`app/api/websocket.py`)

Uses the **Upstream/Downstream pattern** for high-stability bidi-streaming.

- **Upstream**: Client -> Server (Audio/Video/Commands)
- **Downstream**: Server -> Client (Audio/JSON events)

### 3. User & Session Services

- `UserService`: Neon-backed profile management.
- `SessionService`: Results persistence and Supermemory summarization.

## 🔐 Authentication

All routes (HTTP and WebSocket) require **JWT Authentication**.

- **Handshake**: Tokens can be passed in `Authorization` header or `?token=` query param.
- **Verification**: Uses `AuthTokenVerifier` to validate RS256 (Neon Auth) or HS256 (Legacy) tokens.

## 🧪 Troubleshooting

### WebSocket Disconnection (4001)

- Verify that your token is valid and not expired.
- Check that the `DATABASE_URL` is correct in `.env`.
- Ensure Redis is reachable if caching is enabled.

### Audio Quality Issues

- Ensure you are sending **16kHz PCM** audio chunks. Other formats will cause the Gemini model to return errors.

---

_Created by Antigravity AI for roundZero._
