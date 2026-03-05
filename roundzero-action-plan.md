# roundZero — Sprint Plan & WebSocket Fix Guide
## Deadline: March 16, 2026 @ 5:00 PM PDT (~11 days left)

---

## PART 1: WEBSOCKET BUG — ROOT CAUSE & FIX

### What's Actually Happening (from your logs)

1. **First connection SUCCEEDS** — audio streams, transcription works ("Hello! I'm your behavioral interview coach today...")
2. **After first session closes** → every new connection gets `connection rejected (400 Bad Request)`
3. The ADK Live API session throws `ConnectionClosedOK: sent 1000 (OK)` — this is the Gemini Live API closing cleanly, but your app doesn't handle the lifecycle reset
4. Frontend retries rapidly → all rejected

### Root Cause: Stale Session State + Middleware Interference

The official bidi-demo pattern (`/ws/{user_id}/{session_id}`) creates a fresh `LiveRequestQueue` per connection and cleans it up in a `finally` block. Your implementation likely has one or more of these issues:

**Issue A — LiveRequestQueue not closed properly:**
```python
# WRONG: Queue leaks if exception happens before close
live_request_queue = LiveRequestQueue()
# ... if error happens here, queue never closes
# The ADK Runner stays "live" and rejects new connections

# CORRECT: Always close in finally
try:
    live_request_queue = LiveRequestQueue()
    # ... upstream/downstream tasks
finally:
    live_request_queue.close()
```

**Issue B — Middleware blocking WebSocket upgrade on reconnect:**
Your `JWTAuthMiddleware` is likely rejecting the WebSocket `Upgrade` request because it can't find/validate the token on the raw WS handshake. The first connection works because the browser sends cookies from the initial page load, but reconnections may not.

**Issue C — Single LiveRequestQueue reuse:**
If you're creating one `LiveRequestQueue` at app startup and reusing it across connections (instead of one per WebSocket session), the second connection will fail because the queue is already bound to a closed Live API session.

### THE FIX — Align with Official bidi-demo Pattern

```python
# backend/app/main.py — REWRITE your websocket endpoint

from google.adk.runners import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.genai import types
import asyncio

# === PHASE 1: App-level singletons (created ONCE at startup) ===
agent = create_interviewer()  # your agent factory
session_service = InMemorySessionService()
runner = Runner(
    app_name="roundzero",
    agent=agent,
    session_service=session_service
)

# === NO CORSMiddleware needed for WebSocket ===
# Move CORS to only cover HTTP routes, NOT the WS endpoint
# Or: put WS endpoint BEFORE middleware in route order

@app.websocket("/ws/{user_id}/{session_id}")  # PATH params, not query
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    mode: str = Query(default="buddy")  # mode as query param is fine
):
    await websocket.accept()  # Accept FIRST, before any other logic
    
    # === PHASE 2: Per-connection session setup ===
    session = await session_service.get_session(
        app_name="roundzero",
        user_id=user_id,
        session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name="roundzero",
            user_id=user_id,
            session_id=session_id
        )
    
    # Determine modality based on model
    model_name = agent.model  
    is_native_audio = "native-audio" in model_name.lower()
    
    run_config = types.RunConfig(
        response_modalities=["AUDIO"] if is_native_audio else ["TEXT"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Charon"  # or your preferred voice
                )
            )
        ) if is_native_audio else None,
        output_audio_transcription=types.AudioTranscriptionConfig()
        if is_native_audio else None,
    )
    
    # === PHASE 3: Fresh queue PER connection ===
    live_request_queue = LiveRequestQueue()
    
    try:
        # Start upstream + downstream as concurrent tasks
        live_events = runner.run_live(
            session=session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        )
        
        async def upstream():
            """Client → LiveRequestQueue"""
            try:
                while True:
                    data = await websocket.receive()
                    if "text" in data:
                        msg = json.loads(data["text"])
                        if msg.get("type") == "text":
                            content = types.Content(
                                role="user",
                                parts=[types.Part(text=msg["text"])]
                            )
                            live_request_queue.send_content(content)
                    elif "bytes" in data:
                        # Raw PCM audio
                        live_request_queue.send_realtime(
                            types.Blob(
                                data=data["bytes"],
                                mime_type="audio/pcm;rate=16000"
                            )
                        )
            except Exception as e:
                logger.info(f"Upstream ended: {e}")
        
        async def downstream():
            """run_live() events → Client"""
            try:
                async for event in live_events:
                    # Serialize event and send
                    event_json = event.model_dump_json(
                        exclude_none=True
                    )
                    event_dict = json.loads(event_json)
                    
                    # Extract audio bytes if present
                    if hasattr(event, 'content') and event.content:
                        for part in event.content.parts or []:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                await websocket.send_bytes(
                                    part.inline_data.data
                                )
                    
                    # Send JSON metadata
                    await websocket.send_json(event_dict)
                    
            except Exception as e:
                logger.info(f"Downstream ended: {e}")
        
        await asyncio.gather(
            upstream(),
            downstream(),
            return_exceptions=True
        )
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # === PHASE 4: CRITICAL CLEANUP ===
        live_request_queue.close()  # This MUST happen
        logger.info(f"Session {session_id} cleaned up")
```

### Middleware Fix — Remove from WS path

```python
# Don't wrap the entire app with JWT middleware
# Instead, apply JWT only to HTTP routes:

from starlette.routing import Route, WebSocketRoute

# Option 1: Skip JWT for WebSocket in your middleware
class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # SKIP auth for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        # ... normal JWT logic for HTTP
```

### Frontend Fix — Clean Reconnection

```typescript
// In useGeminiLive hook — don't rapid-fire reconnect
const connect = (userId: string, sessionId: string, mode: string) => {
    // Generate NEW session_id for each new interview
    const newSessionId = crypto.randomUUID();
    
    const ws = new WebSocket(
        `ws://localhost:8000/ws/${userId}/${newSessionId}?mode=${mode}`
    );
    
    ws.onclose = (event) => {
        // DON'T auto-reconnect on clean close (1000)
        if (event.code !== 1000) {
            // Only retry on abnormal close, with backoff
            setTimeout(() => connect(userId, newSessionId, mode), 2000);
        }
    };
};
```

---

## PART 2: HACKATHON COMPLIANCE CHECKLIST

Based on the official rules, your submission MUST include:

| Requirement | Status | Action Needed |
|---|---|---|
| Gemini model used | ✅ | gemini-2.5-flash-native-audio-latest |
| GenAI SDK or ADK | ✅ | Google ADK |
| ≥1 Google Cloud service | ⚠️ | Deploy backend to **Cloud Run** |
| Text description | ❌ | Write for Devpost |
| Public code repo | ✅ | GitHub |
| Proof of GCP deployment | ❌ | Screen recording of Cloud Run console |
| Architecture diagram | ✅ | You have the Eraser diagrams |
| Demo video (<4 min) | ❌ | Record after WS fix |
| Category: Live Agents | ✅ | Perfect fit |

### Bonus points:
- [ ] Blog/content with #GeminiLiveAgentChallenge
- [ ] Automated Cloud deployment (Dockerfile + cloudbuild.yaml)
- [ ] GDG membership link

---

## PART 3: 11-DAY SPRINT PLAN

### Days 1-2 (March 5-6): FIX WEBSOCKET — NOTHING ELSE
- [ ] Rewrite `/ws` endpoint following the pattern above
- [ ] Remove/bypass JWTAuthMiddleware for WS routes
- [ ] Ensure `LiveRequestQueue` is created + closed per connection
- [ ] Test: connect → interview → disconnect → reconnect → interview again
- [ ] Frontend: stop auto-reconnect loop, use fresh session_id per interview

### Days 3-4 (March 7-8): CORE INTERVIEW FLOW
- [ ] Verify Pinecone question retrieval works in live session
- [ ] Test both Buddy and Strict persona prompts with audio
- [ ] Implement basic session save to Neon after interview ends
- [ ] Test end-to-end: setup → interview → report screen

### Days 5-6 (March 9-10): VISION (Phase 2) — IF TIME PERMITS
- [ ] Canvas frame capture at 2 FPS from frontend
- [ ] Send frames as image blobs to LiveRequestQueue
- [ ] Add Computer Use instructions to agent prompt
- [ ] Test: agent comments on code visible on screen
- **If this is too risky, SKIP IT — a polished audio-only demo wins over a broken multimodal one**

### Days 7-8 (March 11-12): CLOUD RUN DEPLOYMENT
- [ ] Create `Dockerfile` for backend
- [ ] Deploy to Cloud Run
- [ ] Update frontend to point to Cloud Run WebSocket URL (`wss://`)
- [ ] Deploy frontend to Vercel (or Cloud Run too)
- [ ] Test full flow on deployed version
- [ ] Take screen recording of Cloud Run console for proof

### Days 9-10 (March 13-14): DEMO VIDEO + SUBMISSION
- [ ] Record <4 min demo video showing:
  - Problem statement (interview prep sucks)
  - roundZero in action (real audio interview)
  - Architecture walkthrough (use your Eraser diagrams)
  - Tech stack callout (Gemini, ADK, Cloud Run)
- [ ] Write Devpost text description
- [ ] Upload architecture diagram to Devpost
- [ ] Fill all required fields

### Day 11 (March 15): BUFFER + SUBMIT
- [ ] Final testing on deployed version
- [ ] Submit on Devpost before March 16, 5 PM PDT
- [ ] Optional: Write a quick blog post for bonus points

---

## PART 4: GEMINI.MD — FOR GEMINI CLI / CODING AGENT

Paste this into your project root as `GEMINI.md` or use as context:

```markdown
# roundZero — Project Context for AI Coding Assistants

## What is this?
roundZero is a multimodal AI interview coach for the Gemini Live Agent Challenge hackathon.
Users have real-time voice conversations with an AI interviewer that can see their screen.

## Tech Stack
- Backend: FastAPI (Python 3.12+) + Google ADK (Agent Development Kit)
- Frontend: React 19 + TypeScript + Tailwind CSS + Vite
- LLM: Gemini 2.5 Flash (native-audio) via Multimodal Live API
- DB: Neon Postgres (sessions, auth) + Pinecone (question vector search)
- Deployment target: Google Cloud Run

## Architecture Pattern
- WebSocket bidi-streaming between React frontend and FastAPI backend
- ADK Runner.run_live() manages the Gemini Live API session
- LiveRequestQueue bridges WebSocket messages to the ADK event loop
- Upstream task: WebSocket → LiveRequestQueue (text + PCM audio + images)
- Downstream task: run_live() events → WebSocket (JSON + audio bytes)

## Key Files
- `backend/app/main.py` — FastAPI app, WebSocket endpoint, ADK lifecycle
- `backend/app/agents/interviewer.py` — Agent definition, persona prompts
- `backend/app/tools/` — fetch_questions (Pinecone), save_session (Neon)
- `frontend/src/hooks/useGeminiLive.ts` — WebSocket + audio capture hook
- `frontend/src/components/InterviewScreen.tsx` — Main interview UI

## Current Issues
- WebSocket returns 400 on reconnection (stale LiveRequestQueue / middleware)
- Frontend auto-reconnect loop sends rapid connection attempts

## Coding Guidelines
- Always close LiveRequestQueue in a finally block
- Use path params for user_id/session_id, query params for mode
- Skip JWT middleware for WebSocket upgrade requests
- Use `asyncio.gather()` for concurrent upstream/downstream tasks
- Audio format: PCM16 @ 16kHz, sent as raw binary WebSocket frames
- Don't use response_modalities as a string — it must be a list: ["AUDIO"]

## Testing Commands
```bash
# Backend
cd backend && uv run python -m app.main

# Frontend  
cd frontend && npm run dev

# Quick WS test
websocat ws://localhost:8000/ws/test_user/test_session?mode=buddy
```

## Hackathon Deadline
March 16, 2026 @ 5:00 PM PDT
Must deploy backend on Google Cloud (Cloud Run).
```

---

## QUICK REFERENCE: What to Tell Your AI Coding Agent

When you paste tasks into Gemini CLI or another AI:

**For the WebSocket fix:**
> "Rewrite the WebSocket endpoint in backend/app/main.py following the official ADK bidi-demo pattern. Create a NEW LiveRequestQueue per connection, close it in a finally block, use path params /ws/{user_id}/{session_id}, and skip JWT middleware for WebSocket upgrade requests. The current bug is that after the first successful session, all subsequent connections get 400 Bad Request."

**For type checks / linting:**
> "Run pyright on backend/ and fix all type errors. Focus on ADK imports — RunConfig, LiveRequestQueue, and Content types may have moved between google.adk and google.genai.types."

**For Cloud Run deployment:**
> "Create a Dockerfile for the FastAPI backend in backend/. Use python:3.12-slim, install uv, copy pyproject.toml and uv.lock, run uv sync, expose port 8080, and start with uvicorn. Also create a cloudbuild.yaml for automated deployment."
