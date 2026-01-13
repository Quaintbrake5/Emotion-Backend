#!/usr/bin/env python3
"""
Test script to debug the complete login flow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
from database import SessionLocal
from models import User

def test_login_flow():
    print("Testing complete login flow...")

    # Test login endpoint
    login_url = "http://localhost:8001/auth/token"
    login_data = {
        "username": "denzylibe6",
        "password": "qwerty23"
    }

    try:
        response = requests.post(login_url, data=login_data)
        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.json()}")

        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"Got token: {token[:50]}...")

            # Test get current user endpoint
            user_url = "http://localhost:8001/auth/users/me"
            headers = {"Authorization": f"Bearer {token}"}

            user_response = requests.get(user_url, headers=headers)
            print(f"User endpoint status: {user_response.status_code}")
            print(f"User endpoint response: {user_response.text}")

        else:
            print("Login failed")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_login_flow()
