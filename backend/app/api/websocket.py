"""
WebSocket endpoint for RoundZero AI Interview Coach.

Follows the official ADK 4-phase lifecycle:
  Phase 1 – App Init: Runner, SessionService, Agent created ONCE at module load.
  Phase 2 – Session Init: get-or-create ADK session + fresh RunConfig + fresh queue.
  Phase 3 – Bidi-streaming: concurrent upstream / downstream tasks.
  Phase 4 – Terminate: queue.close() on disconnect.

Reference: https://google.github.io/adk-docs/streaming/dev-guide/part1/
"""

import json
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# ADK imports
from google import adk
from google.adk.agents import RunConfig, LiveRequestQueue
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents.interviewer.agent import create_interviewer
from app.services.session_service import SessionService
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# PHASE 1: Application Initialization (module-level singletons)
# Created exactly ONCE when the module is first imported.
# ============================================================

APP_NAME = "roundzero-interviewer"

# Single in-memory session service shared across all WebSocket connections.
# Replace with DatabaseSessionService for multi-replica production deployments.
_adk_session_service = InMemorySessionService()

# Runner is stateless and reusable across sessions — created once.
# The agent inside is also stateless; individual system prompts are
# injected via create_interviewer() and stored in the ADK session state.
_runner: adk.Runner | None = None
_runner_lock = asyncio.Lock()


async def _get_runner(mode: str, user_profile: dict | None, role: str,
                      topics: list, difficulty: str) -> adk.Runner:
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

    URL: ws://host/ws/{user_id}/{session_id}?mode=buddy
    """
    logger.info(f"DIAGNOSTIC WS: WebSocket request for user={user_id} session={session_id}")

    # Accept the connection FIRST — before any async work that could throw.
    try:
        await websocket.accept()
        logger.info(f"WebSocket accepted: session={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket accept() failed: {exc}")
        return

    # Extract query params
    params = dict(websocket.query_params)
    mode = params.get("mode", "buddy")

    queue: LiveRequestQueue | None = None

    try:
        # --------------------------------------------------------
        # PHASE 2: Session Initialization
        # --------------------------------------------------------

        # 2a. Retrieve the app-level session config from Redis
        session_data = await SessionService.get_session(session_id)
        user_profile = session_data.get("user_profile")

        # 2b. Build a personalised Runner+Agent for this session
        runner = await _get_runner(
            mode=mode,
            user_profile=user_profile,
            role=session_data.get("role", "Software Engineer"),
            topics=session_data.get("topics", []),
            difficulty=session_data.get("difficulty", "Medium"),
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
            )
            logger.info(f"ADK session created: session={session_id}")
        else:
            logger.info(f"ADK session resumed: session={session_id}")

        # 2d. RunConfig — MUST include StreamingMode.BIDI for WebSocket
        settings = get_settings()
        is_native_audio = "native-audio" in settings.gemini_model.lower()
        voice_name = "Kore" if mode == "buddy" else "Charon"

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,            # ← Critical: enables WebSocket bidi
            response_modalities=[genai_types.Modality.AUDIO] if is_native_audio else [genai_types.Modality.TEXT],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
            output_audio_transcription=genai_types.AudioTranscriptionConfig(),
        )

        # 2e. Fresh LiveRequestQueue per connection (never reused)
        queue = LiveRequestQueue()

        # --------------------------------------------------------
        # PHASE 3: Bidi-streaming — concurrent upstream / downstream
        # --------------------------------------------------------

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

                            elif msg_type == "end_session":
                                queue.close()
                                break

                            elif msg_type == "image":
                                b64 = payload.get("data")
                                if b64:
                                    import base64
                                    queue.send_realtime(genai_types.Blob(
                                        data=base64.b64decode(b64),
                                        mime_type=payload.get("mimeType", "image/jpeg"),
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
                logger.error(f"Upstream error: {exc}")

        async def downstream() -> None:
            """run_live() events → WebSocket client"""
            try:
                async for event in runner.run_live(
                    session=adk_session,
                    live_request_queue=queue,
                    run_config=run_config,
                ):
                    # --- Text responses ---
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                await websocket.send_json({
                                    "type": "text",
                                    "content": part.text,
                                    "partial": event.partial,
                                })
                            # Audio bytes (inline_data)
                            if hasattr(part, "inline_data") and part.inline_data:
                                await websocket.send_bytes(part.inline_data.data)

                    # --- AI output transcription ---
                    if event.output_transcription and event.output_transcription.text:
                        await websocket.send_json({
                            "type": "text",
                            "content": event.output_transcription.text,
                            "partial": False,
                        })

                    # --- User input transcription ---
                    if event.input_transcription and event.input_transcription.text:
                        await websocket.send_json({
                            "type": "transcription",
                            "source": "user",
                            "content": event.input_transcription.text,
                            "is_final": getattr(event.input_transcription, "is_final", True),
                        })

                    # --- Conversation boundary signals ---
                    if event.turn_complete:
                        await websocket.send_json({"type": "turn_complete"})

                    if event.interrupted:
                        await websocket.send_json({"type": "interrupt"})

            except Exception as exc:
                logger.error(f"Downstream error: {exc}", exc_info=True)

        # Run both tasks concurrently
        await asyncio.gather(upstream(), downstream(), return_exceptions=True)

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
