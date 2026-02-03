from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import require_admin
from models import User
from services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
INTERNAL_SERVER_ERROR = "Internal server error"

@router.get("/system/stats", response_model=dict)
async def get_system_statistics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        stats = analytics_service.get_system_statistics()

        logger.info(f"Admin {current_user.username} retrieved system statistics")
        return stats
    except Exception as e:
        logger.error(f"Failed to retrieve system statistics for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.get("/system/metrics", response_model=dict)
async def get_system_metrics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        metrics = analytics_service.get_system_metrics()

        logger.info(f"Admin {current_user.username} retrieved system metrics")
        return metrics
    except Exception as e:
        logger.error(f"Failed to retrieve system metrics for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.get("/users/{user_id}/activity", response_model=list[dict])
async def get_user_activity_history(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
    skip: int = 0,
    limit: int = 50
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        activities = analytics_service.get_user_activity_history(user_id, limit, skip)

        logger.info(f"Admin {current_user.username} retrieved activity history for user {user_id}")
        return activities
    except Exception as e:
        logger.error(f"Failed to retrieve activity history for user {user_id} by admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.get("/predictions/analytics", response_model=dict)
async def get_prediction_analytics_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_prediction_analytics_overview()

        logger.info(f"Admin {current_user.username} retrieved prediction analytics overview")
        return analytics
    except Exception as e:
        logger.error(f"Failed to retrieve prediction analytics overview for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.get("/users/activity/summary", response_model=dict)
async def get_user_activity_summary(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        summary = analytics_service.get_user_activity_summary()

        logger.info(f"Admin {current_user.username} retrieved user activity summary")
        return summary
    except Exception as e:
        logger.error(f"Failed to retrieve user activity summary for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.delete("/data/cleanup", response_model=dict)
async def cleanup_old_data(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
    days_old: int = 90
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        result = analytics_service.cleanup_old_data(days_old)

        logger.info(f"Admin {current_user.username} performed data cleanup for data older than {days_old} days")
        return result
    except Exception as e:
        logger.error(f"Failed to perform data cleanup for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)

@router.get("/system/health", response_model=dict)
async def get_system_health(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        analytics_service = AnalyticsService(db)
        health = analytics_service.get_system_health()

        logger.info(f"Admin {current_user.username} retrieved system health status")
        return health
    except Exception as e:
        logger.error(f"Failed to retrieve system health for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail= INTERNAL_SERVER_ERROR)