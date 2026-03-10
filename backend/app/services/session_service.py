import json
import logging
from typing import Optional, Dict, Any
from app.core.redis_client import get_redis
from app.core.settings import get_settings

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

    @staticmethod
    async def update_current_question(session_id: str, index: int, text: str):
        """
        Updates the current question pointer in the session config.
        """
        redis = get_redis()
        if not redis: return
        
        try:
            data = await SessionService.get_session(session_id)
            if data:
                data["current_question_index"] = index
                data["current_question_text"] = text
                await SessionService.save_session(session_id, data)
        except Exception as e:
            logger.error(f"Error updating question index: {e}")

    @staticmethod
    async def create_session_neon(session_id: str, data: Dict[str, Any]):
        """
        Creates a session record in Neon.
        """
        settings = get_settings()
        if not settings.database_url: return
        
        import asyncpg
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                await conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, role, topics, difficulty, mode, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    session_id,
                    data.get("user_id"),
                    data.get("role"),
                    data.get("topics"),
                    data.get("difficulty"),
                    data.get("mode")
                )
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error creating session in Neon: {e}")

    @staticmethod
    async def save_question_result(session_id: str, result: Dict[str, Any]) -> bool:
        """
        Saves a question result to both Redis (for real-time) and Neon (for persistence).
        """
        # 1. Save to Redis
        redis = get_redis()
        if redis:
            try:
                data = await SessionService.get_session(session_id)
                if data:
                    if "results" not in data:
                        data["results"] = []
                    data["results"].append(result)
                    await SessionService.save_session(session_id, data)
            except Exception as e:
                logger.error(f"Error saving question result to Redis: {e}")

        # 2. Save to Neon
        settings = get_settings()
        if not settings.database_url: return True # Fallback to Redis only if DB missing
        
        import asyncpg
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                await conn.execute(
                    """
                    INSERT INTO question_results (
                        session_id, question_text, user_answer, ideal_answer, score, filler_word_count, emotion_log, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, now())
                    """,
                    session_id,
                    result.get("question_text"),
                    result.get("user_answer"),
                    result.get("ideal_answer"),
                    result.get("score"),
                    result.get("filler_word_count"),
                    json.dumps(result.get("emotion_log", {}))
                )
                return True
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving question result to Neon: {e}")
            
        return False
