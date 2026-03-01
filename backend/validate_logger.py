import asyncio
import logging
from logger import setup_mongo_logging

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError as e:
    print(f"ImportError: {e}")
    exit(1)

import os
uri = os.getenv("MONGODB_URI") or "mongodb+srv://maruthirp432_db_user:0Yk4V4yUQnhHPRrJ@cluster0.aa1mbrf.mongodb.net/?appName=Cluster0"

async def test():
    print(f"Starting test script with URI: {uri[:20]}...")
    handler = setup_mongo_logging(uri, "RoundZero")
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    handler.start_worker()
    logger.info("Test message 1 directly through motor")
    
    print("Waiting for queue propagation...")
    await asyncio.sleep(2)
    print("Stopping worker...")
    await handler.stop_worker()

    print("Checking database directly...")
    client = AsyncIOMotorClient(uri)
    db = client["RoundZero"]
    count = await db.logs.count_documents({"name": "test"})
    print(f"DB count for 'test' logger: {count}")
    client.close()

if __name__ == "__main__":
    asyncio.run(test())
