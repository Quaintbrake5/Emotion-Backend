from database import SessionLocal
from models import User

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        admin.is_superuser = True
        db.commit()
        print("Admin user updated: is_superuser set to True")
    else:
        print("No admin user found")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
