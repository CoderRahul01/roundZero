import time
import logging
from fastapi import Request, HTTPException, status
from typing import Optional

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Redis-backed token bucket rate limiter.
    """
    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request, identifier: Optional[str] = None):
        redis = get_redis()
        if not redis:
            # Fall open if Redis is down, log warning ideally
            return True
            
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
            pipe.execute()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fall open on Redis failure
            return True

# Pre-configured limiters
api_limiter = RateLimiter(requests=10, window_seconds=60) # 10 requests per minute
ws_limiter = RateLimiter(requests=5, window_seconds=60) # 5 connection attempts per minute
