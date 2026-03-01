"""
Speech Buffer Component

Accumulates speech transcription segments and provides text for real-time analysis.
"""

import time
from typing import Optional
from dataclasses import dataclass

from agent.realtime_models import TranscriptSegment


class SpeechBuffer:
    """
    Accumulates speech transcription segments for analysis.
    Manages interim and final transcripts from STT service.
    """
    
    def __init__(self, analysis_word_threshold: int = 20):
        self.analysis_word_threshold = analysis_word_threshold
        self._segments: list[TranscriptSegment] = []
        self._accumulated_text = ""
        self._word_count = 0
    
    def add_interim_segment(self, text: str, confidence: float = 0.0):
        """
        Add interim transcription segment.
        Interim segments are temporary and replaced by final segments.
        """
        # Don't store interim segments, just update display
        pass
    
    def add_final_segment(self, text: str, confidence: float = 1.0):
        """
        Add final transcription segment.
        Final segments are accumulated for analysis.
        """
        segment = TranscriptSegment(
            text=text,
            timestamp=time.time(),
            is_final=True,
            confidence=confidence,
            speaker="user",
            word_count=len(text.split())
        )
        
        self._segments.append(segment)
        self._accumulated_text += " " + text
        self._accumulated_text = self._accumulated_text.strip()
        self._word_count = len(self._accumulated_text.split())
    
    def get_accumulated_text(self) -> str:
        """Get all accumulated final transcript text."""
        return self._accumulated_text
    
    def word_count(self) -> int:
        """Get current word count of accumulated text."""
        return self._word_count
    
    def should_trigger_analysis(self) -> bool:
        """Check if buffer has enough content for analysis."""
        return self._word_count >= self.analysis_word_threshold
    
    def get_segments(self) -> list[TranscriptSegment]:
        """Get all transcript segments."""
        return self._segments.copy()
    
    def get_recent_segments(self, count: int = 5) -> list[TranscriptSegment]:
        """Get most recent transcript segments."""
        return self._segments[-count:] if len(self._segments) >= count else self._segments.copy()
    
    def clear(self):
        """Clear all accumulated text and segments."""
        self._segments.clear()
        self._accumulated_text = ""
        self._word_count = 0
    
    def get_buffer_stats(self) -> dict:
        """Get buffer statistics for monitoring."""
        return {
            "total_segments": len(self._segments),
            "word_count": self._word_count,
            "accumulated_length": len(self._accumulated_text),
            "average_confidence": self._calculate_average_confidence()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all segments."""
        if not self._segments:
            return 0.0
        
        total_confidence = sum(seg.confidence for seg in self._segments)
        return total_confidence / len(self._segments)
