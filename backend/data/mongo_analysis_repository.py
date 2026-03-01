"""
MongoDB Analysis Repository for Enhanced Interview Experience.

This module provides async access to multi-modal analysis results stored in MongoDB.
Handles tone, pitch, facial expression analysis, and answer evaluations.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ToneData(BaseModel):
    """Tone analysis data."""
    tone_category: str  # confident, nervous, uncertain, enthusiastic, monotone
    confidence_score: float  # 0.0 to 1.0
    hesitation_count: int
    speech_pace: float  # words per minute


class PitchData(BaseModel):
    """Pitch analysis data."""
    average_pitch_hz: float
    pitch_range: float
    pitch_pattern: str  # rising, falling, stable
    stress_indicators: List[float] = Field(default_factory=list)


class FacialData(BaseModel):
    """Facial expression analysis data."""
    dominant_expression: str  # smile, frown, neutral, surprised, confused
    eye_contact_percentage: float  # 0.0 to 1.0
    head_movements: List[str] = Field(default_factory=list)
    engagement_score: float  # 0.0 to 1.0
    enabled: bool = True


class MultiModalSummary(BaseModel):
    """Combined multi-modal analysis summary."""
    overall_confidence: float  # weighted combination
    consistency_score: float  # cross-modal consistency
    notable_patterns: List[str] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    """Answer evaluation scores and feedback."""
    relevance_score: float  # 0.0 to 1.0
    completeness_score: float  # 0.0 to 1.0
    correctness_score: float  # 0.0 to 1.0
    feedback: str


class AnalysisResult(BaseModel):
    """Complete analysis result for a single question answer."""
    session_id: str
    question_id: str
    question_number: int
    answer_text: str
    
    # Multi-modal analysis data
    tone_data: Optional[ToneData] = None
    pitch_data: Optional[PitchData] = None
    facial_data: Optional[FacialData] = None
    
    # Combined analysis
    multi_modal_summary: Optional[MultiModalSummary] = None
    
    # Answer evaluation
    evaluation: Optional[AnswerEvaluation] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MongoAnalysisRepository:
    """
    Async repository for managing multi-modal analysis results in MongoDB.
    
    Features:
    - Store complete analysis results (tone, pitch, facial, evaluation)
    - Retrieve analysis by session or specific question
    - Support partial results (graceful degradation)
    - Handle missing analyzers without errors
    
    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8
    """
    
    def __init__(self, connection_uri: str, database_name: str = "RoundZero"):
        """
        Initialize Motor client with connection pooling.
        
        Args:
            connection_uri: MongoDB connection string
            database_name: Database name (default: RoundZero)
        """
        self.client = AsyncIOMotorClient(
            connection_uri,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[database_name]
        self.collection = self.db["analysis_results"]
        
        logger.info(f"Initialized MongoAnalysisRepository for database: {database_name}")
    
    async def store_analysis(
        self,
        session_id: str,
        question_id: str,
        question_number: int,
        answer_text: str,
        tone_data: Optional[Dict[str, Any]] = None,
        pitch_data: Optional[Dict[str, Any]] = None,
        facial_data: Optional[Dict[str, Any]] = None,
        multi_modal_summary: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store complete analysis result for a question answer.
        
        Supports partial results - any analyzer can be None if it failed.
        
        Args:
            session_id: Session identifier
            question_id: Question identifier
            question_number: Question number (0-indexed)
            answer_text: Candidate's answer text
            tone_data: Tone analysis results (optional)
            pitch_data: Pitch analysis results (optional)
            facial_data: Facial analysis results (optional)
            multi_modal_summary: Combined analysis summary (optional)
            evaluation: Answer evaluation scores (optional)
        
        Returns:
            MongoDB document ID as string
        
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
        """
        # Create analysis result
        analysis = AnalysisResult(
            session_id=session_id,
            question_id=question_id,
            question_number=question_number,
            answer_text=answer_text,
            tone_data=ToneData(**tone_data) if tone_data else None,
            pitch_data=PitchData(**pitch_data) if pitch_data else None,
            facial_data=FacialData(**facial_data) if facial_data else None,
            multi_modal_summary=MultiModalSummary(**multi_modal_summary) if multi_modal_summary else None,
            evaluation=AnswerEvaluation(**evaluation) if evaluation else None
        )
        
        # Insert into MongoDB
        doc = analysis.model_dump()
        result = await self.collection.insert_one(doc)
        
        logger.info(
            f"Stored analysis for session {session_id}, Q{question_number} "
            f"(tone={tone_data is not None}, pitch={pitch_data is not None}, "
            f"facial={facial_data is not None})"
        )
        
        return str(result.inserted_id)
    
    async def get_analysis(
        self,
        session_id: str,
        sort_by_question: bool = True
    ) -> List[AnalysisResult]:
        """
        Retrieve all analysis results for a session.
        
        Args:
            session_id: Session identifier
            sort_by_question: Sort by question_number (default: True)
        
        Returns:
            List of AnalysisResult objects
        
        Requirements: 15.8, 15.9
        """
        cursor = self.collection.find({"session_id": session_id})
        
        if sort_by_question:
            cursor = cursor.sort("question_number", 1)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(AnalysisResult(**doc))
        
        logger.debug(f"Retrieved {len(results)} analysis results for session {session_id}")
        return results
    
    async def get_question_analysis(
        self,
        session_id: str,
        question_number: int
    ) -> Optional[AnalysisResult]:
        """
        Retrieve analysis result for a specific question.
        
        Args:
            session_id: Session identifier
            question_number: Question number (0-indexed)
        
        Returns:
            AnalysisResult object or None if not found
        
        Requirements: 15.8
        """
        doc = await self.collection.find_one({
            "session_id": session_id,
            "question_number": question_number
        })
        
        if not doc:
            logger.warning(
                f"Analysis not found for session {session_id}, Q{question_number}"
            )
            return None
        
        doc.pop("_id", None)
        return AnalysisResult(**doc)
    
    async def update_evaluation(
        self,
        session_id: str,
        question_number: int,
        evaluation: Dict[str, Any]
    ) -> bool:
        """
        Update the evaluation for an existing analysis result.
        
        Args:
            session_id: Session identifier
            question_number: Question number
            evaluation: Updated evaluation data
        
        Returns:
            True if updated successfully
        
        Raises:
            ValueError: If analysis result doesn't exist
        """
        result = await self.collection.update_one(
            {
                "session_id": session_id,
                "question_number": question_number
            },
            {"$set": {"evaluation": evaluation}}
        )
        
        if result.matched_count == 0:
            raise ValueError(
                f"Analysis not found for session {session_id}, Q{question_number}"
            )
        
        logger.info(f"Updated evaluation for session {session_id}, Q{question_number}")
        return True
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dictionary with average scores and counts
        """
        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": None,
                    "avg_confidence": {"$avg": "$multi_modal_summary.overall_confidence"},
                    "avg_relevance": {"$avg": "$evaluation.relevance_score"},
                    "avg_completeness": {"$avg": "$evaluation.completeness_score"},
                    "avg_correctness": {"$avg": "$evaluation.correctness_score"},
                    "total_questions": {"$sum": 1},
                    "tone_available": {
                        "$sum": {"$cond": [{"$ne": ["$tone_data", None]}, 1, 0]}
                    },
                    "pitch_available": {
                        "$sum": {"$cond": [{"$ne": ["$pitch_data", None]}, 1, 0]}
                    },
                    "facial_available": {
                        "$sum": {"$cond": [{"$ne": ["$facial_data", None]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_questions": 0,
                "avg_confidence": None,
                "avg_relevance": None,
                "avg_completeness": None,
                "avg_correctness": None,
                "tone_available": 0,
                "pitch_available": 0,
                "facial_available": 0
            }
        
        stats = result[0]
        stats.pop("_id", None)
        
        logger.debug(f"Calculated statistics for session {session_id}")
        return stats
    
    async def get_analysis_by_user(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[AnalysisResult]:
        """
        Retrieve all analysis results for a user across all sessions.
        
        Note: This requires joining with transcripts collection to get user_id.
        For now, this is a placeholder that requires session_ids to be provided.
        
        Args:
            user_id: User identifier
            limit: Maximum number of results
        
        Returns:
            List of AnalysisResult objects
        """
        # This would require a join with interview_transcripts
        # For now, return empty list
        logger.warning("get_analysis_by_user requires session_ids - not implemented yet")
        return []
    
    async def delete_analysis(self, session_id: str) -> int:
        """
        Delete all analysis results for a session (for GDPR compliance).
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of documents deleted
        """
        result = await self.collection.delete_many({"session_id": session_id})
        
        logger.info(
            f"Deleted {result.deleted_count} analysis results for session {session_id}"
        )
        return result.deleted_count
    
    async def close(self):
        """Close MongoDB connection and cleanup resources."""
        self.client.close()
        logger.info("Closed MongoDB connection")
    
    async def ping(self) -> bool:
        """
        Ping MongoDB to check connection health.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False
