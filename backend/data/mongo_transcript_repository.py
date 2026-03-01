"""
MongoDB Transcript Repository for Enhanced Interview Experience.

This module provides async access to interview transcripts stored in MongoDB.
Handles complete interview transcripts with all interactions (questions, answers, follow-ups).
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TranscriptEntry(BaseModel):
    """Single entry in an interview transcript."""
    speaker: str  # "AI" or "Candidate"
    text: str
    timestamp: float
    question_number: int
    is_followup: bool = False


class InterviewTranscript(BaseModel):
    """Complete interview transcript with all interactions."""
    session_id: str
    user_id: str
    entries: List[TranscriptEntry] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MongoTranscriptRepository:
    """
    Async repository for managing interview transcripts in MongoDB.
    
    Features:
    - Create new transcript records for interview sessions
    - Append entries (questions, answers, follow-ups) to transcripts
    - Retrieve complete transcripts with chronological ordering
    - Update completion timestamps
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.7
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
        self.collection = self.db["interview_transcripts"]
        
        logger.info(f"Initialized MongoTranscriptRepository for database: {database_name}")
    
    async def create_transcript(
        self,
        session_id: str,
        user_id: str,
        started_at: Optional[datetime] = None
    ) -> InterviewTranscript:
        """
        Create a new interview transcript record.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            started_at: Interview start time (defaults to now)
        
        Returns:
            Created InterviewTranscript object
        
        Raises:
            ValueError: If transcript with session_id already exists
        
        Requirements: 14.1
        """
        # Check if transcript already exists
        existing = await self.collection.find_one({"session_id": session_id})
        if existing:
            raise ValueError(f"Transcript for session {session_id} already exists")
        
        # Create transcript document
        transcript = InterviewTranscript(
            session_id=session_id,
            user_id=user_id,
            started_at=started_at or datetime.utcnow(),
            entries=[]
        )
        
        # Insert into MongoDB
        doc = transcript.model_dump()
        await self.collection.insert_one(doc)
        
        logger.info(f"Created transcript for session: {session_id}")
        return transcript
    
    async def add_entry(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp: float,
        question_number: int,
        is_followup: bool = False
    ) -> bool:
        """
        Append an entry to an existing transcript.
        
        Args:
            session_id: Session identifier
            speaker: "AI" or "Candidate"
            text: Spoken text
            timestamp: Unix timestamp
            question_number: Question number (0-indexed)
            is_followup: Whether this is a follow-up question/answer
        
        Returns:
            True if entry was added successfully
        
        Raises:
            ValueError: If transcript doesn't exist
        
        Requirements: 14.2, 14.3, 14.4, 14.6
        """
        # Validate speaker
        if speaker not in ["AI", "Candidate"]:
            raise ValueError(f"Invalid speaker: {speaker}. Must be 'AI' or 'Candidate'")
        
        # Create entry
        entry = TranscriptEntry(
            speaker=speaker,
            text=text,
            timestamp=timestamp,
            question_number=question_number,
            is_followup=is_followup
        )
        
        # Append to transcript
        result = await self.collection.update_one(
            {"session_id": session_id},
            {"$push": {"entries": entry.model_dump()}}
        )
        
        if result.matched_count == 0:
            raise ValueError(f"Transcript for session {session_id} not found")
        
        logger.debug(
            f"Added {speaker} entry to session {session_id} "
            f"(Q{question_number}, followup={is_followup})"
        )
        return True
    
    async def get_transcript(self, session_id: str) -> Optional[InterviewTranscript]:
        """
        Retrieve complete transcript for a session.
        
        Entries are returned in chronological order (sorted by timestamp).
        
        Args:
            session_id: Session identifier
        
        Returns:
            InterviewTranscript object or None if not found
        
        Requirements: 14.7, 14.10
        """
        doc = await self.collection.find_one({"session_id": session_id})
        
        if not doc:
            logger.warning(f"Transcript not found for session: {session_id}")
            return None
        
        # Remove MongoDB _id field
        doc.pop("_id", None)
        
        # Parse into Pydantic model
        transcript = InterviewTranscript(**doc)
        
        # Ensure entries are sorted by timestamp (chronological order)
        transcript.entries.sort(key=lambda e: e.timestamp)
        
        logger.debug(
            f"Retrieved transcript for session {session_id} "
            f"({len(transcript.entries)} entries)"
        )
        return transcript
    
    async def get_transcripts_by_user(
        self,
        user_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[InterviewTranscript]:
        """
        Retrieve all transcripts for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of transcripts to return
            skip: Number of transcripts to skip (pagination)
        
        Returns:
            List of InterviewTranscript objects, sorted by started_at (newest first)
        
        Requirements: 14.10
        """
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("started_at", -1).limit(limit).skip(skip)
        
        transcripts = []
        async for doc in cursor:
            doc.pop("_id", None)
            transcript = InterviewTranscript(**doc)
            # Ensure entries are sorted
            transcript.entries.sort(key=lambda e: e.timestamp)
            transcripts.append(transcript)
        
        logger.debug(f"Retrieved {len(transcripts)} transcripts for user {user_id}")
        return transcripts
    
    async def update_completion_time(
        self,
        session_id: str,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """
        Update the completion timestamp for a transcript.
        
        Args:
            session_id: Session identifier
            completed_at: Completion time (defaults to now)
        
        Returns:
            True if updated successfully
        
        Raises:
            ValueError: If transcript doesn't exist
        """
        result = await self.collection.update_one(
            {"session_id": session_id},
            {"$set": {"completed_at": completed_at or datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise ValueError(f"Transcript for session {session_id} not found")
        
        logger.info(f"Updated completion time for session: {session_id}")
        return True
    
    async def add_interruption_entry(
        self,
        session_id: str,
        interruption_type: str,
        timestamp: float,
        question_number: int
    ) -> bool:
        """
        Add an interruption or presence check entry to the transcript.
        
        This provides complete context for the interview flow.
        
        Args:
            session_id: Session identifier
            interruption_type: Type of interruption (e.g., "presence_check", "off_topic")
            timestamp: Unix timestamp
            question_number: Current question number
        
        Returns:
            True if entry was added successfully
        
        Requirements: 14.8
        """
        return await self.add_entry(
            session_id=session_id,
            speaker="AI",
            text=f"[{interruption_type}]",
            timestamp=timestamp,
            question_number=question_number,
            is_followup=False
        )
    
    async def get_entry_count(self, session_id: str) -> int:
        """
        Get the number of entries in a transcript.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of entries, or 0 if transcript doesn't exist
        """
        doc = await self.collection.find_one(
            {"session_id": session_id},
            {"entries": 1}
        )
        
        if not doc:
            return 0
        
        return len(doc.get("entries", []))
    
    async def delete_transcript(self, session_id: str) -> bool:
        """
        Delete a transcript (for GDPR compliance).
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if deleted successfully
        """
        result = await self.collection.delete_one({"session_id": session_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted transcript for session: {session_id}")
            return True
        
        logger.warning(f"Transcript not found for deletion: {session_id}")
        return False
    
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
