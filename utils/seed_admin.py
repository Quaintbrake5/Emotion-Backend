from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from middleware.auth import get_password_hash
import logging

logger = logging.getLogger(__name__)

def seed_admin_user():
    """Seed the database with an admin user if it doesn't exist."""
    db: Session = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.is_superuser == True).first()
        if admin_user:
            logger.info("Admin user already exists")
            return

        # Create admin user
        admin_data = {
            "email": "admin@emotionrecognition.com",
            "username": "admin",
            "full_name": "System Administrator",
            "hashed_password": get_password_hash("admin123"),  # Change this password in production
            "is_active": True,
            "is_superuser": True
        }

        admin_user = User(**admin_data)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        logger.info(f"Admin user created successfully: {admin_user.username}")

    except Exception as e:
        logger.error(f"Failed to seed admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin_user()
