from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import require_admin
from models import User, Prediction, AudioFile
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/users", response_model=list[dict])
async def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
    skip: int = 0,
    limit: int = 100
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        users = db.query(User).offset(skip).limit(limit).all()

        # Convert to dict and exclude sensitive info
        user_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            user_list.append(user_dict)

        logger.info(f"Admin {current_user.username} retrieved {len(user_list)} users")
        return user_list
    except Exception as e:
        logger.error(f"Failed to retrieve users for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username} deleting user {user_id}")
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent admin from deleting themselves
        if db_user.id == current_user.id:
            logger.warning(f"Admin {current_user.username} attempted to delete themselves")
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        # Get all predictions and audio files for this user
        predictions = db.query(Prediction).filter(Prediction.user_id == user_id).all()
        audio_files = db.query(AudioFile).filter(AudioFile.user_id == user_id).all()

        # Delete associated files from filesystem (placeholder for actual file deletion)
        for _ in predictions:
            # Note: In a real implementation, you'd delete the actual audio files here
            # For now, we'll just delete the database records
            pass

        for _ in audio_files:
            # Note: In a real implementation, you'd delete the actual audio files here
            # For now, we'll just delete the database records
            pass

        # Delete all predictions and audio files
        db.query(Prediction).filter(Prediction.user_id == user_id).delete()
        db.query(AudioFile).filter(AudioFile.user_id == user_id).delete()

        # Delete the user
        db.delete(db_user)
        db.commit()

        logger.info(f"Admin {current_user.username} deleted user {db_user.username}")
        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deletion failed for user {user_id} by admin {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during deletion")
