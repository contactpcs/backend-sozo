"""User schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.core.constants import UserRole


class UserCreate(BaseModel):
    """User creation request."""
    
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = None
    role: UserRole = UserRole.PATIENT


class UserUpdate(BaseModel):
    """User update request."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""
    
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    verified_email: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response."""
    pass
