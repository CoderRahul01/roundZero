"""
Dataset Migration Service for MongoDB.

Migrates interview question datasets from CSV/JSON files to MongoDB Atlas.
Uses async operations with Motor for high performance.
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionSchema(BaseModel):
    """Pydantic model for question validation during migration."""
    id: str
    question: str
    ideal_answer: str = ""
    category: str = "General"
    difficulty: str = "medium"
    source: str
    topics: list[str] = Field(default_factory=list)


class DatasetMigrator:
    """
    Handles async migration of interview question datasets to MongoDB.
    
    Features:
    - Async bulk operations for performance
    - Batch processing for large datasets
    - Upsert operations for idempotency
    - Progress logging
    """
    
    def __init__(self, mongodb_uri: str, database_name: str = "RoundZero"):
        """
        Initialize migrator with MongoDB connection.
        
        Args:
            mongodb_uri: MongoDB connection string
            database_name: Target database name
        """
        self.client = AsyncIOMotorClient(
            mongodb_uri,
            maxPoolSize=50,
            minPoolSize=10
        )
        self.db = self.client[database_name]
        logger.info(f"Initialized DatasetMigrator for database: {database_name}")
    
    async def migrate_software_questions(self, csv_path: Path) -> int:
        """
        Migrate Software Questions.csv to MongoDB.
        Uses bulk operations for performance.
        
        Args:
            csv_path: Path to Software Questions CSV file
        
        Returns:
            Number of questions migrated
        """
        logger.info(f"Migrating software questions from {csv_path}")
        collection = self.db["software_questions"]
        questions = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    question = {
                        "id": f"sw_{idx}",
                        "question": row.get("Question", "").strip(),
                        "ideal_answer": row.get("Answer", "").strip(),
                        "category": row.get("Category", "General Programming").strip(),
                        "difficulty": row.get("Difficulty", "Medium").strip().lower(),
                        "source": "Software Questions CSV",
                        "topics": []  # Can be enhanced later
                    }
                    
                    # Validate with Pydantic
                    validated = QuestionSchema(**question)
                    questions.append(validated.model_dump())
            
            if not questions:
                logger.warning("No questions found in Software Questions CSV")
                return 0
            
            # Bulk upsert for idempotency
            from pymongo import ReplaceOne
            operations = [
                ReplaceOne(
                    filter={"id": q["id"]},
                    replacement=q,
                    upsert=True
                )
                for q in questions
            ]
            
            result = await collection.bulk_write(operations)
            count = result.upserted_count + result.modified_count
            logger.info(f"✅ Migrated {count} software questions")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error migrating software questions: {e}")
            raise
    
    async def migrate_hr_questions(self, json_path: Path) -> int:
        """
        Migrate hr_interview_questions_dataset.json to MongoDB.
        Uses streaming for large files.
        
        Args:
            json_path: Path to HR questions JSON file
        
        Returns:
            Number of questions migrated
        """
        logger.info(f"Migrating HR questions from {json_path}")
        collection = self.db["hr_questions"]
        
        try:
            # Check file size
            file_size_mb = json_path.stat().st_size / (1024 * 1024)
            logger.info(f"HR questions file size: {file_size_mb:.2f} MB")
            
            # For large files, use ijson for streaming
            if file_size_mb > 10:
                return await self._migrate_hr_questions_streaming(json_path, collection)
            else:
                return await self._migrate_hr_questions_standard(json_path, collection)
                
        except Exception as e:
            logger.error(f"❌ Error migrating HR questions: {e}")
            raise

    
    async def _migrate_hr_questions_standard(self, json_path: Path, collection) -> int:
        """Standard migration for smaller JSON files."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = []
        for idx, item in enumerate(data, start=1):
            question = {
                "id": f"hr_{idx}",
                "question": item.get("question", "").strip(),
                "ideal_answer": item.get("ideal_answer", item.get("answer", "")).strip(),
                "category": item.get("category", "HR").strip(),
                "difficulty": item.get("difficulty", "medium").strip().lower(),
                "source": "HR Questions JSON",
                "topics": item.get("topics", []) if isinstance(item.get("topics"), list) else []
            }
            
            validated = QuestionSchema(**question)
            questions.append(validated.model_dump())
        
        operations = [
            ReplaceOne(
                filter={"id": q["id"]},
                replacement=q,
                upsert=True
            )
            for q in questions
        ]
        
        result = await collection.bulk_write(operations)
        count = result.upserted_count + result.modified_count
        logger.info(f"✅ Migrated {count} HR questions")
        return count
    
    async def _migrate_hr_questions_streaming(self, json_path: Path, collection) -> int:
        """Streaming migration for large JSON files using ijson."""
        import ijson
        
        batch_size = 1000
        questions = []
        total_migrated = 0
        idx = 0
        
        logger.info("Using streaming mode for large HR questions file...")
        logger.info("This may take several minutes for a 1.1GB file...")
        
        with open(json_path, 'rb') as f:
            # Stream parse the JSON array
            parser = ijson.items(f, 'item')
            
            for item in parser:
                idx += 1
                
                # Progress indicator every 10000 questions
                if idx % 10000 == 0:
                    logger.info(f"Processing question {idx}...")
                
                question = {
                    "id": f"hr_{idx}",
                    "question": item.get("question", "").strip(),
                    "ideal_answer": item.get("ideal_answer", item.get("answer", "")).strip(),
                    "category": item.get("category", "HR").strip(),
                    "difficulty": item.get("difficulty", "medium").strip().lower(),
                    "source": "HR Questions JSON",
                    "topics": item.get("topics", []) if isinstance(item.get("topics"), list) else []
                }
                
                try:
                    validated = QuestionSchema(**question)
                    questions.append(validated.model_dump())
                except Exception as e:
                    logger.warning(f"Skipping invalid question at index {idx}: {e}")
                    continue
                
                # Batch insert when batch size reached
                if len(questions) >= batch_size:
                    from pymongo import ReplaceOne
                    operations = [
                        ReplaceOne(
                            filter={"id": q["id"]},
                            replacement=q,
                            upsert=True
                        )
                        for q in questions
                    ]
                    
                    result = await collection.bulk_write(operations)
                    batch_count = result.upserted_count + result.modified_count
                    total_migrated += batch_count
                    logger.info(f"Migrated batch: {batch_count} questions (Total: {total_migrated})")
                    questions = []
        
        # Insert remaining questions
        if questions:
            from pymongo import ReplaceOne
            operations = [
                ReplaceOne(
                    filter={"id": q["id"]},
                    replacement=q,
                    upsert=True
                )
                for q in questions
            ]
            
            result = await collection.bulk_write(operations)
            batch_count = result.upserted_count + result.modified_count
            total_migrated += batch_count
        
        logger.info(f"✅ Migrated {total_migrated} HR questions")
        return total_migrated
    
    async def migrate_leetcode_questions(self, csv_path: Path) -> int:
        """
        Migrate leetcode_dataset - lc.csv to MongoDB.
        Uses streaming for large datasets.
        
        Args:
            csv_path: Path to LeetCode CSV file
        
        Returns:
            Number of questions migrated
        """
        logger.info(f"Migrating LeetCode questions from {csv_path}")
        collection = self.db["leetcode_questions"]
        batch_size = 1000
        questions = []
        total_migrated = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for idx, row in enumerate(reader, start=1):
                    # Extract topics from related_topics field
                    topics_str = row.get("related_topics", "")
                    topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else []
                    
                    question = {
                        "id": f"lc_{row.get('id', idx)}",
                        "question": f"{row.get('title', '')}: {row.get('description', '')}".strip(),
                        "ideal_answer": "",  # LeetCode doesn't provide ideal answers
                        "category": "LeetCode",
                        "difficulty": row.get("difficulty", "medium").strip().lower(),
                        "source": "LeetCode CSV",
                        "topics": topics
                    }
                    
                    try:
                        validated = QuestionSchema(**question)
                        questions.append(validated.model_dump())
                    except Exception as e:
                        logger.warning(f"Skipping invalid question at index {idx}: {e}")
                        continue
                    
                    # Batch insert
                    if len(questions) >= batch_size:
                        from pymongo import ReplaceOne
                        operations = [
                            ReplaceOne(
                                filter={"id": q["id"]},
                                replacement=q,
                                upsert=True
                            )
                            for q in questions
                        ]
                        
                        result = await collection.bulk_write(operations)
                        batch_count = result.upserted_count + result.modified_count
                        total_migrated += batch_count
                        logger.info(f"Migrated batch: {batch_count} questions (Total: {total_migrated})")
                        questions = []
            
            # Insert remaining questions
            if questions:
                from pymongo import ReplaceOne
                operations = [
                    ReplaceOne(
                        filter={"id": q["id"]},
                        replacement=q,
                        upsert=True
                    )
                    for q in questions
                ]
                
                result = await collection.bulk_write(operations)
                batch_count = result.upserted_count + result.modified_count
                total_migrated += batch_count
            
            logger.info(f"✅ Migrated {total_migrated} LeetCode questions")
            return total_migrated
            
        except Exception as e:
            logger.error(f"❌ Error migrating LeetCode questions: {e}")
            raise
    
    async def create_indexes(self):
        """
        Create performance indexes on collections.
        Should be called after migration completes.
        """
        logger.info("Creating indexes on MongoDB collections...")
        
        collections = [
            ("software_questions", self.db["software_questions"]),
            ("hr_questions", self.db["hr_questions"]),
            ("leetcode_questions", self.db["leetcode_questions"])
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
                
                logger.info(f"✅ Created indexes for {name} collection")
            except Exception as e:
                logger.warning(f"Index creation warning for {name}: {e}")
    
    async def verify_migration(self) -> dict[str, int]:
        """
        Verify data accessibility and return counts.
        Useful for migration validation.
        
        Returns:
            Dictionary with collection names and document counts
        """
        logger.info("Verifying migration...")
        
        counts = {
            "software_questions": await self.db["software_questions"].count_documents({}),
            "hr_questions": await self.db["hr_questions"].count_documents({}),
            "leetcode_questions": await self.db["leetcode_questions"].count_documents({})
        }
        
        logger.info(f"Verification results: {counts}")
        return counts
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()
        logger.info("Closed MongoDB connection")


async def main():
    """Run migration with async operations."""
    settings = get_settings()
    
    if not settings.mongodb_uri:
        logger.error("❌ MongoDB URI not configured in .env file")
        logger.error("   Please add MONGODB_URI to backend/.env")
        return False
    
    # Define dataset paths
    data_dir = Path(__file__).parent
    software_csv = data_dir / "Software Questions.csv"
    hr_json = data_dir / "hr_interview_questions_dataset.json"
    leetcode_csv = data_dir / "leetcode_dataset - lc.csv"
    
    # Check if files exist
    missing_files = []
    if not software_csv.exists():
        missing_files.append(str(software_csv))
    if not hr_json.exists():
        missing_files.append(str(hr_json))
    if not leetcode_csv.exists():
        missing_files.append(str(leetcode_csv))
    
    if missing_files:
        logger.error(f"❌ Missing dataset files: {missing_files}")
        return False
    
    migrator = DatasetMigrator(
        mongodb_uri=settings.mongodb_uri,
        database_name="RoundZero"
    )
    
    try:
        logger.info("🚀 Starting dataset migration...")
        logger.info("=" * 60)
        
        # Migrate datasets concurrently for better performance
        software_count, hr_count, leetcode_count = await asyncio.gather(
            migrator.migrate_software_questions(software_csv),
            migrator.migrate_hr_questions(hr_json),
            migrator.migrate_leetcode_questions(leetcode_csv)
        )
        
        logger.info("=" * 60)
        logger.info(f"📊 Migration Summary:")
        logger.info(f"   Software Questions: {software_count}")
        logger.info(f"   HR Questions: {hr_count}")
        logger.info(f"   LeetCode Questions: {leetcode_count}")
        logger.info(f"   Total: {software_count + hr_count + leetcode_count}")
        logger.info("=" * 60)
        
        # Create indexes
        logger.info("📑 Creating indexes...")
        await migrator.create_indexes()
        
        # Verify migration
        logger.info("✅ Verifying migration...")
        counts = await migrator.verify_migration()
        
        logger.info("=" * 60)
        logger.info("🎉 Migration completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        await migrator.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)