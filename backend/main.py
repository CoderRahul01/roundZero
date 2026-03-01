from __future__ import annotations

import asyncio
import json
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

if settings.use_vision:
    try:
        from routes.vision_interview import router as vision_interview_router
        from routes.vision_websocket import router as vision_websocket_router
        from routes.vision_admin import router as vision_admin_router
        from agent.vision.utils.env_validator import validate_and_exit_on_failure
        
        app.include_router(vision_interview_router)
        app.include_router(vision_websocket_router)
        app.include_router(vision_admin_router)
        logger.info("Vision Agents routes enabled")
    except ImportError as e:
        logger.warning(f"Vision Agents not available: {e}. Install with: uv sync --extra vision")
        settings.use_vision = False

try:
    from vision_agents.core import Runner, AgentLauncher, ServeOptions
except ImportError:
    Runner = None
    AgentLauncher = None
    ServeOptions = None


async def create_agent(session_id: str, config: SessionConfig, **kwargs) -> InterviewerAgent:
    """Factory function for AgentLauncher to create interviewer agents."""
    return InterviewerAgent(session_id=session_id, config=config, service=service)


# Initialize the Vision Agents Runner if available
runner = None
# if Runner and AgentLauncher:
#     launcher = AgentLauncher(create_agent=create_agent)
#     port = int(os.environ.get("PORT", 8000))
#     runner = Runner(launcher, serve_options=ServeOptions(fast_api=app, port=port))
# else:
#     runner = None
launcher = None

# Initialized during startup to avoid blocking on import
service = None
mongo_log_handler = None

@app.on_event("startup")
async def startup_event():
    global service, mongo_log_handler
    
    # Validate environment variables first (only for vision if enabled)
    if settings.use_vision:
        try:
            from agent.vision.utils.env_validator import validate_and_exit_on_failure
            logger.info("Validating Vision Agents environment variables...")
            validate_and_exit_on_failure()
        except ImportError:
            logger.warning("Vision Agents validation skipped - package not installed")
    
    # Initialize the interviewer service in the event loop, not at module level
    logger.info("Initializing InterviewerService...")
    service = get_interviewer_service()
    logger.info("InterviewerService initialized.")

    if settings.mongodb_uri:
        logger.info("Setting up MongoDB centralized logging...")
        mongo_log_handler = setup_mongo_logging(settings.mongodb_uri, "RoundZero")
        mongo_log_handler.start_worker()
        logger.info("MongoDB logging active.")
    
    # Preload TTS cache for common phrases (async, non-blocking)
    logger.info("Preloading TTS cache for faster responses...")
    asyncio.create_task(_preload_tts_cache())
    
    logger.info("Initializing middleware with CORS origins: %s", _parse_origins())
    logger.info("Allowed Hosts: %s", settings.allowed_hosts or ["*"])
    
    logger.info("Startup complete - ready for requests")

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

app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=settings.cors_allow_credentials,
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    duration_ms = 0
    
    # Log incoming request for debugging (skip for health checks to reduce noise)
    if not request.url.path in ["/health", "/ready"]:
        logger.info("Incoming request: %s %s | Host: %s | Origin: %s | ACR-Method: %s | ACR-Headers: %s", 
                    request.method, request.url.path, 
                    request.headers.get("host"), 
                    request.headers.get("origin"),
                    request.headers.get("access-control-request-method"),
                    request.headers.get("access-control-request-headers"))

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        
        logger.info(
            "request_success",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "request_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "duration_ms": round(duration_ms, 2),
            },
            exc_info=True
        )
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error during request processing", "error": str(e)}
        )


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
        logger.warning("STREAM_API_SECRET not configured - Stream.io token will be null")
        return None

    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, api_secret, algorithm="HS256")
    logger.info(f"✓ Generated Stream.io token for user {user_id} (length: {len(token)})")
    return token


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
        # If we have a framework launcher, use it for standardized session tracking
        if launcher:
            agent = await launcher.launch(session_id=session_id, config=config)
        else:
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


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "RoundZero AI Backend"}

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
    if runner:
        # Canonical way to start a Vision Agents production server
        # This will use the settings from ServeOptions (host 0.0.0.0, port 8000 by default)
        runner.run()
    else:
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)


async def _preload_tts_cache():
    """Preload common TTS phrases into cache for faster first responses."""
    try:
        from services.tts_service import ElevenLabsTTSService
        from services.tts_cache_service import TTSCacheService
        
        # Initialize services
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.warning("ELEVENLABS_API_KEY not set - skipping TTS preload")
            return
        
        tts_service = ElevenLabsTTSService(api_key=api_key)
        cache_service = TTSCacheService()
        
        # Preload common phrases
        common_phrases = [
            "Hello! Welcome to your mock interview.",
            "Great answer! Let's move on.",
            "Can you elaborate on that?",
            "That's a good start.",
            "Thank you for your response.",
            "Hey, can you hear me?",
            "Let me ask you the question again.",
            "Wait, I asked about",
            "Let me stop you there."
        ]
        
        logger.info(f"Preloading {len(common_phrases)} TTS phrases...")
        
        # Preload in background
        for phrase in common_phrases:
            try:
                # Check if already cached
                cached = await cache_service.get_cached_audio(phrase)
                if not cached:
                    # Generate and cache
                    audio = await tts_service.synthesize_speech(phrase)
                    await cache_service.cache_audio(phrase, audio, "common")
            except Exception as e:
                logger.warning(f"Failed to preload phrase: {e}")
        
        logger.info("TTS cache preload complete")
    except Exception as e:
        logger.error(f"TTS preload error: {e}")
