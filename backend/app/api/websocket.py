import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import adk
from google.adk.agents import RunConfig, LiveRequestQueue
from google.genai import types as genai_types
from app.agents.interviewer.agent import create_interviewer
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
):
    """
    WebSocket endpoint for bidirectional interview streaming.
    Uses ADK Runner.run_live for Gemini 2.0 Flash Live communication.
    """
    logger.info(f"DEBUG: WebSocket request received for user={user_id}, session={session_id}")
    
    try:
        await websocket.accept()
        logger.info(f"WebSocket handshake completed for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket accept failed: {e}")
        return

    # Extract mode from query params
    params = dict(websocket.query_params)
    mode = params.get("mode", "behavioral")
    
    queue = None
    
    try:
        # 1. Retrieve session context
        session_data = await SessionService.get_session(session_id)
        user_profile = session_data.get("user_profile")
        
        # 2. Create Interviewer Agent
        agent = await create_interviewer(
            mode=mode,
            user_profile=user_profile,
            role=session_data.get("role", "Software Engineer"),
            topics=session_data.get("topics", []),
            difficulty=session_data.get("difficulty", "Medium")
        )
        logger.info(f"Interviewer Agent initialized for session {session_id}")
        
        # 3. Initialize ADK Runner and Queue
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        session_service = InMemorySessionService()

        # Pre-create the ADK session so run_live() can find it
        adk_session = await session_service.create_session(
            app_name="interviewer",
            user_id=user_id,
            session_id=session_id
        )

        runner = adk.Runner(
            agent=agent, 
            session_service=session_service, 
            app_name="interviewer"
        )
        
        # Fresh queue PER connection
        queue = LiveRequestQueue()
        
        # Detect whether model requires AUDIO-only modality
        # Native-audio models (gemini-2.5-flash-native-audio-*) cannot return TEXT
        from app.core.settings import get_settings as _get_settings
        _settings = _get_settings()
        is_native_audio = "native-audio" in _settings.gemini_model.lower()
        
        # Configure RunConfig — response_modalities must be string list per ADK API
        config = RunConfig(
            response_modalities=["AUDIO"] if is_native_audio else ["TEXT"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name='Puck'
                    )
                )
            ),
            # Enable transcription so frontend gets text subtitles alongside audio
            output_audio_transcription=genai_types.AudioTranscriptionConfig()
        )

        # 4. Start run_live — use user_id/session_id directly (session param deprecated)
        live_events = runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=queue,
            run_config=config
        )

        async def upstream():
            """Client -> LiveRequestQueue"""
            try:
                while True:
                    receive_data = await websocket.receive()
                    
                    if "text" in receive_data:
                        text_content = receive_data["text"]
                        try:
                            payload = json.loads(text_content)
                            msg_type = payload.get("type")
                            
                            if msg_type == "text":
                                queue.send_content(genai_types.Content(
                                    role="user",
                                    parts=[genai_types.Part(text=payload["content"])]
                                ))
                            elif msg_type == "end_session":
                                queue.close()
                                break
                        except json.JSONDecodeError:
                            # Fallback for raw text
                            queue.send_content(genai_types.Content(
                                role="user",
                                parts=[genai_types.Part(text=text_content)]
                            ))
                    
                    elif "bytes" in receive_data:
                        # Inbound audio frame (expecting 16kHz PCM)
                        queue.send_realtime(genai_types.Blob(
                            data=receive_data["bytes"],
                            mime_type="audio/pcm;rate=16000"
                        ))
            except WebSocketDisconnect:
                logger.info(f"Upstream disconnected for session {session_id}")
            except Exception as e:
                logger.error(f"Error in upstream: {e}")

        async def downstream():
            """run_live() events -> Client"""
            try:
                async for event in live_events:
                    # Handle content from the model (interviewer agent)
                    if event.author == "interviewer":
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.text:
                                    await websocket.send_json({
                                        "type": "text",
                                        "content": part.text
                                    })
                                # Audio bytes: ADK uses inline_data for audio chunks
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    await websocket.send_bytes(part.inline_data.data)
                    
                    # Forward AI output transcription as a text subtitle event
                    # (Native-audio model streams audio + provides text transcription)
                    if event.output_transcription and event.output_transcription.text:
                        await websocket.send_json({
                            "type": "text",
                            "content": event.output_transcription.text
                        })
                    
                    # Forward user/input transcription
                    if event.input_transcription:
                         await websocket.send_json({
                            "type": "transcription",
                            "source": "user",
                            "content": event.input_transcription.text,
                            "is_final": getattr(event.input_transcription, 'is_final', True)
                        })

            except Exception as e:
                logger.error(f"Error in downstream task: {e}")

        # Execute upstream and downstream concurrently
        await asyncio.gather(
            upstream(),
            downstream(),
            return_exceptions=True
        )

    except Exception as e:
        logger.error(f"WebSocket execution error: {str(e)}", exc_info=True)
        if not websocket.client_state.name == "DISCONNECTED":
            try:
                await websocket.close(code=1011)
            except:
                pass
    finally:
        # CRITICAL CLEANUP
        if queue:
            queue.close()
            logger.info(f"LiveRequestQueue closed for session {session_id}")
        logger.info(f"WebSocket session finished for {session_id}")
