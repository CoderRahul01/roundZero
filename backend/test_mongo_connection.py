"""
Simple script to test MongoDB connection.
Run with: uv run python test_mongo_connection.py
"""

import asyncio
from data.mongo_repository import MongoQuestionRepository
from settings import get_settings


async def test_connection():
    """Test MongoDB connection and basic operations."""
    settings = get_settings()
    
    if not settings.mongodb_uri:
        print("❌ MongoDB URI not configured in .env file")
        print("   Please add MONGODB_URI to backend/.env")
        return False
    
    print(f"🔗 Connecting to MongoDB...")
    print(f"   URI: {settings.mongodb_uri[:20]}...")
    
    try:
        repo = MongoQuestionRepository(
            connection_uri=settings.mongodb_uri,
            database_name="RoundZero"
        )
        
        # Test ping
        print("📡 Testing connection...")
        is_connected = await repo.ping()
        
        if is_connected:
            print("✅ MongoDB connection successful!")
            
            # Test basic query
            print("\n📊 Testing basic query...")
            questions = await repo.get_all(category="software", limit=5)
            print(f"   Found {len(questions)} software questions")
            
            if questions:
                print(f"\n   Sample question:")
                print(f"   ID: {questions[0].id}")
                print(f"   Question: {questions[0].question[:100]}...")
                print(f"   Difficulty: {questions[0].difficulty}")
            else:
                print("   ⚠️  No questions found. Run migration script to populate database.")
            
            # Cleanup
            await repo.close()
            return True
        else:
            print("❌ MongoDB connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
