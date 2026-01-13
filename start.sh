#!/bin/bash
# Startup script for Render deployment
export PORT=${PORT:-8001}
echo "Starting server on port $PORT"
uvicorn main:app --host 0.0.0.0 --port $PORT
