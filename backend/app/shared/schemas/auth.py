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
    user: Optional[dict] = None  # Include user data with role after login
    
    class Config:
        # Include None values in serialization so 'user' field is always present
        exclude_none = False


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    user_id: str
    email: str
    first_name: Optional[str] = None
    roles: list[str]
    permissions: Optional[list[str]] = None
    token_type: str = "access"


class JWTClaims(BaseModel):
    """JWT claims extracted from token."""
    
    user_id: str
    email: str
    first_name: Optional[str] = None
    roles: list[str]
    permissions: Optional[list[str]] = None
