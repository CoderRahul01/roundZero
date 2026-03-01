"""
EmotionSnapshot data class for emotion analysis results.

This module defines the data structure for emotion detection results from Gemini Flash-8B.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime


class EmotionSnapshot(BaseModel):
    """
    Data class for emotion analysis results.
    
    Attributes:
        emotion: Detected emotion (confident/nervous/confused/neutral/enthusiastic)
        confidence_score: Confidence level (0-100)
        engagement_level: Engagement level (high/medium/low)
        body_language_observations: Text observations about body language
        timestamp: Unix timestamp when snapshot was taken
    """
    
    emotion: Literal["confident", "nervous", "confused", "neutral", "enthusiastic"]
    confidence_score: int = Field(ge=0, le=100)
    engagement_level: Literal["high", "medium", "low"]
    body_language_observations: str
    timestamp: float
    
    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: int) -> int:
        """Validate confidence_score is in range 0-100."""
        if not 0 <= v <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        return v
    
    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, v: str) -> str:
        """Validate emotion is one of the allowed values."""
        allowed = ["confident", "nervous", "confused", "neutral", "enthusiastic"]
        if v not in allowed:
            raise ValueError(f"emotion must be one of {allowed}")
        return v
    
    @field_validator("engagement_level")
    @classmethod
    def validate_engagement_level(cls, v: str) -> str:
        """Validate engagement_level is one of the allowed values."""
        allowed = ["high", "medium", "low"]
        if v not in allowed:
            raise ValueError(f"engagement_level must be one of {allowed}")
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "emotion": self.emotion,
            "confidence_score": self.confidence_score,
            "engagement_level": self.engagement_level,
            "body_language_observations": self.body_language_observations,
            "timestamp": self.timestamp
        }
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "emotion": "confident",
                "confidence_score": 85,
                "engagement_level": "high",
                "body_language_observations": "Maintaining eye contact, upright posture, minimal fidgeting",
                "timestamp": 1678901234.567
            }
        }
