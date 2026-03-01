"""
QuestionManager for fetching interview questions from Pinecone.

This module manages question retrieval using semantic search with
fallback to MongoDB default questions.
"""

import logging
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class QuestionManager:
    """
    Manages question retrieval from Pinecone using semantic search.
    
    Features:
    - Semantic search via Pinecone
    - Gemini embeddings for query
    - Question shuffling for variety
    - Fallback to MongoDB on failure
    """
    
    def __init__(
        self,
        pinecone_client,
        gemini_embedding_service,
        mongo_repository
    ):
        """
        Initialize QuestionManager.
        
        Args:
            pinecone_client: Pinecone client instance
            gemini_embedding_service: Service for generating embeddings
            mongo_repository: MongoDB repository for fallback
        """
        self.pinecone_client = pinecone_client
        self.gemini_embedding_service = gemini_embedding_service
        self.mongo_repository = mongo_repository
        self.index_name = "interview-questions"
        
        logger.info("Initialized QuestionManager")
    
    async def fetch_questions(
        self,
        query_text: str,
        difficulty: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch questions using semantic search.
        
        Args:
            query_text: Text to search for (e.g., "Software Engineer Python")
            difficulty: Filter by difficulty (easy/medium/hard)
            limit: Number of questions to retrieve
        
        Returns:
            List of question dictionaries
        """
        try:
            # Generate embedding for query
            logger.info(f"Generating embedding for query: {query_text}")
            query_embedding = await self.gemini_embedding_service.generate_embedding(
                text=query_text
            )
            
            # Query Pinecone
            results = await self._query_pinecone(
                embedding=query_embedding,
                difficulty=difficulty,
                limit=limit
            )
            
            # Shuffle for variety
            random.shuffle(results)
            
            # Select first N questions (default 5)
            selected = results[:min(5, len(results))]
            
            logger.info(f"Retrieved {len(selected)} questions from Pinecone")
            return selected
            
        except Exception as e:
            logger.error(f"Pinecone query error: {e}")
            # Fallback to MongoDB default questions
            return await self._fetch_default_questions(difficulty, limit)
    
    async def _query_pinecone(
        self,
        embedding: List[float],
        difficulty: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone index with embedding.
        
        Args:
            embedding: Query embedding vector
            difficulty: Difficulty filter
            limit: Number of results
        
        Returns:
            List of question dictionaries
        """
        try:
            index = self.pinecone_client.Index(self.index_name)
            
            # Query with filter
            results = await index.query(
                vector=embedding,
                filter={"difficulty": difficulty},
                top_k=limit,
                include_metadata=True
            )
            
            # Extract questions from results
            questions = []
            for match in results.matches:
                questions.append({
                    "id": match.id,
                    "text": match.metadata.get("question_text", ""),
                    "difficulty": match.metadata.get("difficulty", "medium"),
                    "topics": match.metadata.get("topics", []),
                    "score": match.score,
                    "source": "pinecone"
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            raise
    
    async def _fetch_default_questions(
        self,
        difficulty: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback: fetch default questions from MongoDB.
        
        Args:
            difficulty: Question difficulty
            limit: Number of questions
        
        Returns:
            List of question dictionaries
        """
        logger.info(f"Using MongoDB fallback for {difficulty} questions")
        
        try:
            # Fetch from MongoDB
            questions = await self.mongo_repository.get_questions_by_category(
                category="software",
                difficulty=difficulty,
                limit=limit
            )
            
            # Convert to standard format
            formatted = []
            for q in questions:
                formatted.append({
                    "id": q.id,
                    "text": q.question,
                    "difficulty": q.difficulty,
                    "topics": q.topics,
                    "source": "mongodb"
                })
            
            # Shuffle and select
            random.shuffle(formatted)
            selected = formatted[:min(5, len(formatted))]
            
            logger.info(f"Retrieved {len(selected)} questions from MongoDB fallback")
            return selected
            
        except Exception as e:
            logger.error(f"MongoDB fallback failed: {e}")
            # Return empty list as last resort
            return []
