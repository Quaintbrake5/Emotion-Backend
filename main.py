import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models
import database
from database_mongo import MongoDB, create_indexes
from routes import audio, user, analytics, export, visualization, admin
from middleware import auth
from middleware.otp_middleware import OTPMiddleware
from middleware.rate_limiting_middleware import RateLimitingMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create all tables at startup
models.Base.metadata.create_all(bind=database.engine)

# Initialize FastAPI app
app = FastAPI(
    title="Emotion Recognition API",
    description="Advanced emotion recognition API with OTP authentication and rate limiting",
    version="2.0.0"
)

# MongoDB connection and setup
@app.on_event("startup")
async def startup_event():
    await MongoDB.connect_to_mongo()
    await create_indexes()
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    await MongoDB.close_mongo_connection()
    logger.info("Application shutdown complete")

# Add custom middleware
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(OTPMiddleware)

# Register route blueprints
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(audio.router, prefix="/audio", tags=["audio"])
app.include_router(user.router, prefix="/users", tags=["user"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(export.router, prefix="/export", tags=["export"])
app.include_router(visualization.router, prefix="/visualization", tags=["visualization"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# Root endpoint
@app.get("/")
def root():
    return {"message": "Welcome to the Emotion Recognition API"}
