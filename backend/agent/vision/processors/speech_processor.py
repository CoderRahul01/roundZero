"""
SpeechProcessor for analyzing speech patterns from transcripts.

This module processes transcript segments to detect filler words,
calculate speech pace, and track pauses.
"""

import time
import re
import logging
from typing import Optional, Dict
from agent.vision.core.speech_metrics import SpeechMetrics

logger = logging.getLogger(__name__)


class SpeechProcessor:
    """
    Processes transcript segments for speech pattern analysis.
    
    Features:
    - Filler word detection (um, uh, like, basically, etc.)
    - Speech pace calculation (words per minute)
    - Long pause detection (3+ seconds)
    - Per-question metrics tracking
    """
    
    def __init__(self, session_id: str, mongo_repository):
        """
        Initialize SpeechProcessor.
        
        Args:
            session_id: Current session identifier
            mongo_repository: LiveSessionRepository instance
        """
        self.session_id = session_id
        self.mongo_repository = mongo_repository
        
        # Filler word regex patterns
        self.filler_patterns = [
            r'\bum\b',
            r'\buh\b',
            r'\blike\b',
            r'\bbasically\b',
            r'\byou know\b',
            r'\bsort of\b',
            r'\bkind of\b'
        ]
        
        # Current question metrics
        self.current_question_id: Optional[str] = None
        self.filler_word_count = 0
        self.word_count = 0
        self.start_time: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        self.long_pause_count = 0
        
        logger.info(f"Initialized SpeechProcessor for session {session_id}")
    
    async def process_transcript_segment(
        self,
        text: str,
        is_final: bool,
        timestamp: float
    ) -> Optional[SpeechMetrics]:
        """
        Process transcript segment for speech pattern analysis.
        
        Args:
            text: Transcript text
            is_final: Whether this is a final transcript
            timestamp: Unix timestamp
        
        Returns:
            SpeechMetrics if final segment, None otherwise
        """
        if not is_final:
            return None
        
        # Initialize timing if first segment
        if self.start_time is None:
            self.start_time = timestamp
        
        # Detect long pauses (3+ seconds since last speech)
        if self.last_speech_time and (timestamp - self.last_speech_time) >= 3.0:
            self.long_pause_count += 1
            logger.debug(
                f"Long pause detected: {timestamp - self.last_speech_time:.1f}s "
                f"(total: {self.long_pause_count})"
            )
        
        self.last_speech_time = timestamp
        
        # Count filler words
        fillers_in_segment = self._count_fillers(text)
        self.filler_word_count += fillers_in_segment
        
        # Count words
        words_in_segment = len(text.split())
        self.word_count += words_in_segment
        
        # Calculate current metrics
        metrics = self._calculate_metrics()
        
        logger.debug(
            f"Processed segment: {words_in_segment} words, "
            f"{fillers_in_segment} fillers, pace={metrics.speech_pace:.1f} WPM"
        )
        
        return metrics
    
    def _count_fillers(self, text: str) -> int:
        """
        Count filler words in text using regex patterns.
        
        Args:
            text: Text to analyze
        
        Returns:
            Number of filler words found
        """
        count = 0
        text_lower = text.lower()
        
        for pattern in self.filler_patterns:
            matches = re.findall(pattern, text_lower)
            count += len(matches)
        
        return count
    
    def _calculate_metrics(self) -> SpeechMetrics:
        """
        Calculate current speech metrics.
        
        Returns:
            SpeechMetrics instance with current values
        """
        # Calculate elapsed time
        elapsed_time = 0
        if self.start_time and self.last_speech_time:
            elapsed_time = self.last_speech_time - self.start_time
        
        # Calculate speech pace (words per minute)
        speech_pace = 0.0
        if elapsed_time > 0:
            speech_pace = (self.word_count / elapsed_time) * 60
        
        # Calculate average filler rate (fillers per 100 words)
        average_filler_rate = 0.0
        if self.word_count > 0:
            average_filler_rate = (self.filler_word_count / self.word_count) * 100
        
        # Detect rapid or slow speech
        rapid_speech = speech_pace > 180
        slow_speech = speech_pace < 100 and speech_pace > 0
        
        return SpeechMetrics(
            filler_word_count=self.filler_word_count,
            speech_pace=speech_pace,
            long_pause_count=self.long_pause_count,
            average_filler_rate=average_filler_rate,
            rapid_speech=rapid_speech,
            slow_speech=slow_speech
        )
    
    async def reset_for_new_question(self, question_id: str) -> None:
        """
        Reset metrics for new question.
        
        Args:
            question_id: New question identifier
        """
        # Store previous question metrics if exists
        if self.current_question_id and self.word_count > 0:
            await self._store_metrics()
        
        # Reset counters
        self.current_question_id = question_id
        self.filler_word_count = 0
        self.word_count = 0
        self.start_time = None
        self.last_speech_time = None
        self.long_pause_count = 0
        
        logger.info(f"Reset speech metrics for question {question_id}")
    
    async def _store_metrics(self) -> None:
        """Store speech metrics to MongoDB."""
        if self.word_count == 0:
            return
        
        metrics = self._calculate_metrics()
        
        try:
            await self.mongo_repository.add_speech_metrics(
                session_id=self.session_id,
                question_id=self.current_question_id,
                metrics=metrics.to_dict()
            )
            logger.debug(f"Stored speech metrics for question {self.current_question_id}")
        except Exception as e:
            logger.error(f"Failed to store speech metrics: {e}")
    
    def get_current_metrics(self) -> Dict:
        """
        Get current speech metrics for decision-making.
        
        Returns:
            Dictionary with current metrics
        """
        metrics = self._calculate_metrics()
        return metrics.to_dict()
