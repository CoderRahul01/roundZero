"""
Enhanced Decision Engine with semantic matching and async operations.

Extends the base DecisionEngine with:
- Semantic similarity analysis using embeddings
- Follow-up question logic
- Async Claude API calls
- Comprehensive answer evaluation
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Literal, Optional, Any
from anthropic import AsyncAnthropic

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


class GeminiEmbeddingService:
    """Service for generating embeddings using Gemini."""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini embedding service.
        
        Args:
            api_key: Gemini API key
        """
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model = "models/gemini-embedding-001"
            logger.info("GeminiEmbeddingService initialized")
        except ImportError:
            logger.error("google-genai package not installed")
            self.client = None
    
    async def get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (768 dimensions for gemini-embedding-001)
        """
        if not self.client:
            return []
        
        def _embed():
            result = self.client.models.embed_content(
                model=self.model,
                contents=text
            )
            return result.embeddings[0].values
        
        try:
            return await asyncio.to_thread(_embed)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []


class EnhancedDecisionEngine:
    """
    Enhanced decision engine with semantic matching and async operations.
    
    Features:
    - Async Claude API calls for answer evaluation
    - Semantic similarity using Gemini embeddings
    - Follow-up question generation
    - Concurrent evaluation tasks
    - Score adjustment based on confidence and fillers
    - Follow-up question limiting (max 2 per question)
    """
    
    def __init__(self, anthropic_api_key: str, gemini_api_key: Optional[str] = None):
        """
        Initialize enhanced decision engine.
        
        Args:
            anthropic_api_key: Anthropic API key for Claude
            gemini_api_key: Optional Gemini API key for embeddings
        """
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
        self.embedding_service = None
        
        if gemini_api_key:
            self.embedding_service = GeminiEmbeddingService(gemini_api_key)
        
        self.followup_counts: dict[str, int] = {}  # Track follow-ups per question
        self.max_followups = 2
        
        logger.info("EnhancedDecisionEngine initialized")
    
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
        Comprehensive async answer evaluation.
        
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
        # Concurrent evaluation tasks
        tasks = []
        
        # Task 1: Claude evaluation
        tasks.append(self._evaluate_with_claude(question, answer, ideal_answer, mode))
        
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
        claude_result = results[0] if not isinstance(results[0], Exception) else None
        semantic_similarity = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
        
        # Fallback to heuristics if Claude fails
        if claude_result is None:
            logger.warning("Claude evaluation failed, using heuristics")
            claude_result = self._evaluate_with_heuristics(answer, confidence, fillers, mode)
        
        # Adjust score based on confidence and fillers
        adjusted_score = self._adjust_score(
            claude_result.get("score"),
            confidence,
            fillers
        )
        
        # Check if follow-up is needed
        requires_followup = False
        followup_question = None
        
        if question_id:
            followup_count = self.followup_counts.get(question_id, 0)
            if followup_count < self.max_followups and claude_result.get("requires_followup"):
                requires_followup = True
                followup_question = claude_result.get("followup_question")
                self.followup_counts[question_id] = followup_count + 1
        
        return EvaluationResult(
            action=claude_result["action"],
            message=claude_result["message"],
            score=adjusted_score,
            semantic_similarity=semantic_similarity,
            requires_followup=requires_followup,
            followup_question=followup_question
        )
    
    async def _evaluate_with_claude(
        self,
        question: str,
        answer: str,
        ideal_answer: str,
        mode: str
    ) -> dict[str, Any]:
        """
        Async Claude evaluation.
        
        Args:
            question: Interview question
            answer: User's answer
            ideal_answer: Expected answer
            mode: Interview mode
        
        Returns:
            Dictionary with action, message, score, requires_followup, followup_question
        """
        prompt = self._build_evaluation_prompt(question, answer, ideal_answer, mode)
        
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = self._parse_claude_response(response.content[0].text)
            logger.debug(f"Claude evaluation: {result['action']}, score: {result.get('score')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in Claude evaluation: {e}")
            raise
    
    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        ideal_answer: str,
        mode: str
    ) -> str:
        """Build evaluation prompt for Claude."""
        return f"""You are an expert interview coach. Evaluate the candidate's answer and decide the next action.

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

Return valid JSON:
{{
  "action": "CONTINUE|NEXT|HINT|ENCOURAGE",
  "message": "feedback message for the candidate",
  "score": 0-100 or null,
  "requires_followup": true/false,
  "followup_question": "follow-up question text or null"
}}"""
    
    def _parse_claude_response(self, text: str) -> dict[str, Any]:
        """Parse Claude's JSON response."""
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
        logger.warning("Failed to parse Claude response, using default")
        return {
            "action": "CONTINUE",
            "message": "Please continue with your answer.",
            "score": None,
            "requires_followup": False,
            "followup_question": None
        }
    
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
            message = "Too short. Clarify your architecture and trade-offs." if mode == "strict" else "Good start. Add more detail."
        elif fillers >= max(3, count // 14):
            action = "HINT"
            message = "Slow down and remove filler words." if mode == "strict" else "Try pausing to reduce filler words."
        elif confidence < 45:
            action = "ENCOURAGE"
            message = "You are close. Start with a high-level plan."
        elif count >= 40:
            action = "NEXT"
            message = "Answer accepted. Next question." if mode == "strict" else "Great explanation. Let's move on."
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
        Calculate semantic similarity using embeddings.
        
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
            base_score: Base score from Claude
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
        
        # Ask Claude if follow-up is needed
        prompt = f"""Question: {question}
User's answer so far: {answer_buffer}

The user has been silent for {silence_duration:.1f} seconds.
Should I ask a follow-up question? If yes, what should I ask?

Respond with JSON: {{"should_interrupt": true/false, "followup": "question text or null"}}"""
        
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = self._parse_interrupt_response(response.content[0].text)
            return result["should_interrupt"], result.get("followup", "")
            
        except Exception as e:
            logger.error(f"Error in should_interrupt: {e}")
            return False, ""
    
    def _parse_interrupt_response(self, text: str) -> dict[str, Any]:
        """Parse interrupt decision response."""
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
