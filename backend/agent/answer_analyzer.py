"""
Answer Analyzer Component

Performs real-time relevance analysis of candidate answers as they speak,
detecting off-topic responses and triggering interruptions.
"""

import asyncio
import time
import json
from typing import Optional
from anthropic import AsyncAnthropic
import numpy as np

from backend.agent.realtime_models import AnalysisResult
from backend.agent.gemini_embedding_service import GeminiEmbeddingService


class AnswerAnalyzer:
    """
    Real-time answer relevance analyzer.
    Evaluates answer relevance using Claude API and Gemini embeddings.
    """
    
    def __init__(
        self,
        claude_client: AsyncAnthropic,
        embedding_service: GeminiEmbeddingService,
        relevance_threshold: float = 0.3,
        analysis_interval: float = 5.0
    ):
        self.claude_client = claude_client
        self.embedding_service = embedding_service
        self.relevance_threshold = relevance_threshold
        self.analysis_interval = analysis_interval
        
        self._last_analysis_time: Optional[float] = None
    
    async def analyze_relevance(
        self,
        question: str,
        answer_buffer: str,
        question_topic: str
    ) -> AnalysisResult:
        """
        Analyze answer relevance in real-time.
        Runs Claude evaluation and Gemini embeddings concurrently.
        """
        # Rate limit analysis (every 5 seconds)
        current_time = time.time()
        if self._last_analysis_time:
            elapsed = current_time - self._last_analysis_time
            if elapsed < self.analysis_interval:
                return AnalysisResult(
                    is_relevant=True,
                    semantic_similarity=1.0,
                    should_interrupt=False,
                    interruption_message=None,
                    confidence=0.0,
                    analysis_duration=0.0,
                    claude_response={},
                    embedding_similarity=1.0
                )
        
        self._last_analysis_time = current_time
        analysis_start = time.time()
        
        # Run analysis tasks concurrently
        claude_task = self._evaluate_with_claude(question, answer_buffer)
        embedding_task = self._calculate_semantic_similarity(question, answer_buffer)
        
        claude_result, semantic_similarity = await asyncio.gather(
            claude_task,
            embedding_task
        )
        
        analysis_duration = time.time() - analysis_start
        
        # Determine if interruption is needed
        should_interrupt = (
            not claude_result["is_relevant"] or
            semantic_similarity < self.relevance_threshold
        )
        
        interruption_message = None
        if should_interrupt:
            interruption_message = self._generate_interruption_message(
                question_topic,
                answer_buffer
            )
        
        return AnalysisResult(
            is_relevant=claude_result["is_relevant"],
            semantic_similarity=semantic_similarity,
            should_interrupt=should_interrupt,
            interruption_message=interruption_message,
            confidence=claude_result["confidence"],
            analysis_duration=analysis_duration,
            claude_response=claude_result,
            embedding_similarity=semantic_similarity
        )
    
    async def evaluate_final_answer(
        self,
        question: str,
        answer: str
    ) -> dict:
        """
        Perform final answer evaluation after completion.
        More comprehensive than real-time analysis.
        """
        prompt = f"""
        Evaluate the following answer to the question:
        
        Question: {question}
        Answer: {answer}
        
        Provide:
        1. Is the answer complete and addresses the question? (YES/NO)
        2. Score out of 100
        3. Brief feedback
        
        Format as JSON:
        {{
            "is_complete": true/false,
            "score": 85,
            "feedback": "Your feedback here"
        }}
        """
        
        response = await self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_evaluation_response(response.content[0].text)
    
    async def _evaluate_with_claude(
        self,
        question: str,
        answer_buffer: str
    ) -> dict:
        """
        Use Claude to evaluate if answer is addressing the question.
        """
        prompt = f"""
        Question: {question}
        User's answer so far: {answer_buffer}
        
        Is the user addressing the question asked? Consider:
        - Are they talking about the right topic?
        - Is their response relevant to what was asked?
        
        Respond with JSON:
        {{
            "is_relevant": true/false,
            "confidence": 0.0-1.0,
            "reason": "brief explanation"
        }}
        """
        
        response = await self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_relevance_response(response.content[0].text)
    
    async def _calculate_semantic_similarity(
        self,
        question: str,
        answer_buffer: str
    ) -> float:
        """
        Calculate semantic similarity using Gemini embeddings.
        """
        # Generate embeddings concurrently
        question_embedding, answer_embedding = await asyncio.gather(
            self.embedding_service.get_embedding(question),
            self.embedding_service.get_embedding(answer_buffer)
        )
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(question_embedding, answer_embedding)
        return similarity
    
    def _generate_interruption_message(
        self,
        question_topic: str,
        off_topic_content: str
    ) -> str:
        """
        Generate context-aware interruption message.
        Format: "Wait, I asked about [topic], please focus on that"
        """
        return f"Wait, I asked about {question_topic}, please focus on that"
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _parse_relevance_response(self, response_text: str) -> dict:
        """Parse Claude's relevance evaluation response."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": "Parse error"
            }
    
    def _parse_evaluation_response(self, response_text: str) -> dict:
        """Parse Claude's final evaluation response."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "is_complete": True,
                "score": 70,
                "feedback": "Unable to parse evaluation"
            }
