"""
TTS Audio Caching Service using Redis.

This module provides caching for ElevenLabs TTS audio to reduce API calls
and improve response times for repeated text.
"""

import hashlib
import logging
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TTSCache:
    """
    Redis-based cache for TTS audio.
    
    Features:
    - Cache audio by text hash
    - 24-hour TTL for cached audio
    - Automatic cache key generation
    - Cache hit/miss tracking
    """
    
    def __init__(self, redis_client: redis.Redis, ttl_hours: int = 24):
        """
        Initialize TTS cache.
        
        Args:
            redis_client: Redis async client
            ttl_hours: Time-to-live for cached audio in hours (default: 24)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_hours * 3600
        self.cache_prefix = "tts:audio:"
        
        logger.info(f"Initialized TTSCache with {ttl_hours}h TTL")
    
    def _generate_cache_key(self, text: str, voice_id: str = "default") -> str:
        """
        Generate cache key from text and voice ID.
        
        Args:
            text: Text to be synthesized
            voice_id: ElevenLabs voice ID
        
        Returns:
            Cache key string
        """
        # Create hash from text + voice_id for consistent key generation
        content = f"{text}:{voice_id}"
        text_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"{self.cache_prefix}{text_hash}"
    
    async def get(self, text: str, voice_id: str = "default") -> Optional[bytes]:
        """
        Get cached audio for text.
        
        Args:
            text: Text to retrieve audio for
            voice_id: ElevenLabs voice ID
        
        Returns:
            Cached audio bytes if found, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(text, voice_id)
            audio_bytes = await self.redis.get(cache_key)
            
            if audio_bytes:
                logger.debug(f"TTS cache HIT for text: {text[:50]}...")
                return audio_bytes
            else:
                logger.debug(f"TTS cache MISS for text: {text[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"TTS cache get error: {e}")
            return None
    
    async def set(self, text: str, audio_bytes: bytes, voice_id: str = "default") -> bool:
        """
        Cache audio for text.
        
        Args:
            text: Text that was synthesized
            audio_bytes: Generated audio data
            voice_id: ElevenLabs voice ID
        
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(text, voice_id)
            
            # Store with TTL
            await self.redis.setex(
                cache_key,
                self.ttl_seconds,
                audio_bytes
            )
            
            logger.debug(f"TTS cached for text: {text[:50]}... (TTL: {self.ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.error(f"TTS cache set error: {e}")
            return False
    
    async def delete(self, text: str, voice_id: str = "default") -> bool:
        """
        Delete cached audio for text.
        
        Args:
            text: Text to delete cache for
            voice_id: ElevenLabs voice ID
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(text, voice_id)
            deleted = await self.redis.delete(cache_key)
            
            if deleted:
                logger.debug(f"TTS cache deleted for text: {text[:50]}...")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"TTS cache delete error: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats (total_keys, memory_usage)
        """
        try:
            # Count keys with our prefix
            cursor = 0
            total_keys = 0
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=f"{self.cache_prefix}*",
                    count=100
                )
                total_keys += len(keys)
                
                if cursor == 0:
                    break
            
            # Get memory info
            info = await self.redis.info("memory")
            memory_usage = info.get("used_memory_human", "N/A")
            
            return {
                "total_cached_items": total_keys,
                "memory_usage": memory_usage,
                "ttl_hours": self.ttl_seconds / 3600
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "total_cached_items": 0,
                "memory_usage": "N/A",
                "ttl_hours": self.ttl_seconds / 3600
            }
    
    async def clear_all(self) -> int:
        """
        Clear all TTS cache entries.
        
        Returns:
            Number of keys deleted
        """
        try:
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=f"{self.cache_prefix}*",
                    count=100
                )
                
                if keys:
                    deleted = await self.redis.delete(*keys)
                    deleted_count += deleted
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {deleted_count} TTS cache entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0


async def get_tts_cache(redis_url: str = None) -> TTSCache:
    """
    Get TTS cache instance.
    
    Args:
        redis_url: Redis connection URL (default: from environment)
    
    Returns:
        TTSCache instance
    """
    import os
    
    if not redis_url:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    redis_client = await redis.from_url(redis_url, decode_responses=False)
    return TTSCache(redis_client)
