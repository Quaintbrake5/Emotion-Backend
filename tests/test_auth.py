#!/usr/bin/env python3
"""
Test script to debug authentication issues
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User
from middleware.auth import authenticate_user, get_password_hash, create_access_token, verify_token_string
from jose import JWTError

def test_auth():
    print("Testing authentication...")

    # Test database connection
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.username == 'denzylibe6').first()
        if not user:
            print("ERROR: User 'denzylibe6' not found in database")
            return

        print(f"User found: {user.username}, id: {user.id}, active: {user.is_active}")

        # Test password verification
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        test_password = "qwerty23"
        if pwd_context.verify(test_password, user.hashed_password):
            print("Password verification: SUCCESS")
        else:
            print("Password verification: FAILED")
            return

        # Test token creation
        token = create_access_token(data={"sub": user.username})
        print(f"Token created: {token[:50]}...")

        # Test token verification
        try:
            payload = verify_token_string(token)
            print(f"Token verification: SUCCESS, username: {payload}")
        except Exception as e:
            print(f"Token verification: FAILED - {e}")

        # Test authenticate_user function
        auth_result = authenticate_user(db, user.username, test_password)
        if auth_result:
            print(f"authenticate_user: SUCCESS - {auth_result.username}")
        else:
            print("authenticate_user: FAILED")

    finally:
        db.close()

if __name__ == "__main__":
    test_auth()
