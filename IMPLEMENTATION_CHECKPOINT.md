    # 🏁 RoundZero — Implementation Checkpoint

    > **Saved: 2026-03-06** | Status: WebSocket + Gemini Live ADK = ✅ WORKING  
    > This document captures the exact working state of the backend WebSocket & Gemini Live integration.  
    > **DO NOT revert files documented here without reading this first.**

    ---

    ## ✅ What Is Currently Working

    | Feature                                  | Status | Notes                                |
    | ---------------------------------------- | ------ | ------------------------------------ |
    | WebSocket connection (browser → backend) | ✅     | Stable with `wsproto`                |
    | Gemini Live bidi-streaming               | ✅     | BIDI mode via ADK runner             |
    | AI voice output (TTS)                    | ✅     | 24kHz PCM, Kore/Charon voice         |
    | Mic capture (STT)                        | ✅     | 16kHz PCM sent as binary             |
    | Vision frames to Gemini                  | ✅     | 1 frame / 5s JPEG base64             |
    | User transcript display                  | ✅     | From `input_transcription` event     |
    | AI response text display                 | ✅     | From `output_transcription` event    |
    | Interrupt signal handling                | ✅     | Clears playback queue                |
    | JWT auth middleware (WS bypass)          | ✅     | WS connections bypass JWT            |
    | CORS (WS bypass)                         | ✅     | Custom ASGI — no Starlette intercept |

    ---

    ## 🏗️ Architecture: The 4 Critical Files

    ### 1. `backend/run.py` — Entry Point

    ```python
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        ws="wsproto",                  # ← CRITICAL: browser WS requires wsproto
        ws_per_message_deflate=False,  # ← CRITICAL: deflate breaks binary audio
        timeout_keep_alive=300,        # ← keeps interview sessions alive
    )
    ```

    > ⚠️ **Never remove `ws="wsproto"`** — the default `ws=auto` or `websockets` causes 400 on browser WS connections.

    ---

    ### 2. `backend/app/main.py` — Middleware Stack

    The middleware is wired as **direct ASGI chain**, NOT via `app.add_middleware()`.  
    `app.add_middleware()` routes through `BaseHTTPMiddleware` which intercepts WS upgrades → 400.

    ```
    DiagnosticMiddleware        ← outermost (logs all scopes)
    └── JWTAuthMiddleware     ← bypasses WebSocket scopes entirely
            └── CORSASGIMiddleware ← bypasses WebSocket scopes entirely
                └── FastAPI   ← innermost (handles /ws/* routes)
    ```

    Code:

    ```python
    asgi_app = CORSASGIMiddleware(fastapi_app)  # innermost
    asgi_app = JWTAuthMiddleware(asgi_app)       # middle
    asgi_app = DiagnosticMiddleware(asgi_app)    # outermost
    app = asgi_app
    ```

    ---

    ### 3. `backend/app/api/websocket.py` — ADK 4-Phase Lifecycle

    **Phase 1 (module load):** `InMemorySessionService` singleton + `Runner` factory per session  
    **Phase 2 (per-connection):** get-or-create ADK session + fresh `LiveRequestQueue` + `RunConfig`  
    **Phase 3 (streaming):** `asyncio.gather(upstream(), downstream())`  
    **Phase 4 (teardown):** `queue.close()`

    Key `RunConfig`:

    ```python
    RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[genai_types.Modality.AUDIO],  # enum, not string "AUDIO"
        speech_config=genai_types.SpeechConfig(
            voice_config=genai_types.VoiceConfig(
                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Kore")
            )
        ),
        output_audio_transcription=genai_types.AudioTranscriptionConfig(),
    )
    ```

    Event type mapping (backend → frontend):
    | Backend emits | Frontend handles |
    |---|---|
    | `{"type": "text", "content": "..."}` | AI transcript display |
    | `{"type": "transcription", "source": "user", "content": "..."}` | User transcript display |
    | `{"type": "turn_complete"}` | Turn boundary |
    | `{"type": "interrupt"}` | Clear playback queue |
    | binary bytes | PCM audio to speaker |

    ---

    ### 4. `frontend/src/hooks/useGeminiLive.ts` — Audio Architecture

    **Two AudioContext instances (critical):**

    ```
    micCtxRef      → 16kHz   ← mic capture (ADK/Gemini STT requirement)
    playbackCtxRef → 24kHz   ← AI audio playback (Gemini native-audio outputs 24kHz PCM)
    ```

    > ⚠️ **Never merge these into one context.** Using a 16kHz context for 24kHz audio causes pitch-shift + speedup.

    **Audio pipeline:**

    ```
    Mic → getUserMedia() → ScriptProcessor (4096 samples) → Int16Array → WebSocket.send(binary)
    Gemini response → WebSocket binary → Int16Array queue → AudioBufferSource (24kHz ctx) → speaker
    ```

    **WebSocket URL construction (local dev):**

    ```typescript
    const wsBase = baseUrl.includes("localhost:3000")
    ? "ws://localhost:8080" // bypass Vite proxy for WS
    : baseUrl.replace("http", "ws"); // production
    ```

    ---

    ## 🔑 Environment Variables (backend/.env)

    ```bash
    GEMINI_MODEL=gemini-2.5-flash-native-audio-latest  # ← DO NOT CHANGE
    GOOGLE_GENAI_USE_VERTEXAI=FALSE
    GOOGLE_API_KEY=...                                  # Google AI Studio key
    ```

    > ⚠️ Model must be `gemini-2.5-flash-native-audio-latest` for bidiGenerateContent support.  
    > `gemini-2.0-flash-*` models do NOT support the Live API bidi endpoint.

    ---

    ## 🚀 How to Run Locally

    ```bash
    # Backend (port 8080)
    cd backend
    uv run run.py

    # Frontend (port 3000 → proxies to 8080)
    cd frontend
    npm start
    ```

    WebSocket connects directly to `ws://localhost:8080/ws/{userId}/{sessionId}?mode=buddy`

    ---

    ## ⚠️ Known Issues / Next Steps

    | Issue                            | Priority | Notes                                                         |
    | -------------------------------- | -------- | ------------------------------------------------------------- |
    | Audio crackling / latency        | HIGH     | ScriptProcessorNode causes glitches — migrate to AudioWorklet |
    | No camera preview in UI          | HIGH     | Need `<video>` element showing webcam                         |
    | Question progression not tracked | HIGH     | Backend drives questions via voice, no UI counter sync        |
    | 5-question limit not enforced    | MEDIUM   | Needs session state + backend signal                          |
    | Report card screen empty         | MEDIUM   | `ReportScreen.tsx` exists but not wired                       |
    | `ScriptProcessorNode` deprecated | LOW      | Works but generates browser warning                           |
