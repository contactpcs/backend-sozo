"""
PRS Database Models — 7 tables for the Patient Rating System.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class PRSScale(Base):
    """Library of all clinical assessment scales (47 scales)."""
    __tablename__ = "prs_scales"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scale_id = Column(String(50), unique=True, nullable=False, index=True)
    short_name = Column(String(100), nullable=False)
    full_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    version = Column(String(20), default="1.0")
    scoring_type = Column(String(50), nullable=False)
    max_score = Column(Float)
    estimated_minutes = Column(Integer, default=5)
    definition = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    is_clinician_rated = Column(Boolean, default=False)
    languages = Column(JSONB, default=["en"])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)


class PRSConditionBattery(Base):
    """Condition-to-scale mapping. 16 neurological conditions."""
    __tablename__ = "prs_condition_batteries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    condition_id = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text)
    scale_ids = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)


class PRSAssessmentSession(Base):
    """A session assigned to a patient — the core PRS workflow entity."""
    __tablename__ = "prs_assessment_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # What is being assessed
    condition_id = Column(String(100))
    custom_scale_ids = Column(JSONB)
    resolved_scale_ids = Column(JSONB, nullable=False)

    # Session info
    title = Column(String(255))
    clinical_notes = Column(Text)
    patient_instructions = Column(Text)

    # Mode
    mode = Column(String(50), default="self")  # self | clinician_administered | voice

    # Status: assigned → in_progress → completed | expired | cancelled | clinician_review
    status = Column(String(50), default="assigned", index=True)

    # Timeline
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_activity_at = Column(DateTime)

    # Summary (filled on completion)
    overall_severity = Column(String(50))
    risk_flag_count = Column(Integer, default=0)
    scales_completed = Column(Integer, default=0)
    scales_total = Column(Integer, default=0)

    # PDF report
    report_blob_path = Column(String(500))
    report_generated_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    scale_responses = relationship("PRSScaleResponse", back_populates="session", cascade="all, delete-orphan")
    risk_alerts = relationship("PRSRiskAlert", back_populates="session", cascade="all, delete-orphan")
    consents = relationship("PRSPatientConsent", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_prs_sessions_patient_status", "patient_id", "status"),
        Index("ix_prs_sessions_assigned_by", "assigned_by"),
    )


class PRSScaleResponse(Base):
    """Patient's answers + computed score for one scale in one session."""
    __tablename__ = "prs_scale_responses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("prs_assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    scale_id = Column(String(50), nullable=False)

    # Raw answers: {"0": 2, "1": 1, "2": 3}
    responses = Column(JSONB)

    # Computed scores
    total_score = Column(Float)
    max_possible_score = Column(Float)
    percentage = Column(Float)
    severity_level = Column(String(50))
    severity_label = Column(String(100))

    # Detailed breakdown
    subscale_scores = Column(JSONB)
    domain_scores = Column(JSONB)
    component_scores = Column(JSONB)
    is_positive = Column(Boolean)
    vas_score = Column(Float)

    # Status: pending → in_progress → completed → clinician_pending → clinician_completed
    status = Column(String(50), default="pending")

    # Clinician input (for EDSS, MADRS, MAS etc.)
    rated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    rated_at = Column(DateTime)
    clinician_notes = Column(Text)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    time_taken_seconds = Column(Integer)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    session = relationship("PRSAssessmentSession", back_populates="scale_responses")

    __table_args__ = (
        UniqueConstraint("session_id", "scale_id", name="uq_session_scale"),
        Index("ix_prs_responses_session_scale", "session_id", "scale_id"),
    )


class PRSRiskAlert(Base):
    """Clinical risk flags detected during scoring."""
    __tablename__ = "prs_risk_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("prs_assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    scale_response_id = Column(String(36), ForeignKey("prs_scale_responses.id", ondelete="SET NULL"))
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_clinician_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))

    # Alert content
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    source_scale_id = Column(String(50))
    source_question_index = Column(Integer)
    source_value = Column(Float)

    # Lifecycle: active → acknowledged → resolved | escalated
    status = Column(String(50), default="active", index=True)

    acknowledged_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)

    notified_user_ids = Column(JSONB, default=[])
    notification_sent_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("PRSAssessmentSession", back_populates="risk_alerts")

    __table_args__ = (
        Index("ix_prs_alerts_patient_status", "patient_id", "status"),
    )


class PRSScoreHistory(Base):
    """Immutable score records for longitudinal trend tracking."""
    __tablename__ = "prs_score_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    scale_id = Column(String(50), nullable=False)
    session_id = Column(String(36), ForeignKey("prs_assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    scale_response_id = Column(String(36), ForeignKey("prs_scale_responses.id", ondelete="CASCADE"), nullable=False)

    total_score = Column(Float, nullable=False)
    max_possible_score = Column(Float)
    percentage = Column(Float)
    severity_level = Column(String(50))
    severity_label = Column(String(100))

    recorded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_prs_history_patient_scale", "patient_id", "scale_id"),
    )


class PRSPatientConsent(Base):
    """DISHA/HIPAA consent records."""
    __tablename__ = "prs_patient_consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("prs_assessment_sessions.id", ondelete="SET NULL"))
    consent_type = Column(String(100), nullable=False)
    consented = Column(Boolean, nullable=False)
    consent_text = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    consented_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("PRSAssessmentSession", back_populates="consents")
