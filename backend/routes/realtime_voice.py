"""
Real-Time Voice Interaction API Routes

FastAPI endpoints for managing real-time voice interaction sessions.
"""

import asyncio
import json
import os
import time
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from anthropic import AsyncAnthropic

from agent.voice_flow_controller import VoiceFlowController
from agent.silence_detector import SilenceDetector
from agent.presence_verifier import PresenceVerifier
from agent.answer_analyzer import AnswerAnalyzer
from agent.interruption_engine import InterruptionEngine
from agent.context_tracker import ContextTracker
from agent.speech_buffer import SpeechBuffer
from agent.gemini_embedding_service import GeminiEmbeddingService
from services.tts_service import TTSService
from rate_limit import RateLimiter
from middleware import get_current_user

router = APIRouter(prefix="/session", tags=["realtime-voice"])

# Global registry for active voice sessions
_voice_sessions: Dict[str, VoiceFlowController] = {}

# Rate limiter for voice sessions
voice_rate_limiter = RateLimiter(max_calls=10, window_seconds=86400)  # 10 per day


class StartRealTimeVoiceRequest(BaseModel):
    enable_interruptions: bool = True
    max_interruptions_per_question: int = 2
    silence_threshold_seconds: float = 10.0
    answer_complete_threshold_seconds: float = 3.0


class ManualInterruptRequest(BaseModel):
    reason: str
    message: Optional[str] = None


async def initialize_voice_controller(
    session_id: str,
    config: StartRealTimeVoiceRequest
) -> VoiceFlowController:
    """Initialize all components and create VoiceFlowController."""
    
    # Initialize AI services
    claude_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    embedding_service = GeminiEmbeddingService()
    
    # Initialize TTS service
    tts_service = TTSService()
    
    # Initialize STT service (placeholder - will be connected via WebSocket)
    stt_service = None  # Will be set up in WebSocket handler
    
    # Initialize components
    silence_detector = SilenceDetector(
        silence_threshold_db=-40.0,
        brief_pause_threshold=2.0,
        prolonged_silence_threshold=config.silence_threshold_seconds
    )
    
    speech_buffer = SpeechBuffer(analysis_word_threshold=20)
    
    context_tracker = ContextTracker(
        claude_client=claude_client,
        history_size=5
    )
    
    answer_analyzer = AnswerAnalyzer(
        claude_client=claude_client,
        embedding_service=embedding_service,
        relevance_threshold=0.3,
        analysis_interval=5.0
    )
    
    interruption_engine = InterruptionEngine(
        max_interruptions_per_question=config.max_interruptions_per_question
    )
    
    presence_verifier = PresenceVerifier(
        tts_service=tts_service,
        stt_service=stt_service,
        claude_client=claude_client,
        max_attempts=3,
        response_timeout=10.0
    )
    
    # Create voice flow controller
    controller = VoiceFlowController(
        session_id=session_id,
        silence_detector=silence_detector,
        presence_verifier=presence_verifier,
        answer_analyzer=answer_analyzer,
        interruption_engine=interruption_engine,
        context_tracker=context_tracker,
        speech_buffer=speech_buffer,
        tts_service=tts_service,
        stt_service=stt_service
    )
    
    return controller


@router.post("/{session_id}/voice/realtime/start")
async def start_realtime_voice(
    session_id: str,
    request: StartRealTimeVoiceRequest
) -> dict:
    """Initialize real-time voice interaction for a session."""
    
    # Check rate limit (using session_id as key)
    if not voice_rate_limiter.allow(session_id):
        raise HTTPException(
            status_code=429,
            detail="Daily session limit reached. Try again tomorrow."
        )
    
    # Initialize voice flow controller
    try:
        voice_controller = await initialize_voice_controller(
            session_id=session_id,
            config=request
        )
        
        # Store in session registry
        _voice_sessions[session_id] = voice_controller
        
        # Get remaining rate limit
        remaining = voice_rate_limiter.get_remaining(session_id, 10, 86400)
        
        return {
            "session_id": session_id,
            "websocket_url": f"/session/{session_id}/voice/realtime/stream",
            "deepgram_config": {
                "model": "nova-2",
                "language": "en-US",
                "interim_results": True
            },
            "state": "IDLE",
            "rate_limit_remaining": remaining
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize voice session: {str(e)}"
        )


@router.websocket("/{session_id}/voice/realtime/stream")
async def realtime_voice_stream(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for real-time voice interaction."""
    
    await websocket.accept()
    
    # Get voice controller for this session
    voice_controller = _voice_sessions.get(session_id)
    
    if not voice_controller:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    # Register WebSocket with controller
    voice_controller.set_websocket(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] == "transcript_segment":
                await voice_controller.handle_speech_input(
                    transcript_segment=message["text"],
                    is_final=message.get("is_final", False)
                )
            
            elif message["type"] == "answer_complete":
                await voice_controller.handle_silence_detected(3.0)
            
            elif message["type"] == "audio_chunk":
                # Process audio for silence detection
                audio_level = message.get("audio_level_db", -50.0)
                await voice_controller.silence_detector.process_audio_level(
                    audio_level
                )
            
            elif message["type"] == "start_question":
                # Start interview with first question
                question = message.get("question", "")
                if question:
                    await voice_controller.start_interview(question)
    
    except WebSocketDisconnect:
        # Cleanup on disconnect
        if session_id in _voice_sessions:
            del _voice_sessions[session_id]
    
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        if session_id in _voice_sessions:
            del _voice_sessions[session_id]


@router.post("/{session_id}/voice/realtime/interrupt")
async def manual_interrupt(
    session_id: str,
    request: ManualInterruptRequest
) -> dict:
    """Manually trigger interruption (for testing or emergency stop)."""
    
    voice_controller = _voice_sessions.get(session_id)
    
    if not voice_controller:
        raise HTTPException(status_code=404, detail="Session not found")
    
    message = request.message or "Let me stop you there"
    
    await voice_controller.handle_off_topic_detected(message)
    
    return {
        "success": True,
        "interruption_sent": True,
        "new_state": voice_controller.state.conversation_state.value
    }


@router.get("/{session_id}/voice/realtime/status")
async def get_realtime_status(session_id: str) -> dict:
    """Get current status of real-time voice session."""
    
    voice_controller = _voice_sessions.get(session_id)
    
    if not voice_controller:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": voice_controller.state.conversation_state.value,
        "current_question": voice_controller.state.current_question,
        "current_question_topic": voice_controller.state.current_question_topic,
        "speech_buffer_word_count": voice_controller.speech_buffer.word_count(),
        "interruption_count": voice_controller.state.interruption_count,
        "silence_duration": voice_controller.silence_detector.get_current_silence_duration(),
        "presence_check_attempts": voice_controller.state.presence_check_attempts,
        "performance_metrics": {
            "stt_failures": 0,
            "tts_failures": 0,
            "claude_failures": 0
        }
    }
