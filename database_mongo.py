from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None # type: ignore
    database = None
    fs = None  # GridFS for large files

    @classmethod
    async def connect_to_mongo(cls):
        """Connect to MongoDB with Render-compatible SSL settings"""
        mongo_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("MONGODB_DATABASE", "emotion_recognition")
        
        # If no MongoDB URL is set, skip connection but don't fail
        if not mongo_url:
            logger.warning("MONGODB_URL not set. MongoDB features disabled.")
            return
        
        try:
            logger.info(f"Attempting to connect to MongoDB at: {database_name}")
            
            # For Render deployment, we need to allow invalid certificates
            # This is a workaround for Render's network configuration
            connection_params = {
                "tls": True,
                "tlsAllowInvalidCertificates": True,  # Required for Render
                "tlsAllowInvalidHostnames": True,     # Required for Render
                "serverSelectionTimeoutMS": 10000,    # Increased timeout
                "maxPoolSize": 10,
                "minPoolSize": 1,
                "retryWrites": True,
                "w": "majority"
            }
            
            # Use the URL from environment variable
            cls.client = AsyncIOMotorClient(mongo_url, **connection_params)
            
            # Test the connection
            await cls.client.admin.command('ping')
            cls.database = cls.client[database_name]
            
            logger.info(f"✅ Successfully connected to MongoDB: {database_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)[:200]}")  # Limit log length
            cls.client = None
            cls.database = None
            return False

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
            raise ConnectionError("MongoDB not connected. Check MONGODB_URL environment variable.")
        return cls.database

    @classmethod
    def get_gridfs(cls):
        """Get GridFS instance"""
        if cls.fs is None:
            raise ConnectionError("GridFS not initialized. MongoDB may not be connected.")
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
    if MongoDB.database is None:
        logger.warning("Skipping index creation: MongoDB not connected")
        return
    
    db = MongoDB.get_database()
    for collection, index in INDEXES:
        try:
            # Check if index already exists
            existing_indexes = await db[collection].index_information()
            index_name = f"{index[0][0]}_{index[0][1]}"
            
            if index_name not in existing_indexes:
                await db[collection].create_index(index)
                logger.info(f"Created index on {collection}: {index}")
            else:
                logger.info(f"Index already exists on {collection}: {index}")
        except Exception as e:
            logger.error(f"Failed to create index on {collection}: {e}")