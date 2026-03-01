"""
Text-to-Speech Service using ElevenLabs API.

Provides async speech synthesis with Redis caching for performance optimization.
"""

import logging
import hashlib
import asyncio
from typing import AsyncIterator, Optional
from elevenlabs import AsyncElevenLabs
from elevenlabs.types import VoiceSettings

logger = logging.getLogger(__name__)


class ElevenLabsTTSService:
    """
    Async text-to-speech service using ElevenLabs API with Redis caching.
    
    Features:
    - High-quality voice synthesis
    - Redis caching for persistent storage across instances
    - In-memory caching for ultra-fast repeated access
    - Streaming support for reduced latency
    - Batch synthesis for preloading
    - Configurable voice settings
    - Error handling and retry logic
    """
    
    def __init__(
        self, 
        api_key: str, 
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default: Rachel voice
        model: str = "eleven_turbo_v2",
        redis_cache=None  # Optional TTSCache instance
    ):
        """
        Initialize ElevenLabs client.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use (default: Rachel)
            model: Model to use (default: eleven_turbo_v2 for low latency)
            redis_cache: Optional TTSCache instance for Redis caching
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.client = AsyncElevenLabs(api_key=api_key)
        self.redis_cache = redis_cache  # Redis cache (persistent)
        self.memory_cache: dict[str, bytes] = {}  # In-memory cache (fast)
        logger.info(f"ElevenLabsTTSService initialized with voice_id: {voice_id}, Redis cache: {redis_cache is not None}")
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice_settings: Optional[VoiceSettings] = None,
        use_cache: bool = True
    ) -> bytes:
        """
        Convert text to audio bytes with two-tier caching (memory + Redis).
        
        Cache hierarchy:
        1. Check in-memory cache (fastest)
        2. Check Redis cache (fast, persistent)
        3. Generate via API (slowest)
        
        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration
            use_cache: Whether to use caching (default: True)
        
        Returns:
            Audio data as bytes
        """
        # Check memory cache first (fastest)
        if use_cache:
            cache_key = self._get_cache_key(text, voice_settings)
            if cache_key in self.memory_cache:
                logger.debug(f"Memory cache HIT for text: {text[:50]}...")
                return self.memory_cache[cache_key]
            
            # Check Redis cache (fast, persistent)
            if self.redis_cache:
                cached_audio = await self.redis_cache.get(text, self.voice_id)
                if cached_audio:
                    logger.debug(f"Redis cache HIT for text: {text[:50]}...")
                    # Store in memory cache for next time
                    self.memory_cache[cache_key] = cached_audio
                    return cached_audio
        
        # Default voice settings for natural interview tone
        if voice_settings is None:
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True
            )
        
        try:
            # Generate audio via API
            audio = await self.client.generate(
                text=text,
                voice=self.voice_id,
                model=self.model,
                voice_settings=voice_settings
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join([chunk async for chunk in audio])
            
            # Cache result if enabled
            if use_cache:
                # Store in memory cache
                self.memory_cache[cache_key] = audio_bytes
                
                # Store in Redis cache (persistent)
                if self.redis_cache:
                    await self.redis_cache.set(text, audio_bytes, self.voice_id)
                
                logger.debug(f"Cached audio for text: {text[:50]}...")
            
            logger.info(f"Synthesized {len(audio_bytes)} bytes for {len(text)} characters")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error in synthesize_speech: {e}")
            raise
    
    async def stream_speech(
        self, 
        text: str,
        voice_settings: Optional[VoiceSettings] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream audio as it's generated.
        Useful for reducing perceived latency in real-time applications.
        
        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration
        
        Yields:
            Audio data chunks as they're generated
        """
        # Default voice settings
        if voice_settings is None:
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True
            )
        
        try:
            audio = await self.client.generate(
                text=text,
                voice=self.voice_id,
                model=self.model,
                stream=True,
                voice_settings=voice_settings
            )
            
            chunk_count = 0
            async for chunk in audio:
                chunk_count += 1
                yield chunk
            
            logger.info(f"Streamed {chunk_count} chunks for {len(text)} characters")
            
        except Exception as e:
            logger.error(f"Error in stream_speech: {e}")
            raise
    
    async def synthesize_batch(
        self, 
        texts: list[str],
        voice_settings: Optional[VoiceSettings] = None
    ) -> list[bytes]:
        """
        Synthesize multiple texts concurrently.
        Useful for preloading common phrases (greetings, feedback, etc.).
        
        Args:
            texts: List of texts to synthesize
            voice_settings: Optional voice configuration
        
        Returns:
            List of audio bytes in the same order as input texts
        """
        tasks = [
            self.synthesize_speech(text, voice_settings, use_cache=True) 
            for text in texts
        ]
        
        try:
            results = await asyncio.gather(*tasks)
            logger.info(f"Batch synthesized {len(texts)} texts")
            return results
        except Exception as e:
            logger.error(f"Error in synthesize_batch: {e}")
            raise
    
    async def synthesize_with_retry(
        self,
        text: str,
        max_retries: int = 3,
        voice_settings: Optional[VoiceSettings] = None
    ) -> Optional[bytes]:
        """
        Synthesize speech with retry logic for error handling.
        
        Args:
            text: Text to convert to speech
            max_retries: Maximum number of retry attempts
            voice_settings: Optional voice configuration
        
        Returns:
            Audio bytes or None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                audio = await self.synthesize_speech(
                    text, 
                    voice_settings, 
                    use_cache=False  # Don't cache failed attempts
                )
                return audio
            except Exception as e:
                logger.warning(
                    f"Synthesis attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error("All synthesis attempts failed")
                    return None
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def preload_common_phrases(self):
        """
        Preload common interview phrases into cache.
        Call this during application startup to improve first-response latency.
        """
        common_phrases = [
            "Hello! Welcome to your mock interview. I'm excited to work with you today.",
            "Great answer! Let's move on to the next question.",
            "Can you elaborate on that a bit more?",
            "That's a good start. Can you provide a specific example?",
            "Excellent! You've completed the interview. Let me generate your report.",
            "I didn't quite catch that. Could you please repeat your answer?",
            "Take your time. There's no rush.",
            "Thank you for your response. Let me ask you this:",
        ]
        
        logger.info("Preloading common phrases into cache...")
        await self.synthesize_batch(common_phrases)
        logger.info(f"Preloaded {len(common_phrases)} phrases")
    
    def _get_cache_key(
        self, 
        text: str, 
        voice_settings: Optional[VoiceSettings]
    ) -> str:
        """
        Generate cache key from text and settings.
        
        Args:
            text: Text content
            voice_settings: Voice configuration
        
        Returns:
            MD5 hash as cache key
        """
        settings_str = ""
        if voice_settings:
            settings_str = f"{voice_settings.stability}{voice_settings.similarity_boost}"
        
        cache_input = f"{text}{settings_str}{self.voice_id}{self.model}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear memory cache to free memory. Redis cache persists."""
        cache_size = self.get_cache_size()
        self.memory_cache.clear()
        logger.info(f"Cleared memory cache ({cache_size / 1024 / 1024:.2f} MB)")
    
    def get_cache_size(self) -> int:
        """
        Get current memory cache size in bytes.
        
        Returns:
            Total size of cached audio in memory
        """
        return sum(len(audio) for audio in self.memory_cache.values())
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache metrics
        """
        return {
            "memory_entries": len(self.memory_cache),
            "memory_size_bytes": self.get_cache_size(),
            "memory_size_mb": self.get_cache_size() / 1024 / 1024,
            "redis_enabled": self.redis_cache is not None
        }
