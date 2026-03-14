"""
GeminiEmbeddingService
======================
Wraps Gemini's embedding API (gemini-embedding-001) for two use cases:

1. Semantic similarity scoring — cosine similarity between a candidate
   answer and an ideal answer. Used by ClaudeStrategyService to blend
   a quantitative semantic signal into the qualitative Claude score.

2. Question retrieval — shared genai.Client with QuestionService for
   Pinecone RAG queries (avoids duplicate API client initialisation).
"""

import asyncio
import logging
import math
from typing import List, Optional

from google import genai

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

# Stable Gemini embedding model. Produces 3072-dim vectors by default;
# we pin output_dimensionality=768 to stay compatible with existing
# Pinecone indexes built with text-embedding-004.
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


class GeminiEmbeddingService:
    _client: Optional[genai.Client] = None

    @classmethod
    def _get_client(cls) -> Optional[genai.Client]:
        if cls._client is None:
            settings = get_settings()
            if not settings.google_api_key:
                return None
            cls._client = genai.Client(api_key=settings.google_api_key)
        return cls._client

    @classmethod
    async def embed(
        cls,
        text: str,
        task_type: str = "SEMANTIC_SIMILARITY",
    ) -> Optional[List[float]]:
        """
        Embed a single text string using gemini-embedding-001.
        Returns None if the API is unavailable or the call fails.
        """
        client = cls._get_client()
        if not client:
            return None
        try:
            res = await asyncio.to_thread(
                client.models.embed_content,
                model=EMBEDDING_MODEL,
                contents=[text],
                config={
                    "task_type": task_type,
                    "output_dimensionality": EMBEDDING_DIM,
                },
            )
            return res.embeddings[0].values
        except Exception as exc:
            logger.warning(f"GeminiEmbeddingService.embed failed: {exc}")
            return None

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Cosine similarity between two equal-length vectors → [0.0, 1.0]."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(y * y for y in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (mag_a * mag_b)))

    @classmethod
    async def semantic_similarity_score(
        cls,
        candidate_answer: str,
        ideal_answer: str,
    ) -> Optional[float]:
        """
        Embed both texts and return their cosine similarity (0.0–1.0).
        Returns None if embeddings are unavailable.
        """
        vec_a, vec_b = await asyncio.gather(
            cls.embed(candidate_answer),
            cls.embed(ideal_answer),
        )
        if vec_a is None or vec_b is None:
            return None
        return cls.cosine_similarity(vec_a, vec_b)
