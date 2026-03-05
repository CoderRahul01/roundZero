from __future__ import annotations
import logging
from upstash_redis import Redis
from app.core.settings import get_settings

logger = logging.getLogger("app.redis")

class RedisClient:
    _instance: Redis | None = None

    @classmethod
    def get_client(cls) -> Redis | None:
        if cls._instance is None:
            settings = get_settings()
            if not settings.use_redis:
                return None
            
            try:
                if settings.upstash_redis_rest_url and settings.upstash_redis_rest_token:
                    logger.info("Initializing Upstash Redis client")
                    cls._instance = Redis(
                        url=settings.upstash_redis_rest_url,
                        token=settings.upstash_redis_rest_token
                    )
                else:
                    # Fallback to local redis if needed or just return None
                    logger.warning("Upstash Redis not configured, caching disabled")
                    return None
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                return None
        
        return cls._instance

def get_redis() -> Redis | None:
    return RedisClient.get_client()
