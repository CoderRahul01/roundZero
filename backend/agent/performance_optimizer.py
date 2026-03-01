"""
Performance Optimizer for Voice Agent

Optimizes voice agent performance for fast, real-time interactions.
Focuses on:
- Parallel processing
- Aggressive caching
- Connection pooling
- Async operations
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    Optimizes voice agent performance for speed.
    """
    
    def __init__(self):
        self.metrics = {
            "tts_calls": 0,
            "tts_cache_hits": 0,
            "claude_calls": 0,
            "embedding_calls": 0,
            "total_latency_ms": 0,
            "operations": 0
        }
        
        # In-memory caches for ultra-fast access
        self._embedding_cache: Dict[str, list[float]] = {}
        self._claude_cache: Dict[str, Any] = {}
        self._tts_memory_cache: Dict[str, bytes] = {}
        
        logger.info("Performance optimizer initialized")
    
    async def optimize_tts_batch(
        self,
        texts: list[str],
        tts_service
    ) -> Dict[str, bytes]:
        """
        Batch TTS synthesis for multiple texts concurrently.
        Returns dict mapping text to audio bytes.
        """
        start_time = time.time()
        
        # Check memory cache first
        results = {}
        texts_to_generate = []
        
        for text in texts:
            cache_key = self._hash_text(text)
            if cache_key in self._tts_memory_cache:
                results[text] = self._tts_memory_cache[cache_key]
                self.metrics["tts_cache_hits"] += 1
            else:
                texts_to_generate.append(text)
        
        # Generate remaining texts concurrently
        if texts_to_generate:
            tasks = [
                tts_service.synthesize_speech(text)
                for text in texts_to_generate
            ]
            
            audio_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for text, audio in zip(texts_to_generate, audio_results):
                if not isinstance(audio, Exception):
                    results[text] = audio
                    # Cache in memory
                    cache_key = self._hash_text(text)
                    self._tts_memory_cache[cache_key] = audio
                    self.metrics["tts_calls"] += 1
        
        latency = (time.time() - start_time) * 1000
        self.metrics["total_latency_ms"] += latency
        self.metrics["operations"] += 1
        
        logger.info(f"Batch TTS: {len(texts)} texts in {latency:.2f}ms")
        return results
    
    async def optimize_parallel_analysis(
        self,
        question: str,
        answer: str,
        claude_client,
        embedding_service
    ) -> Dict[str, Any]:
        """
        Run Claude analysis and embedding calculation in parallel.
        """
        start_time = time.time()
        
        # Check caches
        claude_cache_key = self._hash_text(f"{question}:{answer}")
        embedding_cache_key = self._hash_text(answer)
        
        claude_task = None
        embedding_task = None
        
        # Only call if not cached
        if claude_cache_key not in self._claude_cache:
            claude_task = self._call_claude(question, answer, claude_client)
        else:
            logger.debug("Claude cache hit")
        
        if embedding_cache_key not in self._embedding_cache:
            embedding_task = embedding_service.get_embedding(answer)
        else:
            logger.debug("Embedding cache hit")
        
        # Run tasks in parallel
        tasks = []
        if claude_task:
            tasks.append(claude_task)
        if embedding_task:
            tasks.append(embedding_task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Cache results
            idx = 0
            if claude_task:
                if not isinstance(results[idx], Exception):
                    self._claude_cache[claude_cache_key] = results[idx]
                    self.metrics["claude_calls"] += 1
                idx += 1
            
            if embedding_task:
                if not isinstance(results[idx], Exception):
                    self._embedding_cache[embedding_cache_key] = results[idx]
                    self.metrics["embedding_calls"] += 1
        
        latency = (time.time() - start_time) * 1000
        self.metrics["total_latency_ms"] += latency
        self.metrics["operations"] += 1
        
        logger.info(f"Parallel analysis: {latency:.2f}ms")
        
        return {
            "claude_result": self._claude_cache.get(claude_cache_key),
            "embedding": self._embedding_cache.get(embedding_cache_key),
            "latency_ms": latency
        }
    
    async def _call_claude(
        self,
        question: str,
        answer: str,
        claude_client
    ) -> Dict[str, Any]:
        """Call Claude API for analysis."""
        prompt = f"""
        Question: {question}
        Answer: {answer}
        
        Is the answer relevant? Respond with JSON:
        {{"is_relevant": true/false, "confidence": 0.0-1.0}}
        """
        
        response = await claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        try:
            return json.loads(response.content[0].text)
        except:
            return {"is_relevant": True, "confidence": 0.5}
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for cache key."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        avg_latency = (
            self.metrics["total_latency_ms"] / self.metrics["operations"]
            if self.metrics["operations"] > 0
            else 0
        )
        
        cache_hit_rate = (
            self.metrics["tts_cache_hits"] / 
            (self.metrics["tts_calls"] + self.metrics["tts_cache_hits"])
            if (self.metrics["tts_calls"] + self.metrics["tts_cache_hits"]) > 0
            else 0
        )
        
        return {
            **self.metrics,
            "avg_latency_ms": round(avg_latency, 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "cache_sizes": {
                "tts": len(self._tts_memory_cache),
                "claude": len(self._claude_cache),
                "embedding": len(self._embedding_cache)
            }
        }
    
    def clear_caches(self):
        """Clear all memory caches."""
        self._tts_memory_cache.clear()
        self._claude_cache.clear()
        self._embedding_cache.clear()
        logger.info("Cleared all performance caches")
