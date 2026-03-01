"""
MongoDB Connection Manager with optimized connection pooling.

This module provides a singleton MongoDB client with proper connection
pooling configuration for high-performance async operations.
"""

import logging
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoConnectionManager:
    """
    Singleton MongoDB connection manager with connection pooling.
    
    Features:
    - Connection pooling (min: 10, max: 50)
    - Connection timeout: 5 seconds
    - Automatic reconnection
    - Health check support
    """
    
    _instance: Optional['MongoConnectionManager'] = None
    _client: Optional[AsyncIOMotorClient] = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection manager (only once)."""
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MongoDB client with connection pooling."""
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        
        # Connection pooling configuration
        self._client = AsyncIOMotorClient(
            mongo_url,
            minPoolSize=10,  # Minimum connections in pool
            maxPoolSize=50,  # Maximum connections in pool
            connectTimeoutMS=5000,  # 5 second connection timeout
            serverSelectionTimeoutMS=5000,  # 5 second server selection timeout
            socketTimeoutMS=30000,  # 30 second socket timeout
            maxIdleTimeMS=60000,  # Close idle connections after 60 seconds
            retryWrites=True,  # Retry write operations on failure
            retryReads=True,  # Retry read operations on failure
            w="majority",  # Write concern: majority
            journal=True  # Wait for journal commit
        )
        
        logger.info(
            f"MongoDB client initialized with connection pooling "
            f"(min: 10, max: 50, timeout: 5s)"
        )
    
    def get_client(self) -> AsyncIOMotorClient:
        """
        Get MongoDB client instance.
        
        Returns:
            AsyncIOMotorClient instance
        """
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def get_database(self, db_name: str = None):
        """
        Get database instance.
        
        Args:
            db_name: Database name (default: from MONGODB_DB_NAME env)
        
        Returns:
            Database instance
        """
        if db_name is None:
            db_name = os.getenv("MONGODB_DB_NAME", "roundzero")
        
        return self.get_client()[db_name]
    
    async def health_check(self) -> bool:
        """
        Check MongoDB connection health.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            client = self.get_client()
            # Ping the server
            await client.admin.command('ping')
            logger.debug("MongoDB health check: OK")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB health check error: {e}")
            return False
    
    async def get_connection_stats(self) -> dict:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with connection pool stats
        """
        try:
            client = self.get_client()
            server_info = await client.server_info()
            
            return {
                "connected": True,
                "version": server_info.get("version", "unknown"),
                "pool_min_size": 10,
                "pool_max_size": 50,
                "connection_timeout_ms": 5000
            }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close MongoDB connection and cleanup resources."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")


# Global instance
_mongo_manager = None


def get_mongo_manager() -> MongoConnectionManager:
    """
    Get global MongoDB connection manager instance.
    
    Returns:
        MongoConnectionManager singleton instance
    """
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoConnectionManager()
    return _mongo_manager


async def get_mongo_client() -> AsyncIOMotorClient:
    """
    Get MongoDB client with connection pooling.
    
    Returns:
        AsyncIOMotorClient instance
    """
    manager = get_mongo_manager()
    return manager.get_client()


async def get_mongo_database(db_name: str = None):
    """
    Get MongoDB database instance.
    
    Args:
        db_name: Database name (default: from environment)
    
    Returns:
        Database instance
    """
    manager = get_mongo_manager()
    return manager.get_database(db_name)
