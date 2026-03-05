import json
import logging
from typing import Optional, Dict, Any
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

class SessionService:
    @staticmethod
    async def get_session(session_id: str) -> Dict[str, Any]:
        """
        Retrieves session configuration from Redis.
        """
        redis = get_redis()
        if not redis:
            logger.warning("Redis not available, returning empty session context")
            return {}
            
        try:
            data = redis.get(f"session_config:{session_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            
        return {}
    
    @staticmethod
    async def save_session(session_id: str, data: Dict[str, Any], expire: int = 3600):
        """
        Saves session configuration to Redis.
        """
        redis = get_redis()
        if not redis:
            return
            
        try:
            redis.setex(f"session_config:{session_id}", expire, json.dumps(data))
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
