"""
Real-Time Voice Interaction Data Models

This module defines all data models and state enums for the real-time voice
interaction feature, including conversation states, events, and session state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConversationState(Enum):
    """Enum for conversation states in the voice flow state machine."""
    
    IDLE = "IDLE"
    ASKING_QUESTION = "ASKING_QUESTION"
    LISTENING = "LISTENING"
    ANALYZING = "ANALYZING"
    SILENCE_DETECTED = "SILENCE_DETECTED"
    PRESENCE_CHECK = "PRESENCE_CHECK"
    INTERRUPTING = "INTERRUPTING"
    EVALUATING = "EVALUATING"
    CONNECTION_LOST = "CONNECTION_LOST"


@dataclass
class VoiceFlowState:
    """Current state of the voice flow controller."""
    
    conversation_state: ConversationState
    current_question: Optional[str] = None
    current_question_topic: Optional[str] = None
    speech_buffer: str = ""
    interruption_count: int = 0
    silence_start_time: Optional[float] = None
    presence_check_attempts: int = 0


@dataclass
class SilenceEvent:
    """Event emitted when silence is detected."""
    
    duration: float
    timestamp: float
    context: str  # "prolonged" or "answer_complete"
    audio_level_db: float = -50.0


@dataclass
class PresenceCheckResult:
    """Result of presence verification."""
    
    confirmed: bool
    attempts: int
    response_text: Optional[str]
    confidence: float
    timestamp: float


@dataclass
class AnalysisResult:
    """Result of answer relevance analysis."""
    
    is_relevant: bool
    semantic_similarity: float
    should_interrupt: bool
    interruption_message: Optional[str]
    confidence: float
    analysis_duration: float
    claude_response: dict
    embedding_similarity: float


@dataclass
class InterruptionContext:
    """Context for generating interruption messages."""
    
    question_topic: str
    off_topic_content: str
    attempt_number: int
    previous_interruptions: list[str]
    timestamp: float


@dataclass
class TranscriptSegment:
    """A segment of transcribed speech."""
    
    text: str
    timestamp: float
    is_final: bool
    confidence: float
    speaker: str  # "user" or "agent"
    word_count: int


@dataclass
class QuestionContext:
    """Context information for a question."""
    
    full_question: str
    core_topic: str
    keywords: list[str]
    timestamp: float
    expected_answer_length: Optional[int] = None


@dataclass
class VoiceSessionState:
    """Extended session state for real-time voice interactions."""
    
    # Base session fields
    session_id: str
    user_id: str
    role: str
    topics: list[str]
    difficulty: str
    mode: str
    started_at: float
    
    # Real-time voice fields
    conversation_state: ConversationState = ConversationState.IDLE
    current_question: Optional[str] = None
    current_question_topic: Optional[str] = None
    speech_buffer_text: str = ""
    interruption_count: int = 0
    silence_duration: float = 0.0
    presence_check_attempts: int = 0
    
    # Transcript history
    transcript_segments: list[dict] = field(default_factory=list)
    
    # Audio recordings (GridFS file IDs)
    audio_recordings: list[str] = field(default_factory=list)
    
    # Service failure tracking
    stt_failures: int = 0
    tts_failures: int = 0
    claude_failures: int = 0
    vertex_ai_failures: int = 0
    
    # Performance metrics
    total_analysis_time: float = 0.0
    total_interruptions: int = 0
    average_response_latency: float = 0.0
