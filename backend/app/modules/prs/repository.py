"""
PRS Repository — data access layer for all PRS tables via Supabase.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from app.core.database import get_supabase_client


def _client():
    return get_supabase_client()


# ─── Scales ───

def get_all_scales(active_only: bool = True) -> list[dict]:
    query = _client().table("prs_scales").select("*")
    if active_only:
        query = query.eq("is_active", True).eq("is_deleted", False)
    result = query.order("short_name").execute()
    return result.data or []


def get_scale_by_id(scale_id: str) -> Optional[dict]:
    result = (
        _client().table("prs_scales")
        .select("*")
        .eq("scale_id", scale_id)
        .eq("is_deleted", False)
        .single()
        .execute()
    )
    return result.data


def get_scales_by_ids(scale_ids: list[str]) -> list[dict]:
    result = (
        _client().table("prs_scales")
        .select("*")
        .in_("scale_id", scale_ids)
        .eq("is_deleted", False)
        .execute()
    )
    return result.data or []


# ─── Condition Batteries ───

def get_all_conditions(active_only: bool = True) -> list[dict]:
    query = _client().table("prs_condition_batteries").select("*")
    if active_only:
        query = query.eq("is_active", True).eq("is_deleted", False)
    result = query.order("display_order").execute()
    return result.data or []


def get_condition_by_id(condition_id: str) -> Optional[dict]:
    result = (
        _client().table("prs_condition_batteries")
        .select("*")
        .eq("condition_id", condition_id)
        .eq("is_deleted", False)
        .single()
        .execute()
    )
    return result.data


def create_condition(data: dict) -> dict:
    result = _client().table("prs_condition_batteries").insert(data).execute()
    return result.data[0] if result.data else {}


def update_condition(condition_id: str, data: dict) -> dict:
    data["updated_at"] = datetime.utcnow().isoformat()
    result = (
        _client().table("prs_condition_batteries")
        .update(data)
        .eq("condition_id", condition_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ─── Assessment Sessions ───

def create_session(data: dict) -> dict:
    result = _client().table("prs_assessment_sessions").insert(data).execute()
    return result.data[0] if result.data else {}


def get_session_by_id(session_id: str) -> Optional[dict]:
    result = (
        _client().table("prs_assessment_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("is_deleted", False)
        .single()
        .execute()
    )
    return result.data


def get_sessions_by_patient(patient_id: str) -> list[dict]:
    result = (
        _client().table("prs_assessment_sessions")
        .select("*")
        .eq("patient_id", patient_id)
        .eq("is_deleted", False)
        .order("assigned_at", desc=True)
        .execute()
    )
    return result.data or []


def get_sessions_by_clinician(clinician_id: str) -> list[dict]:
    result = (
        _client().table("prs_assessment_sessions")
        .select("*")
        .eq("assigned_by", clinician_id)
        .eq("is_deleted", False)
        .order("assigned_at", desc=True)
        .execute()
    )
    return result.data or []


def update_session(session_id: str, data: dict) -> dict:
    data["updated_at"] = datetime.utcnow().isoformat()
    result = (
        _client().table("prs_assessment_sessions")
        .update(data)
        .eq("id", session_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ─── Scale Responses ───

def create_scale_response(data: dict) -> dict:
    result = _client().table("prs_scale_responses").insert(data).execute()
    return result.data[0] if result.data else {}


def create_scale_responses_bulk(responses: list[dict]) -> list[dict]:
    result = _client().table("prs_scale_responses").insert(responses).execute()
    return result.data or []


def get_scale_response(session_id: str, scale_id: str) -> Optional[dict]:
    result = (
        _client().table("prs_scale_responses")
        .select("*")
        .eq("session_id", session_id)
        .eq("scale_id", scale_id)
        .eq("is_deleted", False)
        .single()
        .execute()
    )
    return result.data


def get_session_responses(session_id: str) -> list[dict]:
    result = (
        _client().table("prs_scale_responses")
        .select("*")
        .eq("session_id", session_id)
        .eq("is_deleted", False)
        .order("display_order")
        .execute()
    )
    return result.data or []


def update_scale_response(response_id: str, data: dict) -> dict:
    data["updated_at"] = datetime.utcnow().isoformat()
    result = (
        _client().table("prs_scale_responses")
        .update(data)
        .eq("id", response_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ─── Risk Alerts ───

def create_risk_alert(data: dict) -> dict:
    result = _client().table("prs_risk_alerts").insert(data).execute()
    return result.data[0] if result.data else {}


def create_risk_alerts_bulk(alerts: list[dict]) -> list[dict]:
    if not alerts:
        return []
    result = _client().table("prs_risk_alerts").insert(alerts).execute()
    return result.data or []


def get_alerts_by_patient(patient_id: str, status: Optional[str] = None) -> list[dict]:
    query = (
        _client().table("prs_risk_alerts")
        .select("*")
        .eq("patient_id", patient_id)
    )
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


def get_alerts_by_clinician(clinician_id: str, status: Optional[str] = None) -> list[dict]:
    query = (
        _client().table("prs_risk_alerts")
        .select("*")
        .eq("assigned_clinician_id", clinician_id)
    )
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


def get_alerts_by_session(session_id: str) -> list[dict]:
    result = (
        _client().table("prs_risk_alerts")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def update_alert(alert_id: str, data: dict) -> dict:
    data["updated_at"] = datetime.utcnow().isoformat()
    result = (
        _client().table("prs_risk_alerts")
        .update(data)
        .eq("id", alert_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ─── Score History ───

def create_score_history(data: dict) -> dict:
    result = _client().table("prs_score_history").insert(data).execute()
    return result.data[0] if result.data else {}


def get_score_history(
    patient_id: str,
    scale_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    query = (
        _client().table("prs_score_history")
        .select("*")
        .eq("patient_id", patient_id)
    )
    if scale_id:
        query = query.eq("scale_id", scale_id)
    result = query.order("recorded_at", desc=True).limit(limit).execute()
    return result.data or []


# ─── Patient Consents ───

def create_consent(data: dict) -> dict:
    result = _client().table("prs_patient_consents").insert(data).execute()
    return result.data[0] if result.data else {}


def get_consents_by_session(session_id: str) -> list[dict]:
    result = (
        _client().table("prs_patient_consents")
        .select("*")
        .eq("session_id", session_id)
        .order("consented_at", desc=True)
        .execute()
    )
    return result.data or []
