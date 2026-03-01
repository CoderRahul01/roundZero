"""
Live Session Schema for MongoDB

This module defines the schema for the live_sessions collection in MongoDB.
The schema supports real-time updates during interview sessions with Vision Agents data.

Requirements: 8.1-8.16
"""

from typing import TypedDict, List, Optional, Literal
from datetime import datetime


# Type definitions for emotion, engagement, and difficulty
EmotionType = Literal["confident", "nervous", "confused", "neutral", "enthusiastic"]
EngagementLevel = Literal["high", "medium", "low"]
DifficultyLevel = Literal["easy", "medium", "hard"]
InterviewMode = Literal["practice", "mock", "coaching"]
SpeakerType = Literal["user", "agent"]
ActionType = Literal["CONTINUE", "INTERRUPT", "ENCOURAGE", "NEXT", "HINT"]


class TranscriptSegment(TypedDict):
    """
    Individual transcript segment from Deepgram STT.
    
    Requirements: 8.9
    
    Fields:
        speaker: Who spoke (user or agent)
        text: Transcript text content
        timestamp: ISO timestamp when segment was recorded
        is_final: Whether this is a final transcript (not interim)
    """
    speaker: SpeakerType
    text: str
    timestamp: str  # ISO 8601 format
    is_final: bool


class EmotionSnapshot(TypedDict):
    """
    Emotion analysis snapshot from Gemini Flash-8B.
    
    Requirements: 8.11
    
    Fields:
        timestamp: ISO timestamp when snapshot was captured
        emotion: Detected emotion state
        confidence_score: Confidence level (0-100)
        engagement_level: Engagement assessment
        body_language_observations: Text observations about body language
    """
    timestamp: str  # ISO 8601 format
    emotion: EmotionType
    confidence_score: int  # 0-100
    engagement_level: EngagementLevel
    body_language_observations: str


class SpeechMetrics(TypedDict):
    """
    Speech pattern metrics per question from SpeechProcessor.
    
    Requirements: 8.13
    
    Fields:
        question_id: Unique identifier for the question
        filler_word_count: Count of filler words (um, uh, like, etc.)
        speech_pace: Words per minute
        long_pause_count: Number of pauses >= 3 seconds
        average_filler_rate: Filler words per 100 words
        rapid_speech: Flag for speech pace > 180 WPM
        slow_speech: Flag for speech pace < 100 WPM
    """
    question_id: str
    filler_word_count: int
    speech_pace: float  # words per minute
    long_pause_count: int
    average_filler_rate: float  # fillers per 100 words
    rapid_speech: bool
    slow_speech: bool


class DecisionRecord(TypedDict):
    """
    AI decision record from Claude Sonnet 4.
    
    Requirements: 8.15
    
    Fields:
        timestamp: ISO timestamp when decision was made
        action: Decision action type
        context: Context data used for decision (emotion, speech metrics, etc.)
        message: Optional message generated for INTERRUPT/ENCOURAGE/HINT actions
    """
    timestamp: str  # ISO 8601 format
    action: ActionType
    context: dict  # Contains emotion, confidence, speech metrics, transcript
    message: Optional[str]


class LiveSessionDocument(TypedDict):
    """
    Complete live session document structure for MongoDB.
    
    This document stores all data for a live interview session including:
    - Session metadata (IDs, role, topics, difficulty, mode)
    - Real-time transcript from Deepgram
    - Emotion timeline from Gemini Flash-8B
    - Speech metrics from SpeechProcessor
    - AI decisions from Claude Sonnet 4
    - Session summary generated at completion
    
    Requirements: 8.1-8.16
    
    Fields:
        session_id: Unique identifier for the session
        candidate_id: User ID of the candidate
        call_id: Stream.io WebRTC call identifier
        role: Job role for the interview (e.g., "Software Engineer")
        topics: List of interview topics (e.g., ["Python", "System Design"])
        difficulty: Interview difficulty level
        mode: Interview mode type
        started_at: ISO timestamp when session started
        ended_at: ISO timestamp when session ended (null if in progress)
        transcript: Array of transcript segments
        emotion_timeline: Array of emotion snapshots
        speech_metrics: Dictionary of speech metrics per question
        decisions: Array of AI decision records
        session_summary: Final session summary text (null until completion)
    """
    # Session identification (Requirements: 8.2, 8.3, 8.4)
    session_id: str
    candidate_id: str
    call_id: str
    
    # Session configuration (Requirements: 8.5)
    role: str
    topics: List[str]
    difficulty: DifficultyLevel
    mode: InterviewMode
    
    # Timing (Requirements: 8.6, 8.7)
    started_at: str  # ISO 8601 format
    ended_at: Optional[str]  # ISO 8601 format, null if in progress
    
    # Real-time data (Requirements: 8.8, 8.9, 8.10, 8.11, 8.12, 8.13, 8.14, 8.15)
    transcript: List[TranscriptSegment]
    emotion_timeline: List[EmotionSnapshot]
    speech_metrics: dict  # key: question_id, value: SpeechMetrics
    decisions: List[DecisionRecord]
    
    # Session completion (Requirements: 8.16)
    session_summary: Optional[str]


def create_example_live_session() -> LiveSessionDocument:
    """
    Create an example live session document for reference and testing.
    
    Returns:
        LiveSessionDocument: Example document with all required fields
    """
    return LiveSessionDocument(
        # Session identification
        session_id="session_abc123",
        candidate_id="user_xyz789",
        call_id="call_stream_456",
        
        # Session configuration
        role="Software Engineer",
        topics=["Python", "System Design", "Algorithms"],
        difficulty="medium",
        mode="practice",
        
        # Timing
        started_at="2024-01-15T10:30:00Z",
        ended_at=None,  # In progress
        
        # Real-time data
        transcript=[
            TranscriptSegment(
                speaker="agent",
                text="Hello! Welcome to your Software Engineer interview.",
                timestamp="2024-01-15T10:30:05Z",
                is_final=True
            ),
            TranscriptSegment(
                speaker="user",
                text="Thank you, I'm excited to get started.",
                timestamp="2024-01-15T10:30:10Z",
                is_final=True
            ),
        ],
        
        emotion_timeline=[
            EmotionSnapshot(
                timestamp="2024-01-15T10:30:10Z",
                emotion="confident",
                confidence_score=75,
                engagement_level="high",
                body_language_observations="Good posture, maintaining eye contact, relaxed shoulders"
            ),
        ],
        
        speech_metrics={
            "question_1": SpeechMetrics(
                question_id="question_1",
                filler_word_count=3,
                speech_pace=145.5,
                long_pause_count=1,
                average_filler_rate=2.5,
                rapid_speech=False,
                slow_speech=False
            ),
        },
        
        decisions=[
            DecisionRecord(
                timestamp="2024-01-15T10:30:15Z",
                action="CONTINUE",
                context={
                    "emotion": "confident",
                    "confidence_score": 75,
                    "engagement_level": "high",
                    "filler_word_count": 3,
                    "speech_pace": 145.5,
                    "long_pause_count": 1,
                    "transcript_length": 50
                },
                message=None
            ),
        ],
        
        session_summary=None  # Will be populated at session completion
    )


# Field descriptions for documentation
FIELD_DESCRIPTIONS = {
    "session_id": "Unique identifier for the session (generated by backend)",
    "candidate_id": "User ID of the candidate (from JWT token)",
    "call_id": "Stream.io WebRTC call identifier (from Stream API)",
    "role": "Job role for the interview (e.g., 'Software Engineer', 'Product Manager')",
    "topics": "List of interview topics (e.g., ['Python', 'System Design', 'Algorithms'])",
    "difficulty": "Interview difficulty level: 'easy', 'medium', or 'hard'",
    "mode": "Interview mode: 'practice', 'mock', or 'coaching'",
    "started_at": "ISO 8601 timestamp when session started",
    "ended_at": "ISO 8601 timestamp when session ended (null if in progress)",
    "transcript": "Array of transcript segments from Deepgram STT",
    "emotion_timeline": "Array of emotion snapshots from Gemini Flash-8B",
    "speech_metrics": "Dictionary mapping question_id to SpeechMetrics object",
    "decisions": "Array of AI decision records from Claude Sonnet 4",
    "session_summary": "Final session summary text (null until completion)",
}


# Validation rules
VALIDATION_RULES = {
    "session_id": "Must be unique, non-empty string",
    "candidate_id": "Must be non-empty string",
    "call_id": "Must be non-empty string from Stream.io",
    "role": "Must be non-empty string (1-100 characters)",
    "topics": "Must be array with 1-10 items, each 1-50 characters",
    "difficulty": "Must be one of: 'easy', 'medium', 'hard'",
    "mode": "Must be one of: 'practice', 'mock', 'coaching'",
    "started_at": "Must be valid ISO 8601 timestamp",
    "ended_at": "Must be valid ISO 8601 timestamp or null",
    "transcript.speaker": "Must be 'user' or 'agent'",
    "transcript.is_final": "Must be boolean",
    "emotion_timeline.emotion": "Must be one of: 'confident', 'nervous', 'confused', 'neutral', 'enthusiastic'",
    "emotion_timeline.confidence_score": "Must be integer 0-100",
    "emotion_timeline.engagement_level": "Must be one of: 'high', 'medium', 'low'",
    "speech_metrics.filler_word_count": "Must be non-negative integer",
    "speech_metrics.speech_pace": "Must be non-negative float (words per minute)",
    "speech_metrics.long_pause_count": "Must be non-negative integer",
    "speech_metrics.average_filler_rate": "Must be non-negative float",
    "decisions.action": "Must be one of: 'CONTINUE', 'INTERRUPT', 'ENCOURAGE', 'NEXT', 'HINT'",
}
