"""Document models."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer

from app.shared.models import BaseModel


class Document(BaseModel):
    """Document model."""
    
    __tablename__ = "documents"
    
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    document_type = Column(String(50), nullable=False)  # intake_form, questionnaire, etc.
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Azure Blob Storage path
    file_size_bytes = Column(Integer, nullable=False)
    file_mime_type = Column(String(50), nullable=True)
    
    # Metadata
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    
    # Processing
    extracted_text = Column(Text, nullable=True)  # OCR/extraction result
    is_processed = Column(Boolean, default=False)
    processing_errors = Column(Text, nullable=True)
    
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __mapper_args__ = {
        "polymorphic_identity": "document",
    }
