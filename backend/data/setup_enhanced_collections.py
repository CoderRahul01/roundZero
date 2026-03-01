"""
Setup script for Enhanced Interview Experience MongoDB collections.

Creates collections and indexes for:
- interview_transcripts: Complete interview transcripts with all interactions
- analysis_results: Multi-modal analysis results per question
- follow_up_questions: Follow-up questions with reasoning and answers

Run this script once during deployment to initialize the database schema.
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_enhanced_collections():
    """
    Create MongoDB collections and indexes for enhanced interview experience.
    
    Collections:
    1. interview_transcripts: Stores complete interview transcripts
    2. analysis_results: Stores multi-modal analysis results
    3. follow_up_questions: Stores follow-up questions with reasoning
    """
    
    # Get MongoDB connection URI from environment
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI environment variable not set")
    
    # Initialize Motor client
    client = AsyncIOMotorClient(
        mongo_uri,
        maxPoolSize=50,
        minPoolSize=10,
        serverSelectionTimeoutMS=5000
    )
    
    db = client["RoundZero"]
    
    try:
        # Test connection
        await client.admin.command('ping')
        logger.info("✓ Connected to MongoDB successfully")
        
        # ===== 1. Create interview_transcripts collection =====
        logger.info("Creating interview_transcripts collection...")
        
        # Create collection if it doesn't exist
        if "interview_transcripts" not in await db.list_collection_names():
            await db.create_collection("interview_transcripts")
            logger.info("✓ Created interview_transcripts collection")
        else:
            logger.info("✓ interview_transcripts collection already exists")
        
        # Create indexes for interview_transcripts
        transcripts_collection = db["interview_transcripts"]
        
        # Unique index on session_id
        await transcripts_collection.create_index(
            [("session_id", 1)],
            unique=True,
            name="idx_session_id_unique"
        )
        logger.info("✓ Created unique index on session_id")
        
        # Compound index on user_id and started_at for user history queries
        await transcripts_collection.create_index(
            [("user_id", 1), ("started_at", -1)],
            name="idx_user_history"
        )
        logger.info("✓ Created compound index on user_id and started_at")
        
        # Index on created_at for time-based queries
        await transcripts_collection.create_index(
            [("created_at", -1)],
            name="idx_created_at"
        )
        logger.info("✓ Created index on created_at")
        
        # ===== 2. Create analysis_results collection =====
        logger.info("Creating analysis_results collection...")
        
        # Create collection if it doesn't exist
        if "analysis_results" not in await db.list_collection_names():
            await db.create_collection("analysis_results")
            logger.info("✓ Created analysis_results collection")
        else:
            logger.info("✓ analysis_results collection already exists")
        
        # Create indexes for analysis_results
        analysis_collection = db["analysis_results"]
        
        # Compound index on session_id and question_number for fast retrieval
        await analysis_collection.create_index(
            [("session_id", 1), ("question_number", 1)],
            name="idx_session_question"
        )
        logger.info("✓ Created compound index on session_id and question_number")
        
        # Index on session_id for retrieving all results for a session
        await analysis_collection.create_index(
            [("session_id", 1)],
            name="idx_session_id"
        )
        logger.info("✓ Created index on session_id")
        
        # Index on created_at for time-based queries
        await analysis_collection.create_index(
            [("created_at", -1)],
            name="idx_created_at"
        )
        logger.info("✓ Created index on created_at")
        
        # ===== 3. Create follow_up_questions collection =====
        logger.info("Creating follow_up_questions collection...")
        
        # Create collection if it doesn't exist
        if "follow_up_questions" not in await db.list_collection_names():
            await db.create_collection("follow_up_questions")
            logger.info("✓ Created follow_up_questions collection")
        else:
            logger.info("✓ follow_up_questions collection already exists")
        
        # Create indexes for follow_up_questions
        followup_collection = db["follow_up_questions"]
        
        # Compound index on session_id and main_question_number
        await followup_collection.create_index(
            [("session_id", 1), ("main_question_number", 1)],
            name="idx_session_main_question"
        )
        logger.info("✓ Created compound index on session_id and main_question_number")
        
        # Index on session_id for retrieving all follow-ups for a session
        await followup_collection.create_index(
            [("session_id", 1)],
            name="idx_session_id"
        )
        logger.info("✓ Created index on session_id")
        
        # Index on created_at for time-based queries
        await followup_collection.create_index(
            [("created_at", -1)],
            name="idx_created_at"
        )
        logger.info("✓ Created index on created_at")
        
        logger.info("\n✅ All collections and indexes created successfully!")
        
        # Print collection stats
        logger.info("\n📊 Collection Statistics:")
        for collection_name in ["interview_transcripts", "analysis_results", "follow_up_questions"]:
            collection = db[collection_name]
            count = await collection.count_documents({})
            indexes = await collection.index_information()
            logger.info(f"  {collection_name}:")
            logger.info(f"    - Documents: {count}")
            logger.info(f"    - Indexes: {len(indexes)}")
            for index_name in indexes.keys():
                logger.info(f"      • {index_name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating collections: {e}")
        raise
    finally:
        client.close()
        logger.info("\n✓ Closed MongoDB connection")


async def verify_collections():
    """Verify that all collections and indexes exist."""
    
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI environment variable not set")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client["RoundZero"]
    
    try:
        required_collections = [
            "interview_transcripts",
            "analysis_results",
            "follow_up_questions"
        ]
        
        existing_collections = await db.list_collection_names()
        
        logger.info("\n🔍 Verification Results:")
        all_exist = True
        
        for collection_name in required_collections:
            exists = collection_name in existing_collections
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {collection_name}")
            
            if exists:
                collection = db[collection_name]
                indexes = await collection.index_information()
                logger.info(f"    Indexes: {list(indexes.keys())}")
            
            all_exist = all_exist and exists
        
        if all_exist:
            logger.info("\n✅ All required collections exist!")
        else:
            logger.warning("\n⚠️  Some collections are missing!")
        
        return all_exist
        
    finally:
        client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Enhanced Interview Experience - MongoDB Setup")
    print("=" * 60)
    print()
    
    # Create collections and indexes
    asyncio.run(create_enhanced_collections())
    
    print()
    print("=" * 60)
    print("Verifying Setup")
    print("=" * 60)
    print()
    
    # Verify setup
    asyncio.run(verify_collections())
