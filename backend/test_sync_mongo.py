import os
from pymongo import MongoClient

uri = os.getenv("MONGODB_URI") or "mongodb+srv://maruthirp432_db_user:0Yk4V4yUQnhHPRrJ@cluster0.aa1mbrf.mongodb.net/?appName=Cluster0"

print(f"Testing MongoDB connection to: {uri[:25]}...")

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client["RoundZero"]
    # Quick write test
    result = db.logs.insert_one({"name": "sync_test", "message": "hello world"})
    print(f"Inserted document with ID: {result.inserted_id}")
    
    # Read test
    count = db.logs.count_documents({"name": "sync_test"})
    print(f"Found {count} sync_test logs.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
finally:
    client.close()
