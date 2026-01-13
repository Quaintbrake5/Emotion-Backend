from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from services.otp_service import OTPService
from database import get_db
from models import User
from sqlalchemy.orm import Session
import os

logger = logging.getLogger(__name__)

class OTPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/auth/token",
            "/auth/register",
            "/auth/users/me",
            "/auth/password-reset",
            "/auth/email-verification",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        ]
        self.otp_service = OTPService()

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ")[1]

        try:
            # Verify token and get user
            from middleware.auth import verify_token_string, get_current_user
            username = verify_token_string(token)

            # Get database session
            db = next(get_db())
            user = db.query(User).filter(User.username == username).first()

            if not user:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "User not found"}
                )

            # Check if OTP is enabled for this user
            if user.otp_enabled:
                # Check if OTP has been verified in this session
                # This is a simplified check - in production, you'd use session storage
                otp_verified = request.headers.get("X-OTP-Verified") == "true"

                if not otp_verified:
                    # Check for OTP code in headers
                    otp_code = request.headers.get("X-OTP-Code")
                    backup_code = request.headers.get("X-Backup-Code")

                    if otp_code:
                        if not self.otp_service.verify_otp(user.otp_secret, otp_code):
                            logger.warning(f"Invalid OTP code for user {user.username}")
                            return JSONResponse(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                content={"detail": "Invalid OTP code"}
                            )
                    elif backup_code:
                        if not user.otp_backup_codes:
                            return JSONResponse(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                content={"detail": "Backup codes not available"}
                            )

                        is_valid, updated_codes = self.otp_service.verify_backup_code(
                            user.otp_backup_codes, backup_code
                        )

                        if not is_valid:
                            logger.warning(f"Invalid backup code for user {user.username}")
                            return JSONResponse(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                content={"detail": "Invalid backup code"}
                            )

                        # Update backup codes
                        user.otp_backup_codes = updated_codes
                        db.commit()
                    else:
                        return JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={"detail": "OTP verification required", "otp_required": True}
                        )

            # Add user to request state for downstream use
            request.state.user = user

        except HTTPException:
            # Re-raise HTTPExceptions from auth middleware (like expired tokens)
            raise
        except Exception as e:
            logger.error(f"OTP middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )

        response = await call_next(request)
        return response
