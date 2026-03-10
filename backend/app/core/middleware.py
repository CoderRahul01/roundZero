from __future__ import annotations

import logging
import os
from typing import Optional

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.settings import get_settings

logger = logging.getLogger("app.auth")
debug_logger = logging.getLogger("app.debug")
debug_logger.setLevel(logging.DEBUG)

class AuthTokenVerifier:
    def __init__(self):
        settings = get_settings()
        self.jwks_url = settings.neon_auth_jwks_url
        if not self.jwks_url and settings.neon_auth_project_id:
             # Fallback if only project ID is provided
             self.jwks_url = f"https://{settings.neon_auth_project_id}.auth.neon.tech/.well-known/jwks.json"
        
        self.jwks_client = jwt.PyJWKClient(self.jwks_url) if self.jwks_url else None
        self.issuer = settings.neon_auth_issuer
        self.audience = settings.neon_auth_audience or "authenticated"

    def verify_token(self, token: str) -> dict:
        settings = get_settings()
        
        # Try RS256 with Neon Auth if configured
        if self.jwks_client:
            try:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
                decode_kwargs = {
                    "algorithms": ["RS256", "EdDSA"],
                    "audience": self.audience,
                    "leeway": 300,  # 5 minutes leeway for clock drift
                    "options": {"verify_aud": False, "verify_iss": False},
                }
                return jwt.decode(token, signing_key, **decode_kwargs)
            except jwt.ExpiredSignatureError:
                logger.warning("Neon Auth Token has expired (even with leeway)")
                raise
            except Exception as exc:
                print(f"RS256/EdDSA Verification failed: {exc}")
                logger.debug(f"RS256 Verification failed, trying HS256: {exc}")

        # Try HS256 with local secret for development/legacy
        try:
            return jwt.decode(
                token, 
                settings.jwt_secret, 
                algorithms=["HS256"], 
                audience=["authenticated", self.audience] if self.audience else "authenticated",
                leeway=300,
                options={"verify_aud": False}
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Local HS256 Token has expired")
            raise
        except Exception as exc:
            print(f"HS256 Verification failed: {exc}")
            try:
                header = jwt.get_unverified_header(token)
                alg = header.get("alg")
                logger.error(f"JWT Verification failed. Token alg: {alg}. Final error: {exc}")
            except Exception as inner_exc:
                logger.error(f"JWT Verification failed: {exc}")

            raise jwt.InvalidTokenError(str(exc))


def get_auth_token_verifier() -> AuthTokenVerifier:
    return AuthTokenVerifier()


class JWTAuthMiddleware:
    """Raw ASGI middleware — properly handles both HTTP and WebSocket."""
    
    def __init__(self, app):
        self.app = app
        self.verifier = AuthTokenVerifier()

    async def __call__(self, scope, receive, send):
        # WebSocket — skip JWT entirely, pass through
        if scope["type"] == "websocket":
            logger.debug("Bypassing JWTAuthMiddleware for WebSocket")
            return await self.app(scope, receive, send)
        
        # Non-HTTP (lifespan, etc) — pass through
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # HTTP — do JWT validation
        request = Request(scope)
        
        # Skip auth for health checks, CORS preflight, etc.
        if (
            request.method == "OPTIONS" or 
            request.url.path in ["/", "/health", "/ready", "/docs", "/openapi.json"]
        ):
            return await self.app(scope, receive, send)
        
        # Auth logic
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif "token" in request.query_params:
            token = request.query_params["token"]

        if not token:
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=401, 
                content={"detail": "Missing Authorization header or token query param"}
            )
            return await response(scope, receive, send)

        try:
            payload = self.verifier.verify_token(token)
            # Add user to scope state for routes
            scope.setdefault("state", {})
            scope["state"]["user"] = payload
            # Also set directly on scope as suggested for easier access in some contexts
            scope["user"] = payload
            return await self.app(scope, receive, send)
        except jwt.ExpiredSignatureError:
            from fastapi.responses import JSONResponse
            response = JSONResponse(status_code=401, content={"detail": "Token has expired"})
            return await response(scope, receive, send)
        except jwt.InvalidTokenError:
            from fastapi.responses import JSONResponse
            response = JSONResponse(status_code=401, content={"detail": "Invalid token"})
            return await response(scope, receive, send)
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            from fastapi.responses import JSONResponse
            response = JSONResponse(status_code=500, content={"detail": "Internal server error during authentication"})
            return await response(scope, receive, send)


def get_current_user(request: Request) -> Optional[dict]:
    return getattr(request.state, "user", None)


class CORSASGIMiddleware:
    """
    Custom CORS middleware that ONLY processes HTTP requests.
    WebSocket connections pass through completely untouched.

    Allowed origins are built from:
    - Always: localhost dev origins
    - CORS_ORIGINS env var: comma-separated list of production origins
    """

    def __init__(self, app):
        self.app = app
        # Base dev origins
        base_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
        # Production origins from environment
        extra_raw = os.getenv("CORS_ORIGINS", os.getenv("CORS_ALLOW_ORIGINS", ""))
        extra_origins = [o.strip().rstrip("/") for o in extra_raw.split(",") if o.strip()]
        self.allowed_origins = list(dict.fromkeys(base_origins + extra_origins))  # deduplicate
        logger.info(f"CORS allowed origins: {self.allowed_origins}")

    async def __call__(self, scope, receive, send):
        # WebSocket — pass through immediately, no CORS processing
        if scope["type"] == "websocket":
            return await self.app(scope, receive, send)
        
        # Non-HTTP (lifespan, etc) — pass through
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # HTTP — handle CORS
        headers_dict = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        origin = headers_dict.get("origin", "")
        method = scope.get("method", "GET")
        
        # Check if origin is allowed
        origin_allowed = origin in self.allowed_origins or not origin
        
        # Handle preflight OPTIONS
        if method == "OPTIONS" and origin_allowed:
            response_headers = [
                (b"access-control-allow-origin", origin.encode()),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                (b"access-control-allow-headers", b"*"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"600"),
                (b"content-length", b"0"),
            ]
            await send({"type": "http.response.start", "status": 200, "headers": response_headers})
            await send({"type": "http.response.body", "body": b""})
            return
        
        # For regular HTTP requests, inject CORS headers into response
        if origin_allowed and origin:
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"access-control-allow-origin", origin.encode()))
                    headers.append((b"access-control-allow-credentials", b"true"))
                    message["headers"] = headers
                await send(message)
            
            return await self.app(scope, receive, send_with_cors)
        
        # No origin or not allowed — pass through without CORS headers
        return await self.app(scope, receive, send)
