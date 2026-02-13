"""Center models."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Float, Integer

from app.shared.models import BaseModel


class Center(BaseModel):
    """Healthcare center model."""
    
    __tablename__ = "centers"
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(String(50), unique=True, nullable=False)  # Center identifier
    
    # Location
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Operations
    is_active = Column(Boolean, default=True)
    operating_hours = Column(Text, nullable=True)  # JSON
    
    # Capacity
    max_patient_capacity = Column(Integer, default=100)
    current_patient_count = Column(Integer, default=0)
    
    # Performance
    quality_score = Column(Float, default=75.0)  # 0-100
    patient_satisfaction_score = Column(Float, default=75.0)
    
    # Specializations (stored as JSON list)
    specialties = Column(Text, nullable=True)  # JSON array
    
    # Settings
    accepts_insurance = Column(Text, nullable=True)  # JSON array
    accepts_uninsured = Column(Boolean, default=False)
    supported_languages = Column(Text, default='["en"]')  # JSON array
    has_interpreters = Column(Boolean, default=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
