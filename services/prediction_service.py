import numpy as np
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from database_mongo import MongoDB, PREDICTIONS_COLLECTION
from utils.constants import extractor, svm_model, EMOTION_LABELS

logger = logging.getLogger(__name__)

def get_embedding(spectrogram: np.ndarray) -> np.ndarray:
    """Get prediction from CNN model."""
    if extractor is None:
        raise ValueError("CNN model not loaded. Please ensure the model file 'best_cnn.keras' exists in the models directory and TensorFlow is properly installed.")
    # spectrogram should already be in shape (height, width, channels)
    spectrogram = spectrogram[np.newaxis, ...]  # Add batch dimension
    prediction = extractor.predict(spectrogram)
    return prediction

def predict_emotion(embedding: np.ndarray) -> Dict[str, float]:
    """Extract emotion probabilities from SVM prediction on CNN embedding."""
    if svm_model is None:
        raise ValueError("SVM model not loaded. Please ensure the model file 'best_svm.pkl' exists in the models directory and scikit-learn is properly installed.")

    # Get probabilities from SVM
    probabilities = svm_model.predict_proba(embedding.reshape(1, -1))[0]

    # Return all emotions with their probabilities
    emotion_probabilities = {}
    for i, emotion in enumerate(EMOTION_LABELS):
        if i < len(probabilities):
            emotion_probabilities[emotion] = float(probabilities[i])
        else:
            emotion_probabilities[emotion] = 0.0

    return emotion_probabilities

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

def process_audio_for_prediction(signal: np.ndarray) -> Dict[str, float]:
    """Complete pipeline: generate spectrogram, get embedding, predict emotion."""
    from .audio_service import generate_spectrogram
    spectrogram = generate_spectrogram(signal)
    embedding = get_embedding(spectrogram)
    emotion_probabilities = predict_emotion(embedding)
    return emotion_probabilities

async def process_audio_for_prediction_with_storage(
    signal: np.ndarray,
    user_id: str,
    filename: str,
    audio_duration: Optional[float] = None,
    spectrogram_id: Optional[str] = None,
    features: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Complete pipeline with MongoDB storage: generate spectrogram, get embedding, predict emotion, save result."""
    start_time = time.time()

    from .audio_service import generate_spectrogram
    spectrogram = generate_spectrogram(signal)
    embedding = get_embedding(spectrogram)
    emotion_probabilities = predict_emotion(embedding)

    processing_time = time.time() - start_time

    # Find the primary emotion and its confidence
    primary_emotion = max(emotion_probabilities.items(), key=lambda x: x[1])
    emotion_str = primary_emotion[0]
    confidence = primary_emotion[1]

    # Save to MongoDB
    prediction_id = await save_prediction_to_mongo(
        user_id=user_id,
        filename=filename,
        emotion=emotion_str,
        confidence=confidence,
        audio_duration=audio_duration,
        spectrogram_id=spectrogram_id,
        features=features
    )

    # Update processing time
    await update_prediction_processing_time(prediction_id, processing_time)

    return {
        "prediction_id": prediction_id,
        "emotion": emotion_probabilities,
        "confidence": confidence,
        "processing_time": processing_time
    }
