"""Base model with common fields and mixins."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from app.core.database import Base


class TimestampMixin:
    """Mixin for timestamp fields (created_at, updated_at)."""
    
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Record creation timestamp."""
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
    
    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Record last update timestamp."""
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin for soft delete support."""
    
    @declared_attr
    def is_deleted(cls) -> Mapped[bool]:
        """Soft delete flag."""
        return mapped_column(Boolean, default=False, nullable=False, index=True)
    
    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        """Soft delete timestamp."""
        return mapped_column(DateTime(timezone=True), nullable=True, index=True)


class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary key."""
    
    @declared_attr
    def id(cls) -> Mapped[str]:
        """UUID primary key."""
        return mapped_column(
            UUID(as_uuid=False),
            primary_key=True,
            default=lambda: str(uuid.uuid4()),
            nullable=False,
        )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Base model for all domain entities.
    
    Provides:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete support (is_deleted, deleted_at)
    """
    
    __abstract__ = True

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def mark_deleted(self) -> None:
        """Mark record as soft-deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
