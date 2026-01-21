# User-Centric Features TODO

## 1. Add Profile Update Endpoint
- [x] Add PUT /auth/users/me endpoint to middleware/auth.py for updating user profile

## 2. Create User History Routes
- [x] Create routes/user.py with endpoints for user data history
- [x] Add GET /users/me/predictions - View user's prediction history
- [x] Add GET /users/me/audio-files - View user's uploaded audio files

## 3. Update Main Application
- [x] Update main.py to include the new user router
- [x] Ensure proper imports and route registration

## 4. Testing and Validation
- [x] Test all new endpoints for proper authentication
- [x] Verify data retrieval works correctly
- [x] Check error handling and logging
