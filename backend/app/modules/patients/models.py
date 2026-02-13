"""Patient models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import BaseModel
from app.core.constants import WorkflowState


class Patient(BaseModel):
    """Patient domain model.
    
    Inherits from BaseModel:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (is_deleted, deleted_at)
    """
    
    __tablename__ = "patients"
    
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    mrn: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="Medical Record Number",
    )
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(50), default="en")
    
    # Clinical status
    workflow_state: Mapped[str] = mapped_column(
        String(50),
        default=WorkflowState.INTAKE.value,
        index=True,
    )
    center_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    assigned_clinician_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Metadata
    intake_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_assessment_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "patient",
    }

    def __repr__(self) -> str:
        """String representation."""
        return f"<Patient(id={self.id}, user_id={self.user_id}, workflow_state={self.workflow_state})>"
