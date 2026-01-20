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

# Initialize FastAPI app
app = FastAPI(
    title="Emotion Recognition API",
    description="Advanced emotion recognition API with OTP authentication and rate limiting",
    version="2.0.0"
)

# Database initialization at startup
@app.on_event("startup")
async def startup_event():
    # Initialize PostgreSQL tables if DATABASE_URL is available
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            models.Base.metadata.create_all(bind=database.engine)
            logger.info("PostgreSQL tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            logger.warning("PostgreSQL tables not created. User features may not work.")
    else:
        logger.warning("DATABASE_URL not set. PostgreSQL features disabled.")
    
    # Initialize MongoDB connection
    try:
        await MongoDB.connect_to_mongo()
        await create_indexes()
        logger.info("MongoDB connection established and indexes created")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB during startup: {e}")
        logger.warning("Application starting without MongoDB connection. Analytics features may not work.")
    
    logger.info("Application startup complete with dual-database support")

@app.on_event("shutdown")
async def shutdown_event():
    await MongoDB.close_mongo_connection()
    logger.info("Application shutdown complete")

# CORS - Add this first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://emotion-frontend-seven.vercel.app",
        "https://emotion-frontend.vercel.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Add custom middleware
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(OTPMiddleware)

# Register route blueprints
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(audio, prefix="/audio", tags=["audio"])
app.include_router(user, prefix="/users", tags=["user"])
app.include_router(analytics, prefix="/analytics", tags=["analytics"])
app.include_router(export, prefix="/export", tags=["export"])
app.include_router(visualization, prefix="/visualization", tags=["visualization"])
app.include_router(admin, prefix="/admin", tags=["admin"])

# Health check endpoint with dual-database status
@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    status = {
        "status": "healthy", 
        "version": "2.0.0",
        "databases": {
            "postgresql": "connected" if os.getenv("DATABASE_URL") else "not_configured",
            "mongodb": "connected" if MongoDB.database else "not_connected"
        }
    }
    return status

# Root endpoint
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "Welcome to the Emotion Recognition API with dual-database support"}

# Server startup (for local development and deployment)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting server on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )