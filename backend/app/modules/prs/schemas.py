"""
PRS Pydantic Schemas — request/response models for all PRS endpoints.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─── Scale Schemas ───

class ScaleOut(BaseModel):
    id: str
    scale_id: str
    short_name: str
    full_name: str
    category: str
    version: str
    scoring_type: str
    max_score: Optional[float] = None
    estimated_minutes: int
    is_active: bool
    is_clinician_rated: bool
    languages: list[str] = ["en"]

class ScaleDefinitionOut(ScaleOut):
    definition: dict[str, Any]

class ScaleListOut(BaseModel):
    scales: list[ScaleOut]
    total: int


# ─── Condition Battery Schemas ───

class ConditionBatteryOut(BaseModel):
    id: str
    condition_id: str
    label: str
    description: Optional[str] = None
    scale_ids: list[str]
    is_active: bool
    display_order: int

class ConditionListOut(BaseModel):
    conditions: list[ConditionBatteryOut]
    total: int

class ConditionBatteryCreate(BaseModel):
    condition_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    scale_ids: list[str] = Field(min_length=1)
    display_order: int = 0

class ConditionBatteryUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    scale_ids: Optional[list[str]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


# ─── Assessment Session Schemas ───

class SessionCreate(BaseModel):
    patient_id: str
    condition_id: Optional[str] = None
    custom_scale_ids: Optional[list[str]] = None
    title: Optional[str] = None
    clinical_notes: Optional[str] = None
    patient_instructions: Optional[str] = None
    mode: str = "self"  # self | clinician_administered | voice
    due_date: Optional[datetime] = None

class SessionOut(BaseModel):
    id: str
    patient_id: str
    assigned_by: str
    condition_id: Optional[str] = None
    resolved_scale_ids: list[str]
    title: Optional[str] = None
    clinical_notes: Optional[str] = None
    patient_instructions: Optional[str] = None
    mode: str
    status: str
    assigned_at: datetime
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    overall_severity: Optional[str] = None
    risk_flag_count: int = 0
    scales_completed: int = 0
    scales_total: int = 0
    report_blob_path: Optional[str] = None

class SessionDetailOut(SessionOut):
    scale_responses: list[ScaleResponseOut] = []
    risk_alerts: list[RiskAlertOut] = []

class SessionListOut(BaseModel):
    sessions: list[SessionOut]
    total: int

class SessionStatusUpdate(BaseModel):
    status: str  # in_progress | completed | cancelled | expired


# ─── Scale Response Schemas ───

class ResponseSubmit(BaseModel):
    responses: dict[str, Any]  # {"0": 2, "1": 1, ...}

class ResponseAutoSave(BaseModel):
    question_index: int
    value: Any

class ScaleResponseOut(BaseModel):
    id: str
    session_id: str
    scale_id: str
    responses: Optional[dict[str, Any]] = None
    total_score: Optional[float] = None
    max_possible_score: Optional[float] = None
    percentage: Optional[float] = None
    severity_level: Optional[str] = None
    severity_label: Optional[str] = None
    subscale_scores: Optional[dict[str, Any]] = None
    domain_scores: Optional[dict[str, Any]] = None
    component_scores: Optional[dict[str, Any]] = None
    is_positive: Optional[bool] = None
    vas_score: Optional[float] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    display_order: int = 0
    clinician_notes: Optional[str] = None

class ScoreResult(BaseModel):
    scale_id: str
    total_score: float
    max_possible_score: float
    percentage: float
    severity_level: Optional[str] = None
    severity_label: Optional[str] = None
    subscale_scores: Optional[dict[str, Any]] = None
    domain_scores: Optional[dict[str, Any]] = None
    component_scores: Optional[dict[str, Any]] = None
    is_positive: Optional[bool] = None
    vas_score: Optional[float] = None
    risk_flags: list[dict[str, Any]] = []


# ─── Risk Alert Schemas ───

class RiskAlertOut(BaseModel):
    id: str
    session_id: str
    patient_id: str
    alert_type: str
    severity: str
    message: str
    source_scale_id: Optional[str] = None
    source_question_index: Optional[int] = None
    source_value: Optional[float] = None
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

class RiskAlertListOut(BaseModel):
    alerts: list[RiskAlertOut]
    total: int

class RiskAlertAcknowledge(BaseModel):
    pass

class RiskAlertResolve(BaseModel):
    resolution_notes: str = Field(min_length=1)


# ─── Score History Schemas ───

class ScoreHistoryOut(BaseModel):
    id: str
    patient_id: str
    scale_id: str
    session_id: str
    total_score: float
    max_possible_score: Optional[float] = None
    percentage: Optional[float] = None
    severity_level: Optional[str] = None
    severity_label: Optional[str] = None
    recorded_at: datetime

class ScoreHistoryListOut(BaseModel):
    history: list[ScoreHistoryOut]
    total: int


# ─── Consent Schemas ───

class ConsentCreate(BaseModel):
    consent_type: str  # assessment_participation | data_storage | report_sharing
    consented: bool
    consent_text: Optional[str] = None

class ConsentOut(BaseModel):
    id: str
    patient_id: str
    session_id: Optional[str] = None
    consent_type: str
    consented: bool
    consented_at: datetime


# ─── Clinician Rating Schemas ───

class ClinicianRatingSubmit(BaseModel):
    responses: dict[str, Any]
    clinician_notes: Optional[str] = None


# Forward reference resolution
SessionDetailOut.model_rebuild()
