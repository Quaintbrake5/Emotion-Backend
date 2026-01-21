from database import SessionLocal
from models import User

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        print(f"Admin user found: {admin.username}")
        print(f"is_superuser: {admin.is_superuser}")
        print(f"email: {admin.email}")
    else:
        print("No admin user found")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
