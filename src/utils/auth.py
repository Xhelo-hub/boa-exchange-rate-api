"""
Authentication and authorization utilities
"""

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional
import secrets
import hashlib
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Security schemes
bearer_security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthenticationManager:
    """
    Manages API authentication
    """
    
    def __init__(self):
        """Initialize authentication manager"""
        self.admin_api_key = os.getenv('ADMIN_API_KEY')
        self.webhook_secret = os.getenv('WEBHOOK_SECRET')
        
        if not self.admin_api_key:
            logger.warning(
                "ADMIN_API_KEY not set. Generate one with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    
    def verify_admin_api_key(self, api_key: str) -> bool:
        """
        Verify admin API key
        
        Args:
            api_key: API key to verify
            
        Returns:
            True if valid, False otherwise
        """
        if not self.admin_api_key:
            logger.error("ADMIN_API_KEY not configured")
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(api_key, self.admin_api_key)
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature
        
        Args:
            payload: Webhook payload
            signature: Signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        if not self.webhook_secret:
            logger.error("WEBHOOK_SECRET not configured")
            return False
        
        # Calculate expected signature
        expected = hashlib.sha256(
            f"{payload}{self.webhook_secret}".encode()
        ).hexdigest()
        
        return secrets.compare_digest(signature, expected)
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key
        
        Returns:
            Random API key
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for storage
        
        Args:
            api_key: API key to hash
            
        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()


# Global authentication manager
_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """
    Get global authentication manager instance
    
    Returns:
        AuthenticationManager instance
    """
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    
    return _auth_manager


# FastAPI Dependencies

async def verify_admin_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    FastAPI dependency to verify admin API key
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.verify_admin_api_key(api_key):
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_security)
) -> str:
    """
    FastAPI dependency to verify bearer token
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        Token if valid
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    # Add your token verification logic here
    # For example, verify JWT token, check against database, etc.
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


async def verify_webhook_signature_dep(
    signature: str,
    payload: str
) -> bool:
    """
    FastAPI dependency to verify webhook signature
    
    Args:
        signature: Webhook signature from header
        payload: Request payload
        
    Returns:
        True if valid
        
    Raises:
        HTTPException: If signature is invalid
    """
    auth_manager = get_auth_manager()
    
    if not auth_manager.verify_webhook_signature(payload, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    return True


class RateLimiter:
    """
    Simple in-memory rate limiter
    For production, use Redis or similar
    """
    
    def __init__(self):
        self._requests = {}  # {ip: [(timestamp, count), ...]}
        self._cleanup_interval = 3600  # Clean up old entries every hour
        self._last_cleanup = datetime.utcnow()
    
    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 3600
    ) -> bool:
        """
        Check if identifier exceeds rate limit
        
        Args:
            identifier: Client identifier (IP, API key, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Cleanup old entries periodically
        if (now - self._last_cleanup).total_seconds() > self._cleanup_interval:
            self._cleanup_old_entries(window_start)
            self._last_cleanup = now
        
        # Get requests for this identifier
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Filter requests within window
        self._requests[identifier] = [
            ts for ts in self._requests[identifier]
            if ts > window_start
        ]
        
        # Check limit
        if len(self._requests[identifier]) >= max_requests:
            return False
        
        # Add current request
        self._requests[identifier].append(now)
        return True
    
    def _cleanup_old_entries(self, cutoff: datetime):
        """Remove entries older than cutoff"""
        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > cutoff
            ]
            
            # Remove empty entries
            if not self._requests[identifier]:
                del self._requests[identifier]


# Global rate limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    
    return _rate_limiter


async def check_rate_limit(
    identifier: str,
    max_requests: int = 100,
    window_seconds: int = 3600
) -> bool:
    """
    FastAPI dependency for rate limiting
    
    Args:
        identifier: Client identifier
        max_requests: Max requests per window
        window_seconds: Time window in seconds
        
    Returns:
        True if within limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    limiter = get_rate_limiter()
    
    if not limiter.check_rate_limit(identifier, max_requests, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(window_seconds)}
        )
    
    return True


if __name__ == "__main__":
    # Generate keys for setup
    print("Security Setup")
    print("=" * 60)
    print("\nAdd these to your .env file:\n")
    print(f"ADMIN_API_KEY={AuthenticationManager.generate_api_key()}")
    print(f"WEBHOOK_SECRET={AuthenticationManager.generate_api_key()}")
    print("\n" + "=" * 60)
