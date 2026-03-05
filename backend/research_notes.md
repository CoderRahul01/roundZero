# Research Summary: ADK Gemini Live & roundZero Architecture

This document synthesizes best practices from the ADK documentation, Gemini Live Codelabs, and the "Way Back Home" multi-agent series to inform the production-grade implementation of **roundZero**.

## 1. WebSocket & Bidi-Streaming Stability

The technical patterns for high-stability WebSockets in ADK applications involve:

### Upstream/Downstream Task Pattern

- **Upstream**: Handles `websocket.receive()` -> `LiveRequestQueue.send_content()` (or `send_realtime`).
- **Downstream**: Handles `runner.run_live()` -> `websocket.send_text()`.
- **Synchronization**: Uses `asyncio.gather(upstream, downstream)` with `return_exceptions=True`.
- **Heartbeat**: Implement a 20-30s heartbeat (`ping/pong`) to prevent timeouts from Cloud Run or Nginx proxies.

### Robust Handshake & Auth

- **Auth Timing**: Verify JWTs _during_ the WebSocket handshake attempt, not just after connection.
- **Fail-Fast**: If the token is invalid or the origin is `INVALID_ORIGIN`, close with a specific code (e.g., `4001`) to help frontend debugging.

## 2. Database Choice & Scalability (10k+ Users)

Based on the requirements for fast performance and production-grade setup:

| Choice              | Scalability       | Performance       | Best For                          | Decision    |
| :------------------ | :---------------- | :---------------- | :-------------------------------- | :---------- |
| **Neon (Postgres)** | High (Serverless) | Low latency, ACID | Sessions, User Profiles, Auth     | **PRIMARY** |
| **Redis (Upstash)** | Ultra-High        | Sub-ms latency    | Caching Session Context, Heatmaps | **CACHING** |
| **Pinecone**        | High (Vector)     | Fast Retrieval    | Semi-Semantic Question Bank       | **VECTOR**  |
| **MongoDB**         | High              | Document storage  | Unstructured logs                 | _REDUNDANT_ |

**Reasoning**: Neon provides transaction-level integrity needed for interview scores and profile data while scaling automatically. MongoDB adds unnecessary architectural complexity given the current session-based data model.

## 3. The "Way Back Home" Patterns

Findings from Codelabs (Level 3 & 4):

- **LiveRequestQueue**: Essential for decoupling the producer (browser) from the consumer (Gemini model). It ensures "causal timeline" consistency.
- **Multimodal Events**: The `Event` object from `run_live()` is granular. Frontend handlers MUST parse `text`, `audio`, and `tool_call` separately.
- **Agent Cards**: For multi-agent systems, using the `.well-known/agent-card.json` pattern allows agents to "know" each other's capabilities without hardcoding.

## 4. Stability Gotchas

- **PCM 16kHz**: Audio MUST be 16kHz PCM for Gemini Live.
- **Asyncio Wait-For**: Wrap `receive_text` in `asyncio.wait_for(timeout=...)` to ensure the heartbeat logic has a chance to run if the network blips.
- **Memory Persistence**: Supermemory AI should be used to store _summaries_ of past interviews, which are injected into the `InterviewerAgent`'s system prompt during Phase 2 (Session Initialization).

## 5. Implementation Roadmap

1. **Consolidate to Neon**: Add `user_profiles` schema.
2. **Infrastructure Fix**: Deploy `AuthTokenVerifier` in WebSocket logic.
3. **Caching Layer**: Initialize `Upstash Redis` to store transient session state.
4. **Agent Update**: Feed onboarding bio/resume into the `InterviewerAgent` system prompt.
