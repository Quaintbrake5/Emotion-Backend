from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from database import get_db
from schema import VoiceRecordingRequest, VoiceRecordingResponse, PredictionResponse
from models import User, Prediction
from middleware.auth import get_current_active_user
from services.audio_service import record_audio, save_audio_temp, cleanup_temp_file, generate_waveform_data
from services.prediction_service import process_audio_for_prediction
from utils.constants import SAMPLE_RATE
from datetime import datetime
import logging
import shutil
import os
import aiofiles
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
EMPTY_FILE_UPLOADED = "Empty file uploaded"

@router.post("/record-voice", response_model=VoiceRecordingResponse)
async def record_and_predict_emotion(
    request: VoiceRecordingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    logger.info(f"Request received: {req.method} {req.url.path} for user {current_user.username}")
    temp_path = None
    try:
        # Record audio from microphone
        duration = request.duration or 3
        recording = record_audio(duration)

        # Save temporary file
        temp_path = save_audio_temp(recording, f"temp_voice_{current_user.id}_{datetime.now().timestamp()}.wav")

        # Check if models are loaded
        from utils.constants import extractor, svm_model
        if extractor is None or svm_model is None:
            logger.error("ML models not loaded - cannot process audio prediction")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable: Machine learning models are not loaded. Please contact support."
            )

        # Process audio and predict emotion
        emotion_probabilities = process_audio_for_prediction(recording)

        # Get the primary emotion (highest probability)
        primary_emotion = max(emotion_probabilities.items(), key=lambda x: x[1])[0]

        # Save prediction to database
        db_prediction = Prediction(
            user_id=current_user.id,
            filename=f"voice_recording_{datetime.now().timestamp()}.wav",
            emotion_dict=emotion_probabilities,
            audio_duration=duration,
            model_type="hybrid"
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)

        logger.info(f"Voice recording prediction completed for user {current_user.username}: {primary_emotion}")
        return VoiceRecordingResponse(
            emotion=primary_emotion,
            audio_duration=duration
        )

    except Exception as e:
        logger.error(f"Voice recording failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice recording failed: {str(e)}")
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)

@router.post("/predict", response_model=PredictionResponse)
async def predict_emotion(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    logger.info(f"Request received: {req.method} {req.url.path} for user {current_user.username}")
    temp_path = None
    try:
        logger.info(f"Audio file info: filename={audio.filename}, content_type={audio.content_type}")

        if not audio.filename:
            logger.error("No filename provided")
            raise HTTPException(status_code=400, detail="No file uploaded")

        # Validate file extension
        allowed_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.webm']
        file_ext = os.path.splitext(audio.filename.lower())[1]
        if file_ext not in allowed_extensions:
            logger.error(f"Unsupported file extension: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
            )

        # Check file size (max 50MB)
        file_size = 0
        content = await audio.read()
        file_size = len(content)

        logger.info(f"File size: {file_size} bytes")

        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")

        if file_size == 0:
            logger.error(EMPTY_FILE_UPLOADED)
            raise HTTPException(status_code=400, detail=EMPTY_FILE_UPLOADED)

        # Save temporary file
        temp_path = f"temp_{audio.filename}"
        async with aiofiles.open(temp_path, "wb") as buffer:
            await buffer.write(content)

        # Verify file was saved correctly
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=500, detail="Failed to save temporary file")

        saved_size = os.path.getsize(temp_path)
        if saved_size != file_size:
            raise HTTPException(status_code=500, detail=f"File size mismatch: expected {file_size}, got {saved_size}")

        logger.info(f"Saved temporary file: {temp_path}, size: {saved_size} bytes")

        # Load and process audio
        from services.audio_service import load_audio
        signal = load_audio(temp_path)

        # Check if audio has content
        if len(signal) == 0:
            raise HTTPException(status_code=400, detail="Audio file appears to be empty or corrupted")

        emotion_probabilities = process_audio_for_prediction(signal)

        # Save prediction to database
        db_prediction = Prediction(
            user_id=current_user.id,
            filename=audio.filename,
            emotion_dict=emotion_probabilities,
            audio_duration=len(signal) / SAMPLE_RATE,
            model_type="hybrid"
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)

        logger.info(f"Audio prediction completed for user {current_user.username}: {emotion_probabilities}")
        return PredictionResponse.from_orm(db_prediction)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio prediction failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)

@router.post("/waveform")
async def get_waveform_data(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    req: Request = None
) -> Dict[str, Any]:
    """Generate waveform data for audio visualization."""
    logger.info(f"Request received: {req.method} {req.url.path} for user {current_user.username}")
    temp_path = None
    try:
        logger.info(f"Audio file info: filename={audio.filename}, content_type={audio.content_type}")

        if not audio.filename:
            logger.error("No filename provided")
            raise HTTPException(status_code=400, detail=EMPTY_FILE_UPLOADED)

        # Validate file extension
        allowed_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.webm']
        file_ext = os.path.splitext(audio.filename.lower())[1]
        if file_ext not in allowed_extensions:
            logger.error(f"Unsupported file extension: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
            )

        # Check file size (max 50MB)
        file_size = 0
        content = await audio.read()
        file_size = len(content)

        logger.info(f"File size: {file_size} bytes")

        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")

        if file_size == 0:
            logger.error("Empty file uploaded")
            raise HTTPException(status_code=400, detail= EMPTY_FILE_UPLOADED)

        # Save temporary file
        temp_path = f"temp_waveform_{audio.filename}"
        async with aiofiles.open(temp_path, "wb") as buffer:
            await buffer.write(content)

        # Verify file was saved correctly
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=500, detail="Failed to save temporary file")

        saved_size = os.path.getsize(temp_path)
        if saved_size != file_size:
            raise HTTPException(status_code=500, detail=f"File size mismatch: expected {file_size}, got {saved_size}")

        logger.info(f"Saved temporary file: {temp_path}, size: {saved_size} bytes")

        # Load and process audio
        from services.audio_service import load_audio
        signal = load_audio(temp_path)

        # Check if audio has content
        if len(signal) == 0:
            raise HTTPException(status_code=400, detail="Audio file appears to be empty or corrupted")

        # Generate waveform data
        waveform_data = generate_waveform_data(signal)

        logger.info(f"Waveform data generated for user {current_user.username}: {len(waveform_data['waveform'])} points")
        return waveform_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Waveform generation failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Waveform generation failed: {str(e)}")
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)
