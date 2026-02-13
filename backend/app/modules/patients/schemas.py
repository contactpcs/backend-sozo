"""Patient schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    """Create patient request."""
    
    user_id: str
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    preferred_language: str = "en"


class PatientUpdate(BaseModel):
    """Update patient request."""
    
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    preferred_language: Optional[str] = None
    notes: Optional[str] = None


class PatientIntakeData(BaseModel):
    """Patient intake form data."""
    
    date_of_birth: datetime
    gender: str
    phone: str
    address: str
    emergency_contact: str


class PatientResponse(BaseModel):
    """Patient response schema."""
    
    id: str
    user_id: str
    mrn: Optional[str]
    date_of_birth: Optional[datetime]
    gender: Optional[str]
    phone: Optional[str]
    workflow_state: str
    assigned_clinician_id: Optional[str]
    intake_completed_at: Optional[datetime]
    last_assessment_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatientDetailResponse(PatientResponse):
    """Detailed patient response."""
    
    address: Optional[str]
    emergency_contact: Optional[str]
    notes: Optional[str]


class PatientSearchResponse(BaseModel):
    """Patient search result."""
    
    id: str
    mrn: Optional[str]
    user_name: str
    phone: Optional[str]
    workflow_state: str
    created_at: datetime
