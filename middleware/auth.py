from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from database import get_db
from models import AudioFile, Prediction, User
from schema import UserCreate, UserResponse, AdminUserResponse, Token, UserUpdate, PasswordResetRequest, PasswordResetConfirm, EmailVerificationConfirm, TokenRefreshRequest, TokenRefreshResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import logging
import secrets
from services.email_service import EmailService
from services.analytics_service import AnalyticsService
# from services.otp_service import OTPService  # Temporarily commented out due to missing pyotp dependency
from schema import OTPSetupRequest, OTPSetupResponse, OTPVerifyRequest, OTPDisableRequest, OTPBackupCodeRequest

SECRET_KEY = "your-secret-key"  # Change this to a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        logger.info(f"Verifying token: {credentials.credentials[:50]}...")
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        logger.info(f"Token decoded successfully, username: {username}")
        if username is None:
            logger.error("Token payload missing 'sub' claim")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def verify_token_string(token: str):
    """Verify a JWT token string and return the username"""
    try:
        logger.info(f"Verifying token string: {token[:50]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        logger.info(f"Token string decoded successfully, username: {username}")
        if username is None:
            logger.error("Token payload missing 'sub' claim")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_user(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == token).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    # bcrypt has a 72 byte limit, so truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(required_role):
    def role_checker(current_user: User = Depends(get_current_user)):
        # Note: This assumes User model has roles, but current model doesn't have roles
        # For now, just return the user
        return current_user
    return role_checker

def require_admin(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Router for authentication endpoints
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db), request: Request = None):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        # Check if user already exists
        db_user = db.query(User).filter(
            or_(User.email == user.email, User.username == user.username)
        ).first()
        if db_user:
            logger.warning(f"Registration failed: User {user.username} or {user.email} already exists")
            raise HTTPException(status_code=400, detail="Email or username already registered")

        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User {user.username} registered successfully")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed for user {user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Login failed: Invalid credentials for user {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if OTP is required
        if user.otp_enabled:
            # For OTP-enabled users, we need additional verification
            # This would typically be handled in a separate endpoint or middleware
            # For now, we'll allow login but require OTP verification in subsequent requests
            pass

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=user.id,
            action="login",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"User {form_data.username} logged in successfully")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for user {form_data.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during login")

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user), request: Request = None):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Return the user directly - the dependency already provides a valid user
        return current_user
    except Exception as e:
        logger.error(f"Error in read_users_me: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/users/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Check for duplicate email/username if they're being updated
        if user_update.email and user_update.email != current_user.email:
            existing_user = db.query(User).filter(User.email == user_update.email).first()
            if existing_user:
                logger.warning(f"Update failed: Email {user_update.email} already exists")
                raise HTTPException(status_code=400, detail="Email already registered")

        if user_update.username and user_update.username != current_user.username:
            existing_user = db.query(User).filter(User.username == user_update.username).first()
            if existing_user:
                logger.warning(f"Update failed: Username {user_update.username} already exists")
                raise HTTPException(status_code=400, detail="Username already taken")

        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "password":  # Skip password updates through this endpoint
                continue
            setattr(current_user, field, value)

        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)

        logger.info(f"User {current_user.username} updated successfully")
        return current_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during update")

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Log the logout activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="logout",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"User {current_user.username} logged out successfully")
        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during logout")

@router.delete("/users/me")
async def delete_user_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Get all predictions and audio files for this user
        predictions = db.query(Prediction).filter(Prediction.user_id == current_user.id).all()
        audio_files = db.query(AudioFile).filter(AudioFile.user_id == current_user.id).all()

        # Delete associated files from filesystem
        for prediction in predictions:
            # Note: In a real implementation, you'd delete the actual audio files here
            # For now, we'll just delete the database records
            pass

        for audio_file in audio_files:
            # Note: In a real implementation, you'd delete the actual audio files here
            # For now, we'll just delete the database records
            pass

        # Delete all predictions and audio files
        db.query(Prediction).filter(Prediction.user_id == current_user.id).delete()
        db.query(AudioFile).filter(AudioFile.user_id == current_user.id).delete()

        # Delete the user
        db.delete(current_user)
        db.commit()

        logger.info(f"User {current_user.username} and all associated data deleted successfully")
        return {"message": "Account deleted successfully"}

    except Exception as e:
        logger.error(f"Account deletion failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during account deletion")

# Advanced Authentication Endpoints
@router.post("/password-reset/request", response_model=dict)
async def request_password_reset(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request_data.email).first()
        if not user:
            # Don't reveal if email exists or not for security
            logger.warning(f"Password reset requested for non-existent email: {request_data.email}")
            return {"message": "If the email exists, a password reset link has been sent"}

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour

        # Store reset token (in a real app, you'd store this securely)
        # For now, we'll use a simple approach - in production, use Redis or database
        user.reset_token = reset_token
        user.reset_token_expires = expires_at
        db.commit()

        # Send email
        email_service = EmailService()
        reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
        await email_service.send_password_reset_email(user.email, user.username, reset_link)

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=user.id,
            action="password_reset_requested",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Password reset requested for user {user.username}")
        return {"message": "If the email exists, a password reset link has been sent"}

    except Exception as e:
        logger.error(f"Password reset request failed for email {request_data.email}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/password-reset/confirm", response_model=dict)
async def confirm_password_reset(
    request_data: PasswordResetConfirm,
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        # Find user by reset token
        user = db.query(User).filter(
            User.reset_token == request_data.token,
            User.reset_token_expires > datetime.utcnow()
        ).first()

        if not user:
            logger.warning("Invalid or expired password reset token")
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Update password
        hashed_password = get_password_hash(request_data.new_password)
        user.hashed_password = hashed_password
        user.reset_token = None
        user.reset_token_expires = None
        user.updated_at = datetime.utcnow()
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=user.id,
            action="password_reset_completed",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Password reset completed for user {user.username}")
        return {"message": "Password reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/email-verification/request", response_model=dict)
async def request_email_verification(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        if current_user.is_verified:
            return {"message": "Email is already verified"}

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours

        # Store verification token
        current_user.verification_token = verification_token
        current_user.verification_token_expires = expires_at
        db.commit()

        # Send verification email
        email_service = EmailService()
        verification_link = f"http://localhost:8000/verify-email?token={verification_token}"
        await email_service.send_verification_email(current_user.email, current_user.username, verification_link)

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="email_verification_requested",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Email verification requested for user {current_user.username}")
        return {"message": "Verification email sent"}

    except Exception as e:
        logger.error(f"Email verification request failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/email-verification/confirm", response_model=dict)
async def confirm_email_verification(
    request_data: EmailVerificationConfirm,
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        # Find user by verification token
        user = db.query(User).filter(
            User.verification_token == request_data.token,
            User.verification_token_expires > datetime.utcnow()
        ).first()

        if not user:
            logger.warning("Invalid or expired email verification token")
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Mark email as verified
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        user.updated_at = datetime.utcnow()
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=user.id,
            action="email_verified",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Email verified for user {user.username}")
        return {"message": "Email verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification confirmation failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/token/refresh", response_model=TokenRefreshResponse)
async def refresh_access_token(
    request_data: TokenRefreshRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        # Verify refresh token (simplified - in production, validate properly)
        try:
            payload = jwt.decode(request_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Generate new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Generate new refresh token (longer expiry)
        refresh_token_expires = timedelta(days=7)
        refresh_token = create_access_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=user.id,
            action="token_refreshed",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Token refreshed for user {user.username}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Admin-only endpoints
@router.get("/users", response_model=list[AdminUserResponse])
async def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username}")
    try:
        users = db.query(User).all()
        logger.info(f"Admin {current_user.username} retrieved all users")
        return users
    except Exception as e:
        logger.error(f"Failed to retrieve users for admin {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for admin {current_user.username} updating user {user_id}")
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")

        # Check for duplicate email/username if they're being updated
        if user_update.email and user_update.email != db_user.email:
            existing_user = db.query(User).filter(User.email == user_update.email).first()
            if existing_user:
                logger.warning(f"Update failed: Email {user_update.email} already exists")
                raise HTTPException(status_code=400, detail="Email already registered")

        if user_update.username and user_update.username != db_user.username:
            existing_user = db.query(User).filter(User.username == user_update.username).first()
            if existing_user:
                logger.warning(f"Update failed: Username {user_update.username} already exists")
                raise HTTPException(status_code=400, detail="Username already taken")

        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        db_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_user)

        logger.info(f"Admin {current_user.username} updated user {db_user.username}")
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update failed for user {user_id} by admin {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error during update")

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
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

        # Delete associated files from filesystem
        for prediction in predictions:
            # Note: In a real implementation, you'd delete the actual audio files here
            # For now, we'll just delete the database records
            pass

        for audio_file in audio_files:
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

# OTP Endpoints
@router.post("/otp/setup", response_model=OTPSetupResponse)
async def setup_otp(
    request_data: OTPSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Verify password
        if not pwd_context.verify(request_data.password, current_user.hashed_password):
            logger.warning(f"OTP setup failed: Invalid password for user {current_user.username}")
            raise HTTPException(status_code=400, detail="Invalid password")

        if current_user.otp_enabled:
            logger.warning(f"OTP setup failed: OTP already enabled for user {current_user.username}")
            raise HTTPException(status_code=400, detail="OTP is already enabled")

        # Generate OTP setup data
        otp_service = OTPService()
        setup_data = otp_service.setup_otp(current_user.username)

        # Store temporary secret
        current_user.temp_otp_secret = setup_data["secret"]
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="otp_setup_initiated",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"OTP setup initiated for user {current_user.username}")
        return OTPSetupResponse(
            secret=setup_data["secret"],
            qr_code_url=setup_data["qr_code_url"],
            backup_codes=setup_data["backup_codes"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP setup failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/otp/verify", response_model=dict)
async def verify_otp_setup(
    request_data: OTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        if not current_user.temp_otp_secret:
            logger.warning(f"OTP verification failed: No temporary secret for user {current_user.username}")
            raise HTTPException(status_code=400, detail="OTP setup not initiated")

        # Verify OTP code
        otp_service = OTPService()
        if not otp_service.verify_otp(current_user.temp_otp_secret, request_data.otp_code):
            logger.warning(f"OTP verification failed: Invalid code for user {current_user.username}")
            raise HTTPException(status_code=400, detail="Invalid OTP code")

        # Enable OTP
        current_user.otp_secret = current_user.temp_otp_secret
        current_user.otp_enabled = True
        current_user.otp_backup_codes = otp_service.hash_backup_codes(otp_service.generate_backup_codes())
        current_user.temp_otp_secret = None
        current_user.updated_at = datetime.utcnow()
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="otp_enabled",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"OTP enabled for user {current_user.username}")
        return {"message": "OTP enabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/otp/disable", response_model=dict)
async def disable_otp(
    request_data: OTPDisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        # Verify password
        if not pwd_context.verify(request_data.password, current_user.hashed_password):
            logger.warning(f"OTP disable failed: Invalid password for user {current_user.username}")
            raise HTTPException(status_code=400, detail="Invalid password")

        if not current_user.otp_enabled:
            logger.warning(f"OTP disable failed: OTP not enabled for user {current_user.username}")
            raise HTTPException(status_code=400, detail="OTP is not enabled")

        # Disable OTP
        current_user.otp_secret = None
        current_user.otp_enabled = False
        current_user.otp_backup_codes = None
        current_user.temp_otp_secret = None
        current_user.updated_at = datetime.utcnow()
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="otp_disabled",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"OTP disabled for user {current_user.username}")
        return {"message": "OTP disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP disable failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/otp/verify-login", response_model=dict)
async def verify_otp_for_login(
    request_data: OTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        if not current_user.otp_enabled:
            logger.warning(f"OTP login verification failed: OTP not enabled for user {current_user.username}")
            raise HTTPException(status_code=400, detail="OTP is not enabled")

        # Verify OTP code
        otp_service = OTPService()
        if not otp_service.verify_otp(current_user.otp_secret, request_data.otp_code):
            logger.warning(f"OTP login verification failed: Invalid code for user {current_user.username}")
            raise HTTPException(status_code=400, detail="Invalid OTP code")

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="otp_login_verified",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"OTP login verified for user {current_user.username}")
        return {"message": "OTP verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP login verification failed for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/otp/backup-code", response_model=dict)
async def verify_backup_code(
    request_data: OTPBackupCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Request received: {request.method} {request.url.path} for user {current_user.username}")
    try:
        if not current_user.otp_enabled or not current_user.otp_backup_codes:
            logger.warning(f"Backup code verification failed: OTP not enabled for user {current_user.username}")
            raise HTTPException(status_code=400, detail="OTP is not enabled")

        # Verify backup code
        otp_service = OTPService()
        is_valid, updated_codes = otp_service.verify_backup_code(
            current_user.otp_backup_codes,
            request_data.backup_code
        )

        if not is_valid:
            logger.warning(f"Backup code verification failed: Invalid code for user {current_user.username}")
            raise HTTPException(status_code=400, detail="Invalid backup code")

        # Update backup codes
        current_user.otp_backup_codes = updated_codes
        current_user.updated_at = datetime.utcnow()
        db.commit()

        # Log activity
        analytics_service = AnalyticsService(db)
        analytics_service.log_user_activity(
            user_id=current_user.id,
            action="backup_code_used",
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        logger.info(f"Backup code verified for user {current_user.username}")
        return {"message": "Backup code verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup code verification failed for user {current_user.username}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
