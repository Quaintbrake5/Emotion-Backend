from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_current_active_user, require_admin
from models import User
from services.visualization_service import (
    get_user_prediction_trends,
    get_emotion_distribution,
    get_model_performance_comparison,
    get_daily_activity_heatmap,
    get_user_engagement_metrics,
    get_system_overview_metrics
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
NUMBER_OF_DAYS_TO_ANALYZE = "Number of days to analyze"

@router.get("/user/prediction-trends")
async def get_user_prediction_trends_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's prediction trends for time-series visualization.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await get_user_prediction_trends(str(current_user.id), days)
    except Exception as e:
        logger.error(f"Prediction trends failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate prediction trends")

@router.get("/user/emotion-distribution")
async def get_user_emotion_distribution_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's emotion distribution for pie chart visualization.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await get_emotion_distribution(str(current_user.id), days)
    except Exception as e:
        logger.error(f"Emotion distribution failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate emotion distribution")

@router.get("/user/engagement-metrics")
async def get_user_engagement_metrics_endpoint(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive user engagement metrics for dashboard.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await get_user_engagement_metrics(str(current_user.id))
    except Exception as e:
        logger.error(f"Engagement metrics failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate engagement metrics")

@router.get("/admin/model-performance")
async def get_model_performance_comparison_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """
    Get model performance comparison for bar chart (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await get_model_performance_comparison(days)
    except Exception as e:
        logger.error(f"Model performance comparison failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate model performance data")

@router.get("/admin/emotion-distribution")
async def get_system_emotion_distribution_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """
    Get system-wide emotion distribution for pie chart (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await get_emotion_distribution(None, days)
    except Exception as e:
        logger.error(f"System emotion distribution failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate system emotion distribution")

@router.get("/admin/daily-activity-heatmap")
async def get_daily_activity_heatmap_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """
    Get daily activity heatmap data (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await get_daily_activity_heatmap(days)
    except Exception as e:
        logger.error(f"Daily activity heatmap failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate activity heatmap")

@router.get("/admin/system-overview")
async def get_system_overview_metrics_endpoint(
    request: Request,
    days: int = Query(7, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=90),
    current_user: User = Depends(require_admin)
):
    """
    Get system overview metrics for admin dashboard (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await get_system_overview_metrics(days)
    except Exception as e:
        logger.error(f"System overview metrics failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate system overview")

@router.get("/public/emotion-distribution")
async def get_public_emotion_distribution_endpoint(
    request: Request,
    days: int = Query(7, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=30)
):
    """
    Get public emotion distribution (limited to recent data, no auth required).
    """
    logger.info(f"Request received: {request.method} {request.url.path} (public)")

    try:
        return await get_emotion_distribution(None, days)
    except Exception as e:
        logger.error(f"Public emotion distribution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate emotion distribution")

@router.get("/user/combined-dashboard")
async def get_user_combined_dashboard_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get combined dashboard data for user (multiple charts in one response).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        user_id = str(current_user.id)

        # Get all user dashboard data in parallel
        trends_data = await get_user_prediction_trends(user_id, days)
        emotion_data = await get_emotion_distribution(user_id, days)
        engagement_data = await get_user_engagement_metrics(user_id)

        return {
            "dashboard_title": f"{current_user.username}'s Emotion Recognition Dashboard",
            "time_period": f"Last {days} days",
            "charts": {
                "prediction_trends": trends_data,
                "emotion_distribution": emotion_data,
                "engagement_metrics": engagement_data
            },
            "generated_at": datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Combined dashboard failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate dashboard data")

@router.get("/admin/combined-dashboard")
async def get_admin_combined_dashboard_endpoint(
    request: Request,
    days: int = Query(30, description=NUMBER_OF_DAYS_TO_ANALYZE, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """
    Get combined dashboard data for admin (multiple charts in one response).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        # Get all admin dashboard data in parallel
        model_performance = await get_model_performance_comparison(days)
        system_emotions = await get_emotion_distribution(None, days)
        system_overview = await get_system_overview_metrics(days)
        activity_heatmap = await get_daily_activity_heatmap(days)

        return {
            "dashboard_title": "System Administration Dashboard",
            "time_period": f"Last {days} days",
            "charts": {
                "model_performance": model_performance,
                "system_emotion_distribution": system_emotions,
                "system_overview": system_overview,
                "activity_heatmap": activity_heatmap
            },
            "generated_at": datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Combined admin dashboard failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate admin dashboard data")
