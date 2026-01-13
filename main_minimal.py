#!/usr/bin/env python3
"""
Minimal FastAPI app for testing authentication endpoints
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middleware.auth import router as auth_router

app = FastAPI(
    title="Emotion Recognition API - Minimal",
    description="Minimal API for testing authentication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Minimal API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
