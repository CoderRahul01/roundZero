import uuid
from fastapi import APIRouter, HTTPException, Request
from app.core.logger import logger
from app.api.schemas import StartSessionPayload, StartSessionResponse
from app.agents.interviewer.tools import fetch_interview_questions

router = APIRouter()

@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(payload: StartSessionPayload, request: Request):
    """
    Initializes a new interview session.
    """
    session_id = str(uuid.uuid4())
    
    # Extract user_id from the authenticated user context (via JWTAuthMiddleware)
    user = getattr(request.state, "user", None)
    user_id = user.get("sub") or user.get("user_id") if user else (payload.user_id or f"user_{uuid.uuid4().hex[:8]}")
    
    # Capture the token for WebSocket use
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    logger.info(f"Starting session {session_id} for user {user_id}")
    
    # Fetch initial questions using the tool
    questions = await fetch_interview_questions(
        role=payload.role,
        topics=payload.topics,
        difficulty=payload.difficulty.value if hasattr(payload.difficulty, "value") else payload.difficulty
    )
    
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to fetch interview questions")
    
    first_question = questions[0]["question"]
    
    # Persist session config in Redis for WebSocket retrieval
    from app.services.session_service import SessionService
    from app.services.user_service import UserService
    
    config_data = payload.dict()
    # Fetch user profile for personalization
    try:
        profile = await UserService.get_profile(user_id)
        if profile:
            config_data["user_profile"] = profile
            logger.info(f"Profile injected for session {session_id}")
    except Exception as e:
        logger.warning(f"Could not fetch profile for session {session_id}: {e}")

    # If difficulty is an enum, convert to value
    if hasattr(payload.difficulty, "value"):
        config_data["difficulty"] = payload.difficulty.value
    if hasattr(payload.mode, "value"):
        config_data["mode"] = payload.mode.value
    
    # Store config for 1 hour
    await SessionService.save_session(session_id, config_data)
    logger.info(f"Session config persisted for {session_id}")

    return StartSessionResponse(
        session_id=session_id,
        user_id=user_id,
        first_question=first_question,
        question_index=0,
        total_questions=len(questions),
        memory_context="No prior memory found.",
        call_id=f"call_{uuid.uuid4().hex[:12]}",
        token=token,
        backend_token=token,
        stream_api_key=None
    )

@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """
    Finalizes an interview session.
    """
    logger.info(f"Ending session {session_id}")
    return {"session_id": session_id, "status": "ended"}

@router.get("/session/{session_id}/report")
async def get_report(session_id: str):
    """
    Fetches the report for a completed session. 
    Currently returns 404 as real report generation is being implemented.
    """
    logger.info(f"Report requested for {session_id}")
    raise HTTPException(status_code=404, detail="Report not yet available for this session.")
