import logging

from fastapi import HTTPException, Request, status

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Redis-backed token bucket rate limiter.
    fail_open=True  → allow requests when Redis is unavailable (default for API routes)
    fail_open=False → reject requests when Redis is unavailable (stricter, for WS connections)
    """
    def __init__(self, requests: int, window_seconds: int, fail_open: bool = True):
        self.requests = requests
        self.window_seconds = window_seconds
        self.fail_open = fail_open

    async def __call__(self, request: Request, identifier: str | None = None):
        redis = get_redis()
        if not redis:
            if self.fail_open:
                return True
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limiter unavailable. Please try again later.",
            )

        # Use provided ID or fallback to IP
        client_id = identifier or (request.client.host if request.client else "unknown")
        key = f"rate_limit:{request.url.path}:{client_id}"

        try:
            current = redis.get(key)
            if current and int(current) >= self.requests:
                logger.warning(f"Rate limit exceeded for {client_id} at {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )

            pipe = redis.pipeline()
            pipe.incr(key)
            if not current:
                pipe.expire(key, self.window_seconds)
            pipe.exec()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            if self.fail_open:
                return True
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limiter error. Please try again later.",
            ) from e

# Pre-configured limiters
api_limiter = RateLimiter(requests=10, window_seconds=60)                # fail open — API routes
ws_limiter  = RateLimiter(requests=5,  window_seconds=60, fail_open=False)  # fail closed — WS connections
