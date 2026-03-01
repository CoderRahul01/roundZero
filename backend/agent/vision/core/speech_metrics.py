"""
SpeechMetrics data class for speech pattern analysis results.

This module defines the data structure for speech analysis including
filler words, pace, and pauses.
"""

from pydantic import BaseModel, Field


class SpeechMetrics(BaseModel):
    """
    Data class for speech analysis results.
    
    Attributes:
        filler_word_count: Number of filler words detected
        speech_pace: Words per minute
        long_pause_count: Number of pauses >= 3 seconds
        average_filler_rate: Fillers per 100 words
        rapid_speech: Flag for pace > 180 WPM
        slow_speech: Flag for pace < 100 WPM
    """
    
    filler_word_count: int = Field(ge=0)
    speech_pace: float = Field(ge=0)
    long_pause_count: int = Field(ge=0)
    average_filler_rate: float = Field(ge=0)
    rapid_speech: bool = False
    slow_speech: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "filler_word_count": self.filler_word_count,
            "speech_pace": self.speech_pace,
            "long_pause_count": self.long_pause_count,
            "average_filler_rate": self.average_filler_rate,
            "rapid_speech": self.rapid_speech,
            "slow_speech": self.slow_speech
        }
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "filler_word_count": 5,
                "speech_pace": 145.5,
                "long_pause_count": 2,
                "average_filler_rate": 3.4,
                "rapid_speech": False,
                "slow_speech": False
            }
        }
