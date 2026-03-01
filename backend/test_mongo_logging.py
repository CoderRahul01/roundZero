import asyncio
import logging
import os
from dotenv import load_dotenv

# Ensure we load env before importing settings
load_dotenv()

from settings import get_settings
from logger import setup_mongo_logging

async def test_logging():
    settings = get_settings()
    if not settings.mongodb_uri:
        print("Mise configured testing: MONGODB_URI is not set in environment.")
        return

    # 1. Setup handler
    print(f"Connecting logger to MongoDB at: {settings.mongodb_uri[:20]}...")
    mongo_handler = setup_mongo_logging(settings.mongodb_uri, "RoundZero")
    
    # 2. Get a test logger attached to root
    test_logger = logging.getLogger("test.mongo_logger")
    test_logger.setLevel(logging.INFO)

    # 3. Start the background worker queue task
    mongo_handler.start_worker()

    # 4. Emit some logs
    print("Emitting test logs...")
    test_logger.info("This is an info log from the integration test.")
    test_logger.warning("This is a warning log to test different levels.")
    
    try:
        1 / 0
    except Exception as e:
        test_logger.error("Testing exception tracebacks in MongoDB", exc_info=True)

    test_logger.info("This is a structured log.", extra={"user_id": "test_user_123", "action": "test"})

    # 5. Wait slightly for flush, then stop the worker gracefully (which flushes the rest)
    print("Stopping worker and flushing logs to DB...")
    await asyncio.sleep(0.5)
    await mongo_handler.stop_worker()
    
    # 6. Verify directly
    print("Verifying logs exist in MongoDB...")
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client["RoundZero"]
    count = await db.logs.count_documents({"name": "test.mongo_logger"})
    print(f"Result: Found {count} test logs in the 'logs' collection.")
    
    if count >= 4:
         print("✅ MongoDB Logging Implementation works perfectly!")
    else:
         print("❌ MongoDB Logging Verification failed - some logs are missing.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_logging())
