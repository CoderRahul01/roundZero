"""
MongoDB Index Creation Utility

This module provides functions to create and verify MongoDB indexes for optimal
query performance in the Vision Agents integration.

Requirements: 8.17, 8.18

Indexes Created:
1. Unique index on live_sessions.session_id
2. Compound index on live_sessions (candidate_id, started_at)
3. Index on live_sessions.started_at for time-based queries
4. Compound index on question_results (session_id, timestamp)
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Dict, List, Optional
import logging


logger = logging.getLogger(__name__)


async def create_live_sessions_indexes(db: AsyncIOMotorDatabase) -> Dict[str, str]:
    """
    Create indexes for the live_sessions collection.
    
    Indexes:
    1. Unique index on session_id - ensures session uniqueness
    2. Compound index on (candidate_id, started_at) - optimizes candidate session queries
    3. Index on started_at - optimizes time-based queries
    
    Args:
        db: AsyncIOMotorDatabase instance
        
    Returns:
        Dict mapping index description to index name
        
    Requirements: 8.17, 8.18
    """
    collection = db["live_sessions"]
    created_indexes = {}
    
    try:
        # 1. Unique index on session_id
        index_name = await collection.create_index(
            "session_id",
            unique=True,
            name="session_id_unique"
        )
        created_indexes["session_id_unique"] = index_name
        logger.info(f"Created unique index on live_sessions.session_id: {index_name}")
        
        # 2. Compound index on (candidate_id, started_at)
        # Optimizes queries like: find sessions by candidate, sorted by date
        index_name = await collection.create_index(
            [("candidate_id", 1), ("started_at", -1)],
            name="candidate_started_compound"
        )
        created_indexes["candidate_started_compound"] = index_name
        logger.info(f"Created compound index on live_sessions (candidate_id, started_at): {index_name}")
        
        # 3. Index on started_at for time-based queries
        # Optimizes queries like: find sessions in date range
        index_name = await collection.create_index(
            "started_at",
            name="started_at_index"
        )
        created_indexes["started_at_index"] = index_name
        logger.info(f"Created index on live_sessions.started_at: {index_name}")
        
        logger.info(f"Successfully created {len(created_indexes)} indexes for live_sessions collection")
        return created_indexes
        
    except Exception as e:
        logger.error(f"Error creating live_sessions indexes: {e}")
        raise


async def create_question_results_indexes(db: AsyncIOMotorDatabase) -> Dict[str, str]:
    """
    Create indexes for the question_results collection.
    
    Indexes:
    1. Compound index on (session_id, timestamp) - optimizes session timeline queries
    
    Args:
        db: AsyncIOMotorDatabase instance
        
    Returns:
        Dict mapping index description to index name
        
    Requirements: 8.17, 8.18
    """
    collection = db["question_results"]
    created_indexes = {}
    
    try:
        # Compound index on (session_id, timestamp)
        # Optimizes queries like: find all questions for a session, sorted by time
        index_name = await collection.create_index(
            [("session_id", 1), ("timestamp", 1)],
            name="session_timestamp_compound"
        )
        created_indexes["session_timestamp_compound"] = index_name
        logger.info(f"Created compound index on question_results (session_id, timestamp): {index_name}")
        
        logger.info(f"Successfully created {len(created_indexes)} indexes for question_results collection")
        return created_indexes
        
    except Exception as e:
        logger.error(f"Error creating question_results indexes: {e}")
        raise


async def create_all_indexes(db: AsyncIOMotorDatabase) -> Dict[str, Dict[str, str]]:
    """
    Create all indexes for Vision Agents integration collections.
    
    This function creates indexes for:
    - live_sessions collection
    - question_results collection
    
    Args:
        db: AsyncIOMotorDatabase instance
        
    Returns:
        Dict mapping collection name to dict of created indexes
        
    Example:
        {
            "live_sessions": {
                "session_id_unique": "session_id_unique",
                "candidate_started_compound": "candidate_started_compound",
                "started_at_index": "started_at_index"
            },
            "question_results": {
                "session_timestamp_compound": "session_timestamp_compound"
            }
        }
        
    Requirements: 8.17, 8.18
    """
    logger.info("Creating all indexes for Vision Agents integration...")
    
    all_indexes = {}
    
    # Create live_sessions indexes
    live_sessions_indexes = await create_live_sessions_indexes(db)
    all_indexes["live_sessions"] = live_sessions_indexes
    
    # Create question_results indexes
    question_results_indexes = await create_question_results_indexes(db)
    all_indexes["question_results"] = question_results_indexes
    
    total_indexes = sum(len(indexes) for indexes in all_indexes.values())
    logger.info(f"Successfully created {total_indexes} total indexes across {len(all_indexes)} collections")
    
    return all_indexes


async def verify_indexes(db: AsyncIOMotorDatabase) -> Dict[str, List[Dict]]:
    """
    Verify that all required indexes exist.
    
    Args:
        db: AsyncIOMotorDatabase instance
        
    Returns:
        Dict mapping collection name to list of index information
        
    Example:
        {
            "live_sessions": [
                {"name": "session_id_unique", "key": [("session_id", 1)], "unique": True},
                {"name": "candidate_started_compound", "key": [("candidate_id", 1), ("started_at", -1)]},
                {"name": "started_at_index", "key": [("started_at", 1)]}
            ],
            "question_results": [
                {"name": "session_timestamp_compound", "key": [("session_id", 1), ("timestamp", 1)]}
            ]
        }
    """
    logger.info("Verifying indexes for Vision Agents integration...")
    
    all_indexes = {}
    
    # Verify live_sessions indexes
    live_sessions_collection = db["live_sessions"]
    live_sessions_indexes = await live_sessions_collection.list_indexes().to_list(length=None)
    all_indexes["live_sessions"] = [
        {
            "name": idx["name"],
            "key": idx["key"],
            "unique": idx.get("unique", False)
        }
        for idx in live_sessions_indexes
        if idx["name"] != "_id_"  # Exclude default _id index
    ]
    
    # Verify question_results indexes
    question_results_collection = db["question_results"]
    question_results_indexes = await question_results_collection.list_indexes().to_list(length=None)
    all_indexes["question_results"] = [
        {
            "name": idx["name"],
            "key": idx["key"],
            "unique": idx.get("unique", False)
        }
        for idx in question_results_indexes
        if idx["name"] != "_id_"  # Exclude default _id index
    ]
    
    # Log verification results
    for collection_name, indexes in all_indexes.items():
        logger.info(f"Collection '{collection_name}' has {len(indexes)} custom indexes:")
        for idx in indexes:
            logger.info(f"  - {idx['name']}: {idx['key']} (unique: {idx['unique']})")
    
    return all_indexes


async def drop_all_indexes(db: AsyncIOMotorDatabase) -> Dict[str, int]:
    """
    Drop all custom indexes (excluding _id index).
    
    WARNING: This function drops all custom indexes. Use with caution!
    Typically used for testing or index recreation.
    
    Args:
        db: AsyncIOMotorDatabase instance
        
    Returns:
        Dict mapping collection name to number of indexes dropped
    """
    logger.warning("Dropping all custom indexes for Vision Agents integration...")
    
    dropped_counts = {}
    
    # Drop live_sessions indexes
    live_sessions_collection = db["live_sessions"]
    live_sessions_indexes = await live_sessions_collection.list_indexes().to_list(length=None)
    dropped = 0
    for idx in live_sessions_indexes:
        if idx["name"] != "_id_":  # Don't drop default _id index
            await live_sessions_collection.drop_index(idx["name"])
            logger.info(f"Dropped index: {idx['name']} from live_sessions")
            dropped += 1
    dropped_counts["live_sessions"] = dropped
    
    # Drop question_results indexes
    question_results_collection = db["question_results"]
    question_results_indexes = await question_results_collection.list_indexes().to_list(length=None)
    dropped = 0
    for idx in question_results_indexes:
        if idx["name"] != "_id_":  # Don't drop default _id index
            await question_results_collection.drop_index(idx["name"])
            logger.info(f"Dropped index: {idx['name']} from question_results")
            dropped += 1
    dropped_counts["question_results"] = dropped
    
    total_dropped = sum(dropped_counts.values())
    logger.warning(f"Dropped {total_dropped} total indexes across {len(dropped_counts)} collections")
    
    return dropped_counts


# CLI usage example
if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        """Main function for CLI usage."""
        # Get MongoDB connection string from environment
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "roundzero")
        
        logger.info(f"Connecting to MongoDB: {mongodb_uri}")
        logger.info(f"Database: {database_name}")
        
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[database_name]
        
        try:
            # Create all indexes
            created_indexes = await create_all_indexes(db)
            
            print("\n" + "="*60)
            print("INDEXES CREATED SUCCESSFULLY")
            print("="*60)
            
            for collection_name, indexes in created_indexes.items():
                print(f"\n{collection_name}:")
                for desc, name in indexes.items():
                    print(f"  ✓ {desc}: {name}")
            
            # Verify indexes
            print("\n" + "="*60)
            print("VERIFYING INDEXES")
            print("="*60)
            
            verified_indexes = await verify_indexes(db)
            
            for collection_name, indexes in verified_indexes.items():
                print(f"\n{collection_name} ({len(indexes)} indexes):")
                for idx in indexes:
                    unique_str = " [UNIQUE]" if idx["unique"] else ""
                    print(f"  ✓ {idx['name']}: {idx['key']}{unique_str}")
            
            print("\n" + "="*60)
            print("INDEX CREATION COMPLETE")
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error in main: {e}")
            raise
        finally:
            # Close MongoDB connection
            client.close()
            logger.info("MongoDB connection closed")
    
    # Run main function
    asyncio.run(main())
