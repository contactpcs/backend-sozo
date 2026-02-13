"""Assessment models."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float

from app.shared.models import BaseModel


class Assessment(BaseModel):
    """Assessment model."""
    
    __tablename__ = "assessments"
    
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    assessment_type = Column(String(50), nullable=False)  # clinical, psychosocial, sdt
    clinician_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Assessment data
    questionnaire_id = Column(String(36), nullable=True)
    version = Column(Integer, default=1)
    
    # Responses - stored as JSON
    responses = Column(Text, nullable=True)  # JSON of answers
    
    # Scoring
    raw_score = Column(Float, nullable=True)
    normalized_score = Column(Float, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(50), default="draft")  # draft, completed, reviewed
    reviewer_id = Column(String(36), nullable=True)
    
    # Notes
    clinical_notes = Column(Text, nullable=True)
