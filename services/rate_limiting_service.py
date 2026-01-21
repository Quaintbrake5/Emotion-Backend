import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
import redis
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class RateLimitingService:
    def __init__(self):
        self.redis_client = None
        try:
            # Try to connect to Redis if available
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                # Parse Redis URL for Render deployment
                parsed = urlparse(redis_url)
                self.redis_client = redis.Redis(
                    host=parsed.hostname,
                    port=parsed.port,
                    username=parsed.username,
                    password=parsed.password,
                    db=int(parsed.path.lstrip('/')) if parsed.path else 0,
                    decode_responses=True
                )
            else:
                # Fallback to individual env vars for local development
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    decode_responses=True
                )
            self.redis_client.ping()  # Test connection
            logger.info("Connected to Redis for rate limiting")
        except (redis.ConnectionError, redis.TimeoutError):
            logger.warning("Redis not available, using in-memory rate limiting")
            self.in_memory_limits = defaultdict(list)

    def _get_redis_key(self, identifier: str, action: str) -> str:
        return f"rate_limit:{action}:{identifier}"

    def _get_in_memory_key(self, identifier: str, action: str) -> str:
        return f"{action}:{identifier}"

    def is_rate_limited(self, identifier: str, action: str, limit: int, window_seconds: int) -> bool:
        """
        Check if the identifier is rate limited for the given action.

        Args:
            identifier: User ID, IP address, etc.
            action: The action being rate limited (e.g., 'login', 'prediction')
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()

        if self.redis_client:
            return self._check_redis_rate_limit(identifier, action, limit, window_seconds, current_time)
        else:
            return self._check_memory_rate_limit(identifier, action, limit, window_seconds, current_time)

    def _check_redis_rate_limit(self, identifier: str, action: str, limit: int, window_seconds: int, current_time: float) -> bool:
        if not self.redis_client:
            return self._check_memory_rate_limit(identifier, action, limit, window_seconds, current_time)

        key = self._get_redis_key(identifier, action)

        try:
            # Use Redis sorted set to store timestamps
            # Remove old entries outside the window
            min_time = current_time - window_seconds
            self.redis_client.zremrangebyscore(key, '-inf', min_time)

            # Count current requests in window
            request_count = self.redis_client.zcard(key)

            if request_count >= limit:
                return True

            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            # Set expiration on the key
            self.redis_client.expire(key, window_seconds)

            return False
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed during rate limit check, falling back to in-memory: {e}")
            self.redis_client = None  # Disable Redis for future calls
            if not hasattr(self, 'in_memory_limits'):
                self.in_memory_limits = defaultdict(list)
            return self._check_memory_rate_limit(identifier, action, limit, window_seconds, current_time)

    def _check_memory_rate_limit(self, identifier: str, action: str, limit: int, window_seconds: int, current_time: float) -> bool:
        key = self._get_in_memory_key(identifier, action)
        timestamps = self.in_memory_limits[key]

        # Remove old timestamps outside the window
        min_time = current_time - window_seconds
        timestamps[:] = [t for t in timestamps if t > min_time]

        if len(timestamps) >= limit:
            return True

        # Add current timestamp
        timestamps.append(current_time)
        return False

    def get_remaining_requests(self, identifier: str, action: str, limit: int, window_seconds: int) -> int:
        """Get the number of remaining requests allowed in the current window."""
        current_time = time.time()

        if self.redis_client:
            try:
                key = self._get_redis_key(identifier, action)
                min_time = current_time - window_seconds
                self.redis_client.zremrangebyscore(key, '-inf', min_time)
                request_count = self.redis_client.zcard(key)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis connection failed in get_remaining_requests, falling back to in-memory: {e}")
                self.redis_client = None
                if not hasattr(self, 'in_memory_limits'):
                    self.in_memory_limits = defaultdict(list)
                key = self._get_in_memory_key(identifier, action)
                timestamps = self.in_memory_limits[key]
                min_time = current_time - window_seconds
                timestamps[:] = [t for t in timestamps if t > min_time]
                request_count = len(timestamps)
        else:
            key = self._get_in_memory_key(identifier, action)
            timestamps = self.in_memory_limits[key]
            min_time = current_time - window_seconds
            timestamps[:] = [t for t in timestamps if t > min_time]
            request_count = len(timestamps)

        return max(0, limit - request_count)

    def get_reset_time(self, identifier: str, action: str, window_seconds: int) -> float:
        """Get the time when the rate limit window resets."""
        current_time = time.time()

        if self.redis_client:
            try:
                key = self._get_redis_key(identifier, action)
                # Get the oldest timestamp in the current window
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    return oldest[0][1] + window_seconds
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis connection failed in get_reset_time, falling back to in-memory: {e}")
                self.redis_client = None
                if not hasattr(self, 'in_memory_limits'):
                    self.in_memory_limits = defaultdict(list)

        key = self._get_in_memory_key(identifier, action)
        timestamps = self.in_memory_limits[key]
        if timestamps:
            return min(timestamps) + window_seconds

        return current_time + window_seconds

# Global rate limiting configurations
RATE_LIMITS = {
    'login': {'limit': 5, 'window': 300},  # 5 login attempts per 5 minutes
    'password_reset': {'limit': 3, 'window': 3600},  # 3 password resets per hour
    'otp_verify': {'limit': 10, 'window': 300},  # 10 OTP verifications per 5 minutes
    'prediction': {'limit': 100, 'window': 3600},  # 100 predictions per hour
    'upload': {'limit': 50, 'window': 3600},  # 50 uploads per hour
}

def check_rate_limit(identifier: str, action: str) -> Tuple[bool, Dict]:
    """
    Check if the request should be rate limited.

    Returns:
        Tuple of (is_limited: bool, info: dict)
    """
    if action not in RATE_LIMITS:
        return False, {}

    config = RATE_LIMITS[action]
    service = RateLimitingService()

    is_limited = service.is_rate_limited(identifier, action, config['limit'], config['window'])

    if is_limited:
        reset_time = service.get_reset_time(identifier, action, config['window'])
        return True, {
            'retry_after': int(reset_time - time.time()),
            'limit': config['limit'],
            'window': config['window']
        }

    remaining = service.get_remaining_requests(identifier, action, config['limit'], config['window'])
    return False, {
        'remaining': remaining,
        'limit': config['limit'],
        'window': config['window']
    }
