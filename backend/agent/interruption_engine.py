"""
Interruption Engine Component

Generates context-aware interruption messages and manages interruption attempts
to avoid frustrating the candidate.
"""

from typing import Optional
from agent.realtime_models import InterruptionContext


class InterruptionEngine:
    """
    Manages intelligent interruptions for off-topic responses.
    Limits interruptions to max 2 per question.
    """
    
    def __init__(
        self,
        max_interruptions_per_question: int = 2
    ):
        self.max_interruptions_per_question = max_interruptions_per_question
        self._interruption_count = 0
        self._interruption_history: list[str] = []
    
    def can_interrupt(self) -> bool:
        """Check if interruption is allowed based on attempt count."""
        return self._interruption_count < self.max_interruptions_per_question
    
    def generate_interruption(
        self,
        context: InterruptionContext
    ) -> Optional[str]:
        """
        Generate context-aware interruption message.
        Returns None if max interruptions reached.
        """
        if not self.can_interrupt():
            return None
        
        # Generate message based on attempt number
        if context.attempt_number == 1:
            message = self._generate_first_interruption(context)
        else:
            message = self._generate_second_interruption(context)
        
        self._interruption_count += 1
        self._interruption_history.append(message)
        
        return message
    
    def _generate_first_interruption(
        self,
        context: InterruptionContext
    ) -> str:
        """
        Generate first interruption message (gentle redirect).
        Format: "Wait, I asked about [topic], please focus on that"
        """
        return f"Wait, I asked about {context.question_topic}, please focus on that"
    
    def _generate_second_interruption(
        self,
        context: InterruptionContext
    ) -> str:
        """
        Generate second interruption message (more direct).
        Format: "Let me stop you there. The question is specifically about [topic]"
        """
        return f"Let me stop you there. The question is specifically about {context.question_topic}"
    
    def reset_for_new_question(self):
        """Reset interruption counter for new question."""
        self._interruption_count = 0
        self._interruption_history.clear()
    
    def get_interruption_count(self) -> int:
        """Get current interruption count for this question."""
        return self._interruption_count
    
    def get_interruption_history(self) -> list[str]:
        """Get history of interruption messages for this question."""
        return self._interruption_history.copy()
