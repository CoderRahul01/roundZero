"""
TTS Cache Service

Redis-based caching for TTS audio to reduce API calls and improve performance.
"""

import hashlib
import logging
import time
import base64
from typing import Optional
from upstash_redis import Redis
import os

logger = logging.getLogger(__name__)


class TTSCacheService:
    """
    Manages TTS audio caching with Redis.
    Implements LRU eviction and TTL-based expiration.
    """
    
    # Cache configuration
    MAX_CACHE_SIZE_MB = 50
    COMMON_PHRASE_TTL = 86400 * 30  # 30 days for common phrases
    QUESTION_TTL = 86400  # 24 hours for questions
    INTERRUPTION_TTL = 86400 * 7  # 7 days for interruptions
    
    # Common phrases that should be cached permanently
    COMMON_PHRASES = [
        "Hey, can you hear me?",
        "Great! Let me ask you the question again.",
        "Wait, I asked about",
        "Let me stop you there.",
        "The question is specifically about"
    ]
    
    def __init__(self):
        """Initialize Redis connection."""
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        if not redis_url or not redis_token:
            logger.warning("Redis credentials not found. TTS caching disabled.")
            self.redis = None
            self.enabled = False
        else:
            self.redis = Redis(url=redis_url, token=redis_token)
            self.enabled = True
            logger.info("TTS cache service initialized")
    
    def _generate_cache_key(self, text: str, voice_settings: Optional[dict] = None) -> str:
        """
        Generate cache key from text and voice settings.
        """
        # Include voice settings in hash for different voices
        settings_str = ""
        if voice_settings:
            settings_str = f"_{voice_settings.get('voice_id', '')}"
        
        # Hash the text for consistent key length
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"tts:audio:{text_hash}{settings_str}"
    
    def _is_common_phrase(self, text: str) -> bool:
        """Check if text is a common phrase."""
        return any(phrase in text for phrase in self.COMMON_PHRASES)
    
    def _get_ttl(self, text: str, audio_type: str = "question") -> int:
        """
        Get TTL based on audio type.
        """
        if self._is_common_phrase(text):
            return self.COMMON_PHRASE_TTL
        elif audio_type == "interruption":
            return self.INTERRUPTION_TTL
        else:
            return self.QUESTION_TTL
    
    async def get_cached_audio(
        self,
        text: str,
        voice_settings: Optional[dict] = None
    ) -> Optional[bytes]:
        """
        Retrieve cached audio from Redis.
        Returns None if not found.
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._generate_cache_key(text, voice_settings)
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                logger.info(f"TTS cache hit for: {text[:50]}...")
                # Update access time for LRU
                self.redis.expire(cache_key, self._get_ttl(text))
                
                # Decode if it's a string (base64)
                if isinstance(cached_data, str):
                    try:
                        return base64.b64decode(cached_data)
                    except Exception:
                        return cached_data.encode() # Fallback
                return cached_data
            
            logger.debug(f"TTS cache miss for: {text[:50]}...")
            return None
        except Exception as e:
            logger.error(f"TTS cache retrieval error: {e}")
            return None
    
    async def cache_audio(
        self,
        text: str,
        audio_data: bytes,
        audio_type: str = "question",
        voice_settings: Optional[dict] = None
    ) -> bool:
        """
        Cache audio data in Redis with appropriate TTL.
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_cache_key(text, voice_settings)
            ttl = self._get_ttl(text, audio_type)
            
            # Check cache size before adding
            audio_size_mb = len(audio_data) / (1024 * 1024)
            if audio_size_mb > 5:  # Don't cache audio larger than 5MB
                logger.warning(f"Audio too large to cache: {audio_size_mb:.2f}MB")
                return False
            
            # Store with TTL, encode to base64 to avoid JSON serialization errors with REST client
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            self.redis.setex(cache_key, ttl, encoded_audio)
            
            logger.info(f"Cached TTS audio: {text[:50]}... (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"TTS cache storage error: {e}")
            return False
    
    async def preload_common_phrases(self, tts_service) -> int:
        """
        Preload common phrases into cache.
        Returns number of phrases cached.
        """
        if not self.enabled:
            return 0
        
        cached_count = 0
        
        for phrase in self.COMMON_PHRASES:
            # Check if already cached
            cached = await self.get_cached_audio(phrase)
            if cached:
                cached_count += 1
                continue
            
            try:
                # Generate audio
                audio_data = await tts_service.synthesize_speech(phrase)
                
                # Cache it
                success = await self.cache_audio(
                    text=phrase,
                    audio_data=audio_data,
                    audio_type="common"
                )
                
                if success:
                    cached_count += 1
            except Exception as e:
                logger.error(f"Failed to preload phrase '{phrase}': {e}")
        
        logger.info(f"Preloaded {cached_count}/{len(self.COMMON_PHRASES)} common phrases")
        return cached_count
    
    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        """
        if not self.enabled:
            return {
                "enabled": False,
                "total_keys": 0,
                "estimated_size_mb": 0,
                "hit_rate": 0
            }
        
        try:
            # Get all TTS cache keys
            keys = self.redis.keys("tts:audio:*")
            total_keys = len(keys) if keys else 0
            
            # Estimate size (rough approximation)
            estimated_size_mb = total_keys * 0.1  # Assume ~100KB per audio
            
            return {
                "enabled": True,
                "total_keys": total_keys,
                "estimated_size_mb": round(estimated_size_mb, 2),
                "max_size_mb": self.MAX_CACHE_SIZE_MB
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "enabled": True,
                "error": str(e)
            }
    
    async def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        Redis handles this automatically with TTL, but this can be used for manual cleanup.
        """
        if not self.enabled:
            return 0
        
        try:
            # Redis automatically removes expired keys
            # This is just for logging/monitoring
            stats = await self.get_cache_stats()
            logger.info(f"Cache status: {stats['total_keys']} keys, {stats['estimated_size_mb']}MB")
            return 0
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    async def invalidate_cache(self, text: str, voice_settings: Optional[dict] = None) -> bool:
        """
        Invalidate specific cache entry.
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_cache_key(text, voice_settings)
            result = self.redis.delete(cache_key)
            logger.info(f"Invalidated cache for: {text[:50]}...")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    async def clear_all_cache(self) -> bool:
        """
        Clear all TTS cache entries.
        Use with caution.
        """
        if not self.enabled:
            return False
        
        try:
            keys = self.redis.keys("tts:audio:*")
            if keys:
                self.redis.delete(*keys)
                logger.warning(f"Cleared {len(keys)} TTS cache entries")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


class CachedTTSService:
    """
    Wrapper around TTS service that adds caching.
    """
    
    def __init__(self, tts_service, cache_service: TTSCacheService):
        self.tts_service = tts_service
        self.cache_service = cache_service
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def synthesize_speech(
        self,
        text: str,
        audio_type: str = "question",
        voice_settings: Optional[dict] = None
    ) -> bytes:
        """
        Synthesize speech with caching.
        """
        # Try cache first
        cached_audio = await self.cache_service.get_cached_audio(text, voice_settings)
        
        if cached_audio:
            self._cache_hits += 1
            return cached_audio
        
        # Cache miss - generate audio
        self._cache_misses += 1
        audio_data = await self.tts_service.synthesize_speech(text)
        
        # Cache the result
        await self.cache_service.cache_audio(
            text=text,
            audio_data=audio_data,
            audio_type=audio_type,
            voice_settings=voice_settings
        )
        
        return audio_data
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total
    
    def get_cache_stats(self) -> dict:
        """
        Get cache performance stats.
        """
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": round(self.get_cache_hit_rate(), 3),
            "total_requests": self._cache_hits + self._cache_misses
        }
