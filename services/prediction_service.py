import numpy as np
import time
import logging
import asyncio
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database_mongo import MongoDB, PREDICTIONS_COLLECTION
from utils.constants import EMOTION_LABELS
from gradio_client import Client, handle_file
import aiofiles
import aiofiles.tempfile
import requests

logger = logging.getLogger(__name__)

# Hugging Face Space URL - UPDATE THIS WITH YOUR DEPLOYED SPACE URL
# Use the repository name for the Gradio client (works better than direct URL)
HF_SPACE_URL = "Quaintbrake5/Emotion_Recognition_Model"  # Can also use full URL like "https://quaintbrake5-emotion-recognition-model.hf.space"

# Gradio client instance (lazy initialization)
_gradio_client = None

def get_gradio_client() -> Client:
    """Get or create the Gradio client instance."""
    global _gradio_client
    if _gradio_client is None:
        _gradio_client = Client(HF_SPACE_URL)
    return _gradio_client

async def call_hf_space_prediction(audio_file_path: str) -> Dict[str, float]:
    """Call Hugging Face Space for emotion prediction using Gradio client."""
    client = None
    try:
        # Use Gradio client to make prediction
        # The handle_file function handles both local files and URLs
        client = get_gradio_client()
        
        # Run the prediction in executor to avoid blocking the async event loop
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.predict(
                audio=handle_file(audio_file_path),
                api_name="/process_audio"
            )
        )

        # Check if result is None or empty
        if result is None:
            raise ValueError("Gradio Space returned None. The Space might be busy or not responding properly.")
        
        if result == "" or (isinstance(result, str) and len(result.strip()) == 0):
            raise ValueError("Gradio Space returned an empty response. The Space might be experiencing issues.")

        # Parse the result - it may come as a JSON string or directly as a dict
        import json
        import re
        prediction = None
        
        if isinstance(result, str):
            # Try to parse as JSON
            try:
                prediction = json.loads(result)
            except json.JSONDecodeError as je:
                # If it's not JSON, it might be the raw text output from Gradio
                # In this case, try to extract emotion data from the text
                logger.warning(f"Result is not JSON: {result}")
                
                # Try to parse text format like:
                # Primary Emotion: Angry (44.61%)
                #
                # All Probabilities:
                # Angry: 44.61%
                # Disgust: 19.32%
                # Fear: 10.13%
                # Happy: 15.14%
                # Neutral: 4.21%
                # Sad: 6.59%
                
                # Look for patterns like "Emotion: XX.XX%"
                emotion_pattern = r'(\w+):\s*(\d+\.?\d*)%'
                matches = re.findall(emotion_pattern, result)
                
                if matches:
                    prediction = {}
                    for emotion, prob in matches:
                        # Normalize emotion names
                        emotion_lower = emotion.lower()
                        if emotion_lower == 'angry':
                            prediction['angry'] = float(prob) / 100.0
                        elif emotion_lower == 'disgust':
                            prediction['disgust'] = float(prob) / 100.0
                        elif emotion_lower == 'fear':
                            prediction['fear'] = float(prob) / 100.0
                        elif emotion_lower == 'happy':
                            prediction['happy'] = float(prob) / 100.0
                        elif emotion_lower == 'neutral':
                            prediction['neutral'] = float(prob) / 100.0
                        elif emotion_lower == 'sad':
                            prediction['sad'] = float(prob) / 100.0
                        else:
                            prediction[emotion_lower] = float(prob) / 100.0
                    logger.info(f"Parsed text result to dict: {prediction}")
                
                # If still not parsed, try eval as last resort
                if prediction is None and result.startswith('{') and result.endswith('}'):
                    try:
                        prediction = eval(result)
                    except:
                        pass
                
                # If still not parsed, raise an error with the original result
                if prediction is None:
                    raise ValueError(f"Could not parse Gradio result as JSON: {je}. Raw result: {result[:500]}")
        else:
            prediction = result

        # If still no prediction, raise an error
        if prediction is None:
            raise ValueError(f"Could not parse result: {result}")

        # Check if it's an error response
        if isinstance(prediction, dict) and "error" in prediction:
            raise ValueError(f"Gradio app error: {prediction['error']}")

        # Ensure all emotions are present
        if isinstance(prediction, dict):
            for emotion in EMOTION_LABELS:
                if emotion not in prediction:
                    prediction[emotion] = 0.0
            return prediction
        else:
            # If result is not a dict, raise an error
            raise ValueError(f"Unexpected result format: {type(result)} - {result}")

    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(f"Error calling HF Space: {e}")
        raise ValueError(f"Failed to get prediction from Hugging Face Space: {e}")

# Local model functions removed - now using HF Space for predictions

async def save_prediction_to_mongo(
    user_id: str,
    filename: str,
    emotion: str,
    confidence: float,
    model_type: str = "hybrid",
    audio_duration: Optional[float] = None,
    spectrogram_id: Optional[str] = None,
    features: Optional[Dict[str, Any]] = None,
    model_version: str = "v1.0"
) -> str:
    """Save prediction result to MongoDB."""
    db = MongoDB.get_database()

    prediction_doc = {
        "user_id": user_id,
        "filename": filename,
        "emotion": emotion,
        "confidence": confidence,
        "model_type": model_type,
        "audio_duration": audio_duration,
        "spectrogram_id": spectrogram_id,
        "features": features or {},
        "model_version": model_version,
        "processing_time": None,  # Will be set after processing
        "created_at": datetime.now(datetime.timezone.utc)
    }

    result = await db[PREDICTIONS_COLLECTION].insert_one(prediction_doc)
    logger.info(f"Saved prediction {result.inserted_id} for user {user_id}")
    return str(result.inserted_id)

async def update_prediction_processing_time(prediction_id: str, processing_time: float):
    """Update the processing time for a prediction."""
    if MongoDB.database is None:
        logger.warning("MongoDB not connected. Skipping processing time update.")
        return

    db = MongoDB.get_database()
    await db[PREDICTIONS_COLLECTION].update_one(
        {"_id": prediction_id},
        {"$set": {"processing_time": processing_time}}
    )

async def get_user_predictions(
    user_id: str,
    emotion: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """Get predictions for a user with optional filtering."""
    db = MongoDB.get_database()

    query = {"user_id": user_id}
    if emotion:
        query["emotion"] = emotion

    predictions = await db[PREDICTIONS_COLLECTION].find(query)\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(length=None)

    # Convert ObjectId to string for JSON serialization
    for pred in predictions:
        pred["_id"] = str(pred["_id"])
        if pred.get("spectrogram_id"):
            pred["spectrogram_id"] = str(pred["spectrogram_id"])

    return predictions

async def get_prediction_stats(user_id: str) -> Dict[str, Any]:
    """Get prediction statistics for a user."""
    if MongoDB.database is None:
        logger.warning("MongoDB not connected. Returning empty prediction stats.")
        return {
            "total_predictions": 0,
            "emotions": [],
            "avg_confidence": 0.0,
            "avg_processing_time": 0.0,
            "emotion_distribution": {}
        }

    db = MongoDB.get_database()

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_predictions": {"$sum": 1},
            "emotions": {"$addToSet": "$emotion"},
            "avg_confidence": {"$avg": "$confidence"},
            "avg_processing_time": {"$avg": "$processing_time"},
            "last_prediction": {"$max": "$created_at"}
        }}
    ]

    result = await db[PREDICTIONS_COLLECTION].aggregate(pipeline).to_list(length=1)

    if result:
        stats = result[0]
        stats.pop("_id", None)  # Remove the _id field

        # Get emotion distribution
        emotion_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$emotion", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        emotion_dist = await db[PREDICTIONS_COLLECTION].aggregate(emotion_pipeline).to_list(length=None)
        stats["emotion_distribution"] = {doc["_id"]: doc["count"] for doc in emotion_dist}

        return stats

    return {
        "total_predictions": 0,
        "emotions": [],
        "avg_confidence": 0.0,
        "avg_processing_time": 0.0,
        "emotion_distribution": {}
    }

async def process_audio_for_prediction(signal: np.ndarray) -> Dict[str, float]:
    """Complete pipeline: save audio temporarily, call HF Space, get emotion predictions."""
    # Save audio signal to temporary file asynchronously
    async with aiofiles.tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
        # Save as WAV using soundfile (run synchronously in executor)
        import soundfile as sf
        await asyncio.get_event_loop().run_in_executor(None, sf.write, temp_path, signal, 22050)

    try:
        # Call Hugging Face Space
        emotion_probabilities = await call_hf_space_prediction(temp_path)
        return emotion_probabilities
    finally:
        # Clean up temporary file asynchronously
        if os.path.exists(temp_path):
            await asyncio.get_event_loop().run_in_executor(None, os.unlink, temp_path)

async def process_audio_for_prediction_with_storage(
    signal: np.ndarray,
    user_id: str,
    filename: str,
    audio_duration: Optional[float] = None,
    spectrogram_id: Optional[str] = None,
    features: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Complete pipeline with MongoDB storage: call HF Space for emotion prediction."""
    start_time = time.time()

    # Call HF Space for prediction
    emotion_probabilities = await process_audio_for_prediction(signal)

    processing_time = time.time() - start_time

    # Find the primary emotion and its confidence
    primary_emotion = max(emotion_probabilities.items(), key=lambda x: x[1])
    emotion_str = primary_emotion[0]
    confidence = primary_emotion[1]

    prediction_id = None
    # MongoDB saving removed to ensure predictions work without MongoDB dependency
    # Analytics features that require MongoDB will handle connection checks separately

    return {
        "prediction_id": prediction_id,
        "emotion": emotion_probabilities,
        "confidence": confidence,
        "processing_time": processing_time
    }
