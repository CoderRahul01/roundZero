from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Literal

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agent.interviewer import SessionConfig, get_interviewer_service, InterviewerAgent
from middleware import JWTAuthMiddleware, get_current_user
from rate_limit import RateLimiter
from settings import Settings, get_settings
from logger import setup_mongo_logging
from routes.realtime_voice import router as realtime_voice_router
from routes.storage import router as storage_router
from routes.onboarding import router as onboarding_router
from routes.question_progression import router as question_progression_router

load_dotenv(Path(__file__).resolve().parent / ".env")

settings: Settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("roundzero.api")

app = FastAPI(title="RoundZero AI Backend", version="1.0.0", docs_url="/docs", redoc_url=None)

# Include routers
app.include_router(realtime_voice_router)
app.include_router(storage_router)
app.include_router(onboarding_router)
app.include_router(question_progression_router)

# Initialized during startup to avoid blocking on import
service = None
mongo_log_handler = None

@app.on_event("startup")
async def startup_event():
    global service, mongo_log_handler
    # Initialize the interviewer service in the event loop, not at module level
    logger.info("Initializing InterviewerService...")
    service = get_interviewer_service()
    logger.info("InterviewerService initialized.")

    if settings.mongodb_uri:
        logger.info("Setting up MongoDB centralized logging...")
        mongo_log_handler = setup_mongo_logging(settings.mongodb_uri, "RoundZero")
        mongo_log_handler.start_worker()
        logger.info("MongoDB logging active.")

@app.on_event("shutdown")
async def shutdown_event():
    global mongo_log_handler
    if mongo_log_handler:
        logger.info("Shutting down MongoDB centralized logging...")
        await mongo_log_handler.stop_worker()
    
    # Cleanup storage repositories
    logger.info("Closing storage repository connections...")
    from routes.storage import cleanup_repositories
    await cleanup_repositories()
    logger.info("Storage repositories closed.")

def _missing_env(keys: list[str]) -> list[str]:
    return [key for key in keys if not os.getenv(key)]


def _parse_origins() -> list[str]:
    return settings.normalized_cors_origins()


app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=settings.cors_allow_credentials,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(GZipMiddleware, minimum_size=512)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    logger.info(
        "request",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response


class StartSessionRequest(BaseModel):
    user_id: str | None = None
    name: str | None = None
    role: str = Field(min_length=2)
    topics: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    mode: Literal["buddy", "strict"] = "buddy"


class SubmitAnswerRequest(BaseModel):
    transcript: str
    confidence: int | None = Field(default=None, ge=0, le=100)
    emotion: str | None = None


rate_limiter = RateLimiter(
    max_calls=settings.rate_limit_max,
    window_seconds=settings.rate_limit_window_seconds,
)


def _safe_user_id(payload: StartSessionRequest) -> str:
    candidate = (payload.user_id or payload.name or "guest_user").strip().lower()
    slug = re.sub(r"[^a-z0-9_-]+", "_", candidate).strip("_")
    if not slug:
        slug = "guest_user"
    return slug[:64]


def _user_id_from_request(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = user.get("sub") or user.get("user_id") or user.get("email")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid auth payload")
    return str(user_id)


def generate_stream_token(user_id: str) -> str | None:
    """Generate a short-lived JWT token for Stream Video if configured."""
    api_secret = settings.stream_api_secret or os.getenv("STREAM_API_SECRET")
    if not api_secret:
        return None

    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, api_secret, algorithm="HS256")


def generate_backend_token(user_id: str) -> str:
    """Generate a JWT token for backend API authentication."""
    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + (3600 * 24), # 24 hours
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@app.post("/session/start")
async def start_session(payload: StartSessionRequest, request: Request) -> dict[str, Any]:
    user_id = _user_id_from_request(request)
    client_host = request.client.host if request.client else "unknown"
    limiter_key = f"{client_host}:{user_id}"
    if not rate_limiter.allow(limiter_key):
        raise HTTPException(status_code=429, detail="Too many session start requests. Try again in a minute.")

    if not payload.topics:
        raise HTTPException(status_code=400, detail="Please select at least one topic.")

    config = SessionConfig(
        user_id=user_id,
        role=payload.role,
        topics=payload.topics,
        difficulty=payload.difficulty,
        mode=payload.mode,
    )

    try:
        session = await service.start_session(config)
        stream_api_key = settings.stream_api_key or os.getenv("STREAM_API_KEY")
        token = generate_stream_token(user_id)
        backend_token = generate_backend_token(user_id)

        response = {
            **session,
            "user_id": user_id,
            "token": token,
            "backend_token": backend_token,
            "stream_api_key": stream_api_key,
        }
        if settings.use_vision:
            call_id = f"session_{session['session_id'][:8]}"
            asyncio.create_task(_maybe_start_voice_agent(call_id, session["session_id"], config))
            response["call_id"] = call_id
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {exc}") from exc


async def _maybe_start_voice_agent(call_id: str, session_id: str, config: SessionConfig) -> None:
    if not settings.use_vision:
        return
    try:
        agent = InterviewerAgent(session_id=session_id, config=config, service=service)
        await agent.join_session_call(call_id)
    except Exception as exc:  # pragma: no cover - optional path
        logger.warning("Voice agent not started: %s", exc)


@app.post("/session/{session_id}/answer")
async def submit_answer(session_id: str, payload: SubmitAnswerRequest) -> dict[str, Any]:
    try:
        return await service.submit_answer(
            session_id=session_id,
            transcript=payload.transcript,
            confidence=payload.confidence,
            emotion=payload.emotion,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {exc}") from exc


@app.post("/session/{session_id}/end")
async def end_session(session_id: str) -> dict[str, Any]:
    try:
        return await service.end_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {exc}") from exc


@app.get("/session/{session_id}/report")
async def get_report(session_id: str) -> dict[str, Any]:
    try:
        return await service.get_report(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report: {exc}") from exc


@app.get("/session/{session_id}/events")
async def session_events(session_id: str):
    """Server-Sent Events endpoint for real-time session updates."""
    async def event_generator():
        queue = asyncio.Queue()
        await service.register_listener(session_id, queue)
        try:
            while True:
                # Listen to service broadcasts
                event = await queue.get()
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event)
                }
        except asyncio.CancelledError:
            await service.unregister_listener(session_id, queue)
            raise

    return EventSourceResponse(event_generator())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    dependencies = {
        "database": service.db.enabled,
        "pinecone": service.question_bank._pinecone_index is not None,
        "claude": service.decision_engine._llm is not None,
        "env_missing": settings.missing_required(),
    }
    return {
        "status": "ready",
        "environment": settings.environment,
        "dependencies": dependencies,
        "ts": int(time.time()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
