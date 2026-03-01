from motor.motor_asyncio import AsyncIOMotorClient
import logging
import asyncio
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class MongoLogRepository:
    """
    Async repository for writing application logs to MongoDB.
    Uses connection pooling.
    """
    
    def __init__(self, connection_uri: str, database_name: str = "RoundZero"):
        self.client = AsyncIOMotorClient(
            connection_uri,
            maxPoolSize=10, # dedicated small pool for logging
            minPoolSize=2,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[database_name]
        self.logs_collection = self.db["logs"]
        
    async def create_indexes(self):
        """Create indexes on the logs collection for timestamp, level, and logger name."""
        try:
            await self.logs_collection.create_index([("timestamp", -1)])
            await self.logs_collection.create_index([("level", 1)])
            await self.logs_collection.create_index([("name", 1)])
        except Exception as e:
            logger.warning(f"Index creation warning for logs: {e}")

    async def insert_log(self, log_record: dict) -> None:
        """
        Insert a single log record. Wait briefly for operation to complete.
        """
        try:
            # Ensure timestamp is a datetime object
            if "timestamp" in log_record and isinstance(log_record["timestamp"], str):
                 log_record["timestamp"] = datetime.fromisoformat(log_record["timestamp"].replace('Z', '+00:00'))
            else:
                 log_record["timestamp"] = datetime.now(timezone.utc)
                 
            await self.logs_collection.insert_one(log_record)
        except Exception as e:
            # We don't want the logger itself to spam exceptions if it can't write
            # We will fallback to printing to stderr
            import sys
            print(f"[MongoLogRepository Error] Failed to insert log: {e}", file=sys.stderr)

    async def insert_logs_batch(self, log_records: list[dict]) -> None:
        """
        Insert a batch of log records.
        """
        if not log_records:
             return
             
        for record in log_records:
            if "timestamp" in record and isinstance(record["timestamp"], str):
                 record["timestamp"] = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
            elif "timestamp" not in record:
                 record["timestamp"] = datetime.now(timezone.utc)

        try:
            await self.logs_collection.insert_many(log_records, ordered=False)
        except Exception as e:
            import sys
            print(f"[MongoLogRepository Error] Failed to insert log batch: {e}", file=sys.stderr)

    async def close(self):
        self.client.close()
