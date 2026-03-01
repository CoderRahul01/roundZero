"""
MongoDB Live Session Repository using Motor (async driver).

This module provides async access to live interview sessions stored in MongoDB.
Handles session metadata, transcripts, emotion timeline, speech metrics, and decisions.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LiveSessionRepository:
    """
    Async repository for managing live interview sessions in MongoDB.
    
    Features:
    - Session lifecycle management (create, update, finalize)
    - Real-time transcript appending
    - Emotion snapshot storage
    - Speech metrics tracking per question
    - Decision record logging
    - Connection pooling for high concurrency
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
        self.live_sessions = self.db["live_sessions"]
        self.question_results = self.db["question_results"]
        
        logger.info(f"Initialized LiveSessionRepository for database: {database_name}")
    
    async def create_session(
        self,
        session_id: str,
        candidate_id: str,
        call_id: str,
        role: str,
        topics: List[str],
        difficulty: str,
        mode: str,
        question_count: int = 5
    ) -> Dict[str, Any]:
        """
        Create a new live session document.
        
        Args:
            session_id: Unique session identifier
            candidate_id: Candidate identifier
            call_id: Stream.io call identifier
            role: Interview role (e.g., "Software Engineer")
            topics: List of interview topics
            difficulty: Question difficulty (easy/medium/hard)
            mode: Interview mode (practice/mock/coaching)
            question_count: Number of questions in session
        
        Returns:
            Created session document
        """
        session_doc = {
            "session_id": session_id,
            "candidate_id": candidate_id,
            "call_id": call_id,
            "role": role,
            "topics": topics,
            "difficulty": difficulty,
            "mode": mode,
            "question_count": question_count,
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": None,
            "transcript": [],
            "emotion_timeline": [],
            "speech_metrics": {},
            "decisions": [],
            "session_summary": None
        }
        
        await self.live_sessions.insert_one(session_doc)
        logger.info(f"Created live session: {session_id}")
        
        return session_doc

    
    async def add_transcript_segment(
        self,
        session_id: str,
        text: str,
        timestamp: float,
        speaker: str = "user",
        is_final: bool = True
    ) -> None:
        """
        Append a transcript segment to the session.
        
        Args:
            session_id: Session identifier
            text: Transcript text
            timestamp: Unix timestamp
            speaker: Speaker identifier (user/agent)
            is_final: Whether this is a final transcript
        """
        segment = {
            "text": text,
            "timestamp": timestamp,
            "speaker": speaker,
            "is_final": is_final
        }
        
        await self.live_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"transcript": segment}}
        )
        
        logger.debug(f"Added transcript segment to session {session_id}")
    
    async def add_emotion_snapshot(
        self,
        session_id: str,
        snapshot: Dict[str, Any]
    ) -> None:
        """
        Append an emotion snapshot to the session timeline.
        
        Args:
            session_id: Session identifier
            snapshot: Emotion snapshot dict with emotion, confidence_score, 
                     engagement_level, body_language_observations, timestamp
        """
        await self.live_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"emotion_timeline": snapshot}}
        )
        
        logger.debug(f"Added emotion snapshot to session {session_id}")
    
    async def add_speech_metrics(
        self,
        session_id: str,
        question_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Store speech metrics for a specific question.
        
        Args:
            session_id: Session identifier
            question_id: Question identifier
            metrics: Speech metrics dict with filler_word_count, speech_pace,
                    long_pause_count, average_filler_rate, rapid_speech, slow_speech
        """
        await self.live_sessions.update_one(
            {"session_id": session_id},
            {"$set": {f"speech_metrics.{question_id}": metrics}}
        )
        
        logger.debug(f"Added speech metrics for question {question_id} in session {session_id}")
    
    async def add_decision_record(
        self,
        session_id: str,
        decision: Dict[str, Any]
    ) -> None:
        """
        Log a decision record to the session.
        
        Args:
            session_id: Session identifier
            decision: Decision dict with timestamp, action, context, message (optional)
        """
        await self.live_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"decisions": decision}}
        )
        
        logger.debug(f"Added decision record to session {session_id}")
    
    async def finalize_session(
        self,
        session_id: str,
        summary: str
    ) -> None:
        """
        Finalize the session by setting ended_at and summary.
        
        Args:
            session_id: Session identifier
            summary: Session summary text
        """
        await self.live_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "ended_at": datetime.utcnow().isoformat(),
                    "session_summary": summary
                }
            }
        )
        
        logger.info(f"Finalized session: {session_id}")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session document or None if not found
        """
        session = await self.live_sessions.find_one({"session_id": session_id})
        
        if session:
            session.pop("_id", None)
            logger.debug(f"Retrieved session: {session_id}")
            return session
        
        logger.warning(f"Session not found: {session_id}")
        return None
    
    async def store_question_result(
        self,
        session_id: str,
        question_id: str,
        question_text: str,
        answer: str,
        evaluation: Dict[str, Any]
    ) -> None:
        """
        Store question result with evaluation.
        
        Args:
            session_id: Session identifier
            question_id: Question identifier
            question_text: Question text
            answer: Candidate's answer
            evaluation: Evaluation dict with relevance_score, completeness_score,
                       correctness_score, feedback
        """
        result_doc = {
            "session_id": session_id,
            "question_id": question_id,
            "question_text": question_text,
            "answer_text": answer,
            "timestamp": datetime.utcnow().isoformat(),
            **evaluation
        }
        
        await self.question_results.insert_one(result_doc)
        logger.info(f"Stored question result for question {question_id} in session {session_id}")
    
    async def get_session_by_candidate(
        self,
        candidate_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions for a candidate.
        
        Args:
            candidate_id: Candidate identifier
            limit: Maximum number of sessions to return
        
        Returns:
            List of session documents
        """
        cursor = self.live_sessions.find(
            {"candidate_id": candidate_id}
        ).sort("started_at", -1).limit(limit)
        
        sessions = []
        async for doc in cursor:
            doc.pop("_id", None)
            sessions.append(doc)
        
        logger.debug(f"Retrieved {len(sessions)} sessions for candidate {candidate_id}")
        return sessions
    
    async def create_indexes(self) -> None:
        """
        Create performance indexes on collections.
        Should be called during application startup.
        """
        logger.info("Creating indexes on live session collections...")
        
        try:
            # Unique index on session_id
            await self.live_sessions.create_index([("session_id", 1)], unique=True)
            
            # Compound index on candidate_id and started_at
            await self.live_sessions.create_index([("candidate_id", 1), ("started_at", -1)])
            
            # Index on started_at for time-based queries
            await self.live_sessions.create_index([("started_at", -1)])
            
            # Compound index on question_results
            await self.question_results.create_index([("session_id", 1), ("timestamp", -1)])
            
            logger.info("Created indexes for live session collections")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    async def close(self) -> None:
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
