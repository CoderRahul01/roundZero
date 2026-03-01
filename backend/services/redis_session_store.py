"""
Redis Session Store for distributed session management.

Replaces in-memory session storage with Redis for:
- Horizontal scaling across multiple workers
- Session persistence across restarts
- Automatic TTL (1 hour)
- Zero cost using Upstash free tier
"""

import asyncio
import logging
import pickle
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """
    Distributed session storage using Redis.
    
    Features:
    - Async operations for non-blocking I/O
    - Automatic TTL (1 hour default)
    - Connection pooling
    - Graceful fallback to in-memory on Redis failure
    """
    
    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        """
        Initialize Redis session store.
        
        Args:
            redis_url: Redis connection URL (Upstash format)
            ttl_seconds: Session TTL in seconds (default: 1 hour)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.client: Optional[redis.Redis] = None
        self.enabled = False
        self._fallback_store: dict = {}  # In-memory fallback
        
        logger.info(f"RedisSessionStore initialized (TTL: {ttl_seconds}s)")
    
    async def connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We use pickle for serialization
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.client.ping()
            self.enabled = True
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory session storage")
            self.enabled = False
    
    async def get(self, session_id: str) -> Optional[any]:
        """
        Get session from Redis.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Deserialized session object or None
        """
        key = f"session:{session_id}"
        
        if self.enabled and self.client:
            try:
                data = await self.client.get(key)
                if data:
                    return pickle.loads(data)
                return None
            except Exception as e:
                logger.error(f"Redis get error: {e}, using fallback")
                return self._fallback_store.get(session_id)
        else:
            return self._fallback_store.get(session_id)
    
    async def set(self, session_id: str, session_data: any):
        """
        Store session in Redis with TTL.
        
        Args:
            session_id: Session identifier
            session_data: Session object to store
        """
        key = f"session:{session_id}"
        
        if self.enabled and self.client:
            try:
                serialized = pickle.dumps(session_data)
                await self.client.setex(key, self.ttl_seconds, serialized)
                logger.debug(f"Session {session_id} stored in Redis")
            except Exception as e:
                logger.error(f"Redis set error: {e}, using fallback")
                self._fallback_store[session_id] = session_data
        else:
            self._fallback_store[session_id] = session_data
    
    async def delete(self, session_id: str):
        """
        Delete session from Redis.
        
        Args:
            session_id: Session identifier
        """
        key = f"session:{session_id}"
        
        if self.enabled and self.client:
            try:
                await self.client.delete(key)
                logger.debug(f"Session {session_id} deleted from Redis")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        # Also remove from fallback
        self._fallback_store.pop(session_id, None)
    
    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session exists
        """
        key = f"session:{session_id}"
        
        if self.enabled and self.client:
            try:
                return await self.client.exists(key) > 0
            except Exception as e:
                logger.error(f"Redis exists error: {e}")
                return session_id in self._fallback_store
        else:
            return session_id in self._fallback_store
    
    async def extend_ttl(self, session_id: str):
        """
        Extend session TTL (refresh on activity).
        
        Args:
            session_id: Session identifier
        """
        key = f"session:{session_id}"
        
        if self.enabled and self.client:
            try:
                await self.client.expire(key, self.ttl_seconds)
                logger.debug(f"Session {session_id} TTL extended")
            except Exception as e:
                logger.error(f"Redis expire error: {e}")
    
    async def get_all_keys(self) -> list[str]:
        """
        Get all session keys (for monitoring).
        
        Returns:
            List of session IDs
        """
        if self.enabled and self.client:
            try:
                keys = await self.client.keys("session:*")
                return [key.decode('utf-8').replace('session:', '') for key in keys]
            except Exception as e:
                logger.error(f"Redis keys error: {e}")
                return list(self._fallback_store.keys())
        else:
            return list(self._fallback_store.keys())
    
    async def count_sessions(self) -> int:
        """
        Count active sessions.
        
        Returns:
            Number of active sessions
        """
        keys = await self.get_all_keys()
        return len(keys)
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
            logger.info("Redis connection closed")
    
    async def health_check(self) -> dict:
        """
        Check Redis health.
        
        Returns:
            Health status dictionary
        """
        if not self.enabled or not self.client:
            return {
                "status": "disabled",
                "using_fallback": True,
                "fallback_sessions": len(self._fallback_store)
            }
        
        try:
            await self.client.ping()
            session_count = await self.count_sessions()
            
            return {
                "status": "healthy",
                "using_fallback": False,
                "active_sessions": session_count,
                "ttl_seconds": self.ttl_seconds
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "using_fallback": True,
                "fallback_sessions": len(self._fallback_store)
            }


# Global session store instance
_session_store: Optional[RedisSessionStore] = None


def get_session_store(redis_url: str, ttl_seconds: int = 3600) -> RedisSessionStore:
    """
    Get or create global session store instance.
    
    Args:
        redis_url: Redis connection URL
        ttl_seconds: Session TTL in seconds
    
    Returns:
        RedisSessionStore instance
    """
    global _session_store
    
    if _session_store is None:
        _session_store = RedisSessionStore(redis_url, ttl_seconds)
    
    return _session_store


async def init_session_store(redis_url: str, ttl_seconds: int = 3600) -> RedisSessionStore:
    """
    Initialize and connect session store.
    
    Args:
        redis_url: Redis connection URL
        ttl_seconds: Session TTL in seconds
    
    Returns:
        Connected RedisSessionStore instance
    """
    store = get_session_store(redis_url, ttl_seconds)
    await store.connect()
    return store
