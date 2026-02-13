"""Authentication schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request."""
    
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    """Token response after login."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    user_id: str
    email: str
    roles: list[str]
    token_type: str = "access"


class JWTClaims(BaseModel):
    """JWT claims extracted from token."""
    
    user_id: str
    email: str
    roles: list[str]
