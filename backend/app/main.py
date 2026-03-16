import asyncio
import json

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Response

from app.core.gcp_logger import gcp_logger as logger
from app.core.middleware import CORSASGIMiddleware, JWTAuthMiddleware
from app.core.settings import get_settings


class DiagnosticMiddleware:
    """Outermost middleware to log all incoming ASGI scopes."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            query_string = scope.get("query_string", b"").decode()
            safe_query = "&".join([
                p if not p.startswith("token=") else "token=[REDACTED]"
                for p in query_string.split("&")
            ])
            logger.info(f"DIAGNOSTIC WS: Path={scope.get('path')} Query={safe_query}")
            logger.info(f"DIAGNOSTIC WS: Origin={headers.get('origin', 'NONE')}")
        elif scope["type"] == "http":
            user_ip = scope.get("client", ["unknown"])[0]
            logger.info(
                f"DIAGNOSTIC HTTP: {scope.get('method')} {scope.get('path')} from {user_ip}",
                extra={"extra_data": {"http_method": scope.get('method'), "path": scope.get("path"), "client_ip": user_ip}}
            )
        return await self.app(scope, receive, send)


def create_app() -> FastAPI:
    # Core FastAPI app (no middleware added via add_middleware — see below)
    fastapi_app = FastAPI(
        title="RoundZero Gemini Live API",
        version="2.5.0",
        description="Real-time AI Interview Coach powered by Gemini 2.5 Flash Live"
    )

    @fastapi_app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "2.5.0"}

    @fastapi_app.get("/ready")
    async def ready_check():
        checks: dict = {}

        # Redis probe
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            if redis:
                await asyncio.wait_for(asyncio.to_thread(redis.ping), timeout=2.0)
                checks["redis"] = "ok"
            else:
                checks["redis"] = "unconfigured"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        # DB probe (best-effort, skip if not configured)
        try:
            cfg = get_settings()
            if cfg.database_url:
                import asyncpg  # type: ignore
                conn = await asyncio.wait_for(
                    asyncpg.connect(cfg.database_url, timeout=3.0), timeout=4.0
                )
                await conn.close()
                checks["db"] = "ok"
            else:
                checks["db"] = "unconfigured"
        except Exception as e:
            checks["db"] = f"error: {e}"

        degraded = any(v.startswith("error:") for v in checks.values())
        if degraded:
            return Response(
                content=json.dumps({"status": "degraded", "checks": checks}),
                status_code=503,
                media_type="application/json",
            )
        return {"status": "ready", "checks": checks}

    # Register Routers
    from app.api.profile import router as profile_router
    from app.api.routes import router as api_router
    from app.api.websocket import router as websocket_router

    fastapi_app.include_router(api_router)
    fastapi_app.include_router(profile_router)
    fastapi_app.include_router(websocket_router)

    # === DIRECT ASGI WRAPPING (bypasses Starlette's add_middleware machinery) ===
    # app.add_middleware() routes through BaseHTTPMiddleware which intercepts WebSocket
    # upgrades and returns 400 even for "raw ASGI" middleware classes.
    # Direct wrapping connects middleware as plain Python object chains — WebSocket
    # connections flow through without any Starlette interception.
    #
    # Request flow (outer → inner):
    #   DiagnosticMiddleware → CORSASGIMiddleware → JWTAuthMiddleware → FastAPI
    asgi_app = JWTAuthMiddleware(fastapi_app)    # innermost
    asgi_app = CORSASGIMiddleware(asgi_app)      # middle
    asgi_app = DiagnosticMiddleware(asgi_app)    # outermost

    return asgi_app


app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        ws="wsproto",
        timeout_keep_alive=300,
        reload=False
    )
