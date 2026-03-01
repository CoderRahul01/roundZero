"""
Vision Agents Integration - Schema Definitions

This module contains schema definitions for MongoDB collections used in the Vision Agents integration.
"""

from .live_session_schema import (
    LiveSessionDocument,
    TranscriptSegment,
    EmotionSnapshot,
    SpeechMetrics,
    DecisionRecord,
    create_example_live_session,
)

from .question_result_schema import (
    QuestionResultDocument,
    EvaluationScores,
    ContextFields,
    create_example_question_result,
)

__all__ = [
    # Live Session Schema
    "LiveSessionDocument",
    "TranscriptSegment",
    "EmotionSnapshot",
    "SpeechMetrics",
    "DecisionRecord",
    "create_example_live_session",
    
    # Question Result Schema
    "QuestionResultDocument",
    "EvaluationScores",
    "ContextFields",
    "create_example_question_result",
]
