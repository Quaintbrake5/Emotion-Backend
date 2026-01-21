#!/usr/bin/env python3
"""
Test script to verify admin login flow
"""
import requests
import json

def test_admin_login():
    print("Testing admin login flow...")

    # Admin credentials from seed_admin.py
    admin_credentials = {
        "username": "admin",
        "password": "admin123"
    }

    # Login endpoint
    login_url = "http://localhost:8001/auth/token"

    try:
        # Step 1: Login with admin credentials
        print("1. Logging in with admin credentials...")
        response = requests.post(login_url, data=admin_credentials)
        print(f"Login response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return False

        login_data = response.json()
        access_token = login_data["access_token"]
        print(f"Login successful! Got access token: {access_token[:50]}...")

        # Step 2: Get current user info
        print("\n2. Fetching current user info...")
        user_url = "http://localhost:8001/auth/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        user_response = requests.get(user_url, headers=headers)
        print(f"User info response status: {user_response.status_code}")

        if user_response.status_code != 200:
            print(f"Failed to get user info: {user_response.text}")
            return False

        user_data = user_response.json()
        print(f"User data: {json.dumps(user_data, indent=2)}")

        # Step 3: Verify admin status
        print("\n3. Verifying admin status...")
        if user_data.get("is_superuser"):
            print("✅ SUCCESS: User is superuser (admin)")
            print("✅ Admin login flow works correctly!")
            return True
        else:
            print("❌ FAILURE: User is not superuser")
            return False

    except Exception as e:
        print(f"Error during test: {e}")
        return False

if __name__ == "__main__":
    success = test_admin_login()
    if success:
        print("\n🎉 Admin login verification PASSED!")
        print("The system correctly identifies admin users and should redirect to admin dashboard.")
    else:
        print("\n💥 Admin login verification FAILED!")
        print("There may be an issue with admin login or user identification.")
