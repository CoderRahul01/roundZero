"""
MongoDB Question Repository using Motor (async driver).

This module provides async access to interview questions stored in MongoDB Atlas.
Uses connection pooling for high performance and scalability.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field
from typing import AsyncIterator, Optional
import logging

logger = logging.getLogger(__name__)


class Question(BaseModel):
    """Pydantic model for question validation."""
    id: str
    question: str
    ideal_answer: str = ""
    category: str = "General"
    difficulty: str = "medium"
    source: str = "MongoDB"
    topics: list[str] = Field(default_factory=list)


class MongoQuestionRepository:
    """
    Async repository for accessing interview questions from MongoDB.
    
    Features:
    - Connection pooling for high concurrency
    - GridFS for audio storage with streaming
    - Async operations for non-blocking I/O
    - Comprehensive indexing for fast queries
    """
    
    def __init__(self, connection_uri: str, database_name: str = "RoundZero"):
        """
        Initialize Motor client with connection pooling.
        
        Args:
            connection_uri: MongoDB connection string
            database_name: Database name (default: RoundZero)
        
        Connection Pool Configuration:
        - maxPoolSize: 50 (handles high concurrency)
        - minPoolSize: 10 (maintains warm connections)
        - serverSelectionTimeoutMS: 5000 (fail fast on connection issues)
        """
        self.client = AsyncIOMotorClient(
            connection_uri,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[database_name]
        self.software_questions = self.db["software_questions"]
        self.hr_questions = self.db["hr_questions"]
        self.leetcode_questions = self.db["leetcode_questions"]
        self.gridfs = AsyncIOMotorGridFSBucket(self.db)
        
        logger.info(f"Initialized MongoQuestionRepository for database: {database_name}")
    
    async def get_by_id(self, question_id: str, category: str = "software") -> Optional[Question]:
        """
        Get a single question by ID.
        
        Args:
            question_id: Unique question identifier
            category: Question category (software, hr, leetcode)
        
        Returns:
            Question object or None if not found
        """
        collection = self._get_collection_by_category(category)
        doc = await collection.find_one({"id": question_id})
        
        if doc:
            # Remove MongoDB _id field
            doc.pop("_id", None)
            return Question(**doc)
        return None
    
    async def get_all(
        self, 
        category: str = "software",
        limit: int = 100,
        skip: int = 0
    ) -> list[Question]:
        """
        Get all questions from a category with pagination.
        
        Args:
            category: Question category (software, hr, leetcode)
            limit: Maximum number of questions to return
            skip: Number of questions to skip (for pagination)
        
        Returns:
            List of Question objects
        """
        collection = self._get_collection_by_category(category)
        cursor = collection.find({}, limit=limit, skip=skip)
        
        questions = []
        async for doc in cursor:
            doc.pop("_id", None)
            questions.append(Question(**doc))
        
        logger.debug(f"Retrieved {len(questions)} questions from {category} category")
        return questions
    
    async def get_questions_by_category(
        self, 
        category: str, 
        difficulty: str, 
        limit: int = 10,
        skip: int = 0
    ) -> list[Question]:
        """
        Async fetch questions with pagination.
        Uses indexes on category and difficulty for fast queries.
        
        Args:
            category: Question category (software, hr, leetcode)
            difficulty: Question difficulty (easy, medium, hard)
            limit: Maximum number of questions to return
            skip: Number of questions to skip (for pagination)
        
        Returns:
            List of Question objects matching criteria
        """
        collection = self._get_collection_by_category(category)
        cursor = collection.find(
            {"difficulty": difficulty},
            limit=limit,
            skip=skip
        )
        
        questions = []
        async for doc in cursor:
            doc.pop("_id", None)
            questions.append(Question(**doc))
        
        logger.debug(
            f"Retrieved {len(questions)} {difficulty} questions from {category} category"
        )
        return questions
    
    async def get_questions_by_topics(
        self, 
        topics: list[str], 
        difficulty: str, 
        limit: int = 10,
        skip: int = 0
    ) -> list[Question]:
        """
        Async fetch questions matching topics.
        Uses compound index on topics and difficulty.
        
        Args:
            topics: List of topic strings to match
            difficulty: Question difficulty (easy, medium, hard)
            limit: Maximum number of questions to return
            skip: Number of questions to skip (for pagination)
        
        Returns:
            List of Question objects matching criteria
        """
        # Search across all collections
        pipeline = [
            {"$match": {"topics": {"$in": topics}, "difficulty": difficulty}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        questions = []
        
        # Search in all collections
        for collection in [self.software_questions, self.hr_questions, self.leetcode_questions]:
            async for doc in collection.aggregate(pipeline):
                doc.pop("_id", None)
                questions.append(Question(**doc))
        
        logger.debug(
            f"Retrieved {len(questions)} questions matching topics {topics} with difficulty {difficulty}"
        )
        return questions[:limit]  # Ensure we don't exceed limit
    
    async def search_questions(
        self, 
        query: str, 
        source: Optional[str] = None,
        limit: int = 10
    ) -> list[Question]:
        """
        Full-text search across question collections.
        Uses text index on question field.
        
        Args:
            query: Search query string
            source: Optional source filter (e.g., "Software Questions CSV")
            limit: Maximum number of questions to return
        
        Returns:
            List of Question objects matching search query, sorted by relevance
        """
        search_filter = {"$text": {"$search": query}}
        if source:
            search_filter["source"] = source
        
        questions = []
        
        # Search across all collections
        for collection in [self.software_questions, self.hr_questions, self.leetcode_questions]:
            cursor = collection.find(
                search_filter,
                {"score": {"$meta": "textScore"}},
                limit=limit
            ).sort([("score", {"$meta": "textScore"})])
            
            async for doc in cursor:
                doc.pop("_id", None)
                doc.pop("score", None)  # Remove score field
                questions.append(Question(**doc))
        
        # Sort by relevance and limit
        logger.debug(f"Found {len(questions)} questions matching query: {query}")
        return questions[:limit]

    
    async def store_audio_recording(
        self,
        audio_data: bytes,
        filename: str,
        metadata: dict
    ) -> str:
        """
        Store audio in GridFS with metadata.
        Returns file_id for retrieval.
        
        Args:
            audio_data: Audio file bytes
            filename: Name for the audio file
            metadata: Dictionary with session_id, question_index, duration, timestamp
        
        Returns:
            String file_id for retrieval
        """
        file_id = await self.gridfs.upload_from_stream(
            filename,
            audio_data,
            metadata=metadata
        )
        
        logger.info(f"Stored audio recording: {filename} with file_id: {file_id}")
        return str(file_id)
    
    async def get_audio_recording(self, file_id: str) -> bytes:
        """
        Retrieve audio from GridFS.
        
        Args:
            file_id: GridFS file identifier
        
        Returns:
            Audio file bytes
        """
        try:
            grid_out = await self.gridfs.open_download_stream(file_id)
            audio_data = await grid_out.read()
            logger.debug(f"Retrieved audio recording: {file_id}")
            return audio_data
        except Exception as e:
            logger.error(f"Failed to retrieve audio recording {file_id}: {e}")
            raise
    
    async def stream_audio_recording(self, file_id: str) -> AsyncIterator[bytes]:
        """
        Stream audio from GridFS in chunks.
        Useful for large audio files to reduce memory usage.
        
        Args:
            file_id: GridFS file identifier
        
        Yields:
            Audio data chunks
        """
        try:
            grid_out = await self.gridfs.open_download_stream(file_id)
            while True:
                chunk = await grid_out.readchunk()
                if not chunk:
                    break
                yield chunk
            logger.debug(f"Streamed audio recording: {file_id}")
        except Exception as e:
            logger.error(f"Failed to stream audio recording {file_id}: {e}")
            raise
    
    async def delete_audio_recording(self, file_id: str) -> None:
        """
        Delete audio recording from GridFS.
        
        Args:
            file_id: GridFS file identifier
        """
        try:
            await self.gridfs.delete(file_id)
            logger.info(f"Deleted audio recording: {file_id}")
        except Exception as e:
            logger.error(f"Failed to delete audio recording {file_id}: {e}")
            raise
    
    async def create_indexes(self):
        """
        Create performance indexes on collections.
        Should be called during application startup.
        
        Creates:
        - Text indexes for full-text search
        - Compound indexes for common queries
        - Indexes on topics array
        - Unique indexes on id field
        """
        logger.info("Creating indexes on MongoDB collections...")
        
        collections = [
            ("software_questions", self.software_questions),
            ("hr_questions", self.hr_questions),
            ("leetcode_questions", self.leetcode_questions)
        ]
        
        for name, collection in collections:
            try:
                # Text index for full-text search
                await collection.create_index([("question", "text")])
                
                # Compound indexes for common queries
                await collection.create_index([("category", 1), ("difficulty", 1)])
                
                # Index on topics array
                await collection.create_index([("topics", 1)])
                
                # Unique index on id field
                await collection.create_index([("id", 1)], unique=True)
                
                logger.info(f"Created indexes for {name} collection")
            except Exception as e:
                logger.warning(f"Index creation warning for {name}: {e}")
    
    def _get_collection_by_category(self, category: str):
        """
        Helper to route to correct collection based on category.
        
        Args:
            category: Question category (software, hr, leetcode)
        
        Returns:
            Motor collection object
        """
        category_map = {
            "software": self.software_questions,
            "hr": self.hr_questions,
            "leetcode": self.leetcode_questions
        }
        return category_map.get(category.lower(), self.software_questions)
    
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
