from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None # pyright: ignore[reportInvalidTypeForm]
    database = None
    fs = None  # GridFS placeholder if you add it later

    @classmethod
    async def connect_to_mongo(cls):
        """Connect to MongoDB (Render + Atlas safe)"""
        mongo_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("MONGODB_DATABASE", "emotion_recognition")

        if not mongo_url:
            logger.warning("MONGODB_URL not set. MongoDB features disabled.")
            return

        try:
            # IMPORTANT:
            # - TLS is handled via the connection string (?tls=true)
            # - Do NOT pass tls / ssl flags here
            cls.client = AsyncIOMotorClient(
                mongo_url,
                serverSelectionTimeoutMS=10000,
                maxPoolSize=10,
                minPoolSize=1,
                retryWrites=True
            )

            # Hard check — this will fail if TLS/auth/DNS is wrong
            await cls.client.admin.command("ping")

            cls.database = cls.client[database_name]
            logger.info(f"MongoDB connected successfully → DB: {database_name}")

        except Exception as e:
            logger.error(f"MongoDB connection FAILED: {e}")
            cls.client = None
            cls.database = None
            return  # ⬅️ critical: stop execution on failure

    @classmethod
    async def close_mongo_connection(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.database = None
            logger.info("MongoDB connection closed")

    @classmethod
    def get_database(cls):
        """Get database instance"""
        if cls.database is None:
            raise ConnectionError("MongoDB not connected. Check MONGODB_URL.")
        return cls.database

    @classmethod
    def get_gridfs(cls):
        """Get GridFS instance"""
        if cls.fs is None:
            raise ConnectionError("GridFS not initialized.")
        return cls.fs


# =========================
# Collections
# =========================

PREDICTIONS_COLLECTION = "predictions"
AUDIO_FILES_COLLECTION = "audio_files"
ANALYTICS_COLLECTION = "analytics"

# =========================
# Index definitions
# =========================

INDEXES = [
    # Predictions
    (PREDICTIONS_COLLECTION, [("user_id", 1)]),
    (PREDICTIONS_COLLECTION, [("created_at", -1)]),
    (PREDICTIONS_COLLECTION, [("emotion", 1)]),
    (PREDICTIONS_COLLECTION, [("model_type", 1)]),

    # Audio files
    (AUDIO_FILES_COLLECTION, [("user_id", 1)]),
    (AUDIO_FILES_COLLECTION, [("uploaded_at", -1)]),
    (AUDIO_FILES_COLLECTION, [("filename", 1)]),

    # Analytics
    (ANALYTICS_COLLECTION, [("timestamp", -1)]),
    (ANALYTICS_COLLECTION, [("metric_type", 1)]),
]


async def create_indexes():
    """Create database indexes for performance"""
    if MongoDB.database is None:
        logger.warning("Skipping index creation: MongoDB not connected")
        return

    db = MongoDB.get_database()

    for collection, index in INDEXES:
        try:
            existing_indexes = await db[collection].index_information()
            index_name = f"{index[0][0]}_{index[0][1]}"

            if index_name not in existing_indexes:
                await db[collection].create_index(index)
                logger.info(f"Created index on {collection}: {index}")
            else:
                logger.info(f"Index already exists on {collection}: {index}")

        except Exception as e:
            logger.error(f"Failed to create index on {collection}: {e}")
