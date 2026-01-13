# Admin and Enhanced User Features TODO

## 1. Enhanced User Profile Management
- [ ] Add profile picture support to User model (optional field)
- [ ] Update UserUpdate schema to include profile_picture_url
- [ ] Add DELETE /auth/users/me endpoint for account deletion
- [ ] Add proper account deletion logic (cascade delete predictions/audio files)

## 2. Admin Role Implementation
- [x] Create admin-only endpoints in middleware/auth.py
- [x] Add GET /auth/users endpoint to list all users (admin only)
- [x] Add PUT /auth/users/{user_id} endpoint to update any user (admin only)
- [x] Add DELETE /auth/users/{user_id} endpoint to delete any user (admin only)
- [x] Add admin role checking middleware

## 3. Admin User Seeding
- [x] Create database seeding script for admin user
- [x] Add admin user creation on first startup
- [x] Ensure admin user has is_superuser=True

## 4. Update Schemas and Models
- [ ] Add profile_picture_url to User model
- [ ] Update UserResponse schema to include is_superuser for admin users
- [ ] Add AdminUserResponse schema for admin endpoints

## 5. Testing and Validation
- [ ] Test all new admin endpoints with proper authentication
- [ ] Test user account deletion functionality
- [ ] Verify admin user seeding works correctly
- [ ] Test profile picture upload (if implemented)
