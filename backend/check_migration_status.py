"""
Check migration status in MongoDB.
"""

import asyncio
from data.mongo_repository import MongoQuestionRepository
from settings import get_settings


async def check_status():
    """Check current migration status."""
    settings = get_settings()
    
    if not settings.mongodb_uri:
        print("❌ MongoDB URI not configured")
        return
    
    repo = MongoQuestionRepository(
        connection_uri=settings.mongodb_uri,
        database_name="RoundZero"
    )
    
    try:
        print("📊 Checking MongoDB collections...")
        print("=" * 60)
        
        # Check each collection
        collections = [
            ("Software Questions", "software"),
            ("HR Questions", "hr"),
            ("LeetCode Questions", "leetcode")
        ]
        
        total = 0
        for name, category in collections:
            questions = await repo.get_all(category=category, limit=1000000)
            count = len(questions)
            total += count
            print(f"{name}: {count:,} questions")
            
            if count > 0 and count <= 3:
                print(f"  Sample: {questions[0].question[:100]}...")
        
        print("=" * 60)
        print(f"Total Questions: {total:,}")
        
        if total == 0:
            print("\n⚠️  No questions found. Migration has not been run yet.")
            print("   Run: uv run python data/migrate_to_mongodb.py")
        else:
            print(f"\n✅ Database contains {total:,} questions")
        
        await repo.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_status())
