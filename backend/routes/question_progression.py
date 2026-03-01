"""
Question Progression API Routes

FastAPI endpoints for managing question progression and feedback.
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from anthropic import AsyncAnthropic

from agent.question_progression_engine import QuestionProgressionEngine
from services.tts_service import ElevenLabsTTSService
from middleware import get_current_user

router = APIRouter(prefix="/interview", tags=["question-progression"])
logger = logging.getLogger(__name__)


class GetCurrentQuestionResponse(BaseModel):
    """Response model for current question."""
    session_id: str
    question_number: int
    total_questions: int
    question_text: str
    question_topic: Optional[str] = None
    progress_percentage: float
    is_final: bool


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer."""
    answer_text: str
    audio_duration_seconds: Optional[float] = None


class SubmitAnswerResponse(BaseModel):
    """Response model for answer submission."""
    session_id: str
    feedback: str
    next_question_number: Optional[int] = None
    has_next_question: bool
    is_complete: bool


# Global registry for progression engines per session
_progression_engines: dict[str, QuestionProgressionEngine] = {}


def get_progression_engine(session_id: str) -> QuestionProgressionEngine:
    """Get or create QuestionProgressionEngine for session."""
    if session_id not in _progression_engines:
        # Initialize services
        tts_service = ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        )
        
        claude_client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        engine = QuestionProgressionEngine(
            tts_service=tts_service,
            claude_client=claude_client
        )
        
        _progression_engines[session_id] = engine
        logger.info(f"Created QuestionProgressionEngine for session {session_id}")
    
    return _progression_engines[session_id]


@router.get("/{session_id}/current-question")
async def get_current_question(
    session_id: str,
    current_user: dict = Depends(get_current_user)
) -> GetCurrentQuestionResponse:
    """
    Get the current question for the session.
    
    Returns question text, progress, and metadata.
    """
    try:
        engine = get_progression_engine(session_id)
        
        # Get current question
        question = engine.get_current_question()
        if not question:
            raise HTTPException(
                status_code=404,
                detail="No current question available"
            )
        
        # Get progress
        progress = engine.get_progress()
        
        return GetCurrentQuestionResponse(
            session_id=session_id,
            question_number=progress["current"],
            total_questions=progress["total"],
            question_text=question.get("text", ""),
            question_topic=question.get("topic"),
            progress_percentage=progress["percentage"],
            is_final=progress["is_final"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current question: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current question: {str(e)}"
        )


@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    current_user: dict = Depends(get_current_user)
) -> SubmitAnswerResponse:
    """
    Submit an answer and get feedback.
    
    Generates feedback, advances to next question if available.
    """
    try:
        engine = get_progression_engine(session_id)
        
        # Get current question for feedback generation
        current_question = engine.get_current_question()
        if not current_question:
            raise HTTPException(
                status_code=400,
                detail="No active question to answer"
            )
        
        # Generate feedback
        feedback = await engine.generate_feedback(
            question=current_question.get("text", ""),
            answer=request.answer_text
        )
        
        # Move to next question
        next_question = engine.get_next_question()
        
        return SubmitAnswerResponse(
            session_id=session_id,
            feedback=feedback,
            next_question_number=engine.get_progress()["current"] if next_question else None,
            has_next_question=next_question is not None,
            is_complete=engine.is_complete()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit answer: {str(e)}"
        )


@router.get("/{session_id}/progress")
async def get_progress(
    session_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current progress information.
    
    Returns current question number, total, percentage, etc.
    """
    try:
        engine = get_progression_engine(session_id)
        progress = engine.get_progress()
        
        return {
            "session_id": session_id,
            **progress,
            "remaining": engine.get_remaining_count()
        }
    
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress: {str(e)}"
        )


@router.post("/{session_id}/load-questions")
async def load_questions(
    session_id: str,
    question_ids: list[str],
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Load questions for the session.
    
    Must be called before starting question progression.
    """
    try:
        engine = get_progression_engine(session_id)
        
        count = await engine.load_questions(
            session_id=session_id,
            question_ids=question_ids
        )
        
        return {
            "session_id": session_id,
            "questions_loaded": count,
            "status": "ready"
        }
    
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load questions: {str(e)}"
        )


@router.delete("/{session_id}/progression")
async def cleanup_progression(
    session_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Cleanup progression engine for session.
    
    Call this when interview is complete or cancelled.
    """
    try:
        if session_id in _progression_engines:
            del _progression_engines[session_id]
            logger.info(f"Cleaned up progression engine for session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "cleaned_up"
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up progression: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup progression: {str(e)}"
        )
