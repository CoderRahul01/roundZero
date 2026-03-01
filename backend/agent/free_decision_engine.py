"""
Free Decision Engine using Groq API (zero cost).

Replaces expensive Claude/Gemini APIs with:
- Groq API (14,400 free requests/day)
- Llama 3.1 8B model (fast, good quality)
- Sentence Transformers for embeddings (self-hosted)
- Async operations for performance
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Literal, Optional, Any

logger = logging.getLogger(__name__)

Action = Literal["CONTINUE", "NEXT", "HINT", "ENCOURAGE"]


@dataclass
class EvaluationResult:
    """Result of answer evaluation."""
    action: Action
    message: str
    score: Optional[int]
    semantic_similarity: Optional[float] = None
    requires_followup: bool = False
    followup_question: Optional[str] = None


class FreeEmbeddingService:
    """Free embedding service using Sentence Transformers."""
    
    def __init__(self):
        """Initialize Sentence Transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            # all-MiniLM-L6-v2: 384 dims, fast, good quality, 80MB
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("FreeEmbeddingService initialized with all-MiniLM-L6-v2")
        except ImportError:
            logger.error("sentence-transformers package not installed")
            self.model = None
    
    async def get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (384 dimensions)
        """
        if not self.model:
            return []
        
        def _embed():
            return self.model.encode(text).tolist()
        
        try:
            return await asyncio.to_thread(_embed)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []


class FreeDecisionEngine:
    """
    Free decision engine using Groq API.
    
    Features:
    - Groq API with Llama 3.1 8B (14,400 free requests/day)
    - Sentence Transformers for embeddings (self-hosted)
    - Follow-up question generation
    - Concurrent evaluation tasks
    - Score adjustment based on confidence and fillers
    - Request counting for free tier monitoring
    """
    
    def __init__(self, groq_api_key: str, enable_embeddings: bool = True):
        """
        Initialize free decision engine.
        
        Args:
            groq_api_key: Groq API key (free tier)
            enable_embeddings: Whether to enable semantic similarity
        """
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=groq_api_key)
            self.model = 'llama-3.1-8b-instant'  # Fast, good quality
            logger.info(f"FreeDecisionEngine initialized with Groq ({self.model})")
        except ImportError:
            logger.error("groq package not installed")
            self.client = None
        
        self.embedding_service = None
        if enable_embeddings:
            self.embedding_service = FreeEmbeddingService()
        
        self.followup_counts: dict[str, int] = {}
        self.max_followups = 2
        self.request_count = 0  # Track API usage
        self.daily_limit = 14400  # Groq free tier limit
        
        logger.info("FreeDecisionEngine ready (zero cost)")
    
    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        confidence: int,
        fillers: int,
        mode: Literal["buddy", "strict"],
        ideal_answer: str = "",
        question_id: Optional[str] = None
    ) -> EvaluationResult:
        """
        Comprehensive async answer evaluation using Groq.
        
        Args:
            question: Interview question
            answer: User's answer
            confidence: Confidence score (0-100)
            fillers: Number of filler words
            mode: Interview mode (buddy or strict)
            ideal_answer: Expected answer for comparison
            question_id: Question identifier for follow-up tracking
        
        Returns:
            EvaluationResult with action, message, score, and semantic_similarity
        """
        # Check free tier limit
        if self.request_count >= self.daily_limit:
            logger.warning(f"Groq daily limit reached ({self.daily_limit}), using heuristics")
            return self._evaluate_with_heuristics_result(answer, confidence, fillers, mode)
        
        # Concurrent evaluation tasks
        tasks = []
        
        # Task 1: Groq evaluation
        tasks.append(self._evaluate_with_groq(question, answer, ideal_answer, mode))
        
        # Task 2: Semantic similarity (if embedding service available)
        if self.embedding_service and ideal_answer:
            tasks.append(
                self._calculate_semantic_similarity(ideal_answer, answer)
            )
        else:
            tasks.append(asyncio.sleep(0))  # No-op task
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract results
        groq_result = results[0] if not isinstance(results[0], Exception) else None
        semantic_similarity = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
        
        # Fallback to heuristics if Groq fails
        if groq_result is None:
            logger.warning("Groq evaluation failed, using heuristics")
            return self._evaluate_with_heuristics_result(answer, confidence, fillers, mode)
        
        # Adjust score based on confidence and fillers
        adjusted_score = self._adjust_score(
            groq_result.get("score"),
            confidence,
            fillers
        )
        
        # Check if follow-up is needed
        requires_followup = False
        followup_question = None
        
        if question_id:
            followup_count = self.followup_counts.get(question_id, 0)
            if followup_count < self.max_followups and groq_result.get("requires_followup"):
                requires_followup = True
                followup_question = groq_result.get("followup_question")
                self.followup_counts[question_id] = followup_count + 1
        
        return EvaluationResult(
            action=groq_result["action"],
            message=groq_result["message"],
            score=adjusted_score,
            semantic_similarity=semantic_similarity,
            requires_followup=requires_followup,
            followup_question=followup_question
        )
    
    async def _evaluate_with_groq(
        self,
        question: str,
        answer: str,
        ideal_answer: str,
        mode: str
    ) -> dict[str, Any]:
        """
        Async Groq evaluation using Llama 3.1 8B.
        
        Args:
            question: Interview question
            answer: User's answer
            ideal_answer: Expected answer
            mode: Interview mode
        
        Returns:
            Dictionary with action, message, score, requires_followup, followup_question
        """
        if not self.client:
            raise RuntimeError("Groq client not initialized")
        
        prompt = self._build_evaluation_prompt(question, answer, ideal_answer, mode)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert interview coach. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            self.request_count += 1
            
            result = self._parse_llm_response(response.choices[0].message.content)
            logger.debug(f"Groq evaluation: {result['action']}, score: {result.get('score')} (request #{self.request_count})")
            return result
            
        except Exception as e:
            logger.error(f"Error in Groq evaluation: {e}")
            raise
    
    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        ideal_answer: str,
        mode: str
    ) -> str:
        """Build evaluation prompt for Groq."""
        return f"""Evaluate the candidate's interview answer and decide the next action.

Mode: {mode}
Question: {question}
Ideal Answer: {ideal_answer}
Candidate Answer: {answer}

Evaluate based on:
1. Technical accuracy and depth
2. Completeness of the answer
3. Communication clarity
4. Relevance to the question

Decide the next action:
- NEXT: Answer is complete and satisfactory, move to next question
- CONTINUE: Answer needs more detail, let them continue
- HINT: Answer is off-track, provide a hint
- ENCOURAGE: Answer is weak, provide encouragement

If action is NEXT, provide a score from 0 to 100.
If the answer is incomplete or unclear, set requires_followup to true and provide a followup_question.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "action": "CONTINUE|NEXT|HINT|ENCOURAGE",
  "message": "feedback message for the candidate",
  "score": 0-100 or null,
  "requires_followup": true or false,
  "followup_question": "follow-up question text or null"
}}"""
    
    def _parse_llm_response(self, text: str) -> dict[str, Any]:
        """Parse LLM's JSON response."""
        text = text.strip()
        
        # Remove markdown code blocks if present
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            match = re.search(r'\{.*\}', text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        
        # Fallback: return default structure
        logger.warning("Failed to parse LLM response, using default")
        return {
            "action": "CONTINUE",
            "message": "Please continue with your answer.",
            "score": None,
            "requires_followup": False,
            "followup_question": None
        }
    
    def _evaluate_with_heuristics_result(
        self,
        answer: str,
        confidence: int,
        fillers: int,
        mode: str
    ) -> EvaluationResult:
        """Fallback heuristic evaluation returning EvaluationResult."""
        result = self._evaluate_with_heuristics(answer, confidence, fillers, mode)
        return EvaluationResult(
            action=result["action"],
            message=result["message"],
            score=result.get("score"),
            semantic_similarity=None,
            requires_followup=False,
            followup_question=None
        )
    
    def _evaluate_with_heuristics(
        self,
        answer: str,
        confidence: int,
        fillers: int,
        mode: str
    ) -> dict[str, Any]:
        """Fallback heuristic evaluation."""
        words = re.findall(r"[a-zA-Z']+", answer)
        count = len(words)
        
        if count < 20:
            action = "HINT" if mode == "strict" else "ENCOURAGE"
            message = "Too short. Clarify your architecture and trade-offs." if mode == "strict" else "Good start. Add more detail on your reasoning."
        elif fillers >= max(3, count // 14):
            action = "HINT"
            message = "Slow down and remove filler words. Structure your answer in clear steps." if mode == "strict" else "Try pausing briefly to reduce filler words."
        elif confidence < 45:
            action = "ENCOURAGE"
            message = "You are close. Start with a high-level plan, then drill into details."
        elif count >= 40:
            action = "NEXT"
            message = "Answer accepted. Next question." if mode == "strict" else "Great explanation. Let's move to the next question."
        else:
            action = "CONTINUE"
            message = "Continue your answer and include edge cases."
        
        return {
            "action": action,
            "message": message,
            "score": 70 if action == "NEXT" else None,
            "requires_followup": False,
            "followup_question": None
        }
    
    async def _calculate_semantic_similarity(
        self,
        ideal_answer: str,
        user_answer: str
    ) -> float:
        """
        Calculate semantic similarity using Sentence Transformers.
        
        Args:
            ideal_answer: Expected answer
            user_answer: User's answer
        
        Returns:
            Cosine similarity score (0-1)
        """
        if not self.embedding_service:
            return 0.0
        
        try:
            # Get embeddings concurrently
            ideal_embedding, user_embedding = await asyncio.gather(
                self.embedding_service.get_embedding(ideal_answer),
                self.embedding_service.get_embedding(user_answer)
            )
            
            if not ideal_embedding or not user_embedding:
                return 0.0
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(ideal_embedding, user_embedding)
            logger.debug(f"Semantic similarity: {similarity:.3f}")
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _adjust_score(
        self,
        base_score: Optional[int],
        confidence: int,
        fillers: int
    ) -> Optional[int]:
        """
        Adjust score based on confidence and filler words.
        
        Args:
            base_score: Base score from Groq
            confidence: Confidence score (0-100)
            fillers: Number of filler words
        
        Returns:
            Adjusted score or None
        """
        if base_score is None:
            return None
        
        adjusted = base_score
        
        # Penalize low confidence
        if confidence < 50:
            adjusted -= (50 - confidence) // 5
        
        # Penalize excessive fillers
        if fillers > 5:
            adjusted -= min(10, (fillers - 5) * 2)
        
        # Clamp to 0-100
        return max(0, min(100, adjusted))
    
    async def should_interrupt(
        self,
        answer_buffer: str,
        question: str,
        silence_duration: float
    ) -> tuple[bool, str]:
        """
        Determine if AI should interrupt with follow-up question.
        
        Args:
            answer_buffer: User's answer so far
            question: Original question
            silence_duration: Seconds of silence
        
        Returns:
            Tuple of (should_interrupt, follow_up_question)
        """
        # Don't interrupt too early
        if silence_duration < 3.0:
            return False, ""
        
        # Don't interrupt very short answers
        if len(answer_buffer.split()) < 10:
            return False, ""
        
        # Check free tier limit
        if self.request_count >= self.daily_limit:
            return False, ""
        
        if not self.client:
            return False, ""
        
        # Ask Groq if follow-up is needed
        prompt = f"""Question: {question}
User's answer so far: {answer_buffer}

The user has been silent for {silence_duration:.1f} seconds.
Should I ask a follow-up question? If yes, what should I ask?

Respond with ONLY valid JSON (no markdown):
{{"should_interrupt": true or false, "followup": "question text or null"}}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an interview coach. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            self.request_count += 1
            
            result = self._parse_interrupt_response(response.choices[0].message.content)
            return result["should_interrupt"], result.get("followup", "")
            
        except Exception as e:
            logger.error(f"Error in should_interrupt: {e}")
            return False, ""
    
    def _parse_interrupt_response(self, text: str) -> dict[str, Any]:
        """Parse interrupt decision response."""
        text = text.strip()
        
        # Remove markdown code blocks
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        
        return {"should_interrupt": False, "followup": None}
    
    def reset_followup_count(self, question_id: str):
        """Reset follow-up count for a question."""
        self.followup_counts.pop(question_id, None)
    
    def get_followup_count(self, question_id: str) -> int:
        """Get current follow-up count for a question."""
        return self.followup_counts.get(question_id, 0)
    
    def get_request_count(self) -> int:
        """Get current request count for monitoring."""
        return self.request_count
    
    def reset_request_count(self):
        """Reset request count (call daily)."""
        self.request_count = 0
        logger.info("Groq request count reset")
    
    def get_remaining_requests(self) -> int:
        """Get remaining free tier requests."""
        return max(0, self.daily_limit - self.request_count)
    
    def is_near_limit(self, threshold: float = 0.8) -> bool:
        """Check if approaching free tier limit."""
        return self.request_count >= (self.daily_limit * threshold)
