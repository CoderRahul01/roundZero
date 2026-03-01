import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    uri = os.getenv("MONGODB_URI") or "mongodb+srv://maruthirp432_db_user:0Yk4V4yUQnhHPRrJ@cluster0.aa1mbrf.mongodb.net/?appName=Cluster0"
    print(f"Testing async connection to: {uri[:25]}...")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        # The ismaster command is cheap and does not require auth.
        await client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(f"Exception during ping: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
