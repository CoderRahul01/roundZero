"""
WebSocket endpoint for RoundZero AI Interview Coach.

Follows the official ADK 4-phase lifecycle:
  Phase 1 – App Init: Runner, SessionService, Agent created ONCE at module load.
  Phase 2 – Session Init: get-or-create ADK session + fresh RunConfig + fresh queue.
  Phase 3 – Bidi-streaming: concurrent upstream / downstream tasks.
  Phase 4 – Terminate: queue.close() on disconnect.

Reference: https://google.github.io/adk-docs/streaming/dev-guide/part1/
"""

import asyncio
import json
import time

import google.genai.errors
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from google import adk
from google.adk.agents import LiveRequestQueue, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents.interviewer.agent import create_interviewer
from app.core.gcp_logger import gcp_logger as logger
from app.core.rate_limit import ws_limiter
from app.core.settings import get_settings
from app.services.session_service import SessionService

INTERVIEW_DURATION_SECONDS = 10 * 60  # 10 minutes

# ---------------------------------------------------------------------------
# Helper: Tool Result Interception
# ---------------------------------------------------------------------------
async def process_tool_results(event, websocket: WebSocket, session_state: dict, session_id: str):
    """
    Intercept tool call results from the agent and forward relevant
    signals to the frontend.
    """
    from app.services.session_service import SessionService

    calls = event.get_function_calls()
    if not calls:
        return

    for call in calls:
        if call.name == "record_score":
            # Forward score to frontend
            score_entry = {
                "question_number": call.args.get("question_number"),
                "question_text": call.args.get("question_text"),
                "candidate_answer_summary": call.args.get("candidate_answer_summary"),
                "score": call.args.get("score"),
                "max_score": call.args.get("max_score", 10),
                "feedback": call.args.get("feedback"),
                "is_followup": call.args.get("is_followup", False),
            }
            if "scores" not in session_state:
                session_state["scores"] = []
            session_state["scores"].append(score_entry)

            # Persist to Redis + Neon so ReportGenerator can read it
            try:
                await SessionService.save_question_result(session_id, {
                    "question_text": call.args.get("question_text", ""),
                    "user_answer": call.args.get("candidate_answer_summary", ""),
                    "ideal_answer": "",
                    "score": call.args.get("score", 0),
                    "filler_word_count": 0,
                    "emotion_log": {},
                    "feedback": call.args.get("feedback", ""),
                    "max_score": call.args.get("max_score", 10),
                    "question_number": call.args.get("question_number"),
                })
            except Exception as e:
                logger.error(f"Failed to persist score for session {session_id}: {e}")

            await websocket.send_json({
                "type": "score_update",
                "data": score_entry,
                "running_total": sum(s["score"] for s in session_state["scores"]),
                "running_max": sum(s["max_score"] for s in session_state["scores"]),
            })

        elif call.name == "request_screen_share":
            await websocket.send_json({
                "type": "screen_share",
                "action": "request",
            })

        elif call.name == "stop_screen_share":
            await websocket.send_json({
                "type": "screen_share",
                "action": "stop",
            })

        elif call.name == "signal_interview_end":
            await websocket.send_json({
                "type": "interview_end",
                "data": {
                    "total_score": call.args.get("total_score"),
                    "max_possible_score": call.args.get("max_possible_score"),
                    "overall_feedback": call.args.get("overall_feedback"),
                    "strengths": call.args.get("strengths", []),
                    "areas_for_improvement": call.args.get("areas_for_improvement", []),
                },
            })

router = APIRouter()

# ============================================================
# PHASE 1: Application Initialization (module-level singletons)
# Created exactly ONCE when the module is first imported.
# ============================================================

# Should match the Agent.name property to avoid warnings
APP_NAME = "interviewer"

# Use Redis-backed session service in production; fall back to in-memory if
# Redis is not configured (e.g. local dev without Upstash credentials).
def _build_session_service():
    from app.core.redis_client import get_redis
    from app.core.redis_session_service import RedisSessionService
    if get_redis() is not None:
        logger.info("Using RedisSessionService for ADK sessions")
        return RedisSessionService()
    logger.warning("Redis not available — falling back to InMemorySessionService (dev only)")
    return InMemorySessionService()

_adk_session_service = _build_session_service()

# Runner is stateless and reusable across sessions — created once.
# The agent inside is also stateless; individual system prompts are
# injected via create_interviewer() and stored in the ADK session state.
_runner: adk.Runner | None = None
_runner_lock = asyncio.Lock()


async def _get_runner(mode: str, user_profile: dict | None, role: str,
                      topics: list, difficulty: str, session_id: str, question_bank: list | None = None) -> adk.Runner:
    """
    Return a fresh Runner for this session's specific agent configuration.
    Each session gets its own Agent instance (personalised system prompt),
    but shares the same InMemorySessionService.
    """
    agent = await create_interviewer(
        mode=mode,
        user_profile=user_profile,
        role=role,
        topics=topics,
        difficulty=difficulty,
        question_bank=question_bank,
        session_id=session_id
    )
    return adk.Runner(
        agent=agent,
        session_service=_adk_session_service,
        app_name=APP_NAME,
    )


# ============================================================
# WebSocket endpoint
# ============================================================

@router.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    """
    Bidirectional interview streaming endpoint.

    URL: ws://host/ws/{user_id}/{session_id}?mode=buddy&token=JWT
    """
    logger.info(f"DIAGNOSTIC WS: WebSocket request for user={user_id} session={session_id}")

    # Extract query params FIRST (before accept) for Authentication
    params = dict(websocket.query_params)
    mode = params.get("mode", "buddy")
    token = params.get("token")

    # --------------------------------------------------------
    # SECURITY: Origin Validation
    # --------------------------------------------------------
    origin = websocket.headers.get("origin")
    from app.core.middleware import CORSASGIMiddleware
    if not CORSASGIMiddleware.is_origin_allowed(origin):
        logger.warning(f"Connection rejected: Forbidden origin {origin} for {session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # --------------------------------------------------------
    # SECURITY: Rate Limiting for WebSockets
    # --------------------------------------------------------
    user_ip = websocket.client.host if websocket.client else "unknown"
    try:
        # We manually call the limiter since Depends() doesn't auto-handle WS well
        # We pass a mock request object just containing the client host
        mock_request = type('obj', (object,), {'url': type('obj', (object,), {'path': '/ws'}), 'client': type('obj', (object,), {'host': user_ip})})()
        await ws_limiter(mock_request, identifier=f"{user_id}")
    except Exception:
        logger.warning(f"Connection rejected: Rate limit exceeded for user={user_id} ip={user_ip}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # --------------------------------------------------------
    # SECURITY: JWT Authentication for WebSockets
    # (Since ASGI Middleware skips WS for compatibility reasons)
    # --------------------------------------------------------
    if not token:
        logger.warning(f"Connection rejected: Missing token for {session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        from app.core.middleware import get_auth_token_verifier
        verifier = get_auth_token_verifier()
        # verify_token raises an exception if invalid/expired
        payload = verifier.verify_token(token)
        # Optional: verify payload['sub'] == user_id if strict enforcement needed
    except Exception as e:
        logger.warning(f"Connection rejected: Invalid token for {session_id}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept the connection now that it is authenticated
    try:
        await websocket.accept()
        logger.info(f"WebSocket accepted and authenticated: session={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket accept() failed: {exc}")
        return

    queue: LiveRequestQueue | None = None

    try:
        # --------------------------------------------------------
        # PHASE 2: Session Initialization
        # --------------------------------------------------------

        # 2a. Retrieve the app-level session config from Redis
        session_data = await SessionService.get_session(session_id)
        if not session_data:
            logger.warning(f"No session data found for {session_id}, using defaults")
            session_data = {}

        user_profile = session_data.get("user_profile") or {}
        if "id" not in user_profile:
            user_profile["id"] = user_id or session_data.get("user_id")

        question_bank = session_data.get("questions")

        # 2b. Build a personalised Runner+Agent for this session
        runner = await _get_runner(
            mode=mode,
            user_profile=user_profile,
            role=session_data.get("role", "Software Engineer"),
            topics=session_data.get("topics", []),
            difficulty=session_data.get("difficulty", "Medium"),
            question_bank=question_bank,
            session_id=session_id
        )
        logger.info(f"Runner created for session={session_id}")

        # 2c. Get-or-create the ADK Session (handles reconnects gracefully)
        # InMemorySessionService methods are async def despite annotation showing Session
        adk_session = await _adk_session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        if not adk_session:
            adk_session = await _adk_session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                state={"scores": [], "start_time": time.time(), "ended": False}
            )
            logger.info(f"ADK session created: session={session_id}")
        else:
            logger.info(f"ADK session resumed: session={session_id}")

        # 2d. Create RunConfig with optimal streaming and resumption settings
        settings = get_settings()
        is_native_audio = "native-audio" in settings.gemini_model.lower()
        voice_name = "Kore" if mode == "buddy" else "Charon"

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,            # ← Critical: enables WebSocket bidi
            session_resumption=genai_types.SessionResumptionConfig(),
            context_window_compression=genai_types.ContextWindowCompressionConfig(),
            tool_thread_pool_config=adk.agents.run_config.ToolThreadPoolConfig(max_workers=4),
            response_modalities=["AUDIO"] if is_native_audio else ["TEXT"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
            output_audio_transcription=genai_types.AudioTranscriptionConfig(),
        )

        # 2e. Inject per-connection context vars so tool functions can persist
        # results and push WS events without needing the event-stream path.
        from app.agents.interviewer.tools import _session_id_ctx, _websocket_ctx
        _session_id_ctx.set(session_id)
        _websocket_ctx.set(websocket)

        # 2f. Fresh LiveRequestQueue per connection (never reused)
        queue = LiveRequestQueue()

        # Trigger the first greeting/question automatically so the candidate doesn't have to speak first
        first_q = session_data.get("questions", [{}])[0].get("question", "Could you please introduce yourself?")
        queue.send_content(
            genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(
                        text=f"The session is starting. You are RoundZero. Start with a formal, professional greeting and introduction in the REQUIRED JSON FORMAT (NEW_QUESTION #1). Then, transition into the first interview question: {first_q}"
                    )
                ],
            )
        )

        # --------------------------------------------------------
        # PHASE 3: Bidi-streaming — concurrent upstream / downstream
        # --------------------------------------------------------

        async def timer_task():
            """Send time updates to frontend and pacing clues to agent."""
            try:
                state = adk_session.state
                start_time = state.get("start_time", time.time())

                while not state.get("ended", False):
                    elapsed = time.time() - start_time
                    remaining = INTERVIEW_DURATION_SECONDS - elapsed

                    if remaining <= 0:
                        state["ended"] = True
                        queue.send_content(genai_types.Content(
                            role="user",
                            parts=[genai_types.Part(text="[SYSTEM: Interview time is up. Wrap up immediately and call signal_interview_end.]")]
                        ))
                        await websocket.send_json({"type": "timer", "remaining_seconds": 0, "status": "expired"})
                        break

                    # Send update to UI
                    await websocket.send_json({
                        "type": "timer",
                        "remaining_seconds": int(remaining),
                        "elapsed_seconds": int(elapsed),
                        "status": "running"
                    })

                    # Pacing clues to agent
                    mins_left = int(remaining / 60)
                    if mins_left in [8, 5, 2, 1] and (int(elapsed) % 60 < 5):
                        queue.send_content(genai_types.Content(
                            role="user",
                            parts=[genai_types.Part(text=f"[SYSTEM: {mins_left} minutes remaining]")]
                        ))

                    await asyncio.sleep(30)
            except Exception as e:
                logger.debug(f"Timer task stopped for {session_id}: {e}")

        async def heartbeat():
            """Send periodic pings to keep the connection alive."""
            try:
                while True:
                    await asyncio.sleep(30)
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({"type": "ping"})
                    else:
                        break
            except Exception as e:
                logger.debug(f"Heartbeat stopped for {session_id}: {e}")

        async def upstream() -> None:
            """WebSocket client → LiveRequestQueue"""
            try:
                while True:
                    raw = await websocket.receive()

                    if "text" in raw:
                        try:
                            payload = json.loads(raw["text"])
                            msg_type = payload.get("type")

                            if msg_type == "text":
                                queue.send_content(genai_types.Content(
                                    role="user",
                                    parts=[genai_types.Part(text=payload["content"])],
                                ))

                            elif msg_type == "pong":
                                # Client responding to heartbeat
                                continue

                            elif msg_type == "end_session":
                                logger.info(f"Client requested session end: {session_id}")
                                queue.close()
                                break

                            elif msg_type in ["image", "screen_frame"]:
                                b64 = payload.get("data")
                                if b64:
                                    import base64
                                    queue.send_realtime(genai_types.Blob(
                                        data=base64.b64decode(b64),
                                        mime_type=payload.get("mimeType") or payload.get("mime_type") or "image/jpeg",
                                    ))
                        except json.JSONDecodeError:
                            # Plain text fallback
                            queue.send_content(genai_types.Content(
                                role="user",
                                parts=[genai_types.Part(text=raw["text"])],
                            ))

                    elif "bytes" in raw:
                        # Inbound PCM audio (16 kHz)
                        queue.send_realtime(genai_types.Blob(
                            data=raw["bytes"],
                            mime_type="audio/pcm;rate=16000",
                        ))

            except WebSocketDisconnect:
                logger.info(f"Upstream disconnected: session={session_id}")
            except Exception as exc:
                logger.error(f"Upstream error in session {session_id}: {exc}")
            finally:
                if queue:
                    queue.close()

        async def downstream() -> None:
            """run_live() events → WebSocket client"""
            try:
                async for event in runner.run_live(
                    session=adk_session,
                    live_request_queue=queue,
                    run_config=run_config,
                ):
                    # --- Text responses ---
                    if getattr(event, 'content', None) and event.content.parts:
                        for part in event.content.parts:
                            # Skip internal thinking/reasoning segments
                            if getattr(part, 'thought', False):
                                continue

                            if getattr(part, 'text', None):
                                await websocket.send_json({
                                    "type": "text",
                                    "content": part.text,
                                    "partial": getattr(event, 'partial', False),
                                })
                            # Audio bytes (inline_data)
                            if (hasattr(part, "inline_data") and part.inline_data) or (hasattr(part, "data") and part.data):
                                audio_data = getattr(part, "inline_data", None)
                                if audio_data:
                                    await websocket.send_bytes(audio_data.data)
                                elif hasattr(part, "data"):
                                    await websocket.send_bytes(part.data)

                    # --- AI output transcription ---
                    ot = getattr(event, 'output_transcription', None)
                    if ot and ot.text:
                        await websocket.send_json({
                            "type": "text",
                            "content": ot.text,
                            "partial": False,
                        })

                    # --- User input transcription ---
                    it = getattr(event, 'input_transcription', None)
                    if it and it.text:
                        await websocket.send_json({
                            "type": "transcription",
                            "source": "user",
                            "content": it.text,
                            "is_final": getattr(it, "is_final", True),
                        })

                    # --- Conversation boundary signals ---
                    if getattr(event, 'turn_complete', False):
                        await websocket.send_json({"type": "turn_complete"})

                    if getattr(event, 'interrupted', False):
                        await websocket.send_json({"type": "interrupt"})

                    # --- Tool calls and interception ---
                    await process_tool_results(event, websocket, adk_session.state, session_id)

                    calls = event.get_function_calls()
                    if calls:
                        for call in calls:
                            await websocket.send_json({
                                "type": "tool_call",
                                "payload": {
                                    "name": call.name,
                                    "args": call.args
                                }
                            })

            except google.genai.errors.APIError as e:
                if "1000" in str(e):
                    logger.info(f"Session {session_id} ended normally (Live API 1000)")
                else:
                    logger.error(f"Live API error in session {session_id}: {e}")
            except Exception as exc:
                logger.error(f"Downstream error in session {session_id}: {exc}", exc_info=True)

        # Run both tasks concurrently
        await asyncio.gather(upstream(), downstream(), heartbeat(), timer_task(), return_exceptions=True)

    except Exception as exc:
        logger.error(f"WebSocket handler error: {exc}", exc_info=True)
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=1011)
        except Exception:
            pass

    finally:
        # --------------------------------------------------------
        # PHASE 4: Terminate — always close the queue
        # --------------------------------------------------------
        if queue is not None:
            queue.close()
            logger.info(f"LiveRequestQueue closed: session={session_id}")
        logger.info(f"WebSocket session finished: session={session_id}")
