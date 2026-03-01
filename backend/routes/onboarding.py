"""
Onboarding API Routes

FastAPI endpoints for managing interview onboarding flow.
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from anthropic import AsyncAnthropic

from agent.onboarding_manager import OnboardingManager
from services.tts_service import ElevenLabsTTSService
from middleware import get_current_user

router = APIRouter(prefix="/interview", tags=["onboarding"])
logger = logging.getLogger(__name__)


class StartInterviewRequest(BaseModel):
    """Request model for starting an interview."""
    first_name: Optional[str] = None
    question_count: int = 5


class ConfirmReadinessRequest(BaseModel):
    """Request model for readiness confirmation."""
    candidate_response: str
    attempt: int = 1


# Initialize services (singleton pattern)
_onboarding_manager: Optional[OnboardingManager] = None


def get_onboarding_manager() -> OnboardingManager:
    """Get or create OnboardingManager instance."""
    global _onboarding_manager
    
    if _onboarding_manager is None:
        # Initialize TTS service
        tts_service = ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        )
        
        # Initialize Claude client
        claude_client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        _onboarding_manager = OnboardingManager(
            tts_service=tts_service,
            claude_client=claude_client
        )
        
        logger.info("OnboardingManager initialized")
    
    return _onboarding_manager


@router.post("/start")
async def start_interview(
    request: StartInterviewRequest,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Start interview with personalized onboarding.
    
    Generates greeting and introduction audio, returns session information.
    """
    try:
        # Generate session ID (in production, this would come from database)
        session_id = f"session_{current_user.get('user_id', 'anonymous')}_{int(os.urandom(4).hex(), 16)}"
        
        # Get onboarding manager
        onboarding_manager = get_onboarding_manager()
        
        # Start onboarding flow
        onboarding_result = await onboarding_manager.start_onboarding(
            session_id=session_id,
            first_name=request.first_name,
            question_count=request.question_count
        )
        
        logger.info(f"Started onboarding for session {session_id}")
        
        return {
            "session_id": session_id,
            "greeting_text": onboarding_result["greeting_text"],
            "introduction_text": onboarding_result["introduction_text"],
            "question_count": request.question_count,
            "readiness_question": "Are you ready to start?",
            "status": "onboarding_started"
        }
    
    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start interview: {str(e)}"
        )


@router.post("/{session_id}/confirm-readiness")
async def confirm_readiness(
    session_id: str,
    request: ConfirmReadinessRequest,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Confirm candidate readiness using Claude interpretation.
    
    Interprets candidate's response to "Are you ready?" question.
    """
    try:
        # Get onboarding manager
        onboarding_manager = get_onboarding_manager()
        
        # Confirm readiness
        readiness_result = await onboarding_manager.confirm_readiness(
            candidate_response=request.candidate_response,
            attempt=request.attempt,
            max_attempts=3
        )
        
        logger.info(
            f"Readiness confirmation for session {session_id}: "
            f"{readiness_result['classification']}"
        )
        
        return {
            "session_id": session_id,
            "ready": readiness_result["ready"],
            "message": readiness_result["message"],
            "classification": readiness_result["classification"],
            "retry": readiness_result.get("retry", False),
            "next_step": "countdown" if readiness_result["ready"] else "wait"
        }
    
    except Exception as e:
        logger.error(f"Error confirming readiness: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm readiness: {str(e)}"
        )


@router.get("/{session_id}/onboarding-status")
async def get_onboarding_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current onboarding status for a session.
    
    Returns information about onboarding progress.
    """
    # In production, this would query the database
    # For now, return basic status
    return {
        "session_id": session_id,
        "onboarding_completed": False,
        "current_step": "greeting",
        "steps": ["greeting", "introduction", "readiness_check", "countdown"]
    }
