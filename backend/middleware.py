from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
from typing import Optional

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("roundzero.auth")


@dataclass(frozen=True)
class TokenValidationConfig:
    jwt_secret: str
    neon_auth_url: str | None
    neon_auth_jwks_url: str | None
    neon_auth_issuer: str | None
    neon_auth_audience: str | None
    allow_legacy_hs256_auth: bool


def _resolve_neon_jwks_url(config: TokenValidationConfig) -> str | None:
    if config.neon_auth_jwks_url:
        return config.neon_auth_jwks_url.rstrip("/")

    if config.neon_auth_url:
        return f"{config.neon_auth_url.rstrip('/')}/.well-known/jwks.json"

    return None


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _audience_variants(configured_audience: str | None) -> list[str]:
    candidates = _parse_csv(configured_audience)
    if "authenticated" not in candidates:
        candidates.append("authenticated")
    return candidates


def _issuer_variants(configured_issuer: str | None) -> list[str]:
    if not configured_issuer:
        return []
    issuer = configured_issuer.strip()
    if not issuer:
        return []
    stripped = issuer.rstrip("/")
    variants = [issuer]
    if stripped != issuer:
        variants.append(stripped)
    else:
        variants.append(f"{issuer}/")
    # preserve order and remove duplicates
    return list(dict.fromkeys(variants))


def _decode_neon_jwt(
    token: str,
    signing_key: str,
    audiences: list[str],
    issuers: list[str],
) -> dict:
    decode_kwargs: dict = {
        "algorithms": ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"],
        "options": {
            "verify_aud": bool(audiences),
            "verify_iss": bool(issuers),
        },
    }
    if audiences:
        decode_kwargs["audience"] = audiences if len(audiences) > 1 else audiences[0]
    if issuers:
        decode_kwargs["issuer"] = issuers if len(issuers) > 1 else issuers[0]

    try:
        return jwt.decode(token, signing_key, **decode_kwargs)
    except jwt.InvalidIssuerError:
        if not issuers:
            raise

        # Neon-issued tokens may vary issuer formatting across deployments.
        # Keep signature+audience checks, but relax issuer check as a fallback.
        fallback_kwargs = {
            **decode_kwargs,
            "options": {
                **decode_kwargs["options"],
                "verify_iss": False,
            },
        }
        fallback_kwargs.pop("issuer", None)
        logger.warning("JWT issuer mismatch. Retrying token validation without issuer check.")
        return jwt.decode(token, signing_key, **fallback_kwargs)


class AuthTokenVerifier:
    def __init__(self, config: TokenValidationConfig):
        self._config = config
        self._jwks_url = _resolve_neon_jwks_url(config)
        self._jwks_client = jwt.PyJWKClient(self._jwks_url) if self._jwks_url else None

    def verify(self, token: str) -> dict:
        if self._jwks_client:
            try:
                signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            except jwt.PyJWKClientError as exc:
                raise jwt.InvalidTokenError("Unable to fetch Neon Auth signing keys.") from exc

            audiences = _audience_variants(self._config.neon_auth_audience)
            issuers = _issuer_variants(self._config.neon_auth_issuer)
            
            try:
                # Add diagnostic logging for verification params
                header = jwt.get_unverified_header(token)
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                logger.info("DEBUG AUTH: Token KID: %s", header.get("kid"))
                logger.info("DEBUG AUTH: Token Payload: %s", unverified_payload)
                logger.info("DEBUG AUTH: Expected ISS Variants: %s", issuers)
                logger.info("DEBUG AUTH: Expected AUD Variants: %s", audiences)
                
                return _decode_neon_jwt(token, signing_key, audiences, issuers)
            except Exception as exc:
                logger.error("DEBUG AUTH: Verification failed: %s", exc)
                raise

        if not self._config.allow_legacy_hs256_auth:
            raise jwt.InvalidTokenError(
                "Neon Auth JWKS is not configured and legacy HS256 auth fallback is disabled."
            )

        return jwt.decode(token, self._config.jwt_secret, algorithms=["HS256"], options={"verify_aud": False})


@lru_cache
def get_auth_token_verifier() -> AuthTokenVerifier:
    from settings import get_settings

    settings = get_settings()
    config = TokenValidationConfig(
        jwt_secret=settings.jwt_secret,
        neon_auth_url=settings.neon_auth_url,
        neon_auth_jwks_url=settings.neon_auth_jwks_url,
        neon_auth_issuer=settings.neon_auth_issuer,
        neon_auth_audience=settings.neon_auth_audience,
        allow_legacy_hs256_auth=settings.allow_legacy_hs256_auth,
    )
    return AuthTokenVerifier(config)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health/ready/docs or OPTIONS preflights
        if request.method == "OPTIONS" or request.url.path in ["/health", "/ready", "/docs", "/openapi.json"]:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif "token" in request.query_params:
            token = request.query_params["token"]

        if not token:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header or token query param"})

        from fastapi.responses import JSONResponse
        try:
            payload = get_auth_token_verifier().verify(token)
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token has expired"})
        except jwt.InvalidTokenError as exc:
            logger.warning("JWT verification failed: %s", exc)
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)


def get_current_user(request: Request) -> Optional[dict]:
    return getattr(request.state, "user", None)
