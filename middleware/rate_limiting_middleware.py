from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from services.rate_limiting_service import check_rate_limit
from typing import Optional

logger = logging.getLogger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get identifier (IP address for anonymous requests, user ID for authenticated)
        identifier = self._get_identifier(request)

        # Determine action based on path and method
        action = self._get_action(request)

        if action:
            # Check rate limit
            is_limited, info = check_rate_limit(identifier, action)

            if is_limited:
                logger.warning(f"Rate limit exceeded for {identifier} on action {action}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": info.get("retry_after", 60),
                        "limit": info.get("limit"),
                        "window": info.get("window")
                    },
                    headers={"Retry-After": str(info.get("retry_after", 60))}
                )

            # Add rate limit info to response headers
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Window"] = str(info.get("window", 0))
            return response

        return await call_next(request)

    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting (IP or user ID)"""
        # Try to get user ID from token (simplified - in production, validate properly)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from middleware.auth import verify_token_string
                token = auth_header.split(" ")[1]
                username = verify_token_string(token)
                return f"user:{username}"
            except:
                pass

        # Fall back to IP address
        return request.client.host if request.client else "unknown"

    def _get_action(self, request: Request) -> Optional[str]:
        """Determine the action based on request path and method"""
        path = request.url.path
        method = request.method

        # Authentication endpoints
        if path.startswith("/auth/token") and method == "POST":
            return "login"
        elif path.startswith("/auth/password-reset") and method == "POST":
            return "password_reset"
        elif path.startswith("/auth/otp/verify") and method == "POST":
            return "otp_verify"

        # Prediction endpoints
        elif path.startswith("/predict") and method in ["POST", "PUT"]:
            return "prediction"

        # Upload endpoints
        elif path.startswith("/upload") and method == "POST":
            return "upload"

        # Default - no rate limiting
        return None
