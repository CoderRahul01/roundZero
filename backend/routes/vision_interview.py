"""
Vision Agents Interview API endpoints.

This module provides REST API endpoints for live video interview sessions
using Vision Agents integration.
"""

import uuid
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from auth.jwt_handler import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["vision-interview"])


# Request/Response Models
class StartLiveSessionRequest(BaseModel):
    """Request model for starting a live interview session."""
    role: str = Field(..., min_length=1, max_length=100, description="Interview role")
    topics: List[str] = Field(..., min_items=1, max_items=10, description="Interview topics")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$", description="Question difficulty")
    mode: str = Field(..., pattern="^(practice|mock|coaching)$", description="Interview mode")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "Software Engineer",
                "topics": ["Python", "System Design", "Algorithms"],
                "difficulty": "medium",
                "mode": "practice"
            }
        }


class StartLiveSessionResponse(BaseModel):
    """Response model for start live session."""
    session_id: str
    call_id: str
    stream_token: str
    stream_api_key: str
    status: str
    question_count: int


async def check_rate_limit(candidate_id: str) -> bool:
    """
    Check if user has exceeded rate limit (10 sessions per day).
    
    TODO: Implement Redis-based rate limiting
    """
    # Placeholder - implement rate limiting
    return True


async def get_stream_client():
    """
    Get Stream.io client instance.
    
    TODO: Implement Stream.io client initialization
    """
    # Placeholder
    return None


async def get_mongo_repository():
    """
    Get MongoDB repository instance.
    
    TODO: Implement repository dependency injection
    """
    # Placeholder
    from data.live_session_repository import LiveSessionRepository
    import os
    
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB URI not configured"
        )
    
    return LiveSessionRepository(mongo_uri)


@router.post("/start-live-session", response_model=StartLiveSessionResponse)
async def start_live_session(
    request: StartLiveSessionRequest,
    candidate_id: str = Depends(get_current_user_id),
    mongo_repo = Depends(get_mongo_repository)
):
    """
    Start a new live interview session with video call.
    
    Flow:
    1. Validate authentication
    2. Check rate limit (10 sessions per day)
    3. Create Stream.io call
    4. Initialize RoundZeroAgent
    5. Store session metadata
    6. Return call_id and session_id
    
    Args:
        request: Session configuration
        candidate_id: Authenticated user ID
        mongo_repo: MongoDB repository
    
    Returns:
        Session details including call_id and stream_token
    
    Raises:
        HTTPException: 429 if rate limit exceeded, 500 on failure
    """
    try:
        # Check rate limit
        if not await check_rate_limit(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 10 live sessions per day."
            )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create Stream.io call
        call_id = f"call_{session_id[:8]}"
        
        # Generate Stream token (placeholder - implement with Stream SDK)
        stream_token = "placeholder_token"
        
        # Create session in MongoDB
        await mongo_repo.create_session(
            session_id=session_id,
            candidate_id=candidate_id,
            call_id=call_id,
            role=request.role,
            topics=request.topics,
            difficulty=request.difficulty,
            mode=request.mode,
            question_count=5
        )
        
        logger.info(
            f"Started live session {session_id} for candidate {candidate_id} "
            f"(role={request.role}, difficulty={request.difficulty})"
        )
        
        # Initialize RoundZeroAgent (will be done in background)
        # This will be implemented when all processors are complete
        
        return StartLiveSessionResponse(
            session_id=session_id,
            call_id=call_id,
            stream_token=stream_token,
            stream_api_key=os.getenv("STREAM_API_KEY", ""),
            status="initialized",
            question_count=5
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start live session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize interview session"
        )


@router.delete("/{session_id}/end-live-session")
async def end_live_session(
    session_id: str,
    candidate_id: str = Depends(get_current_user_id),
    mongo_repo = Depends(get_mongo_repository)
):
    """
    End a live interview session.
    
    Flow:
    1. Validate session ownership
    2. Complete interview (generate summary)
    3. Store final data
    4. Cleanup resources
    
    Args:
        session_id: Session identifier
        candidate_id: Authenticated user ID
        mongo_repo: MongoDB repository
    
    Returns:
        Completion status
    
    Raises:
        HTTPException: 404 if session not found, 403 if not owner
    """
    try:
        # Get session
        session = await mongo_repo.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Validate ownership
        if session["candidate_id"] != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session"
            )
        
        # TODO: Complete interview and generate summary
        # This will be implemented when RoundZeroAgent is complete
        
        logger.info(f"Ended live session {session_id}")
        
        return {"status": "completed", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end live session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end interview session"
        )


@router.get("/{session_id}/live-state")
async def get_live_state(
    session_id: str,
    candidate_id: str = Depends(get_current_user_id),
    mongo_repo = Depends(get_mongo_repository)
):
    """
    Get current state of live interview session.
    
    Returns real-time state including:
    - Current question progress
    - Latest emotion data
    - Current speech metrics
    - AI state (listening/thinking/speaking)
    
    Args:
        session_id: Session identifier
        candidate_id: Authenticated user ID
        mongo_repo: MongoDB repository
    
    Returns:
        Current session state
    
    Raises:
        HTTPException: 404 if session not found, 403 if not owner
    """
    try:
        # Get session
        session = await mongo_repo.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Validate ownership
        if session["candidate_id"] != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # TODO: Get real-time state from RoundZeroAgent
        # This will be implemented when RoundZeroAgent is complete
        
        # Return placeholder state
        return {
            "session_id": session_id,
            "status": "active",
            "current_question": 1,
            "total_questions": session.get("question_count", 5),
            "ai_state": "listening",
            "emotion": {
                "emotion": "neutral",
                "confidence_score": 50,
                "engagement_level": "medium"
            },
            "speech_metrics": {
                "filler_word_count": 0,
                "speech_pace": 0,
                "long_pause_count": 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get live state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session state"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Vision Agents integration.
    
    Tests connectivity to all required services:
    - MongoDB
    - Gemini API
    - Claude API
    - Deepgram API
    - Stream.io
    
    Returns:
        Health status with service availability
    """
    import os
    
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check MongoDB
    try:
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri:
            from data.live_session_repository import LiveSessionRepository
            repo = LiveSessionRepository(mongo_uri)
            is_healthy = await repo.ping()
            health_status["services"]["mongodb"] = "healthy" if is_healthy else "unhealthy"
            await repo.close()
        else:
            health_status["services"]["mongodb"] = "not_configured"
    except Exception as e:
        health_status["services"]["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Gemini API
    gemini_key = os.getenv("GEMINI_API_KEY")
    health_status["services"]["gemini"] = "configured" if gemini_key else "not_configured"
    
    # Check Claude API
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    health_status["services"]["claude"] = "configured" if claude_key else "not_configured"
    
    # Check Deepgram API
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    health_status["services"]["deepgram"] = "configured" if deepgram_key else "not_configured"
    
    # Check Stream.io
    stream_key = os.getenv("STREAM_API_KEY")
    health_status["services"]["stream"] = "configured" if stream_key else "not_configured"
    
    # Determine overall status
    if any("not_configured" in str(v) or "error" in str(v) for v in health_status["services"].values()):
        health_status["status"] = "degraded"
    
    return health_status
