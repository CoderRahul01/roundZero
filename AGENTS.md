# RoundZero - AI Interview Coach

## Vision

To build a premium, realtime AI interview coaching platform that uses Vision Agents to analyze body language, speech, and technical correctness.

## Tech Stack

- **Frontend**: React, TypeScript, Vite
- **Backend**: FastAPI, Vision Agents, Stream.io WebRTC
- **Storage**: Pinecone (Vector Store), Supabase (Postgres + Auth)
- **AI**: Anthropic Claude-3.5-Sonnet (Brain), Gemini (Embeddings)

## Working Agreements

- Use `uv` for backend dependency management.
- Use `npm` for frontend.
- All AI logic should reside in `backend/agent/`.
- Ensure security: NEVER hardcode secrets; use `.env`.
- Follow vertical slice development: Schema -> API -> UI.
- Maintain high design aesthetics in the frontend.

## Multi-Agent Collaboration

- **Developer (Self)**: Responsible for implementation, testing, and UI/UX.
- **Codex (Secondary)**: Responsible for architectural audits, quality assurance, and security reviews.
