#!/bin/bash
# Startup script for Render deployment

# Ensure models directory exists
mkdir -p models

# Copy models from Emotion-Dataset if it exists (for deployment)
if [ -d "../Emotion-Dataset" ]; then
    echo "Copying models from Emotion-Dataset to models/"
    cp ../Emotion-Dataset/best_cnn.keras models/ 2>/dev/null || echo "best_cnn.keras not found in Emotion-Dataset"
    cp ../Emotion-Dataset/best_svm.pkl models/ 2>/dev/null || echo "best_svm.pkl not found in Emotion-Dataset"
else
    echo "Emotion-Dataset not found, assuming models are already in models/"
fi

export PORT=${PORT:-8001}
echo "Starting server on port $PORT"
uvicorn main:app --host 0.0.0.0 --port $PORT
