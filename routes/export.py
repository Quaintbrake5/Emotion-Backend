from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_current_active_user, require_admin
from models import User
from services.export_service import (
    export_predictions_csv,
    export_predictions_json,
    export_analytics_csv,
    export_user_insights_csv
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
NUMBERS_OF_DAYS_TO_EXPORT = "Number of days to export" 
EXPORT_FAILED = "Export failed"

@router.get("/predictions/csv")
async def export_predictions_to_csv(
    request: Request,
    emotion: str = Query(None, description="Filter by emotion"),
    days: int = Query(30, description=NUMBERS_OF_DAYS_TO_EXPORT, ge=1, le=365),
    include_features: bool = Query(False, description="Include feature data"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export user's predictions as CSV file.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await export_predictions_csv(
            user_id=str(current_user.id),
            emotion=emotion,
            days=days,
            include_features=include_features
        )
    except Exception as e:
        logger.error(f"CSV export failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=EXPORT_FAILED)

@router.get("/predictions/json")
async def export_predictions_to_json(
    request: Request,
    emotion: str = Query(None, description="Filter by emotion"),
    days: int = Query(30, description=NUMBERS_OF_DAYS_TO_EXPORT, ge=1, le=365),
    include_features: bool = Query(False, description="Include feature data"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export user's predictions as JSON file.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await export_predictions_json(
            user_id=str(current_user.id),
            emotion=emotion,
            days=days,
            include_features=include_features
        )
    except Exception as e:
        logger.error(f"JSON export failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=EXPORT_FAILED)

@router.get("/analytics/csv")
async def export_analytics_to_csv(
    request: Request,
    days: int = Query(30, description=NUMBERS_OF_DAYS_TO_EXPORT, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """
    Export system analytics as CSV file (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await export_analytics_csv(days=days)
    except Exception as e:
        logger.error(f"Analytics CSV export failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=EXPORT_FAILED)

@router.get("/user/insights/csv")
async def export_user_insights_to_csv(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Export user's personal insights as CSV file.
    """
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")

    try:
        return await export_user_insights_csv(user_id=str(current_user.id))
    except Exception as e:
        logger.error(f"User insights CSV export failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=EXPORT_FAILED)

@router.get("/admin/user/{user_id}/insights/csv")
async def export_admin_user_insights_to_csv(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """
    Export specific user's insights as CSV file (Admin only).
    """
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")

    try:
        return await export_user_insights_csv(user_id=str(user_id))
    except Exception as e:
        logger.error(f"Admin user insights CSV export failed for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=EXPORT_FAILED)
