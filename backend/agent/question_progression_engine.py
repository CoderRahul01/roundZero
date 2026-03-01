"""
Question Progression Engine

Manages question sequencing, progress tracking, and feedback generation
for the interview flow.
"""

import logging
from typing import Optional, List, Dict
from anthropic import AsyncAnthropic
from elevenlabs.types import VoiceSettings

logger = logging.getLogger(__name__)


class QuestionProgressionEngine:
    """
    Manages question progression and feedback generation.
    
    Features:
    - Question loading and sequencing
    - Progress tracking (current/total)
    - Feedback generation with Claude
    - End-of-questions detection
    """
    
    def __init__(
        self,
        tts_service,
        claude_client: AsyncAnthropic,
        question_repository=None
    ):
        """
        Initialize QuestionProgressionEngine.
        
        Args:
            tts_service: Text-to-speech service for audio generation
            claude_client: Anthropic Claude client for feedback generation
            question_repository: Optional repository for question retrieval
        """
        self.tts_service = tts_service
        self.claude_client = claude_client
        self.question_repository = question_repository
        
        self.questions: List[Dict] = []
        self.current_index: int = 0
        
        # Voice settings for professional tone
        self.question_voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
        
        logger.info("QuestionProgressionEngine initialized")
    
    async def load_questions(
        self,
        session_id: str,
        question_ids: Optional[List[str]] = None
    ) -> int:
        """
        Load questions for the interview session.
        
        Args:
            session_id: Interview session identifier
            question_ids: Optional list of specific question IDs to load
        
        Returns:
            Number of questions loaded
        """
        if self.question_repository:
            # Load from repository
            self.questions = await self.question_repository.get_questions(
                session_id=session_id,
                question_ids=question_ids
            )
        else:
            # Fallback: use provided question IDs or empty list
            self.questions = []
            if question_ids:
                # In production, this would fetch from database
                # For now, create placeholder questions
                self.questions = [
                    {"id": qid, "text": f"Question {i+1}", "topic": "general"}
                    for i, qid in enumerate(question_ids)
                ]
        
        self.current_index = 0
        logger.info(f"Loaded {len(self.questions)} questions for session {session_id}")
        return len(self.questions)
    
    def get_next_question(self) -> Optional[Dict]:
        """
        Get the next question in the sequence.
        
        Returns:
            Question dictionary or None if no more questions
        """
        if self.current_index >= len(self.questions):
            logger.info("No more questions available")
            return None
        
        question = self.questions[self.current_index]
        self.current_index += 1
        
        logger.debug(f"Retrieved question {self.current_index}/{len(self.questions)}")
        return question
    
    def get_current_question(self) -> Optional[Dict]:
        """
        Get the current question without advancing.
        
        Returns:
            Current question dictionary or None
        """
        if self.current_index == 0 or self.current_index > len(self.questions):
            return None
        
        return self.questions[self.current_index - 1]
    
    def get_progress(self) -> Dict:
        """
        Get current progress information.
        
        Returns:
            Dictionary with progress metrics
        """
        completed = self.current_index
        total = len(self.questions)
        percentage = (completed / total * 100) if total > 0 else 0
        is_final = completed == total
        
        return {
            "current": completed,
            "total": total,
            "percentage": round(percentage, 1),
            "display": f"Question {completed} of {total}",
            "is_final": is_final
        }
    
    async def generate_feedback(
        self,
        question: str,
        answer: str,
        evaluation: Optional[Dict] = None
    ) -> str:
        """
        Generate encouraging feedback using Claude.
        
        Args:
            question: The question that was asked
            answer: The candidate's answer
            evaluation: Optional evaluation results
        
        Returns:
            Feedback message (1-2 sentences)
        """
        prompt = f"""Generate brief, encouraging feedback (1-2 sentences) for this interview answer.

Question: {question}
Answer: {answer}

Guidelines:
- Keep it positive and encouraging
- Be concise (max 2 sentences)
- Focus on what they did well
- If the answer was weak, still be supportive

Feedback:"""
        
        try:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            feedback = response.content[0].text.strip()
            logger.debug(f"Generated feedback: {feedback}")
            return feedback
        
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            # Fallback feedback
            return "Thank you for your answer. Let's move on to the next question."
    
    async def generate_transition_message(self, next_question_number: int) -> str:
        """
        Generate transition message between questions.
        
        Args:
            next_question_number: The number of the next question
        
        Returns:
            Transition message
        """
        return f"Moving to question {next_question_number}..."
    
    async def generate_question_audio(self, question_text: str) -> bytes:
        """
        Generate audio for a question.
        
        Args:
            question_text: The question text to convert to audio
        
        Returns:
            Audio bytes
        """
        try:
            audio = await self.tts_service.synthesize_speech(
                text=question_text,
                voice_settings=self.question_voice_settings,
                use_cache=True
            )
            
            logger.debug(f"Generated audio for question: {question_text[:50]}...")
            return audio
        
        except Exception as e:
            logger.error(f"Error generating question audio: {e}")
            raise
    
    def is_complete(self) -> bool:
        """
        Check if all questions have been answered.
        
        Returns:
            True if all questions completed
        """
        return self.current_index >= len(self.questions)
    
    def reset(self):
        """Reset progression to start."""
        self.current_index = 0
        logger.info("Question progression reset")
    
    def get_remaining_count(self) -> int:
        """
        Get number of remaining questions.
        
        Returns:
            Number of questions left
        """
        return max(0, len(self.questions) - self.current_index)
