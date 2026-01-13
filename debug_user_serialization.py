#!/usr/bin/env python3
"""
Debug script to test user serialization
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User
from schema import UserResponse

def debug_user_serialization():
    print("Debugging user serialization...")

    db = SessionLocal()
    try:
        # Get a user
        user = db.query(User).filter(User.username == "denzylibe6").first()
        if not user:
            print("User not found")
            return

        print(f"User object: {user}")
        print(f"User attributes: {user.__dict__}")

        # Try to serialize
        try:
            user_response = UserResponse.from_orm(user)
            print(f"Serialized user: {user_response}")
            print(f"Serialized dict: {user_response.dict()}")
        except Exception as e:
            print(f"Serialization error: {e}")
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    debug_user_serialization()
