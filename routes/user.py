from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from schema import PredictionResponse, AudioFileResponse, UserStatisticsResponse, UserActivityResponse, PredictionAnalyticsResponse
from models import User, Prediction, AudioFile
from middleware.auth import get_current_active_user
from services.analytics_service import AnalyticsService
from services.visualization_service import (
    get_user_prediction_trends,
    get_emotion_distribution,
    get_user_engagement_metrics
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/me/predictions", response_model=list[PredictionResponse])
async def get_user_predictions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
    skip: int = 0,
    limit: int = 50
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        predictions = db.query(Prediction).filter(
            Prediction.user_id == current_user.id
        ).offset(skip).limit(limit).all()

        logger.info(f"Retrieved {len(predictions)} predictions for user {current_user.username}")
        return predictions
    except Exception as e:
        logger.error(f"Failed to retrieve predictions for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving predictions")

@router.get("/me/audio-files", response_model=list[AudioFileResponse])
async def get_user_audio_files(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
    skip: int = 0,
    limit: int = 50
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        audio_files = db.query(AudioFile).filter(
            AudioFile.user_id == current_user.id
        ).offset(skip).limit(limit).all()

        logger.info(f"Retrieved {len(audio_files)} audio files for user {current_user.username}")
        return audio_files
    except Exception as e:
        logger.error(f"Failed to retrieve audio files for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving audio files")

@router.get("/me/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        stats = analytics_service.get_user_statistics(current_user.id)

        # Log the analytics access
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="view_statistics",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Retrieved statistics for user {current_user.username}")
        return stats
    except Exception as e:
        logger.error(f"Failed to retrieve statistics for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving statistics")

@router.get("/me/activity", response_model=list[UserActivityResponse])
async def get_user_activity_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
    skip: int = 0,
    limit: int = 50
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        activities = analytics_service.get_user_activity_history(current_user.id, limit, skip)

        # Log the activity access
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="view_activity_history",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Retrieved {len(activities)} activity records for user {current_user.username}")
        return activities
    except Exception as e:
        logger.error(f"Failed to retrieve activity history for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving activity history")

@router.get("/me/predictions/{prediction_id}/analytics", response_model=PredictionAnalyticsResponse)
async def get_prediction_analytics(
    prediction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Verify the prediction belongs to the user
        prediction = db.query(Prediction).filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id
        ).first()

        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_prediction_analytics(prediction_id)

        if not analytics:
            raise HTTPException(status_code=404, detail="Analytics not found for this prediction")

        # Log the analytics access
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="view_prediction_analytics",
            details={"prediction_id": prediction_id},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Retrieved analytics for prediction {prediction_id} for user {current_user.username}")
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve prediction analytics for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving prediction analytics")

@router.get("/me/visualization/prediction-trends")
async def get_user_prediction_trends_visualization(
    current_user: User = Depends(get_current_active_user),
    days: int = 30,
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        trends = await get_user_prediction_trends(str(current_user.id), days)
        logger.info(f"Retrieved prediction trends for user {current_user.username}")
        return trends
    except Exception as e:
        logger.error(f"Failed to retrieve prediction trends for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving prediction trends")

@router.get("/me/visualization/emotion-distribution")
async def get_user_emotion_distribution_visualization(
    current_user: User = Depends(get_current_active_user),
    days: int = 30,
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        distribution = await get_emotion_distribution(str(current_user.id), days)
        logger.info(f"Retrieved emotion distribution for user {current_user.username}")
        return distribution
    except Exception as e:
        logger.error(f"Failed to retrieve emotion distribution for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving emotion distribution")

@router.get("/me/visualization/engagement-metrics")
async def get_user_engagement_metrics_visualization(
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        metrics = await get_user_engagement_metrics(str(current_user.id))
        logger.info(f"Retrieved engagement metrics for user {current_user.username}")
        return metrics
    except Exception as e:
        logger.error(f"Failed to retrieve engagement metrics for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving engagement metrics")
