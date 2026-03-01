"""
Gemini Embedding Service

Generates embeddings for semantic similarity calculations using Google's Gemini API.
"""

import asyncio
import os
from typing import Optional
import google.genai as genai


class GeminiEmbeddingService:
    """
    Embedding service using Gemini API.
    Uses the embedding-001 model for text embeddings.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
    
    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using Gemini.
        Returns 768-dimensional vector.
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._generate_embedding_sync,
            text
        )
        return embedding
    
    def _generate_embedding_sync(self, text: str) -> list[float]:
        """Synchronous embedding generation."""
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="semantic_similarity"
        )
        return result['embedding']
    
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        More efficient than individual calls.
        """
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._generate_embeddings_batch_sync,
            texts
        )
        return embeddings
    
    def _generate_embeddings_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding generation."""
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="semantic_similarity"
            )
            embeddings.append(result['embedding'])
        return embeddings
