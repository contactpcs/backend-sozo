"""Security utilities: JWT handling, password hashing, RBAC."""
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jwt import PyJWTError, decode, encode

from .config import get_settings
from ..shared.schemas.auth import TokenPayload, JWTClaims


logger = logging.getLogger(__name__)

# HTTP Bearer scheme
security = HTTPBearer()


class PasswordManager:
    """Handle password hashing and verification using SHA256.
    
    Note: For demo purposes with hardcoded auth. 
    In production, use bcrypt with proper salt management.
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


class JWTManager:
    """Handle JWT token generation and validation."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def create_access_token(
        self,
        user_id: str,
        user_email: str,
        roles: list[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=self.settings.jwt.access_token_expire_minutes
            )
        
        now = datetime.now(timezone.utc)
        expires = now + expires_delta
        
        payload = {
            "sub": user_id,
            "email": user_email,
            "roles": roles,
            "iat": now,
            "exp": expires,
            "type": "access"
        }
        
        token = encode(
            payload,
            self.settings.jwt.secret_key.get_secret_value(),
            algorithm=self.settings.jwt.algorithm
        )
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        expires_delta = timedelta(
            days=self.settings.jwt.refresh_token_expire_days
        )
        
        now = datetime.now(timezone.utc)
        expires = now + expires_delta
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires,
            "type": "refresh"
        }
        
        token = encode(
            payload,
            self.settings.jwt.secret_key.get_secret_value(),
            algorithm=self.settings.jwt.algorithm
        )
        return token
    
    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode JWT token."""
        try:
            payload = decode(
                token,
                self.settings.jwt.secret_key.get_secret_value(),
                algorithms=[self.settings.jwt.algorithm]
            )
            
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            roles: list[str] = payload.get("roles", [])
            token_type: str = payload.get("type", "access")
            
            if user_id is None:
                raise PyJWTError("Invalid token payload")
            
            return TokenPayload(
                user_id=user_id,
                email=email,
                roles=roles,
                token_type=token_type
            )
        
        except PyJWTError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def refresh_access_token(self, refresh_token: str, user_roles: list[str]) -> str:
        """Create new access token from refresh token."""
        payload = self.verify_token(refresh_token)
        
        if payload.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return self.create_access_token(
            user_id=payload.user_id,
            user_email=payload.email,
            roles=user_roles or []
        )


class JWTBearer:
    """JWT Bearer token dependency."""
    
    def __init__(self):
        self.jwt_manager = JWTManager()
    
    async def __call__(
        self,
        credentials = Depends(security)
    ) -> JWTClaims:
        """Extract and validate JWT from request."""
        token = credentials.credentials
        
        try:
            payload = self.jwt_manager.verify_token(token)
            return JWTClaims(
                user_id=payload.user_id,
                email=payload.email,
                roles=payload.roles
            )
        except HTTPException:
            raise


def get_jwt_bearer() -> JWTBearer:
    """Dependency for JWT validation."""
    return JWTBearer()


def require_role(*allowed_roles: str):
    """Decorator to enforce role-based access control."""
    async def role_checker(claims: JWTClaims = Depends(get_jwt_bearer())) -> JWTClaims:
        if not any(role in allowed_roles for role in claims.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return claims
    
    return role_checker
