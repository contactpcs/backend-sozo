"""User models."""
from typing import Optional
from sqlalchemy import String, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import BaseModel
from app.core.constants import UserRole


class User(BaseModel):
    """User domain model.
    
    Inherits from BaseModel:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (is_deleted, deleted_at)
    """
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.PATIENT.value,
        nullable=False,
        index=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    verified_email: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
