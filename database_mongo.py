from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None # pyright: ignore[reportInvalidTypeForm]
    database: Optional[object] = None
    fs: Optional[object] = None  # GridFS for large files

    @classmethod
    async def connect_to_mongo(cls):
        """Connect to MongoDB"""
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "emotion_recognition")

        try:
            cls.client = AsyncIOMotorClient(mongo_url)
            # Test the connection
            await cls.client.admin.command('ping')
            cls.database = cls.client[database_name]
            # cls.fs = AsyncIOMotorGridFS(cls.database)  # Temporarily commented out
            logger.info(f"Connected to MongoDB: {database_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def close_mongo_connection(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    def get_database(cls):
        """Get database instance"""
        if cls.database is None:
            raise ConnectionError("MongoDB not connected")
        return cls.database

    @classmethod
    def get_gridfs(cls):
        """Get GridFS instance"""
        if cls.fs is None:
            raise ConnectionError("MongoDB not connected")
        return cls.fs

# Collections
PREDICTIONS_COLLECTION = "predictions"
AUDIO_FILES_COLLECTION = "audio_files"
ANALYTICS_COLLECTION = "analytics"

# Indexes to create
INDEXES = [
    # Predictions collection
    (PREDICTIONS_COLLECTION, [("user_id", 1)]),
    (PREDICTIONS_COLLECTION, [("created_at", -1)]),
    (PREDICTIONS_COLLECTION, [("emotion", 1)]),
    (PREDICTIONS_COLLECTION, [("model_type", 1)]),

    # Audio files collection
    (AUDIO_FILES_COLLECTION, [("user_id", 1)]),
    (AUDIO_FILES_COLLECTION, [("uploaded_at", -1)]),
    (AUDIO_FILES_COLLECTION, [("filename", 1)]),

    # Analytics collection
    (ANALYTICS_COLLECTION, [("timestamp", -1)]),
    (ANALYTICS_COLLECTION, [("metric_type", 1)]),
]

async def create_indexes():
    """Create database indexes for performance"""
    db = MongoDB.get_database()
    for collection, index in INDEXES:
        try:
            await db[collection].create_index(index)
            logger.info(f"Created index on {collection}: {index}")
        except Exception as e:
            logger.error(f"Failed to create index on {collection}: {e}")
