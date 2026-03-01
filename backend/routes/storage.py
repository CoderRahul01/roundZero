"""
Storage API Routes for Enhanced Interview Experience

FastAPI endpoints for retrieving interview transcripts, analysis results, and follow-ups.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from data.mongo_transcript_repository import (
    MongoTranscriptRepository,
    InterviewTranscript,
    TranscriptEntry
)
from data.mongo_analysis_repository import (
    MongoAnalysisRepository,
    AnalysisResult
)
from data.mongo_followup_repository import (
    MongoFollowUpRepository,
    FollowUpQuestion
)
from middleware import get_current_user

router = APIRouter(prefix="/interview", tags=["storage"])

# Initialize repositories
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable not set")

transcript_repo = MongoTranscriptRepository(MONGODB_URI)
analysis_repo = MongoAnalysisRepository(MONGODB_URI)
followup_repo = MongoFollowUpRepository(MONGODB_URI)


# Response models
class TranscriptResponse(BaseModel):
    """Response model for transcript retrieval."""
    session_id: str
    user_id: str
    entries: List[TranscriptEntry]
    started_at: datetime
    completed_at: Optional[datetime]
    total_entries: int


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    session_id: str
    results: List[AnalysisResult]
    total_questions: int
    statistics: dict


class FollowUpResponse(BaseModel):
    """Response model for follow-up questions."""
    session_id: str
    follow_ups: List[FollowUpQuestion]
    total_follow_ups: int
    statistics: dict


# ===== Transcript Endpoints =====

@router.get(
    "/{session_id}/transcript",
    response_model=TranscriptResponse,
    summary="Get interview transcript",
    description="Retrieve complete transcript for an interview session with all interactions"
)
async def get_transcript(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete interview transcript.
    
    Returns all questions, answers, and follow-ups in chronological order.
    
    Requirements: 25.6, 14.10
    """
    try:
        # Retrieve transcript
        transcript = await transcript_repo.get_transcript(session_id)
        
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for session {session_id}"
            )
        
        # Authorization check: ensure user owns this session
        if transcript.user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this transcript"
            )
        
        return TranscriptResponse(
            session_id=transcript.session_id,
            user_id=transcript.user_id,
            entries=transcript.entries,
            started_at=transcript.started_at,
            completed_at=transcript.completed_at,
            total_entries=len(transcript.entries)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )


@router.get(
    "/user/{user_id}/transcripts",
    response_model=List[TranscriptResponse],
    summary="Get user's interview transcripts",
    description="Retrieve all transcripts for a user"
)
async def get_user_transcripts(
    user_id: str,
    limit: int = 10,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all transcripts for a user.
    
    Supports pagination with limit and skip parameters.
    """
    try:
        # Authorization check
        if user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access these transcripts"
            )
        
        # Retrieve transcripts
        transcripts = await transcript_repo.get_transcripts_by_user(
            user_id=user_id,
            limit=limit,
            skip=skip
        )
        
        return [
            TranscriptResponse(
                session_id=t.session_id,
                user_id=t.user_id,
                entries=t.entries,
                started_at=t.started_at,
                completed_at=t.completed_at,
                total_entries=len(t.entries)
            )
            for t in transcripts
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcripts: {str(e)}"
        )


# ===== Analysis Endpoints =====

@router.get(
    "/{session_id}/analysis",
    response_model=AnalysisResponse,
    summary="Get analysis results",
    description="Retrieve multi-modal analysis results for all questions in a session"
)
async def get_analysis(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete analysis results for a session.
    
    Includes tone, pitch, facial analysis, and answer evaluations.
    
    Requirements: 25.7, 15.9, 15.10
    """
    try:
        # First verify user owns this session by checking transcript
        transcript = await transcript_repo.get_transcript(session_id)
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        # Authorization check
        if transcript.user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this analysis"
            )
        
        # Retrieve analysis results
        results = await analysis_repo.get_analysis(session_id)
        
        # Get statistics
        statistics = await analysis_repo.get_session_statistics(session_id)
        
        return AnalysisResponse(
            session_id=session_id,
            results=results,
            total_questions=len(results),
            statistics=statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )


@router.get(
    "/{session_id}/analysis/{question_number}",
    response_model=AnalysisResult,
    summary="Get analysis for specific question",
    description="Retrieve analysis result for a specific question number"
)
async def get_question_analysis(
    session_id: str,
    question_number: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get analysis result for a specific question.
    
    Requirements: 15.8
    """
    try:
        # Verify authorization
        transcript = await transcript_repo.get_transcript(session_id)
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        if transcript.user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this analysis"
            )
        
        # Retrieve analysis
        result = await analysis_repo.get_question_analysis(
            session_id=session_id,
            question_number=question_number
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for question {question_number}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve question analysis: {str(e)}"
        )


# ===== Follow-Up Endpoints =====

@router.get(
    "/{session_id}/follow-ups",
    response_model=FollowUpResponse,
    summary="Get follow-up questions",
    description="Retrieve all follow-up questions for a session"
)
async def get_followups(
    session_id: str,
    main_question_number: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get follow-up questions for a session.
    
    Optionally filter by main question number.
    
    Requirements: 25.5, 9.9, 9.10
    """
    try:
        # Verify authorization
        transcript = await transcript_repo.get_transcript(session_id)
        if not transcript:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        if transcript.user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access these follow-ups"
            )
        
        # Retrieve follow-ups
        follow_ups = await followup_repo.get_followups(
            session_id=session_id,
            main_question_number=main_question_number
        )
        
        # Get statistics
        statistics = await followup_repo.get_session_statistics(session_id)
        
        return FollowUpResponse(
            session_id=session_id,
            follow_ups=follow_ups,
            total_follow_ups=len(follow_ups),
            statistics=statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve follow-ups: {str(e)}"
        )


# ===== Health Check =====

@router.get(
    "/storage/health",
    summary="Storage health check",
    description="Check MongoDB connection health"
)
async def storage_health():
    """
    Check storage layer health.
    
    Pings all MongoDB repositories to verify connections.
    """
    try:
        transcript_ok = await transcript_repo.ping()
        analysis_ok = await analysis_repo.ping()
        followup_ok = await followup_repo.ping()
        
        all_ok = transcript_ok and analysis_ok and followup_ok
        
        return {
            "status": "healthy" if all_ok else "degraded",
            "repositories": {
                "transcript": "ok" if transcript_ok else "error",
                "analysis": "ok" if analysis_ok else "error",
                "followup": "ok" if followup_ok else "error"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


# Cleanup on shutdown
async def cleanup_repositories():
    """Close all repository connections."""
    await transcript_repo.close()
    await analysis_repo.close()
    await followup_repo.close()
