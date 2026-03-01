"""
Voice Session Repository

Handles persistence of voice interaction sessions to MongoDB.
Ensures all voice data is saved: transcripts, interruptions, analysis results.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class VoiceSessionRepository:
    """
    Repository for voice session data persistence.
    Saves all voice interaction data to MongoDB.
    """
    
    def __init__(self, mongodb_uri: str, database_name: str = "roundzero"):
        """
        Initialize repository with MongoDB connection.
        
        Args:
            mongodb_uri: MongoDB connection string
            database_name: Database name (default: roundzero)
        """
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db: AsyncIOMotorDatabase = self.client[database_name]
        self.sessions = self.db["voice_sessions"]
        self.transcripts = self.db["voice_transcripts"]
        self.interruptions = self.db["voice_interruptions"]
        self.analyses = self.db["voice_analyses"]
        
        logger.info(f"VoiceSessionRepository initialized for database: {database_name}")
    
    async def create_session(
        self,
        session_id: str,
        user_id: str,
        config: Dict[str, Any]
    ) -> str:
        """
        Create a new voice session record.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            config: Session configuration
        
        Returns:
            Session document ID
        """
        document = {
            "session_id": session_id,
            "user_id": user_id,
            "config": config,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "questions_asked": 0,
            "interruptions_count": 0,
            "total_speech_duration_seconds": 0.0,
            "metadata": {}
        }
        
        result = await self.sessions.insert_one(document)
        logger.info(f"Created voice session: {session_id}")
        return str(result.inserted_id)
    
    async def save_transcript(
        self,
        session_id: str,
        question_id: str,
        transcript_segment: str,
        is_final: bool,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Save a transcript segment.
        
        Args:
            session_id: Session identifier
            question_id: Current question identifier
            transcript_segment: Transcribed text
            is_final: Whether this is a final transcript
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Transcript document ID
        """
        document = {
            "session_id": session_id,
            "question_id": question_id,
            "transcript": transcript_segment,
            "is_final": is_final,
            "timestamp": timestamp or datetime.utcnow(),
            "word_count": len(transcript_segment.split())
        }
        
        result = await self.transcripts.insert_one(document)
        logger.debug(f"Saved transcript for session {session_id}: {transcript_segment[:50]}...")
        return str(result.inserted_id)
    
    async def save_interruption(
        self,
        session_id: str,
        question_id: str,
        interruption_message: str,
        reason: str,
        off_topic_content: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Save an interruption event.
        
        Args:
            session_id: Session identifier
            question_id: Current question identifier
            interruption_message: Message sent to user
            reason: Reason for interruption
            off_topic_content: Content that triggered interruption
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Interruption document ID
        """
        document = {
            "session_id": session_id,
            "question_id": question_id,
            "interruption_message": interruption_message,
            "reason": reason,
            "off_topic_content": off_topic_content,
            "timestamp": timestamp or datetime.utcnow()
        }
        
        result = await self.interruptions.insert_one(document)
        
        # Update session interruption count
        await self.sessions.update_one(
            {"session_id": session_id},
            {
                "$inc": {"interruptions_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        logger.info(f"Saved interruption for session {session_id}")
        return str(result.inserted_id)
    
    async def save_analysis_result(
        self,
        session_id: str,
        question_id: str,
        analysis_type: str,
        result: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Save an analysis result.
        
        Args:
            session_id: Session identifier
            question_id: Current question identifier
            analysis_type: Type of analysis (relevance, final_evaluation, etc.)
            result: Analysis result data
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Analysis document ID
        """
        document = {
            "session_id": session_id,
            "question_id": question_id,
            "analysis_type": analysis_type,
            "result": result,
            "timestamp": timestamp or datetime.utcnow()
        }
        
        result_doc = await self.analyses.insert_one(document)
        logger.debug(f"Saved {analysis_type} analysis for session {session_id}")
        return str(result_doc.inserted_id)
    
    async def update_session_status(
        self,
        session_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New status (active, completed, error, etc.)
            metadata: Optional metadata to merge
        
        Returns:
            True if updated successfully
        """
        update_doc = {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        }
        
        if metadata:
            update_doc["$set"]["metadata"] = metadata
        
        result = await self.sessions.update_one(
            {"session_id": session_id},
            update_doc
        )
        
        logger.info(f"Updated session {session_id} status to: {status}")
        return result.modified_count > 0
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session document or None
        """
        return await self.sessions.find_one({"session_id": session_id})
    
    async def get_session_transcripts(
        self,
        session_id: str,
        question_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transcripts for a session or question.
        
        Args:
            session_id: Session identifier
            question_id: Optional question identifier to filter
        
        Returns:
            List of transcript documents
        """
        query = {"session_id": session_id}
        if question_id:
            query["question_id"] = question_id
        
        cursor = self.transcripts.find(query).sort("timestamp", 1)
        return await cursor.to_list(length=None)
    
    async def get_session_interruptions(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all interruptions for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of interruption documents
        """
        cursor = self.interruptions.find({"session_id": session_id}).sort("timestamp", 1)
        return await cursor.to_list(length=None)
    
    async def get_session_analyses(
        self,
        session_id: str,
        analysis_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all analyses for a session.
        
        Args:
            session_id: Session identifier
            analysis_type: Optional type filter
        
        Returns:
            List of analysis documents
        """
        query = {"session_id": session_id}
        if analysis_type:
            query["analysis_type"] = analysis_type
        
        cursor = self.analyses.find(query).sort("timestamp", 1)
        return await cursor.to_list(length=None)
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete session summary with all data.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Complete session summary
        """
        session = await self.get_session(session_id)
        if not session:
            return {}
        
        transcripts = await self.get_session_transcripts(session_id)
        interruptions = await self.get_session_interruptions(session_id)
        analyses = await self.get_session_analyses(session_id)
        
        return {
            "session": session,
            "transcripts": transcripts,
            "interruptions": interruptions,
            "analyses": analyses,
            "stats": {
                "total_transcripts": len(transcripts),
                "total_interruptions": len(interruptions),
                "total_analyses": len(analyses),
                "final_transcripts": len([t for t in transcripts if t.get("is_final")])
            }
        }
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()
        logger.info("VoiceSessionRepository connection closed")


def get_voice_session_repository(mongodb_uri: str) -> VoiceSessionRepository:
    """
    Get voice session repository instance.
    
    Args:
        mongodb_uri: MongoDB connection string
    
    Returns:
        VoiceSessionRepository instance
    """
    return VoiceSessionRepository(mongodb_uri)
