"""
Question Results Schema for MongoDB

This module defines the schema for the question_results collection in MongoDB.
The schema stores individual question results with evaluation scores and multimodal context.

Requirements: 8.1
"""

from typing import TypedDict, Optional, Literal


# Type definitions for emotion and engagement
EmotionType = Literal["confident", "nervous", "confused", "neutral", "enthusiastic"]


class EvaluationScores(TypedDict):
    """
    Evaluation scores for answer quality assessment.
    
    Fields:
        relevance_score: How relevant the answer is to the question (0-100)
        completeness_score: How complete the answer is (0-100)
        correctness_score: How correct the answer is (0-100)
        feedback: Detailed feedback text from Claude evaluation
    """
    relevance_score: int  # 0-100
    completeness_score: int  # 0-100
    correctness_score: int  # 0-100
    feedback: str


class ContextFields(TypedDict):
    """
    Multimodal context captured during the answer.
    
    Fields:
        emotion: Detected emotion state during answer
        confidence_score: Confidence level during answer (0-100)
        filler_word_count: Number of filler words in answer
        speech_pace: Words per minute during answer
    """
    emotion: EmotionType
    confidence_score: int  # 0-100
    filler_word_count: int
    speech_pace: float  # words per minute


class QuestionResultDocument(TypedDict):
    """
    Complete question result document structure for MongoDB.
    
    This document stores the result of a single question within an interview session,
    including the question text, candidate's answer, evaluation scores, and multimodal
    context (emotion and speech metrics) captured during the answer.
    
    Requirements: 8.1
    
    Fields:
        session_id: Reference to the parent live session
        question_id: Unique identifier for the question
        question_text: The actual question asked
        answer_text: The candidate's complete answer
        evaluation: Evaluation scores and feedback
        context: Multimodal context (emotion, confidence, speech metrics)
        timestamp: ISO timestamp when question was answered
    """
    # Session and question identification
    session_id: str
    question_id: str
    
    # Question and answer content
    question_text: str
    answer_text: str
    
    # Evaluation results
    evaluation: EvaluationScores
    
    # Multimodal context
    context: ContextFields
    
    # Timing
    timestamp: str  # ISO 8601 format


def create_example_question_result() -> QuestionResultDocument:
    """
    Create an example question result document for reference and testing.
    
    Returns:
        QuestionResultDocument: Example document with all required fields
    """
    return QuestionResultDocument(
        # Session and question identification
        session_id="session_abc123",
        question_id="question_1",
        
        # Question and answer content
        question_text="Can you explain the difference between a list and a tuple in Python?",
        answer_text="A list is a mutable data structure in Python, meaning you can modify it after creation. "
                    "A tuple is immutable, so once created, you cannot change its contents. "
                    "Lists use square brackets while tuples use parentheses. "
                    "Tuples are generally faster and use less memory than lists.",
        
        # Evaluation results
        evaluation=EvaluationScores(
            relevance_score=95,
            completeness_score=85,
            correctness_score=90,
            feedback="Excellent answer! You correctly identified the key differences: mutability, "
                    "syntax, and performance characteristics. You could enhance this by mentioning "
                    "use cases where tuples are preferred, such as dictionary keys or function returns."
        ),
        
        # Multimodal context
        context=ContextFields(
            emotion="confident",
            confidence_score=78,
            filler_word_count=2,
            speech_pace=145.5
        ),
        
        # Timing
        timestamp="2024-01-15T10:35:30Z"
    )


# Field descriptions for documentation
FIELD_DESCRIPTIONS = {
    "session_id": "Reference to the parent live_sessions document",
    "question_id": "Unique identifier for the question (e.g., 'question_1', 'question_2')",
    "question_text": "The actual question text asked to the candidate",
    "answer_text": "The candidate's complete answer (transcript)",
    "evaluation.relevance_score": "How relevant the answer is to the question (0-100)",
    "evaluation.completeness_score": "How complete the answer is (0-100)",
    "evaluation.correctness_score": "How correct the answer is (0-100)",
    "evaluation.feedback": "Detailed feedback text from Claude evaluation",
    "context.emotion": "Detected emotion state during answer",
    "context.confidence_score": "Confidence level during answer (0-100)",
    "context.filler_word_count": "Number of filler words in answer",
    "context.speech_pace": "Words per minute during answer",
    "timestamp": "ISO 8601 timestamp when question was answered",
}


# Validation rules
VALIDATION_RULES = {
    "session_id": "Must be non-empty string, references live_sessions.session_id",
    "question_id": "Must be non-empty string, unique within session",
    "question_text": "Must be non-empty string",
    "answer_text": "Must be non-empty string",
    "evaluation.relevance_score": "Must be integer 0-100",
    "evaluation.completeness_score": "Must be integer 0-100",
    "evaluation.correctness_score": "Must be integer 0-100",
    "evaluation.feedback": "Must be non-empty string",
    "context.emotion": "Must be one of: 'confident', 'nervous', 'confused', 'neutral', 'enthusiastic'",
    "context.confidence_score": "Must be integer 0-100",
    "context.filler_word_count": "Must be non-negative integer",
    "context.speech_pace": "Must be non-negative float (words per minute)",
    "timestamp": "Must be valid ISO 8601 timestamp",
}


# Index recommendations
INDEX_RECOMMENDATIONS = {
    "session_id": "Index for fast queries by session",
    "timestamp": "Index for time-based queries",
    "compound": "Compound index on (session_id, timestamp) for session timeline queries",
}
