"""Common request/response schemas."""
from datetime import datetime
from typing import Generic, TypeVar, Optional

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageInfo(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    
    data: list[T]
    pagination: PageInfo


class BaseResponse(BaseModel):
    """Base response schema."""
    
    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime


class TimestampedSchema(BaseModel):
    """Base schema with timestamp fields."""
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BaseEntitySchema(TimestampedSchema):
    """Base schema for domain entities."""
    
    id: str
    
    class Config:
        from_attributes = True
