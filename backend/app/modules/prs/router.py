"""
PRS Router — all API endpoints for the Patient Rating System.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from app.core.dependencies import get_current_user, require_roles
from app.shared.schemas.auth import JWTClaims
from . import service
from .schemas import (
    ScaleOut, ScaleDefinitionOut, ScaleListOut,
    ConditionBatteryOut, ConditionListOut, ConditionBatteryCreate, ConditionBatteryUpdate,
    SessionCreate, SessionOut, SessionDetailOut, SessionListOut, SessionStatusUpdate,
    ResponseSubmit, ResponseAutoSave, ScaleResponseOut, ScoreResult,
    RiskAlertOut, RiskAlertListOut, RiskAlertAcknowledge, RiskAlertResolve,
    ScoreHistoryOut, ScoreHistoryListOut,
    ConsentCreate, ConsentOut,
    ClinicianRatingSubmit,
)

router = APIRouter(prefix="/prs", tags=["PRS"])


# ─── Health Check ───

@router.get("/health")
async def prs_health():
    return {"status": "ok", "module": "prs"}


# ─── Scales ───

@router.get("/scales", response_model=ScaleListOut)
async def list_scales(
    active_only: bool = True,
    _user: JWTClaims = Depends(get_current_user),
):
    scales = service.list_scales(active_only)
    return {"scales": scales, "total": len(scales)}


@router.get("/scales/{scale_id}")
async def get_scale(
    scale_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    try:
        return service.get_scale_definition(scale_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Conditions ───

@router.get("/conditions", response_model=ConditionListOut)
async def list_conditions(
    active_only: bool = True,
    _user: JWTClaims = Depends(get_current_user),
):
    conditions = service.list_conditions(active_only)
    return {"conditions": conditions, "total": len(conditions)}


@router.get("/conditions/{condition_id}", response_model=ConditionBatteryOut)
async def get_condition(
    condition_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    try:
        return service.get_condition(condition_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conditions", response_model=ConditionBatteryOut, status_code=201)
async def create_condition(
    body: ConditionBatteryCreate,
    user: JWTClaims = Depends(require_roles("doctor", "platform_admin", "clinical_admin")),
):
    return service.create_condition(body.model_dump(), user.user_id)


@router.patch("/conditions/{condition_id}", response_model=ConditionBatteryOut)
async def update_condition(
    condition_id: str,
    body: ConditionBatteryUpdate,
    _user: JWTClaims = Depends(require_roles("doctor", "platform_admin", "clinical_admin")),
):
    return service.update_condition(condition_id, body.model_dump(exclude_none=True))


# ─── Sessions ───

@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant", "platform_admin")),
):
    try:
        return service.create_session(
            patient_id=body.patient_id,
            assigned_by=user.user_id,
            condition_id=body.condition_id,
            custom_scale_ids=body.custom_scale_ids,
            title=body.title,
            clinical_notes=body.clinical_notes,
            patient_instructions=body.patient_instructions,
            mode=body.mode,
            due_date=body.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/my", response_model=SessionListOut)
async def get_my_sessions(
    user: JWTClaims = Depends(get_current_user),
):
    """Get sessions for current user (patient sees their own, clinician sees assigned)."""
    roles = user.roles if isinstance(user.roles, list) else [user.roles]
    if "patient" in roles:
        sessions = service.get_patient_sessions(user.user_id)
    else:
        sessions = service.get_clinician_sessions(user.user_id)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/patient/{patient_id}", response_model=SessionListOut)
async def get_patient_sessions(
    patient_id: str,
    _user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant", "platform_admin")),
):
    sessions = service.get_patient_sessions(patient_id)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
async def get_session_detail(
    session_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    try:
        return service.get_session_detail(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/sessions/{session_id}/start", response_model=SessionOut)
async def start_session(
    session_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    return service.start_session(session_id)


@router.patch("/sessions/{session_id}/cancel", response_model=SessionOut)
async def cancel_session(
    session_id: str,
    _user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant", "platform_admin")),
):
    return service.cancel_session(session_id)


# ─── Scale Responses ───

@router.get("/sessions/{session_id}/responses", response_model=list[ScaleResponseOut])
async def get_session_responses(
    session_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    return service.get_session_detail(session_id).get("scale_responses", [])


@router.patch("/sessions/{session_id}/responses/{scale_id}/auto-save")
async def auto_save_response(
    session_id: str,
    scale_id: str,
    body: ResponseAutoSave,
    _user: JWTClaims = Depends(get_current_user),
):
    try:
        return service.auto_save_response(
            session_id, scale_id, body.question_index, body.value
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/responses/{scale_id}/submit")
async def submit_scale_response(
    session_id: str,
    scale_id: str,
    body: ResponseSubmit,
    _user: JWTClaims = Depends(get_current_user),
):
    try:
        return service.submit_scale_response(session_id, scale_id, body.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/responses/{scale_id}/clinician-rating")
async def submit_clinician_rating(
    session_id: str,
    scale_id: str,
    body: ClinicianRatingSubmit,
    user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant")),
):
    try:
        return service.submit_clinician_rating(
            session_id, scale_id, body.responses,
            rated_by=user.user_id,
            clinician_notes=body.clinician_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Risk Alerts ───

@router.get("/alerts/my", response_model=RiskAlertListOut)
async def get_my_alerts(
    status: Optional[str] = None,
    user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant", "platform_admin")),
):
    alerts = service.get_clinician_alerts(user.user_id, status)
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/alerts/patient/{patient_id}", response_model=RiskAlertListOut)
async def get_patient_alerts(
    patient_id: str,
    status: Optional[str] = None,
    _user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant", "platform_admin")),
):
    alerts = service.get_patient_alerts(patient_id, status)
    return {"alerts": alerts, "total": len(alerts)}


@router.patch("/alerts/{alert_id}/acknowledge", response_model=RiskAlertOut)
async def acknowledge_alert(
    alert_id: str,
    user: JWTClaims = Depends(require_roles("doctor", "clinical_assistant")),
):
    return service.acknowledge_alert(alert_id, user.user_id)


@router.patch("/alerts/{alert_id}/resolve", response_model=RiskAlertOut)
async def resolve_alert(
    alert_id: str,
    body: RiskAlertResolve,
    user: JWTClaims = Depends(require_roles("doctor")),
):
    return service.resolve_alert(alert_id, user.user_id, body.resolution_notes)


# ─── Score History ───

@router.get("/history/{patient_id}", response_model=ScoreHistoryListOut)
async def get_score_history(
    patient_id: str,
    scale_id: Optional[str] = None,
    limit: int = 50,
    _user: JWTClaims = Depends(get_current_user),
):
    history = service.get_patient_score_history(patient_id, scale_id, limit)
    return {"history": history, "total": len(history)}


# ─── Consent ───

@router.post("/sessions/{session_id}/consent", response_model=ConsentOut, status_code=201)
async def record_consent(
    session_id: str,
    body: ConsentCreate,
    request: Request,
    user: JWTClaims = Depends(get_current_user),
):
    return service.record_consent(
        patient_id=user.user_id,
        session_id=session_id,
        consent_type=body.consent_type,
        consented=body.consented,
        consent_text=body.consent_text,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/sessions/{session_id}/consents", response_model=list[ConsentOut])
async def get_session_consents(
    session_id: str,
    _user: JWTClaims = Depends(get_current_user),
):
    return service.get_session_consents(session_id)
