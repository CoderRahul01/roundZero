"""
Context Tracker Component

Extracts core topics from questions and maintains conversation context for
generating specific interruption messages.
"""

import asyncio
import time
from typing import Optional
from anthropic import AsyncAnthropic

from agent.realtime_models import QuestionContext


class ContextTracker:
    """
    Tracks conversation context and extracts question topics.
    Maintains history of recent questions for context-aware interactions.
    """
    
    def __init__(
        self,
        claude_client: AsyncAnthropic,
        history_size: int = 5
    ):
        self.claude_client = claude_client
        self.history_size = history_size
        self._question_history: list[QuestionContext] = []
    
    async def extract_topic(self, question: str) -> str:
        """
        Extract core topic from question using Claude.
        Returns concise phrase (3-7 words) summarizing what the question asks.
        
        Examples:
        - "What is the value of four plus two?" → "the mathematical calculation"
        - "Describe your experience with React" → "your React experience"
        """
        prompt = f"""
        Extract the core topic from this question as a concise phrase (3-7 words):
        
        Question: "{question}"
        
        The topic should complete the sentence: "I asked about ___"
        
        Examples:
        - "What is 4 + 2?" → "the mathematical calculation"
        - "Tell me about React" → "your React experience"
        - "How does async/await work?" → "how async/await works"
        
        Return only the topic phrase, nothing else.
        """
        
        try:
            response = await asyncio.wait_for(
                self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=0.5  # 500ms timeout
            )
            
            topic = response.content[0].text.strip()
            
            # Store in history
            context = QuestionContext(
                full_question=question,
                core_topic=topic,
                keywords=self._extract_keywords(question),
                timestamp=time.time()
            )
            self._add_to_history(context)
            
            return topic
            
        except asyncio.TimeoutError:
            # Fallback: use first 10 words
            words = question.split()[:10]
            fallback_topic = " ".join(words)
            
            context = QuestionContext(
                full_question=question,
                core_topic=fallback_topic,
                keywords=self._extract_keywords(question),
                timestamp=time.time()
            )
            self._add_to_history(context)
            
            return fallback_topic
    
    def get_current_context(self) -> Optional[QuestionContext]:
        """Get context for the current question."""
        if not self._question_history:
            return None
        return self._question_history[-1]
    
    def get_question_history(self) -> list[QuestionContext]:
        """Get history of recent questions."""
        return self._question_history.copy()
    
    def _extract_keywords(self, question: str) -> list[str]:
        """Extract important keywords from question (simple implementation)."""
        # Remove common words
        stop_words = {
            'what', 'is', 'the', 'a', 'an', 'how', 'why', 'when', 'where',
            'who', 'which', 'can', 'you', 'tell', 'me', 'about', 'describe'
        }
        
        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords[:5]  # Top 5 keywords
    
    def _add_to_history(self, context: QuestionContext):
        """Add question context to history with size limit."""
        self._question_history.append(context)
        if len(self._question_history) > self.history_size:
            self._question_history.pop(0)
    
    def clear_history(self):
        """Clear question history."""
        self._question_history.clear()
