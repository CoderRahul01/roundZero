"""
JWT authentication handler for Vision Agents endpoints.

This module provides JWT token validation and user extraction.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class JWTHandler:
    """
    Handles JWT token creation and validation.
    
    Features:
    - Token generation with expiry
    - Token validation
    - User ID extraction
    - Error handling
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT handler.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT token for user.
        
        Args:
            user_id: User identifier
            expires_delta: Token expiry duration (default: 24 hours)
        
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)
        
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_token(self, token: str) -> dict:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload dictionary
        
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def get_user_id(self, token: str) -> str:
        """
        Extract user ID from token.
        
        Args:
            token: JWT token string
        
        Returns:
            User ID string
        """
        payload = self.decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user_id


# Global JWT handler instance
def get_jwt_handler() -> JWTHandler:
    """
    Get JWT handler instance from environment.
    
    Returns:
        JWTHandler instance
    
    Raises:
        ValueError: If JWT_SECRET not configured
    """
    secret_key = os.getenv("JWT_SECRET")
    
    if not secret_key:
        raise ValueError(
            "JWT_SECRET not configured. "
            "Set JWT_SECRET environment variable."
        )
    
    return JWTHandler(secret_key=secret_key)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency to extract current user ID from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
    
    Returns:
        User ID string
    
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    try:
        jwt_handler = get_jwt_handler()
        user_id = jwt_handler.get_user_id(token)
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Dependency to extract user ID if token is provided (optional auth).
    
    Args:
        credentials: HTTP authorization credentials (optional)
    
    Returns:
        User ID string or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None
