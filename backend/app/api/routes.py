import uuid
from fastapi import APIRouter, HTTPException, Request, Depends
from app.core.gcp_logger import gcp_logger as logger
from app.core.rate_limit import api_limiter
from app.api.schemas import StartSessionPayload, StartSessionResponse
from app.services.question_engine import QuestionEngine
from app.services.session_service import SessionService
from app.services.user_service import UserService

router = APIRouter()

@router.post("/session/prepare", dependencies=[Depends(api_limiter)])
async def prepare_session(payload: StartSessionPayload):
    """
    Pre-generates custom interview questions based on setup.
    """
    from app.services.supermemory_service import SupermemoryService
    
    session_id = str(uuid.uuid4())
    user_id = payload.user_id or f"temp_{uuid.uuid4().hex[:6]}"
    
    logger.info(f"Preparing session {session_id} for {payload.role} (User: {user_id})")
    
    # 1. Fetch User Memory (Phase 6)
    user_memory = ""
    try:
        user_memory = await SupermemoryService.get_user_memory(user_id)
        if user_memory:
            logger.info(f"Retrieved memory for {user_id}: {len(user_memory)} chars")
    except Exception as e:
        logger.warning(f"Failed to fetch Supermemory for {user_id}: {e}")

    # 2. Generate tailoring questions
    questions = await QuestionEngine.generate_questions(
        role=payload.role,
        topics=payload.topics,
        difficulty=payload.difficulty,
        user_memory=user_memory
    )
    
    # 3. Store in Redis/SessionService
    config_data = payload.dict()
    config_data["user_id"] = user_id
    config_data["questions"] = questions
    config_data["total_questions"] = len(questions)
    config_data["user_memory"] = user_memory
    
    await SessionService.save_session(session_id, config_data)
    await SessionService.create_session_neon(session_id, config_data)
    
    return {
        "session_id": session_id,
        "total_questions": len(questions),
        "questions": questions
    }

@router.post("/session/start", response_model=StartSessionResponse, dependencies=[Depends(api_limiter)])
async def start_session(payload: StartSessionPayload, request: Request):
    """
    Initializes a new interview session using pre-prepared questions.
    """
    # Check if we were passed a session_id (preferred in the new flow)
    # If not, generate a new one (legacy fallback)
    session_id = request.query_params.get("session_id") or str(uuid.uuid4())
    
    # Try to load existing config if it exists
    session_data = await SessionService.get_session(session_id) or {}
    
    # Extract user_id from the authenticated user context (via JWTAuthMiddleware)
    user = getattr(request.state, "user", None)
    user_id = user.get("sub") or user.get("user_id") if user else (payload.user_id or f"user_{uuid.uuid4().hex[:8]}")
    
    # Capture the token for WebSocket use
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    logger.info(f"Starting session {session_id} for user {user_id}")
    
    # If we don't have questions yet (e.g. direct /start call), generate them now
    questions = session_data.get("questions")
    if not questions:
        logger.info(f"No pre-prepared questions for {session_id}, generating now...")
        questions = await QuestionEngine.generate_questions(
            role=payload.role,
            topics=payload.topics,
            difficulty=payload.difficulty
        )
    
    first_question = questions[0]["question"] if questions else "Could you introduce yourself?"
    
    config_data = {**payload.dict(), **session_data}
    config_data["questions"] = questions
    
    # Fetch user profile for personalization
    try:
        profile = await UserService.get_profile(user_id)
        if profile:
            config_data["user_profile"] = profile
            logger.info(f"Profile injected for session {session_id}")
    except Exception as e:
        logger.warning(f"Could not fetch profile for session {session_id}: {e}")

    # Ensure metadata is clean for Redis
    if hasattr(payload.difficulty, "value"):
        config_data["difficulty"] = payload.difficulty.value
    if hasattr(payload.mode, "value"):
        config_data["mode"] = payload.mode.value
    
    # Store/Update config for 1 hour
    await SessionService.save_session(session_id, config_data)
    await SessionService.create_session_neon(session_id, config_data)
    logger.info(f"Session {session_id} ready for WebSocket")

    return StartSessionResponse(
        session_id=session_id,
        user_id=user_id,
        first_question=first_question,
        question_index=0,
        total_questions=len(questions),
        memory_context="Initial session context established.",
        call_id=f"call_{uuid.uuid4().hex[:12]}",
        token=token,
        backend_token=token,
        stream_api_key=None
    )

@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """
    Finalizes an interview session and triggers report generation.
    """
    from app.services.report_generator import ReportGenerator
    logger.info(f"Ending session {session_id}")
    
    # Pre-generate report to warm cache
    try:
        await ReportGenerator.generate_report(session_id)
    except Exception as e:
        logger.error(f"Falled to pre-generate report: {e}")
        
    return {"session_id": session_id, "status": "ended"}

@router.get("/session/{session_id}/report")
async def get_report(session_id: str):
    """
    Fetches the compiled report for a completed session.
    """
    from app.services.report_generator import ReportGenerator
    try:
        report = await ReportGenerator.generate_report(session_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to compile report.")
