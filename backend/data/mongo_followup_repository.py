"""
MongoDB Follow-Up Repository for Enhanced Interview Experience.

This module provides async access to follow-up questions and their reasoning stored in MongoDB.
Handles contextual follow-up questions generated during interviews.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FollowUpEvaluation(BaseModel):
    """Evaluation of follow-up answer."""
    relevance_score: float  # 0.0 to 1.0
    completeness_score: float  # 0.0 to 1.0
    feedback: str


class FollowUpQuestion(BaseModel):
    """Follow-up question with reasoning and answer."""
    session_id: str
    main_question_id: str
    main_question_number: int
    follow_up_text: str
    reasoning: str
    answer_text: Optional[str] = None
    evaluation: Optional[FollowUpEvaluation] = None
    effectiveness: Optional[bool] = None  # Did the follow-up provide useful information?
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MongoFollowUpRepository:
    """
    Async repository for managing follow-up questions in MongoDB.
    
    Features:
    - Store follow-up questions with reasoning
    - Update follow-up answers
    - Track follow-up effectiveness
    - Retrieve follow-ups by session or main question
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10
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
        self.collection = self.db["follow_up_questions"]
        
        logger.info(f"Initialized MongoFollowUpRepository for database: {database_name}")
    
    async def store_followup(
        self,
        session_id: str,
        main_question_id: str,
        main_question_number: int,
        follow_up_text: str,
        reasoning: str
    ) -> str:
        """
        Store a follow-up question with its reasoning.
        
        Args:
            session_id: Session identifier
            main_question_id: ID of the main question this follows up on
            main_question_number: Number of the main question (0-indexed)
            follow_up_text: The follow-up question text
            reasoning: Explanation of why this follow-up was asked
        
        Returns:
            MongoDB document ID as string
        
        Requirements: 9.1, 9.2, 9.3, 9.4, 16.1, 16.2, 16.3, 16.5, 16.6
        """
        # Create follow-up question
        followup = FollowUpQuestion(
            session_id=session_id,
            main_question_id=main_question_id,
            main_question_number=main_question_number,
            follow_up_text=follow_up_text,
            reasoning=reasoning
        )
        
        # Insert into MongoDB
        doc = followup.model_dump()
        result = await self.collection.insert_one(doc)
        
        logger.info(
            f"Stored follow-up for session {session_id}, "
            f"main Q{main_question_number}: {follow_up_text[:50]}..."
        )
        
        return str(result.inserted_id)
    
    async def update_followup_answer(
        self,
        session_id: str,
        main_question_number: int,
        answer_text: str,
        evaluation: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the answer for a follow-up question.
        
        Updates the most recent follow-up for the given main question.
        
        Args:
            session_id: Session identifier
            main_question_number: Main question number
            answer_text: Candidate's answer to the follow-up
            evaluation: Optional evaluation of the answer
        
        Returns:
            True if updated successfully
        
        Raises:
            ValueError: If follow-up doesn't exist
        
        Requirements: 9.5, 9.6, 9.7, 9.8
        """
        # Find the most recent follow-up for this main question
        update_data = {
            "answer_text": answer_text
        }
        
        if evaluation:
            update_data["evaluation"] = evaluation
        
        result = await self.collection.update_one(
            {
                "session_id": session_id,
                "main_question_number": main_question_number,
                "answer_text": None  # Only update if not already answered
            },
            {"$set": update_data},
            sort=[("timestamp", -1)]  # Get most recent
        )
        
        if result.matched_count == 0:
            raise ValueError(
                f"No unanswered follow-up found for session {session_id}, "
                f"main Q{main_question_number}"
            )
        
        logger.info(
            f"Updated follow-up answer for session {session_id}, "
            f"main Q{main_question_number}"
        )
        return True
    
    async def update_effectiveness(
        self,
        session_id: str,
        main_question_number: int,
        effectiveness: bool
    ) -> bool:
        """
        Update the effectiveness tracking for a follow-up.
        
        Args:
            session_id: Session identifier
            main_question_number: Main question number
            effectiveness: Whether the follow-up provided useful information
        
        Returns:
            True if updated successfully
        
        Requirements: 9.9, 16.8, 16.9
        """
        result = await self.collection.update_one(
            {
                "session_id": session_id,
                "main_question_number": main_question_number
            },
            {"$set": {"effectiveness": effectiveness}},
            sort=[("timestamp", -1)]
        )
        
        if result.matched_count == 0:
            logger.warning(
                f"No follow-up found to update effectiveness for session {session_id}, "
                f"main Q{main_question_number}"
            )
            return False
        
        logger.info(
            f"Updated follow-up effectiveness for session {session_id}, "
            f"main Q{main_question_number}: {effectiveness}"
        )
        return True
    
    async def get_followups(
        self,
        session_id: str,
        main_question_number: Optional[int] = None
    ) -> List[FollowUpQuestion]:
        """
        Retrieve follow-up questions for a session.
        
        Args:
            session_id: Session identifier
            main_question_number: Optional filter by main question number
        
        Returns:
            List of FollowUpQuestion objects, sorted by timestamp
        
        Requirements: 9.9, 9.10, 16.7
        """
        query = {"session_id": session_id}
        if main_question_number is not None:
            query["main_question_number"] = main_question_number
        
        cursor = self.collection.find(query).sort("timestamp", 1)
        
        followups = []
        async for doc in cursor:
            doc.pop("_id", None)
            followups.append(FollowUpQuestion(**doc))
        
        logger.debug(
            f"Retrieved {len(followups)} follow-ups for session {session_id}"
            + (f", main Q{main_question_number}" if main_question_number is not None else "")
        )
        return followups
    
    async def get_followup_count(
        self,
        session_id: str,
        main_question_number: int
    ) -> int:
        """
        Get the number of follow-ups asked for a main question.
        
        Args:
            session_id: Session identifier
            main_question_number: Main question number
        
        Returns:
            Number of follow-ups
        """
        count = await self.collection.count_documents({
            "session_id": session_id,
            "main_question_number": main_question_number
        })
        
        return count
    
    async def get_unanswered_followup(
        self,
        session_id: str,
        main_question_number: int
    ) -> Optional[FollowUpQuestion]:
        """
        Get the most recent unanswered follow-up for a main question.
        
        Args:
            session_id: Session identifier
            main_question_number: Main question number
        
        Returns:
            FollowUpQuestion object or None if all are answered
        """
        doc = await self.collection.find_one(
            {
                "session_id": session_id,
                "main_question_number": main_question_number,
                "answer_text": None
            },
            sort=[("timestamp", -1)]
        )
        
        if not doc:
            return None
        
        doc.pop("_id", None)
        return FollowUpQuestion(**doc)
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate follow-up statistics for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dictionary with follow-up counts and effectiveness metrics
        """
        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": None,
                    "total_followups": {"$sum": 1},
                    "answered_followups": {
                        "$sum": {"$cond": [{"$ne": ["$answer_text", None]}, 1, 0]}
                    },
                    "effective_followups": {
                        "$sum": {"$cond": [{"$eq": ["$effectiveness", True]}, 1, 0]}
                    },
                    "avg_relevance": {"$avg": "$evaluation.relevance_score"},
                    "avg_completeness": {"$avg": "$evaluation.completeness_score"}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_followups": 0,
                "answered_followups": 0,
                "effective_followups": 0,
                "avg_relevance": None,
                "avg_completeness": None,
                "effectiveness_rate": 0.0
            }
        
        stats = result[0]
        stats.pop("_id", None)
        
        # Calculate effectiveness rate
        if stats["answered_followups"] > 0:
            stats["effectiveness_rate"] = (
                stats["effective_followups"] / stats["answered_followups"]
            )
        else:
            stats["effectiveness_rate"] = 0.0
        
        logger.debug(f"Calculated follow-up statistics for session {session_id}")
        return stats
    
    async def get_reasoning_patterns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Analyze reasoning patterns across follow-ups for improvement.
        
        Args:
            limit: Maximum number of follow-ups to analyze
        
        Returns:
            List of follow-ups with reasoning and effectiveness
        
        Requirements: 16.10
        """
        cursor = self.collection.find(
            {"effectiveness": {"$ne": None}},
            {"reasoning": 1, "effectiveness": 1, "follow_up_text": 1}
        ).limit(limit)
        
        patterns = []
        async for doc in cursor:
            patterns.append({
                "reasoning": doc.get("reasoning"),
                "effectiveness": doc.get("effectiveness"),
                "follow_up_text": doc.get("follow_up_text")
            })
        
        logger.debug(f"Retrieved {len(patterns)} reasoning patterns")
        return patterns
    
    async def delete_followups(self, session_id: str) -> int:
        """
        Delete all follow-ups for a session (for GDPR compliance).
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of documents deleted
        """
        result = await self.collection.delete_many({"session_id": session_id})
        
        logger.info(
            f"Deleted {result.deleted_count} follow-ups for session {session_id}"
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
