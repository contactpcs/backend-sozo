"""Utility functions and helpers."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
import string
import random


def generate_uuid() -> str:
    """Generate UUID string."""
    return str(uuid4())


def generate_reference_id(prefix: str = "REF") -> str:
    """Generate human-readable reference ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_suffix}"


def parse_uuid(value: str) -> Optional[UUID]:
    """Parse string to UUID."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def is_valid_uuid(value: str) -> bool:
    """Check if string is valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def calculate_pagination(
    total: int,
    page: int,
    page_size: int
) -> dict:
    """Calculate pagination metadata."""
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def get_past_date(days: int = 0, hours: int = 0) -> datetime:
    """Get datetime in the past."""
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


def get_future_date(days: int = 0, hours: int = 0) -> datetime:
    """Get datetime in the future."""
    return datetime.now(timezone.utc) + timedelta(days=days, hours=hours)
