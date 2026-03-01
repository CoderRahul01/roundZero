# Design Document: Voice AI Interview System

## Overview

The Voice AI Interview System extends RoundZero's existing interview platform with two major capabilities: (1) MongoDB-based question storage for team-wide accessibility and deployment readiness, and (2) real-time voice-enabled interviews with AI-powered question delivery, speech recognition, and intelligent answer evaluation.

This design leverages the existing FastAPI backend architecture, Vision Agents framework, and integrates with MongoDB Atlas for persistent storage. The system maintains the current interview flow while adding voice interaction capabilities through Deepgram (STT), ElevenLabs (TTS), and enhanced AI decision-making through Anthropic Claude.

### Key Design Principles

1. **Backward Compatibility**: Existing interview functionality remains unchanged; voice features are additive
2. **Graceful Degradation**: System falls back to text-only mode if voice services fail
3. **Separation of Concerns**: Dataset migration is independent of voice interview features
4. **Minimal Latency**: Preloading and caching strategies to maintain <2s response times
5. **Security First**: All API keys in environment variables, no client-side exposure

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Interview UI │  │ Voice Controls│  │ Transcript   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend (FastAPI - Async)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         InterviewerService (Async)                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ Question   │  │ Decision   │  │ Speech     │    │   │
│  │  │ Bank       │  │ Engine     │  │ Analyzer   │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Data Access Layer (Async)                         │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ Motor      │  │ asyncpg    │  │ Redis      │    │   │
│  │  │ (MongoDB)  │  │ (NeonDB)   │  │ (Cache)    │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   MongoDB    │   │   NeonDB     │   │   Upstash    │
│   (Motor)    │   │  (Postgres)  │   │   Redis      │
│              │   │              │   │              │
│ - Questions  │   │ - Users      │   │ - Cache      │
│ - GridFS     │   │ - Sessions   │   │ - Rate Limit │
│   Audio      │   │ - Results    │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Pinecone    │   │ Supermemory  │   │  Deepgram    │
│  (Vectors)   │   │  (Memory)    │   │  (STT)       │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐   ┌──────────────┐
│  Anthropic   │   │ ElevenLabs   │
│  Claude      │   │  (TTS)       │
└──────────────┘   └──────────────┘
```

### Technology Stack Rationale

**MongoDB with Motor (Async Driver)**
- Stores interview question datasets (Software, HR, LeetCode)
- GridFS for audio recording storage with streaming support
- Flexible schema for different question types
- Horizontal scaling capability for growing datasets
- Connection pooling (min: 10, max: 50) for high concurrency

**NeonDB (Postgres) for Transactional Data**
- Stores user accounts and authentication
- Stores interview sessions metadata
- Stores question results and scores
- ACID compliance for critical user data
- Strong consistency for relational integrity
- Connection pooling (min: 5, max: 20) via asyncpg

**Data Distribution Strategy**
- **MongoDB**: Questions (flexible schema, fast reads, horizontal scaling)
- **NeonDB**: Sessions, users, results (ACID compliance, relational integrity)
- **Pinecone**: Question embeddings (vector similarity search)
- **Supermemory**: User learning patterns (AI-powered personalization)
- **MongoDB GridFS**: Audio recordings (integrated storage, streaming support)
- **Upstash Redis**: Caching and rate limiting (low latency, serverless)

**Async Operations Throughout**
- Motor for async MongoDB queries
- asyncpg for async Postgres queries
- Async STT/TTS service calls
- asyncio for concurrent operations
- Non-blocking I/O for maximum throughput

### Component Interaction Flow

**Dataset Migration Flow (Async):**
```
1. Migration Script → Read CSV/JSON files
2. Migration Script → Parse and normalize data with Pydantic validation
3. Migration Script → Connect to MongoDB with Motor (connection pooling)
4. Migration Script → Concurrent bulk insert with upsert operations
5. Migration Script → Create indexes for performance (async)
6. Migration Script → Verify data accessibility (async queries)
```

**Voice Interview Flow (Async):**
```
1. User clicks "Start Interview"
2. Frontend requests camera/mic permissions
3. Backend → Check rate limit (Redis cache)
4. Backend → Create Interview_Session in NeonDB (asyncpg)
5. Backend → Fetch questions from MongoDB (Motor) or Redis cache
6. Backend → Preload next question (async background task)
7. AI generates greeting → Check TTS cache → ElevenLabs TTS → Audio playback
8. AI asks first question → Check TTS cache → ElevenLabs TTS → Audio playback
9. User speaks → Deepgram STT (async stream) → Text transcript
10. Frontend displays real-time transcript
11. User clicks "Submit Answer"
12. Backend → Check evaluation cache (Redis)
13. Backend → Anthropic Claude evaluates answer (async)
14. Backend → Gemini generates embeddings (async, concurrent with Claude)
15. Backend → Store result in NeonDB (async)
16. Backend → Store audio in MongoDB GridFS (async)
17. AI decides: CONTINUE, NEXT, HINT, or ENCOURAGE
18. If NEXT: Fetch next question (from preload cache), repeat from step 7
19. If CONTINUE/HINT/ENCOURAGE: Provide feedback, continue listening
20. On completion: Generate report, store in NeonDB, cleanup resources
```

**Async Performance Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Concurrent Operations                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User Answer Submission                                      │
│         │                                                     │
│         ├──→ [Async] Claude Evaluation                       │
│         │                                                     │
│         ├──→ [Async] Gemini Embeddings                       │
│         │                                                     │
│         ├──→ [Async] Store to NeonDB                         │
│         │                                                     │
│         ├──→ [Async] Store Audio to GridFS                   │
│         │                                                     │
│         └──→ [Async] Preload Next Question                   │
│                                                               │
│  All operations complete → Return response to user           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MongoDB Data Access Layer (Motor - Async)

**Purpose**: Provide async abstraction layer for accessing interview questions from MongoDB with connection pooling and GridFS audio storage.

**Class: MongoQuestionRepository**

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field
from typing import AsyncIterator

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
    """Async repository for accessing interview questions from MongoDB."""
    
    def __init__(self, connection_uri: str, database_name: str = "RoundZero"):
        """
        Initialize Motor client with connection pooling.
        
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
        """
        collection = self._get_collection_by_category(category)
        cursor = collection.find(
            {"difficulty": difficulty},
            limit=limit,
            skip=skip
        )
        questions = []
        async for doc in cursor:
            questions.append(Question(**doc))
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
        """
        pipeline = [
            {"$match": {"topics": {"$in": topics}, "difficulty": difficulty}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        questions = []
        async for doc in self.software_questions.aggregate(pipeline):
            questions.append(Question(**doc))
        return questions
    
    async def search_questions(
        self, 
        query: str, 
        source: str | None = None,
        limit: int = 10
    ) -> list[Question]:
        """
        Full-text search across question collections.
        Uses text index on question field.
        """
        search_filter = {"$text": {"$search": query}}
        if source:
            search_filter["source"] = source
        
        cursor = self.software_questions.find(
            search_filter,
            {"score": {"$meta": "textScore"}},
            limit=limit
        ).sort([("score", {"$meta": "textScore"})])
        
        questions = []
        async for doc in cursor:
            questions.append(Question(**doc))
        return questions
    
    async def store_audio_recording(
        self,
        audio_data: bytes,
        filename: str,
        metadata: dict
    ) -> str:
        """
        Store audio in GridFS with metadata.
        Returns file_id for retrieval.
        
        Metadata includes: session_id, question_index, duration, timestamp
        """
        file_id = await self.gridfs.upload_from_stream(
            filename,
            audio_data,
            metadata=metadata
        )
        return str(file_id)
    
    async def get_audio_recording(self, file_id: str) -> bytes:
        """
        Retrieve audio from GridFS.
        Supports streaming for large files.
        """
        grid_out = await self.gridfs.open_download_stream(file_id)
        audio_data = await grid_out.read()
        return audio_data
    
    async def stream_audio_recording(self, file_id: str) -> AsyncIterator[bytes]:
        """
        Stream audio from GridFS in chunks.
        Useful for large audio files to reduce memory usage.
        """
        grid_out = await self.gridfs.open_download_stream(file_id)
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk
    
    async def delete_audio_recording(self, file_id: str) -> None:
        """Delete audio recording from GridFS."""
        await self.gridfs.delete(file_id)
    
    async def create_indexes(self):
        """
        Create performance indexes on collections.
        Should be called during application startup.
        """
        # Text index for full-text search
        await self.software_questions.create_index([("question", "text")])
        await self.hr_questions.create_index([("question", "text")])
        await self.leetcode_questions.create_index([("question", "text")])
        
        # Compound indexes for common queries
        await self.software_questions.create_index([("category", 1), ("difficulty", 1)])
        await self.hr_questions.create_index([("category", 1), ("difficulty", 1)])
        await self.leetcode_questions.create_index([("category", 1), ("difficulty", 1)])
        
        # Index on topics array
        await self.software_questions.create_index([("topics", 1)])
        await self.hr_questions.create_index([("topics", 1)])
        await self.leetcode_questions.create_index([("topics", 1)])
        
        # Unique index on id field
        await self.software_questions.create_index([("id", 1)], unique=True)
        await self.hr_questions.create_index([("id", 1)], unique=True)
        await self.leetcode_questions.create_index([("id", 1)], unique=True)
    
    def _get_collection_by_category(self, category: str):
        """Helper to route to correct collection."""
        category_map = {
            "software": self.software_questions,
            "hr": self.hr_questions,
            "leetcode": self.leetcode_questions
        }
        return category_map.get(category.lower(), self.software_questions)
    
    async def close(self):
        """Close MongoDB connection and cleanup resources."""
        self.client.close()
```

**Integration Point**: Replaces local JSON file reading in `QuestionBank._load_local_questions()`.

**Performance Optimizations**:
- Connection pooling prevents connection exhaustion
- Async operations enable concurrent query execution
- Indexes on category, difficulty, topics for fast filtering
- Text indexes for full-text search
- GridFS for efficient audio storage and streaming
- Pagination support to limit memory usage

### 3. Dataset Migration Service

**Purpose**: One-time migration of CSV/JSON datasets to MongoDB Atlas with async operations.

**Script: migrate_to_mongodb.py**

```python
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import csv
import json
from pathlib import Path
from typing import AsyncIterator

class DatasetMigrator:
    """Handles async migration of interview question datasets to MongoDB."""
    
    def __init__(self, mongodb_uri: str):
        self.client = AsyncIOMotorClient(
            mongodb_uri,
            maxPoolSize=50,
            minPoolSize=10
        )
        self.db = self.client["RoundZero"]
    
    async def migrate_software_questions(self, csv_path: Path) -> int:
        """
        Migrate Software Questions.csv to MongoDB.
        Uses bulk operations for performance.
        """
        collection = self.db["software_questions"]
        questions = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = {
                    "id": row.get("id", ""),
                    "question": row.get("question", ""),
                    "ideal_answer": row.get("ideal_answer", ""),
                    "category": row.get("category", "software"),
                    "difficulty": row.get("difficulty", "medium"),
                    "source": "Software Questions CSV",
                    "topics": row.get("topics", "").split(",") if row.get("topics") else []
                }
                questions.append(question)
        
        # Bulk upsert for idempotency
        operations = [
            {"replaceOne": {
                "filter": {"id": q["id"]},
                "replacement": q,
                "upsert": True
            }}
            for q in questions
        ]
        
        result = await collection.bulk_write(operations)
        return result.upserted_count + result.modified_count
    
    async def migrate_hr_questions(self, json_path: Path) -> int:
        """
        Migrate hr_interview_questions_dataset.json to MongoDB.
        Uses async bulk operations.
        """
        collection = self.db["hr_questions"]
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = []
        for item in data:
            question = {
                "id": item.get("id", ""),
                "question": item.get("question", ""),
                "ideal_answer": item.get("ideal_answer", ""),
                "category": item.get("category", "hr"),
                "difficulty": item.get("difficulty", "medium"),
                "source": "HR Questions JSON",
                "topics": item.get("topics", [])
            }
            questions.append(question)
        
        operations = [
            {"replaceOne": {
                "filter": {"id": q["id"]},
                "replacement": q,
                "upsert": True
            }}
            for q in questions
        ]
        
        result = await collection.bulk_write(operations)
        return result.upserted_count + result.modified_count
    
    async def migrate_leetcode_questions(self, csv_path: Path) -> int:
        """
        Migrate leetcode_dataset - lc.csv to MongoDB.
        Uses streaming for large datasets.
        """
        collection = self.db["leetcode_questions"]
        batch_size = 1000
        questions = []
        total_migrated = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = {
                    "id": row.get("id", ""),
                    "question": row.get("question", ""),
                    "ideal_answer": row.get("ideal_answer", ""),
                    "category": row.get("category", "leetcode"),
                    "difficulty": row.get("difficulty", "medium"),
                    "source": "LeetCode CSV",
                    "topics": row.get("topics", "").split(",") if row.get("topics") else []
                }
                questions.append(question)
                
                # Batch insert for large datasets
                if len(questions) >= batch_size:
                    operations = [
                        {"replaceOne": {
                            "filter": {"id": q["id"]},
                            "replacement": q,
                            "upsert": True
                        }}
                        for q in questions
                    ]
                    result = await collection.bulk_write(operations)
                    total_migrated += result.upserted_count + result.modified_count
                    questions = []
        
        # Insert remaining questions
        if questions:
            operations = [
                {"replaceOne": {
                    "filter": {"id": q["id"]},
                    "replacement": q,
                    "upsert": True
                }}
                for q in questions
            ]
            result = await collection.bulk_write(operations)
            total_migrated += result.upserted_count + result.modified_count
        
        return total_migrated
    
    async def create_indexes(self):
        """
        Create performance indexes on collections.
        Should be called after migration completes.
        """
        collections = [
            self.db["software_questions"],
            self.db["hr_questions"],
            self.db["leetcode_questions"]
        ]
        
        for collection in collections:
            # Text index for full-text search
            await collection.create_index([("question", "text")])
            
            # Compound indexes for common queries
            await collection.create_index([("category", 1), ("difficulty", 1)])
            
            # Index on topics array
            await collection.create_index([("topics", 1)])
            
            # Unique index on id field
            await collection.create_index([("id", 1)], unique=True)
    
    async def verify_migration(self) -> dict[str, int]:
        """
        Verify data accessibility and return counts.
        Useful for migration validation.
        """
        counts = {
            "software_questions": await self.db["software_questions"].count_documents({}),
            "hr_questions": await self.db["hr_questions"].count_documents({}),
            "leetcode_questions": await self.db["leetcode_questions"].count_documents({})
        }
        return counts
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()

# Migration script entry point
async def main():
    """Run migration with async operations."""
    migrator = DatasetMigrator(mongodb_uri="mongodb://localhost:27017")
    
    try:
        print("Starting migration...")
        
        # Migrate datasets concurrently
        software_count, hr_count, leetcode_count = await asyncio.gather(
            migrator.migrate_software_questions(Path("data/Software Questions.csv")),
            migrator.migrate_hr_questions(Path("data/hr_interview_questions_dataset.json")),
            migrator.migrate_leetcode_questions(Path("data/leetcode_dataset - lc.csv"))
        )
        
        print(f"Migrated {software_count} software questions")
        print(f"Migrated {hr_count} HR questions")
        print(f"Migrated {leetcode_count} LeetCode questions")
        
        # Create indexes
        print("Creating indexes...")
        await migrator.create_indexes()
        
        # Verify migration
        print("Verifying migration...")
        counts = await migrator.verify_migration()
        print(f"Verification: {counts}")
        
    finally:
        await migrator.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Performance Optimizations**:
- Async bulk operations for fast inserts
- Batch processing for large datasets (1000 records per batch)
- Concurrent migration of multiple datasets
- Upsert operations for idempotency
- Index creation after data insertion for better performance

**Purpose**: Manage interview sessions, user data, and results in Postgres with ACID compliance.

**Class: NeonSessionRepository**

```python
import asyncpg
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SessionMetadata(BaseModel):
    """Pydantic model for session validation."""
    session_id: str
    user_id: str
    role: str
    topics: list[str]
    difficulty: str
    mode: str
    voice_enabled: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[int] = None
    confidence_avg: Optional[int] = None
    total_fillers: int = 0

class QuestionResult(BaseModel):
    """Pydantic model for question result validation."""
    session_id: str
    question_id: str
    question_text: str
    user_answer: str
    score: int
    confidence: int
    emotion: str
    fillers: int
    feedback: str
    semantic_similarity: Optional[float] = None
    created_at: datetime

class NeonSessionRepository:
    """Async repository for managing sessions in NeonDB (Postgres)."""
    
    def __init__(self, database_url: str):
        """
        Initialize asyncpg connection pool.
        
        Connection Pool Configuration:
        - min_size: 5 (maintains warm connections)
        - max_size: 20 (handles concurrent sessions)
        - command_timeout: 60 (prevents hanging queries)
        """
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = database_url
    
    async def connect(self):
        """Initialize connection pool. Call during application startup."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    
    async def create_session(self, session: SessionMetadata) -> str:
        """
        Create new interview session in NeonDB.
        Returns session_id.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (
                    session_id, user_id, role, topics, difficulty, 
                    mode, voice_enabled, started_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                session.session_id,
                session.user_id,
                session.role,
                session.topics,
                session.difficulty,
                session.mode,
                session.voice_enabled,
                session.started_at
            )
        return session.session_id
    
    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Retrieve session metadata by session_id."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM sessions WHERE session_id = $1
                """,
                session_id
            )
            if row:
                return SessionMetadata(**dict(row))
            return None
    
    async def update_session_completion(
        self,
        session_id: str,
        completed_at: datetime,
        overall_score: int,
        confidence_avg: int,
        total_fillers: int
    ):
        """Update session with completion data."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sessions 
                SET completed_at = $1, overall_score = $2, 
                    confidence_avg = $3, total_fillers = $4
                WHERE session_id = $5
                """,
                completed_at,
                overall_score,
                confidence_avg,
                total_fillers,
                session_id
            )
    
    async def store_question_result(self, result: QuestionResult):
        """Store individual question result."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO question_results (
                    session_id, question_id, question_text, user_answer,
                    score, confidence, emotion, fillers, feedback,
                    semantic_similarity, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                result.session_id,
                result.question_id,
                result.question_text,
                result.user_answer,
                result.score,
                result.confidence,
                result.emotion,
                result.fillers,
                result.feedback,
                result.semantic_similarity,
                result.created_at
            )
    
    async def get_session_results(self, session_id: str) -> list[QuestionResult]:
        """Retrieve all question results for a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM question_results 
                WHERE session_id = $1 
                ORDER BY created_at ASC
                """,
                session_id
            )
            return [QuestionResult(**dict(row)) for row in rows]
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        limit: int = 10,
        offset: int = 0
    ) -> list[SessionMetadata]:
        """Retrieve user's interview sessions with pagination."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM sessions 
                WHERE user_id = $1 
                ORDER BY started_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset
            )
            return [SessionMetadata(**dict(row)) for row in rows]
    
    async def get_user_session_count_today(self, user_id: str) -> int:
        """
        Get count of sessions started today for rate limiting.
        Used to enforce 10 sessions per day limit.
        """
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM sessions 
                WHERE user_id = $1 
                AND started_at >= CURRENT_DATE
                """,
                user_id
            )
            return count
    
    async def create_tables(self):
        """
        Create database tables if they don't exist.
        Should be called during application startup.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    role VARCHAR(100) NOT NULL,
                    topics TEXT[] NOT NULL,
                    difficulty VARCHAR(50) NOT NULL,
                    mode VARCHAR(50) NOT NULL,
                    voice_enabled BOOLEAN NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    overall_score INTEGER,
                    confidence_avg INTEGER,
                    total_fillers INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON sessions(user_id);
                
                CREATE INDEX IF NOT EXISTS idx_sessions_started_at 
                ON sessions(started_at);
                
                CREATE TABLE IF NOT EXISTS question_results (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    question_id VARCHAR(255) NOT NULL,
                    question_text TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    confidence INTEGER NOT NULL,
                    emotion VARCHAR(50) NOT NULL,
                    fillers INTEGER NOT NULL,
                    feedback TEXT NOT NULL,
                    semantic_similarity FLOAT,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_question_results_session_id 
                ON question_results(session_id);
                
                CREATE INDEX IF NOT EXISTS idx_question_results_created_at 
                ON question_results(created_at);
                """
            )
    
    async def close(self):
        """Close connection pool and cleanup resources."""
        if self.pool:
            await self.pool.close()
```

**Integration Point**: Replaces in-memory session storage and provides persistent storage for user data.

**Performance Optimizations**:
- Connection pooling for concurrent session management
- Async operations for non-blocking database access
- Indexes on user_id, session_id, timestamps for fast queries
- Batch operations support for bulk inserts
- Query result pagination to limit memory usage
- Foreign key constraints for data integrity

**Purpose**: One-time migration of CSV/JSON datasets to MongoDB Atlas.

**Script: migrate_to_mongodb.py**

```python
class DatasetMigrator:
    """Handles migration of interview question datasets to MongoDB."""
    
    def __init__(self, mongodb_uri: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client["RoundZero"]
    
    def migrate_software_questions(self, csv_path: Path) -> int:
        """Migrate Software Questions.csv to MongoDB."""
        pass
    
    def migrate_hr_questions(self, json_path: Path) -> int:
        """Migrate hr_interview_questions_dataset.json to MongoDB."""
        pass
    
    def migrate_leetcode_questions(self, csv_path: Path) -> int:
        """Migrate leetcode_dataset - lc.csv to MongoDB."""
        pass
    
    def create_indexes(self):
        """Create performance indexes on collections."""
        pass
    
    def verify_migration(self) -> dict[str, int]:
        """Verify data accessibility and return counts."""
        pass
```

### 3. Voice Interface Component (Frontend)

**Purpose**: Handle browser permissions, audio capture, and real-time transcript display.

**Component: VoiceInterviewPanel.tsx**

```typescript
interface VoiceInterviewPanelProps {
  sessionId: string;
  onComplete: () => void;
}

interface VoiceState {
  micPermission: 'granted' | 'denied' | 'prompt';
  cameraPermission: 'granted' | 'denied' | 'prompt';
  isRecording: boolean;
  transcript: string;
  isProcessing: boolean;
}

const VoiceInterviewPanel: React.FC<VoiceInterviewPanelProps> = ({
  sessionId,
  onComplete
}) => {
  const [voiceState, setVoiceState] = useState<VoiceState>({
    micPermission: 'prompt',
    cameraPermission: 'prompt',
    isRecording: false,
    transcript: '',
    isProcessing: false
  });
  
  const requestPermissions = async () => {
    // Request camera and microphone permissions
  };
  
  const startRecording = () => {
    // Initialize Deepgram connection
  };
  
  const stopRecording = () => {
    // Stop recording and submit answer
  };
  
  const submitAnswer = async () => {
    // Send transcript to backend
  };
  
  return (
    // UI components
  );
};
```

### 4. Speech Recognition Service (Async)

**Purpose**: Convert user speech to text using Deepgram API with async operations.

**Class: DeepgramSTTService**

```python
from deepgram import DeepgramClient, PrerecordedOptions, LiveOptions
from typing import AsyncIterator
import asyncio

class DeepgramSTTService:
    """Async speech-to-text service using Deepgram API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = DeepgramClient(api_key)
    
    async def transcribe_stream(
        self, 
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """
        Real-time transcription of audio stream.
        Uses Deepgram's live transcription API.
        """
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            interim_results=True,
            punctuate=True,
            diarize=False
        )
        
        connection = self.client.listen.live.v("1")
        
        async def on_message(result):
            """Handle transcription results."""
            if result.is_final:
                transcript = result.channel.alternatives[0].transcript
                if transcript:
                    yield transcript
        
        connection.on("transcript", on_message)
        
        # Start connection
        await connection.start(options)
        
        # Stream audio data
        async for audio_chunk in audio_stream:
            await connection.send(audio_chunk)
        
        # Close connection
        await connection.finish()
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe complete audio buffer.
        Uses Deepgram's prerecorded API for better accuracy.
        """
        options = PrerecordedOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            punctuate=True,
            diarize=False
        )
        
        response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(
            {"buffer": audio_data},
            options
        )
        
        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript
    
    async def transcribe_with_confidence(
        self, 
        audio_data: bytes
    ) -> tuple[str, float]:
        """
        Transcribe audio and return confidence score.
        Useful for quality assessment.
        """
        options = PrerecordedOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            punctuate=True,
            diarize=False
        )
        
        response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(
            {"buffer": audio_data},
            options
        )
        
        alternative = response.results.channels[0].alternatives[0]
        transcript = alternative.transcript
        confidence = alternative.confidence
        
        return transcript, confidence
```

**Integration**: Used by `InterviewerAgent` for real-time speech recognition.

**Performance Optimizations**:
- Async API calls for non-blocking operations
- Streaming support for real-time transcription
- Confidence scores for quality assessment
- Smart formatting and punctuation for better readability

### 5. Text-to-Speech Service (Async)

**Purpose**: Convert AI responses to natural-sounding speech using ElevenLabs with caching.

**Class: ElevenLabsTTSService**

```python
from elevenlabs import AsyncElevenLabs
from typing import AsyncIterator, Optional
import hashlib
import asyncio

class ElevenLabsTTSService:
    """Async text-to-speech service using ElevenLabs API with caching."""
    
    def __init__(self, api_key: str, voice_id: str = "default"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.client = AsyncElevenLabs(api_key=api_key)
        self.cache: dict[str, bytes] = {}  # In-memory cache for repeated phrases
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice_settings: Optional[dict] = None
    ) -> bytes:
        """
        Convert text to audio bytes with caching.
        Caches common phrases to reduce API calls.
        """
        # Check cache first
        cache_key = self._get_cache_key(text, voice_settings)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Generate audio
        audio = await self.client.generate(
            text=text,
            voice=self.voice_id,
            model="eleven_turbo_v2",
            voice_settings=voice_settings or {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        )
        
        # Convert generator to bytes
        audio_bytes = b"".join([chunk async for chunk in audio])
        
        # Cache result
        self.cache[cache_key] = audio_bytes
        
        return audio_bytes
    
    async def stream_speech(
        self, 
        text: str,
        voice_settings: Optional[dict] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream audio as it's generated.
        Useful for reducing perceived latency.
        """
        audio = await self.client.generate(
            text=text,
            voice=self.voice_id,
            model="eleven_turbo_v2",
            stream=True,
            voice_settings=voice_settings or {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        )
        
        async for chunk in audio:
            yield chunk
    
    async def synthesize_batch(
        self, 
        texts: list[str]
    ) -> list[bytes]:
        """
        Synthesize multiple texts concurrently.
        Useful for preloading common phrases.
        """
        tasks = [self.synthesize_speech(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _get_cache_key(self, text: str, voice_settings: Optional[dict]) -> str:
        """Generate cache key from text and settings."""
        settings_str = str(voice_settings) if voice_settings else ""
        return hashlib.md5(f"{text}{settings_str}".encode()).hexdigest()
    
    def clear_cache(self):
        """Clear audio cache to free memory."""
        self.cache.clear()
    
    def get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        return sum(len(audio) for audio in self.cache.values())
```

**Integration**: Used by `InterviewerAgent.simple_response()` for AI voice output.

**Performance Optimizations**:
- In-memory caching for repeated phrases (greetings, common feedback)
- Async API calls for non-blocking operations
- Streaming support for reduced perceived latency
- Batch synthesis for preloading common phrases
- Cache management to prevent memory bloat

### 6. Answer Evaluation Engine (Async)

**Purpose**: Analyze user answers for completeness, relevance, and quality with async AI calls.

**Enhanced DecisionEngine**

```python
from anthropic import AsyncAnthropic
import asyncio

class EnhancedDecisionEngine(DecisionEngine):
    """Extended decision engine with voice-specific analysis and async operations."""
    
    def __init__(self, anthropic_api_key: str):
        super().__init__(anthropic_api_key)
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
    
    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        confidence: int,
        fillers: int,
        mode: Literal["buddy", "strict"],
        ideal_answer: str = "",
        embedding_service: Optional[GeminiEmbeddingService] = None
    ) -> EvaluationResult:
        """
        Comprehensive async answer evaluation.
        
        Returns:
            EvaluationResult with action, message, score, and semantic_similarity
        """
        # Concurrent evaluation tasks
        tasks = [
            self._evaluate_with_claude(question, answer, ideal_answer, mode),
            self._calculate_semantic_similarity(question, answer, embedding_service) if embedding_service else asyncio.sleep(0)
        ]
        
        claude_result, semantic_similarity = await asyncio.gather(*tasks)
        
        # Adjust score based on confidence and fillers
        adjusted_score = self._adjust_score(
            claude_result["score"],
            confidence,
            fillers
        )
        
        return EvaluationResult(
            action=claude_result["action"],
            message=claude_result["message"],
            score=adjusted_score,
            semantic_similarity=semantic_similarity,
            requires_followup=claude_result.get("requires_followup", False),
            followup_question=claude_result.get("followup_question")
        )
    
    async def _evaluate_with_claude(
        self,
        question: str,
        answer: str,
        ideal_answer: str,
        mode: str
    ) -> dict:
        """Async Claude evaluation."""
        prompt = self._build_evaluation_prompt(question, answer, ideal_answer, mode)
        
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_claude_response(response.content[0].text)
    
    async def _calculate_semantic_similarity(
        self,
        question: str,
        answer: str,
        embedding_service: GeminiEmbeddingService
    ) -> float:
        """Calculate semantic similarity using embeddings."""
        question_embedding, answer_embedding = await asyncio.gather(
            embedding_service.get_embedding(question),
            embedding_service.get_embedding(answer)
        )
        
        # Cosine similarity
        similarity = self._cosine_similarity(question_embedding, answer_embedding)
        return similarity
    
    async def should_interrupt(
        self,
        answer_buffer: str,
        question: str,
        silence_duration: float
    ) -> tuple[bool, str]:
        """
        Determine if AI should interrupt with follow-up question.
        
        Returns:
            (should_interrupt, follow_up_question)
        """
        if silence_duration < 3.0:
            return False, ""
        
        if len(answer_buffer.split()) < 10:
            return False, ""
        
        # Ask Claude if follow-up is needed
        prompt = f"""
        Question: {question}
        User's answer so far: {answer_buffer}
        
        Should I ask a follow-up question? If yes, what should I ask?
        Respond with JSON: {{"should_interrupt": true/false, "followup": "question text"}}
        """
        
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = self._parse_interrupt_response(response.content[0].text)
        return result["should_interrupt"], result.get("followup", "")
```

**Integration**: Used by `InterviewerAgent` for answer evaluation.

**Performance Optimizations**:
- Async Claude API calls for non-blocking evaluation
- Concurrent execution of evaluation and semantic similarity
- Retry logic with exponential backoff for API failures
- Caching of evaluation results for identical answers

### 8. Session Management (Async)

**Purpose**: Track interview state, store interactions, and manage session lifecycle with async persistence.

**Enhanced SessionState**

```python
from dataclasses import dataclass, field
from typing import Optional, Literal
import asyncio

@dataclass
class VoiceSessionState(SessionState):
    """Extended session state for voice interviews with async operations."""
    
    # Existing fields from SessionState
    id: str
    config: SessionConfig
    questions: list[Question]
    memory_context: str
    started_at: float
    current_q_idx: int = 0
    answer_buffer: str = ""
    question_results: list[QuestionResult] = field(default_factory=list)
    total_fillers: int = 0
    completed: bool = False
    completed_at: Optional[float] = None
    agent: Optional[InterviewerAgent] = None
    
    # New voice-specific fields
    audio_recordings: list[str] = field(default_factory=list)  # GridFS file IDs
    transcript_history: list[dict] = field(default_factory=list)
    voice_enabled: bool = True
    stt_failures: int = 0
    tts_failures: int = 0
    
    # Async persistence
    _mongo_repo: Optional[MongoQuestionRepository] = None
    _neon_repo: Optional[NeonSessionRepository] = None
    _cache_service: Optional[CacheService] = None
    
    async def persist_to_neondb(self):
        """Async persist session metadata to NeonDB."""
        if not self._neon_repo:
            return
        
        session_metadata = SessionMetadata(
            session_id=self.id,
            user_id=self.config.user_id,
            role=self.config.role,
            topics=self.config.topics,
            difficulty=self.config.difficulty,
            mode=self.config.mode,
            voice_enabled=self.voice_enabled,
            started_at=datetime.fromtimestamp(self.started_at),
            completed_at=datetime.fromtimestamp(self.completed_at) if self.completed_at else None,
            overall_score=self._calculate_overall_score(),
            confidence_avg=self._calculate_confidence_avg(),
            total_fillers=self.total_fillers
        )
        
        await self._neon_repo.create_session(session_metadata)
    
    async def persist_question_result(self, result: QuestionResult):
        """Async persist individual question result to NeonDB."""
        if not self._neon_repo:
            return
        
        await self._neon_repo.store_question_result(result)
    
    async def store_audio_recording(
        self,
        audio_data: bytes,
        question_index: int,
        duration: float
    ) -> str:
        """Async store audio recording to MongoDB GridFS."""
        if not self._mongo_repo:
            return ""
        
        filename = f"session_{self.id}_q{question_index}.wav"
        metadata = {
            "session_id": self.id,
            "question_index": question_index,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        file_id = await self._mongo_repo.store_audio_recording(
            audio_data,
            filename,
            metadata
        )
        
        self.audio_recordings.append(file_id)
        return file_id
    
    async def preload_next_question(self):
        """Async preload next question while user is answering current question."""
        if not self._mongo_repo or not self._cache_service:
            return
        
        next_idx = self.current_q_idx + 1
        if next_idx >= len(self.questions):
            return
        
        # Check cache first
        next_question = self.questions[next_idx]
        cached = await self._cache_service.get_cached_questions(
            next_question.category,
            next_question.difficulty,
            1
        )
        
        if not cached:
            # Preload from MongoDB
            questions = await self._mongo_repo.get_questions_by_category(
                next_question.category,
                next_question.difficulty,
                limit=1,
                skip=next_idx
            )
            
            # Cache for future use
            if questions:
                await self._cache_service.cache_questions(
                    next_question.category,
                    next_question.difficulty,
                    1,
                    [q.dict() for q in questions]
                )
```

**NeonDB Schema (Postgres)**

```sql
-- sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    topics TEXT[] NOT NULL,
    difficulty VARCHAR(50) NOT NULL,
    mode VARCHAR(50) NOT NULL,
    voice_enabled BOOLEAN NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    overall_score INTEGER,
    confidence_avg INTEGER,
    total_fillers INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);
CREATE INDEX idx_sessions_session_id ON sessions(session_id);

-- question_results table
CREATE TABLE IF NOT EXISTS question_results (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    question_id VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    score INTEGER NOT NULL,
    confidence INTEGER NOT NULL,
    emotion VARCHAR(50) NOT NULL,
    fillers INTEGER NOT NULL,
    feedback TEXT NOT NULL,
    semantic_similarity FLOAT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_question_results_session_id ON question_results(session_id);
CREATE INDEX idx_question_results_created_at ON question_results(created_at);
```

**MongoDB Schema (Collections)**

```javascript
// software_questions collection
{
  _id: ObjectId,
  id: String (unique indexed),
  question: String (text indexed),
  ideal_answer: String,
  category: String (indexed),
  difficulty: String (indexed),
  source: String,
  topics: [String] (indexed)
}

// hr_questions collection (same schema)
// leetcode_questions collection (same schema)

// GridFS files (fs.files collection)
{
  _id: ObjectId,
  filename: String,
  length: Number,
  chunkSize: Number,
  uploadDate: Date,
  metadata: {
    session_id: String,
    question_index: Number,
    duration_seconds: Number,
    timestamp: String
  }
}

// GridFS chunks (fs.chunks collection)
{
  _id: ObjectId,
  files_id: ObjectId,
  n: Number,
  data: Binary
}
```

**Performance Optimizations**:
- Async persistence prevents blocking interview flow
- Question preloading reduces wait time between questions
- GridFS streaming for efficient audio storage
- Indexes on all frequently queried fields
- Foreign key constraints for data integrity
- Cascade delete for cleanup

**Purpose**: Reduce latency and API costs through intelligent caching.

**Class: CacheService**

```python
import redis.asyncio as redis
import json
from typing import Optional, Any
import hashlib

class CacheService:
    """Async caching service using Redis/Upstash."""
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis connection pool.
        
        Connection Pool Configuration:
        - max_connections: 50 (handles high concurrency)
        - decode_responses: True (automatic string decoding)
        """
        self.redis = redis.from_url(
            redis_url,
            max_connections=50,
            decode_responses=True
        )
    
    async def get_cached_questions(
        self,
        category: str,
        difficulty: str,
        limit: int
    ) -> Optional[list[dict]]:
        """Get cached questions by category and difficulty."""
        cache_key = f"questions:{category}:{difficulty}:{limit}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_questions(
        self,
        category: str,
        difficulty: str,
        limit: int,
        questions: list[dict],
        ttl: int = 3600  # 1 hour
    ):
        """Cache questions with TTL."""
        cache_key = f"questions:{category}:{difficulty}:{limit}"
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(questions)
        )
    
    async def get_cached_audio(self, text: str) -> Optional[bytes]:
        """Get cached TTS audio by text hash."""
        cache_key = f"audio:{self._hash_text(text)}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return cached.encode('latin1')  # Binary data
        return None
    
    async def cache_audio(
        self,
        text: str,
        audio_data: bytes,
        ttl: int = 86400  # 24 hours
    ):
        """Cache TTS audio with TTL."""
        cache_key = f"audio:{self._hash_text(text)}"
        await self.redis.setex(
            cache_key,
            ttl,
            audio_data.decode('latin1')
        )
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 10,
        window: int = 86400  # 24 hours
    ) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit.
        
        Returns:
            (is_allowed, remaining_requests)
        """
        cache_key = f"rate_limit:{user_id}"
        current = await self.redis.get(cache_key)
        
        if current is None:
            await self.redis.setex(cache_key, window, 1)
            return True, limit - 1
        
        current_count = int(current)
        if current_count >= limit:
            return False, 0
        
        await self.redis.incr(cache_key)
        return True, limit - current_count - 1
    
    async def cache_evaluation_result(
        self,
        question: str,
        answer: str,
        result: dict,
        ttl: int = 3600
    ):
        """Cache evaluation results for identical Q&A pairs."""
        cache_key = f"eval:{self._hash_text(question + answer)}"
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )
    
    async def get_cached_evaluation(
        self,
        question: str,
        answer: str
    ) -> Optional[dict]:
        """Get cached evaluation result."""
        cache_key = f"eval:{self._hash_text(question + answer)}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for cache key."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def close(self):
        """Close Redis connection."""
        await self.redis.close()
```

**Caching Strategy**:
- **Questions**: Cache frequently accessed questions (1 hour TTL)
- **TTS Audio**: Cache common phrases and feedback (24 hour TTL)
- **Evaluation Results**: Cache identical Q&A evaluations (1 hour TTL)
- **Rate Limiting**: Track user request counts (24 hour window)

**Performance Impact**:
- Reduces MongoDB queries by ~60% for popular questions
- Reduces TTS API calls by ~40% for common phrases
- Reduces Claude API calls by ~20% for similar answers
- Enables sub-100ms response times for cached data

**Purpose**: Track interview state, store interactions, and manage session lifecycle.

**Enhanced SessionState**

```python
@dataclass
class VoiceSessionState(SessionState):
    """Extended session state for voice interviews."""
    
    # Existing fields from SessionState
    id: str
    config: SessionConfig
    questions: list[Question]
    memory_context: str
    started_at: float
    current_q_idx: int = 0
    answer_buffer: str = ""
    question_results: list[QuestionResult] = field(default_factory=list)
    total_fillers: int = 0
    completed: bool = False
    completed_at: float | None = None
    agent: InterviewerAgent | None = None
    
    # New voice-specific fields
    audio_recordings: list[str] = field(default_factory=list)  # S3/MongoDB URLs
    transcript_history: list[dict] = field(default_factory=list)
    voice_enabled: bool = True
    stt_failures: int = 0
    tts_failures: int = 0
```

**MongoDB Schema**

```javascript
// sessions collection
{
  _id: ObjectId,
  session_id: String (indexed),
  user_id: String (indexed),
  role: String,
  topics: [String],
  difficulty: String,
  mode: String,
  voice_enabled: Boolean,
  started_at: ISODate,
  completed_at: ISODate,
  overall_score: Number,
  confidence_avg: Number,
  total_fillers: Number,
  audio_recordings: [String],  // URLs to audio files
  transcript_history: [
    {
      timestamp: ISODate,
      speaker: String,  // "user" or "agent"
      text: String,
      confidence: Number
    }
  ]
}

// question_results collection
{
  _id: ObjectId,
  session_id: String (indexed),
  question_id: String,
  question_text: String,
  user_answer: String,
  score: Number,
  confidence: Number,
  emotion: String,
  fillers: Number,
  feedback: String,
  semantic_similarity: Number,  // 0-1 score from embeddings
  created_at: ISODate
}

// questions collections (software_questions, hr_questions, leetcode_questions)
{
  _id: ObjectId,
  id: String (unique indexed),
  question: String (text indexed),
  ideal_answer: String,
  category: String (indexed),
  difficulty: String (indexed),
  source: String,
  topics: [String] (indexed)
}
```

## Data Models

### Question Model (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional

class Question(BaseModel):
    """Pydantic model for question validation and serialization."""
    id: str
    question: str
    ideal_answer: str = ""
    category: str = "General"
    difficulty: str = "medium"
    source: str = "MongoDB"
    topics: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sw_001",
                "question": "Explain the difference between REST and GraphQL",
                "ideal_answer": "REST uses multiple endpoints...",
                "category": "software",
                "difficulty": "medium",
                "source": "Software Questions CSV",
                "topics": ["API", "Architecture"]
            }
        }
```

### SessionMetadata Model (Pydantic)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SessionMetadata(BaseModel):
    """Pydantic model for session metadata validation."""
    session_id: str
    user_id: str
    role: str
    topics: list[str]
    difficulty: str
    mode: str
    voice_enabled: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_score: Optional[int] = None
    confidence_avg: Optional[int] = None
    total_fillers: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": "user_xyz789",
                "role": "Software Engineer",
                "topics": ["Python", "FastAPI"],
                "difficulty": "medium",
                "mode": "buddy",
                "voice_enabled": True,
                "started_at": "2024-01-15T10:30:00Z"
            }
        }
```

### QuestionResult Model (Pydantic)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class QuestionResult(BaseModel):
    """Pydantic model for question result validation."""
    session_id: str
    question_id: str
    question_text: str
    user_answer: str
    score: int
    confidence: int
    emotion: str
    fillers: int
    feedback: str
    semantic_similarity: Optional[float] = None
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "question_id": "sw_001",
                "question_text": "Explain REST vs GraphQL",
                "user_answer": "REST uses multiple endpoints...",
                "score": 85,
                "confidence": 90,
                "emotion": "confident",
                "fillers": 2,
                "feedback": "Good explanation of key differences",
                "semantic_similarity": 0.87,
                "created_at": "2024-01-15T10:35:00Z"
            }
        }
```

### EvaluationResult Model (Pydantic)

```python
from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum

class Action(str, Enum):
    """Enum for evaluation actions."""
    CONTINUE = "CONTINUE"
    NEXT = "NEXT"
    HINT = "HINT"
    ENCOURAGE = "ENCOURAGE"

class EvaluationResult(BaseModel):
    """Pydantic model for evaluation result validation."""
    action: Action
    message: str
    score: Optional[int] = None
    semantic_similarity: Optional[float] = None
    requires_followup: bool = False
    followup_question: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "NEXT",
                "message": "Great answer! You covered the key points.",
                "score": 85,
                "semantic_similarity": 0.87,
                "requires_followup": False,
                "followup_question": None
            }
        }
```

### VoiceTranscript Model (Pydantic)

```python
from pydantic import BaseModel
from typing import Literal

class VoiceTranscript(BaseModel):
    """Pydantic model for voice transcript validation."""
    timestamp: float
    speaker: Literal["user", "agent"]
    text: str
    confidence: float  # 0-1 from STT service
    is_final: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1705315800.123,
                "speaker": "user",
                "text": "REST uses multiple endpoints for different resources",
                "confidence": 0.95,
                "is_final": True
            }
        }
```

### AudioRecording Model (Pydantic)

```python
from pydantic import BaseModel

class AudioRecording(BaseModel):
    """Pydantic model for audio recording metadata."""
    session_id: str
    question_index: int
    file_id: str  # MongoDB GridFS file ID
    duration_seconds: float
    created_at: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "question_index": 0,
                "file_id": "507f1f77bcf86cd799439011",
                "duration_seconds": 45.3,
                "created_at": 1705315800.123
            }
        }
```

### ConnectionPoolConfig Model (Pydantic)

```python
from pydantic import BaseModel

class MongoPoolConfig(BaseModel):
    """Configuration for MongoDB connection pool."""
    max_pool_size: int = 50
    min_pool_size: int = 10
    server_selection_timeout_ms: int = 5000
    
class PostgresPoolConfig(BaseModel):
    """Configuration for Postgres connection pool."""
    min_size: int = 5
    max_size: int = 20
    command_timeout: int = 60
    
class RedisPoolConfig(BaseModel):
    """Configuration for Redis connection pool."""
    max_connections: int = 50
    decode_responses: bool = True
```

## Performance Monitoring and Optimization

### Performance Metrics

**Latency Targets:**
- MongoDB query response time: <500ms (p95)
- NeonDB query response time: <300ms (p95)
- Redis cache hit: <50ms (p95)
- STT transcription latency: <1s (real-time)
- TTS audio generation: <1.5s (p95)
- Answer evaluation: <2s (p95)
- End-to-end question cycle: <5s (p95)

**Throughput Targets:**
- Concurrent interview sessions: 100 users
- Questions per second: 50 queries/sec
- Audio recordings per hour: 1000 recordings/hour

### Connection Pool Monitoring

```python
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class PoolMetrics:
    """Metrics for connection pool monitoring."""
    pool_name: str
    active_connections: int
    idle_connections: int
    total_connections: int
    max_connections: int
    wait_time_ms: float
    query_count: int
    error_count: int

class PerformanceMonitor:
    """Monitor performance metrics for all services."""
    
    def __init__(self):
        self.metrics: dict[str, list[float]] = {
            "mongo_query_time": [],
            "neon_query_time": [],
            "redis_query_time": [],
            "stt_latency": [],
            "tts_latency": [],
            "evaluation_time": [],
            "end_to_end_time": []
        }
    
    async def track_mongo_query(self, query_func, *args, **kwargs):
        """Track MongoDB query performance."""
        start = time.time()
        try:
            result = await query_func(*args, **kwargs)
            latency = (time.time() - start) * 1000  # ms
            self.metrics["mongo_query_time"].append(latency)
            
            if latency > 500:  # Alert on slow queries
                print(f"⚠️ Slow MongoDB query: {latency:.2f}ms")
            
            return result
        except Exception as e:
            print(f"❌ MongoDB query error: {e}")
            raise
    
    async def track_neon_query(self, query_func, *args, **kwargs):
        """Track NeonDB query performance."""
        start = time.time()
        try:
            result = await query_func(*args, **kwargs)
            latency = (time.time() - start) * 1000  # ms
            self.metrics["neon_query_time"].append(latency)
            
            if latency > 300:  # Alert on slow queries
                print(f"⚠️ Slow NeonDB query: {latency:.2f}ms")
            
            return result
        except Exception as e:
            print(f"❌ NeonDB query error: {e}")
            raise
    
    async def get_pool_metrics(
        self,
        mongo_repo: MongoQuestionRepository,
        neon_repo: NeonSessionRepository
    ) -> dict[str, PoolMetrics]:
        """Get connection pool metrics from all services."""
        return {
            "mongodb": PoolMetrics(
                pool_name="MongoDB",
                active_connections=mongo_repo.client.nodes[0].pool.active_sockets,
                idle_connections=mongo_repo.client.nodes[0].pool.idle_sockets,
                total_connections=mongo_repo.client.nodes[0].pool.active_sockets + 
                                 mongo_repo.client.nodes[0].pool.idle_sockets,
                max_connections=50,
                wait_time_ms=0.0,
                query_count=len(self.metrics["mongo_query_time"]),
                error_count=0
            ),
            "neondb": PoolMetrics(
                pool_name="NeonDB",
                active_connections=neon_repo.pool.get_size() - neon_repo.pool.get_idle_size(),
                idle_connections=neon_repo.pool.get_idle_size(),
                total_connections=neon_repo.pool.get_size(),
                max_connections=20,
                wait_time_ms=0.0,
                query_count=len(self.metrics["neon_query_time"]),
                error_count=0
            )
        }
    
    def get_percentile(self, metric_name: str, percentile: float = 0.95) -> float:
        """Calculate percentile for a metric."""
        values = sorted(self.metrics.get(metric_name, []))
        if not values:
            return 0.0
        
        index = int(len(values) * percentile)
        return values[min(index, len(values) - 1)]
    
    def get_summary(self) -> dict:
        """Get performance summary."""
        return {
            "mongo_query_p95": self.get_percentile("mongo_query_time"),
            "neon_query_p95": self.get_percentile("neon_query_time"),
            "redis_query_p95": self.get_percentile("redis_query_time"),
            "stt_latency_p95": self.get_percentile("stt_latency"),
            "tts_latency_p95": self.get_percentile("tts_latency"),
            "evaluation_time_p95": self.get_percentile("evaluation_time"),
            "end_to_end_p95": self.get_percentile("end_to_end_time")
        }
```

### Query Optimization Strategies

**MongoDB Indexes:**
```javascript
// Compound index for common query pattern
db.software_questions.createIndex({ category: 1, difficulty: 1 })

// Text index for full-text search
db.software_questions.createIndex({ question: "text" })

// Index on topics array
db.software_questions.createIndex({ topics: 1 })

// Unique index on id
db.software_questions.createIndex({ id: 1 }, { unique: true })
```

**NeonDB Indexes:**
```sql
-- Index on user_id for user session queries
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- Index on started_at for time-based queries
CREATE INDEX idx_sessions_started_at ON sessions(started_at);

-- Composite index for rate limiting queries
CREATE INDEX idx_sessions_user_date ON sessions(user_id, started_at);

-- Index on session_id for question results
CREATE INDEX idx_question_results_session_id ON question_results(session_id);
```

### Caching Strategy

**Cache Hit Rates:**
- Questions: Target 60% hit rate
- TTS Audio: Target 40% hit rate
- Evaluation Results: Target 20% hit rate

**Cache Invalidation:**
- Questions: 1 hour TTL (questions rarely change)
- TTS Audio: 24 hour TTL (audio is static)
- Evaluation Results: 1 hour TTL (answers may vary)
- Rate Limits: 24 hour TTL (daily reset)

**Cache Warming:**
```python
async def warm_cache(
    cache_service: CacheService,
    mongo_repo: MongoQuestionRepository,
    tts_service: ElevenLabsTTSService
):
    """Warm cache with frequently accessed data."""
    # Preload popular questions
    popular_categories = ["software", "hr", "leetcode"]
    difficulties = ["easy", "medium", "hard"]
    
    for category in popular_categories:
        for difficulty in difficulties:
            questions = await mongo_repo.get_questions_by_category(
                category, difficulty, limit=10
            )
            await cache_service.cache_questions(
                category, difficulty, 10,
                [q.dict() for q in questions]
            )
    
    # Preload common TTS phrases
    common_phrases = [
        "Great answer! Let's move to the next question.",
        "Can you elaborate on that?",
        "That's a good start. Can you provide more details?",
        "Excellent! You covered all the key points."
    ]
    
    await tts_service.synthesize_batch(common_phrases)
```

### Horizontal Scaling Readiness

**Stateless Backend:**
- FastAPI backend is stateless (can scale horizontally)
- Session state stored in NeonDB (shared across instances)
- No in-memory session storage

**Database Scaling:**
- MongoDB: Sharding strategy for large question datasets
- NeonDB: Read replicas for read-heavy operations
- Redis: Cluster mode for high availability

**Load Balancing:**
- Round-robin distribution across backend instances
- Health checks on /health endpoint
- Graceful shutdown handling

## Error Handling

### Error Categories and Recovery Strategies

**1. MongoDB Connection Errors**
- **Detection**: Connection timeout or authentication failure
- **Recovery**: Async retry with exponential backoff (3 attempts)
- **Fallback**: Return error to user, prevent interview start
- **Logging**: Log connection string (sanitized), error details

```python
async def connect_with_retry(
    connection_uri: str,
    max_attempts: int = 3
) -> AsyncIOMotorClient:
    """Connect to MongoDB with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            client = AsyncIOMotorClient(
                connection_uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            await client.admin.command('ping')
            return client
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
```

**2. NeonDB Connection Errors**
- **Detection**: Connection pool exhaustion or query timeout
- **Recovery**: Async retry with exponential backoff (3 attempts)
- **Fallback**: Return error to user, log for investigation
- **Logging**: Log query, connection pool metrics, error details

```python
async def execute_with_retry(
    pool: asyncpg.Pool,
    query: str,
    *args,
    max_attempts: int = 3
):
    """Execute query with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            async with pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except asyncpg.PostgresError as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
```

**3. Speech-to-Text Failures**
- **Detection**: Deepgram API error or timeout
- **Recovery**: Retry current request once (async)
- **Fallback**: Switch to text-only input mode
- **User Notification**: "Voice recognition unavailable. Please type your answer."

```python
async def transcribe_with_fallback(
    stt_service: DeepgramSTTService,
    audio_data: bytes
) -> tuple[str, bool]:
    """Transcribe with fallback to text mode."""
    try:
        transcript = await stt_service.transcribe_audio(audio_data)
        return transcript, True  # voice_enabled
    except Exception as e:
        print(f"STT failed: {e}")
        return "", False  # fallback to text mode
```

**4. Text-to-Speech Failures**
- **Detection**: ElevenLabs API error or timeout
- **Recovery**: Check cache first, retry once if not cached
- **Fallback**: Display text without audio
- **User Notification**: "Audio unavailable. Question displayed as text."

```python
async def synthesize_with_fallback(
    tts_service: ElevenLabsTTSService,
    cache_service: CacheService,
    text: str
) -> tuple[Optional[bytes], bool]:
    """Synthesize speech with caching and fallback."""
    # Check cache first
    cached_audio = await cache_service.get_cached_audio(text)
    if cached_audio:
        return cached_audio, True
    
    # Try TTS service
    try:
        audio = await tts_service.synthesize_speech(text)
        await cache_service.cache_audio(text, audio)
        return audio, True
    except Exception as e:
        print(f"TTS failed: {e}")
        return None, False  # fallback to text only
```

**5. AI Evaluation Failures**
- **Detection**: Anthropic API error or timeout
- **Recovery**: Async retry with exponential backoff (3 attempts, 1s, 2s, 4s)
- **Fallback**: Use heuristic evaluation from existing `DecisionEngine`
- **Logging**: Log question, answer length, error details

```python
async def evaluate_with_fallback(
    claude_client: AsyncAnthropic,
    question: str,
    answer: str,
    max_attempts: int = 3
) -> dict:
    """Evaluate answer with retry and fallback."""
    for attempt in range(max_attempts):
        try:
            response = await claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": f"Evaluate: {answer}"}]
            )
            return parse_evaluation(response.content[0].text)
        except Exception as e:
            if attempt == max_attempts - 1:
                # Fallback to heuristic evaluation
                return heuristic_evaluation(question, answer)
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
```

**6. Network Disconnection**
- **Detection**: WebSocket connection lost
- **Recovery**: Save session state to localStorage (frontend)
- **Reconnection**: Sync localStorage to NeonDB when connection restored
- **User Notification**: "Connection lost. Your progress is saved locally."

**7. Permission Denial**
- **Detection**: Browser permission API returns "denied"
- **Recovery**: None (user action required)
- **Fallback**: Provide instructions for enabling permissions
- **Alternative**: Offer text-only interview mode

### Error Response Format

```typescript
interface ErrorResponse {
  error: string;
  error_code: string;
  message: string;
  fallback_available: boolean;
  retry_after?: number;  // seconds
}
```

### Retry Configuration

```python
from dataclasses import dataclass

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int
    backoff_factor: int
    initial_delay: float

RETRY_CONFIG = {
    "mongodb": RetryConfig(
        max_attempts=3,
        backoff_factor=2,
        initial_delay=1.0
    ),
    "neondb": RetryConfig(
        max_attempts=3,
        backoff_factor=2,
        initial_delay=1.0
    ),
    "anthropic": RetryConfig(
        max_attempts=3,
        backoff_factor=2,
        initial_delay=1.0
    ),
    "deepgram": RetryConfig(
        max_attempts=1,
        backoff_factor=1,
        initial_delay=0.5
    ),
    "elevenlabs": RetryConfig(
        max_attempts=1,
        backoff_factor=1,
        initial_delay=0.5
    )
}
```

### Circuit Breaker Pattern

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            
            raise
```

## Testing Strategy

### Unit Testing

**Backend Unit Tests** (pytest with pytest-asyncio):
- `test_mongo_question_repository.py`: Test async MongoDB query methods with mock data
  - Test connection pooling behavior
  - Test async bulk operations
  - Test GridFS audio storage and retrieval
  - Test index creation
- `test_neon_session_repository.py`: Test async NeonDB operations
  - Test connection pool management
  - Test session CRUD operations
  - Test transaction handling
  - Test query performance
- `test_dataset_migrator.py`: Test async CSV/JSON parsing and data normalization
  - Test concurrent migration
  - Test batch processing
  - Test upsert idempotency
- `test_deepgram_stt_service.py`: Test async STT service with mock audio data
  - Test streaming transcription
  - Test confidence scores
  - Test error handling
- `test_elevenlabs_tts_service.py`: Test async TTS service with mock text
  - Test audio caching
  - Test batch synthesis
  - Test streaming audio
- `test_enhanced_decision_engine.py`: Test async answer evaluation logic
  - Test concurrent Claude and embedding calls
  - Test retry logic
  - Test fallback to heuristic evaluation
- `test_cache_service.py`: Test Redis caching operations
  - Test cache hit/miss scenarios
  - Test TTL expiration
  - Test rate limiting
- `test_voice_session_state.py`: Test async session state management
  - Test async persistence
  - Test question preloading
  - Test audio recording storage

**Example Async Test:**
```python
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

@pytest_asyncio.fixture
async def mongo_repo():
    """Fixture for MongoDB repository."""
    repo = MongoQuestionRepository("mongodb://localhost:27017")
    await repo.create_indexes()
    yield repo
    await repo.close()

@pytest.mark.asyncio
async def test_get_questions_by_category(mongo_repo):
    """Test async question retrieval."""
    questions = await mongo_repo.get_questions_by_category(
        category="software",
        difficulty="medium",
        limit=10
    )
    assert len(questions) <= 10
    assert all(q.category == "software" for q in questions)
    assert all(q.difficulty == "medium" for q in questions)

@pytest.mark.asyncio
async def test_connection_pool_limits(mongo_repo):
    """Test connection pool handles concurrent requests."""
    tasks = [
        mongo_repo.get_questions_by_category("software", "medium", 5)
        for _ in range(100)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 100
```

**Frontend Unit Tests** (Jest + React Testing Library):
- `VoiceInterviewPanel.test.tsx`: Test permission requests, recording controls
- `TranscriptDisplay.test.tsx`: Test real-time transcript rendering
- `AudioPlayer.test.tsx`: Test audio playback controls
- `PermissionHandler.test.tsx`: Test permission state management

### Integration Testing

**API Integration Tests** (pytest with async support):
- Test complete interview flow from start to completion
- Test MongoDB connection and async query performance
- Test NeonDB session persistence and retrieval
- Test Deepgram STT with sample audio files
- Test ElevenLabs TTS with sample text
- Test Anthropic Claude evaluation with sample answers
- Test Redis caching behavior
- Test error handling and fallback mechanisms
- Test concurrent session handling

**Example Integration Test:**
```python
@pytest.mark.asyncio
async def test_complete_interview_flow():
    """Test end-to-end interview flow with async operations."""
    # Setup
    mongo_repo = MongoQuestionRepository(MONGO_URI)
    neon_repo = NeonSessionRepository(NEON_URI)
    cache_service = CacheService(REDIS_URI)
    
    await neon_repo.connect()
    
    try:
        # Create session
        session = SessionMetadata(
            session_id="test_session",
            user_id="test_user",
            role="Software Engineer",
            topics=["Python"],
            difficulty="medium",
            mode="buddy",
            voice_enabled=True,
            started_at=datetime.now()
        )
        await neon_repo.create_session(session)
        
        # Fetch questions (should use cache after first call)
        questions = await mongo_repo.get_questions_by_category(
            "software", "medium", 5
        )
        assert len(questions) == 5
        
        # Simulate answer evaluation
        result = QuestionResult(
            session_id="test_session",
            question_id=questions[0].id,
            question_text=questions[0].question,
            user_answer="Test answer",
            score=85,
            confidence=90,
            emotion="confident",
            fillers=2,
            feedback="Good answer",
            semantic_similarity=0.87,
            created_at=datetime.now()
        )
        await neon_repo.store_question_result(result)
        
        # Verify persistence
        retrieved_session = await neon_repo.get_session("test_session")
        assert retrieved_session.session_id == "test_session"
        
        results = await neon_repo.get_session_results("test_session")
        assert len(results) == 1
        assert results[0].score == 85
        
    finally:
        await mongo_repo.close()
        await neon_repo.close()
        await cache_service.close()
```

**End-to-End Tests** (Playwright):
- Test user journey: permissions → interview → completion
- Test voice input and transcript display
- Test text fallback when voice fails
- Test session persistence across page reloads
- Test report generation and display

### Performance Testing

**Latency Benchmarks:**
- MongoDB query response time: <500ms (p95)
- NeonDB query response time: <300ms (p95)
- Redis cache hit: <50ms (p95)
- STT transcription latency: <1s (real-time)
- TTS audio generation: <1.5s (p95)
- Answer evaluation: <2s (p95)
- End-to-end question cycle: <5s (p95)

**Load Testing:**
- Concurrent interview sessions: 100 users
- MongoDB connection pool: 50 connections
- NeonDB connection pool: 20 connections
- API rate limits: 10 requests/second per user

**Performance Test Example:**
```python
import asyncio
import time

@pytest.mark.asyncio
async def test_concurrent_sessions_performance():
    """Test system handles 100 concurrent sessions."""
    mongo_repo = MongoQuestionRepository(MONGO_URI)
    
    async def simulate_session():
        start = time.time()
        questions = await mongo_repo.get_questions_by_category(
            "software", "medium", 10
        )
        latency = time.time() - start
        return latency, len(questions)
    
    # Simulate 100 concurrent sessions
    tasks = [simulate_session() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    latencies = [r[0] for r in results]
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    
    assert p95_latency < 0.5  # 500ms
    assert all(r[1] == 10 for r in results)  # All got 10 questions
    
    await mongo_repo.close()
```

### Property-Based Testing

Property-based tests will be configured to run a minimum of 100 iterations per property to ensure comprehensive coverage through randomization. Each test will be tagged with the format: **Feature: voice-ai-interview-system, Property {number}: {property_text}**

**Example Property Test:**
```python
from hypothesis import given, strategies as st
import pytest

@given(
    category=st.sampled_from(["software", "hr", "leetcode"]),
    difficulty=st.sampled_from(["easy", "medium", "hard"]),
    limit=st.integers(min_value=1, max_value=50)
)
@pytest.mark.asyncio
async def test_query_result_filtering_property(category, difficulty, limit):
    """
    Property 3: Query Result Filtering
    For any query with category, difficulty filters, all returned questions
    should match the specified filter criteria.
    
    Feature: voice-ai-interview-system, Property 3: Query Result Filtering
    """
    mongo_repo = MongoQuestionRepository(MONGO_URI)
    
    questions = await mongo_repo.get_questions_by_category(
        category, difficulty, limit
    )
    
    # Property: All results match filters
    assert all(q.category == category for q in questions)
    assert all(q.difficulty == difficulty for q in questions)
    assert len(questions) <= limit
    
    await mongo_repo.close()
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Dataset Migration Properties

**Property 1: Data Migration Completeness**
*For any* valid dataset file (CSV or JSON), migrating it to MongoDB should result in all records being inserted into the appropriate collection with no data loss.
**Validates: Requirements 1.3, 1.4, 1.5**

**Property 2: Migration Idempotence**
*For any* dataset, running the migration multiple times should produce the same final state in MongoDB (upsert behavior prevents duplicates).
**Validates: Requirements 1.3, 1.4, 1.5**

**Property 3: Query Result Filtering**
*For any* query with category, difficulty, or topic filters, all returned questions should match the specified filter criteria.
**Validates: Requirements 1.8**

**Property 4: Migration Error Logging**
*For any* migration failure, the system should log error details and halt the migration process without partial data corruption.
**Validates: Requirements 1.7**

### Voice Interface Properties

**Property 5: Text-to-Speech Consistency**
*For any* AI-generated text (greeting, question, or feedback), the Text_To_Speech_Service should be invoked to convert it to audio.
**Validates: Requirements 4.2, 4.5, 6.8**

**Property 6: Speech-to-Text Transcription**
*For any* audio input from the user, the Speech_Recognition_Service should produce a text transcript that is displayed in real-time.
**Validates: Requirements 5.2, 5.3**

**Property 7: Answer Submission Completeness**
*For any* submitted answer (voice or text), the system should send it to the Answer_Evaluator with all required context (question, user_id, session_id).
**Validates: Requirements 5.7**

### Answer Evaluation Properties

**Property 8: Answer Evaluation Consistency**
*For any* submitted answer, the Interview_Agent should use Anthropic Claude to evaluate both completeness and relevance, returning one of four actions: CONTINUE, NEXT, HINT, or ENCOURAGE.
**Validates: Requirements 6.2, 6.3**

**Property 9: Semantic Matching**
*For any* answer and question pair, the Embedding_Service should generate embeddings and compute semantic similarity to assess topic relevance.
**Validates: Requirements 6.4**

**Property 10: Follow-up Question Limiting**
*For any* original question, the system should generate at most 2 follow-up questions before proceeding to the next question.
**Validates: Requirements 6.10**

**Property 11: Context Preservation**
*For any* follow-up question evaluation, the system should include the original answer and all previous follow-up answers in the evaluation context.
**Validates: Requirements 6.9**

### Session Management Properties

**Property 12: Session Data Persistence**
*For any* interview action (question asked, answer submitted, evaluation completed), the corresponding data should be stored in MongoDB with correct timestamps and associations.
**Validates: Requirements 7.3, 7.4, 7.5**

**Property 13: Question-Answer Ordering**
*For any* completed interview session, the stored questions and answers should maintain their chronological sequence order.
**Validates: Requirements 7.9**

**Property 14: Audio Recording Consent**
*For any* user response, audio recordings should be stored in MongoDB if and only if the user has provided consent.
**Validates: Requirements 7.8**

### Error Handling Properties

**Property 15: Service Failure Graceful Degradation**
*For any* external service failure (Deepgram, ElevenLabs, Anthropic), the system should fall back to an alternative mode (text-only, heuristic evaluation) and notify the user.
**Validates: Requirements 8.3, 8.4, 8.7, 8.8**

**Property 16: Retry with Exponential Backoff**
*For any* Anthropic API failure, the system should retry the request up to 3 times with exponential backoff (1s, 2s, 4s) before falling back to heuristic evaluation.
**Validates: Requirements 8.2**

**Property 17: Offline Session Persistence**
*For any* network disconnection during an interview, the current session state should be saved to localStorage and synced to MongoDB when connection is restored.
**Validates: Requirements 8.5, 8.6**

**Property 18: Error Logging Completeness**
*For any* error that occurs, the system should log the error with sufficient context (timestamp, user_id, session_id, error type, stack trace) for debugging.
**Validates: Requirements 8.9**

**Property 19: User-Friendly Error Messages**
*For any* error displayed to the user, the message should be user-friendly and should not expose technical details (API keys, stack traces, internal paths).
**Validates: Requirements 8.10**

### Performance Properties

**Property 20: Answer Evaluation Latency**
*For any* submitted answer, the Answer_Evaluator should return evaluation results within 2 seconds (p95).
**Validates: Requirements 9.1**

**Property 21: Question Retrieval Latency**
*For any* question request, the Question_Repository should return the question from MongoDB within 500 milliseconds (p95).
**Validates: Requirements 9.2**

**Property 22: Question Preloading**
*For any* interview session, the system should fetch the next question while the user is answering the current question to minimize wait time.
**Validates: Requirements 9.5**

**Property 23: Audio Response Caching**
*For any* repeated AI response text (e.g., standard feedback messages), the system should use cached audio instead of calling the TTS API again.
**Validates: Requirements 9.6**

### Security Properties

**Property 24: Input Sanitization**
*For any* user input sent to AI services, the system should sanitize the input to remove potentially malicious content (SQL injection, XSS, prompt injection).
**Validates: Requirements 10.6**

**Property 25: Authentication Enforcement**
*For any* interview session start request, the system should validate user authentication and reject unauthenticated requests with a 401 status code.
**Validates: Requirements 10.3**

**Property 26: Rate Limiting Enforcement**
*For any* user, the system should enforce a rate limit of 10 interview sessions per day and reject additional requests with a 429 status code.
**Validates: Requirements 10.7**

**Property 27: API Call Audit Logging**
*For any* API call to external services (Anthropic, Deepgram, ElevenLabs, Gemini), the system should log the call details (timestamp, service, endpoint, user_id, session_id) for audit purposes.
**Validates: Requirements 10.8**

**Property 28: Data Retention Policy**
*For any* audio recording older than 90 days, the system should automatically delete it from MongoDB to comply with data retention policies.
**Validates: Requirements 10.9**
