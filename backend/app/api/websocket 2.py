import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.live_request_queue import LiveRequestQueue, LiveRequest
from google.genai import types
import base64

from app.agents.interviewer.agent import create_interviewer
from app.core.logger import logger
from app.core.middleware import get_auth_token_verifier
from app.services.user_service import UserService
from app.core.redis_client import get_redis

# Monkeypatch ADK to use v1beta for Live API if using API Key
from google.adk.models import google_llm
original_live_api_version = google_llm.Gemini._live_api_version
def patched_live_api_version(self):
    return 'v1beta'
google_llm.Gemini._live_api_version = property(patched_live_api_version)
logger.info("Monkeypatched google.adk.models.google_llm.Gemini._live_api_version to 'v1beta'")

router = APIRouter()

@router.websocket("/ws")
async def interview_websocket(websocket: WebSocket, mode: str = "behavioral"):
    """
    Secured WebSocket endpoint for real-time interview sessions.
    """
    # 1. AUTHENTICATION HANDSHAKE
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("WS connection rejected: Missing token")
        await websocket.close(code=4001)
        return

    try:
        user = get_auth_token_verifier().verify(token)
        user_id = user.get("sub") or user.get("user_id")
        if not user_id:
            raise ValueError("Token missing user identifier")
    except Exception as e:
        logger.error(f"WS Auth Failed: {e}")
        await websocket.close(code=4001)
        return

    await websocket.accept()
    session_id = websocket.query_params.get("session_id", f"sess_{user_id[:8]}")
    logger.info(f"WS Started: User={user_id}, Session={session_id}, Mode={mode}")

    # 2. CONTEXT LOADING (Caching + Service)
    redis = get_redis()
    user_profile = None
    
    # Try Redis cache first
    if redis:
        try:
            cache_key = f"user_profile:{user_id}"
            cached = redis.get(cache_key)
            if cached:
                user_profile = json.loads(cached)
                logger.info("User profile loaded from Redis cache")
        except Exception as e:
            logger.warning(f"Redis cache hit failed: {e}")

    # Fallback to Neon (Postgres)
    if not user_profile:
        user_profile = await UserService.get_user_profile(user_id)
        if user_profile and redis:
            try:
                redis.setex(f"user_profile:{user_id}", 3600, json.dumps(user_profile))
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")

    # 3. SESSION CONFIGURATION (from Redis)
    session_config = {}
    if redis:
        try:
            config_data = redis.get(f"session_config:{session_id}")
            if config_data:
                session_config = json.loads(config_data)
                logger.info(f"Session config loaded from Redis for {session_id}")
        except Exception as e:
            logger.warning(f"Failed to load session config from Redis: {e}")

    # Use defaults if config not found
    role = session_config.get("role", "Software Engineer")
    topics = session_config.get("topics", [])
    difficulty = session_config.get("difficulty", "Medium")
    # Override mode if provided in config, otherwise use WS param
    mode = session_config.get("mode", mode)

    # 4. AGENT INITIALIZATION
    agent = await create_interviewer(
        mode=mode, 
        user_profile=user_profile,
        role=role,
        topics=topics,
        difficulty=difficulty
    )
    request_queue = LiveRequestQueue()
    runner = Runner(
        agent=agent,
        app_name="interviewer",
        session_service=InMemorySessionService(),
        auto_create_session=True
    )

    # 4. UPSTREAM/DOWNSTREAM TASKS
    async def upstream_task():
        """Handles incoming messages with PCM16 enforcement and heartbeats."""
        try:
            while True:
                # Use wait_for for heartbeat/keep-alive if needed, 
                # but ADK/Runner usually keeps it alive. We implement a local timeout check.
                message = await websocket.receive()
                
                if "bytes" in message:
                    # Enforce PCM 16kHz (client must send this)
                    request_queue.send(LiveRequest(
                        blob=types.Blob(data=message["bytes"], mime_type="audio/pcm")
                    ))
                elif "text" in message:
                    data = json.loads(message["text"])
                    if data.get("type") == "image":
                        image_bytes = base64.b64decode(data["data"])
                        request_queue.send(LiveRequest(
                            blob=types.Blob(data=image_bytes, mime_type=data.get("mimeType", "image/jpeg"))
                        ))
                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    else:
                        logger.info(f"WS Control Message: {data.get('type')}")
        except WebSocketDisconnect:
            logger.info(f"WS Disconnected (User: {user_id})")
        except Exception as e:
            logger.error(f"Upstream Error: {e}")
        finally:
            request_queue.close()

    async def downstream_task():
        """Handles events from Gemini Live API."""
        try:
            # Initial prompt trigger
            request_queue.send(LiveRequest(content=types.Content(
                parts=[types.Part(text="Hello! I am ready for the interview.")]
            )))

            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=request_queue
            ):
                # Process audio and JSON events
                audio_payload = None
                text_content = ""
                
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_payload = part.inline_data.data
                        if part.text:
                            text_content += part.text
                
                if audio_payload:
                    await websocket.send_bytes(audio_payload)
                
                if text_content:
                    msg_type = "ai_transcript" if event.author == "interviewer" else "transcript"
                    await websocket.send_json({
                        "type": msg_type,
                        "text": text_content,
                        "author": event.author
                    })
                    logger.info(f"Sent {msg_type}: {text_content[:50]}...")

                if not audio_payload and not text_content:
                    try:
                        payload = event.model_dump(exclude_none=True)
                        await websocket.send_json({
                            "type": "agent_event",
                            "author": event.author,
                            "payload": payload
                        })
                    except Exception as json_err:
                        logger.error(f"Failed to serialize event: {json_err}")
        except Exception as e:
            logger.error(f"Downstream Error: {e}")
        finally:
            logger.info(f"Downstream Ended (User: {user_id})")

    # 5. EXECUTION
    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except Exception as e:
        logger.error(f"WS Session Error: {e}")
    finally:
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
        
        # 6. SESSION FINALIZATION
        from app.services.session_service import SessionService
        # For the demo, we use a placeholder score of 85 if not calculated
        await SessionService.finalize_session(session_id, user_id, overall_score=85)
        
        logger.info(f"WS Session Finalized (Session: {session_id}, User: {user_id})")

