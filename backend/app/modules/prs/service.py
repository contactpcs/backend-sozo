"""
PRS Service — business logic layer for the Patient Rating System.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional

from . import repository as repo
from .scale_engine import calculate_score, validate_responses
from .risk_detector import evaluate_risk_alerts, get_overall_severity


# ─── Scales ───

def list_scales(active_only: bool = True) -> list[dict]:
    return repo.get_all_scales(active_only)


def get_scale(scale_id: str) -> dict:
    scale = repo.get_scale_by_id(scale_id)
    if not scale:
        raise ValueError(f"Scale '{scale_id}' not found")
    return scale


def get_scale_definition(scale_id: str) -> dict:
    """Get scale with full JSONB definition for rendering questionnaire."""
    return get_scale(scale_id)


# ─── Conditions ───

def list_conditions(active_only: bool = True) -> list[dict]:
    return repo.get_all_conditions(active_only)


def get_condition(condition_id: str) -> dict:
    condition = repo.get_condition_by_id(condition_id)
    if not condition:
        raise ValueError(f"Condition '{condition_id}' not found")
    return condition


def create_condition(data: dict, created_by: str) -> dict:
    data["id"] = str(uuid.uuid4())
    data["created_by"] = created_by
    return repo.create_condition(data)


def update_condition(condition_id: str, data: dict) -> dict:
    return repo.update_condition(condition_id, data)


# ─── Sessions ───

def create_session(
    patient_id: str,
    assigned_by: str,
    condition_id: Optional[str] = None,
    custom_scale_ids: Optional[list[str]] = None,
    title: Optional[str] = None,
    clinical_notes: Optional[str] = None,
    patient_instructions: Optional[str] = None,
    mode: str = "self",
    due_date: Optional[datetime] = None,
) -> dict:
    """Create an assessment session and pre-generate scale response stubs."""

    # Resolve which scales to include
    if condition_id:
        condition = get_condition(condition_id)
        resolved_scale_ids = condition.get("scale_ids", [])
    elif custom_scale_ids:
        resolved_scale_ids = custom_scale_ids
    else:
        raise ValueError("Either condition_id or custom_scale_ids is required")

    # Validate all scale IDs exist
    existing_scales = repo.get_scales_by_ids(resolved_scale_ids)
    existing_ids = {s["scale_id"] for s in existing_scales}
    invalid = [sid for sid in resolved_scale_ids if sid not in existing_ids]
    if invalid:
        raise ValueError(f"Invalid scale IDs: {invalid}")

    session_id = str(uuid.uuid4())
    session_data = {
        "id": session_id,
        "patient_id": patient_id,
        "assigned_by": assigned_by,
        "condition_id": condition_id,
        "custom_scale_ids": custom_scale_ids,
        "resolved_scale_ids": resolved_scale_ids,
        "title": title,
        "clinical_notes": clinical_notes,
        "patient_instructions": patient_instructions,
        "mode": mode,
        "status": "assigned",
        "due_date": due_date.isoformat() if due_date else None,
        "scales_total": len(resolved_scale_ids),
        "scales_completed": 0,
    }

    session = repo.create_session(session_data)

    # Create stub response records for each scale
    response_stubs = []
    for i, scale_id in enumerate(resolved_scale_ids):
        scale_data = next((s for s in existing_scales if s["scale_id"] == scale_id), {})
        is_clinician = scale_data.get("is_clinician_rated", False)
        response_stubs.append({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "scale_id": scale_id,
            "status": "clinician_pending" if is_clinician and mode == "self" else "pending",
            "display_order": i,
        })

    if response_stubs:
        repo.create_scale_responses_bulk(response_stubs)

    return session


def get_session(session_id: str) -> dict:
    session = repo.get_session_by_id(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found")
    return session


def get_session_detail(session_id: str) -> dict:
    """Session with all scale responses and risk alerts."""
    session = get_session(session_id)
    session["scale_responses"] = repo.get_session_responses(session_id)
    session["risk_alerts"] = repo.get_alerts_by_session(session_id)
    return session


def get_patient_sessions(patient_id: str) -> list[dict]:
    return repo.get_sessions_by_patient(patient_id)


def get_clinician_sessions(clinician_id: str) -> list[dict]:
    return repo.get_sessions_by_clinician(clinician_id)


def start_session(session_id: str) -> dict:
    return repo.update_session(session_id, {
        "status": "in_progress",
        "started_at": datetime.utcnow().isoformat(),
        "last_activity_at": datetime.utcnow().isoformat(),
    })


def cancel_session(session_id: str) -> dict:
    return repo.update_session(session_id, {"status": "cancelled"})


# ─── Responses & Scoring ───

def auto_save_response(
    session_id: str,
    scale_id: str,
    question_index: int,
    value: Any,
) -> dict:
    """Save a single answer (auto-save on each question)."""
    response = repo.get_scale_response(session_id, scale_id)
    if not response:
        raise ValueError(f"Scale response not found for {scale_id} in session {session_id}")

    current_responses = response.get("responses") or {}
    current_responses[str(question_index)] = value

    update_data = {
        "responses": current_responses,
        "status": "in_progress" if response["status"] == "pending" else response["status"],
        "started_at": response.get("started_at") or datetime.utcnow().isoformat(),
    }

    updated = repo.update_scale_response(response["id"], update_data)

    # Also update session last_activity_at
    repo.update_session(session_id, {
        "last_activity_at": datetime.utcnow().isoformat(),
        "status": "in_progress",
    })

    return updated


def submit_scale_response(
    session_id: str,
    scale_id: str,
    responses: dict[str, Any],
) -> dict:
    """Submit all answers for a scale, compute score, detect risks."""
    response_record = repo.get_scale_response(session_id, scale_id)
    if not response_record:
        raise ValueError(f"Scale response not found for {scale_id}")

    # Get scale definition for scoring
    scale = get_scale(scale_id)
    scale_config = scale.get("definition", scale)

    # Validate
    validation = validate_responses(responses, scale_config)
    if not validation["is_valid"]:
        raise ValueError(f"Missing required questions: {validation['missing_questions']}")

    # Score
    score_data = calculate_score(scale_id, responses, scale_config)

    # Build update
    now = datetime.utcnow().isoformat()
    started = response_record.get("started_at") or now
    time_taken = None
    if response_record.get("started_at"):
        try:
            start_dt = datetime.fromisoformat(response_record["started_at"])
            time_taken = int((datetime.utcnow() - start_dt).total_seconds())
        except (ValueError, TypeError):
            pass

    update_data = {
        "responses": responses,
        "total_score": score_data.get("total"),
        "max_possible_score": score_data.get("max_possible"),
        "percentage": score_data.get("percentage"),
        "severity_level": score_data.get("severity", {}).get("level") if score_data.get("severity") else None,
        "severity_label": score_data.get("severity", {}).get("label") if score_data.get("severity") else None,
        "subscale_scores": score_data.get("subscale_scores"),
        "domain_scores": score_data.get("domain_scores"),
        "component_scores": score_data.get("component_scores"),
        "is_positive": score_data.get("is_positive"),
        "vas_score": score_data.get("vas_score"),
        "status": "completed",
        "started_at": started,
        "completed_at": now,
        "time_taken_seconds": time_taken,
    }

    updated_response = repo.update_scale_response(response_record["id"], update_data)

    # Get session for context
    session = get_session(session_id)

    # Create risk alerts
    risk_alerts = evaluate_risk_alerts(
        score_data=score_data,
        patient_id=session["patient_id"],
        session_id=session_id,
        scale_response_id=response_record["id"],
        assigned_clinician_id=session.get("assigned_by"),
    )
    if risk_alerts:
        repo.create_risk_alerts_bulk(risk_alerts)

    # Create score history record
    repo.create_score_history({
        "id": str(uuid.uuid4()),
        "patient_id": session["patient_id"],
        "scale_id": scale_id,
        "session_id": session_id,
        "scale_response_id": response_record["id"],
        "total_score": score_data.get("total", 0),
        "max_possible_score": score_data.get("max_possible"),
        "percentage": score_data.get("percentage"),
        "severity_level": score_data.get("severity", {}).get("level") if score_data.get("severity") else None,
        "severity_label": score_data.get("severity", {}).get("label") if score_data.get("severity") else None,
    })

    # Update session progress
    all_responses = repo.get_session_responses(session_id)
    completed_count = sum(1 for r in all_responses if r.get("status") == "completed")
    all_done = completed_count >= session.get("scales_total", 0)

    session_update = {
        "scales_completed": completed_count,
        "risk_flag_count": len(risk_alerts) + session.get("risk_flag_count", 0),
        "last_activity_at": now,
    }

    if all_done:
        session_update["status"] = "completed"
        session_update["completed_at"] = now
        session_update["overall_severity"] = get_overall_severity(
            [r for r in all_responses if r.get("severity_level")]
        )

    repo.update_session(session_id, session_update)

    return {
        "response": updated_response,
        "score": score_data,
        "risk_alerts_created": len(risk_alerts),
        "session_completed": all_done,
    }


def submit_clinician_rating(
    session_id: str,
    scale_id: str,
    responses: dict[str, Any],
    rated_by: str,
    clinician_notes: Optional[str] = None,
) -> dict:
    """Submit a clinician-rated scale (EDSS, MADRS, MAS etc.)."""
    result = submit_scale_response(session_id, scale_id, responses)

    response_record = repo.get_scale_response(session_id, scale_id)
    if response_record:
        repo.update_scale_response(response_record["id"], {
            "rated_by": rated_by,
            "rated_at": datetime.utcnow().isoformat(),
            "clinician_notes": clinician_notes,
            "status": "clinician_completed",
        })

    return result


# ─── Risk Alerts ───

def get_patient_alerts(patient_id: str, status: Optional[str] = None) -> list[dict]:
    return repo.get_alerts_by_patient(patient_id, status)


def get_clinician_alerts(clinician_id: str, status: Optional[str] = None) -> list[dict]:
    return repo.get_alerts_by_clinician(clinician_id, status)


def acknowledge_alert(alert_id: str, acknowledged_by: str) -> dict:
    return repo.update_alert(alert_id, {
        "status": "acknowledged",
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": datetime.utcnow().isoformat(),
    })


def resolve_alert(alert_id: str, resolved_by: str, resolution_notes: str) -> dict:
    return repo.update_alert(alert_id, {
        "status": "resolved",
        "resolved_by": resolved_by,
        "resolved_at": datetime.utcnow().isoformat(),
        "resolution_notes": resolution_notes,
    })


# ─── Score History ───

def get_patient_score_history(
    patient_id: str,
    scale_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    return repo.get_score_history(patient_id, scale_id, limit)


# ─── Consent ───

def record_consent(
    patient_id: str,
    session_id: str,
    consent_type: str,
    consented: bool,
    consent_text: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    return repo.create_consent({
        "id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "session_id": session_id,
        "consent_type": consent_type,
        "consented": consented,
        "consent_text": consent_text,
        "ip_address": ip_address,
        "user_agent": user_agent,
    })


def get_session_consents(session_id: str) -> list[dict]:
    return repo.get_consents_by_session(session_id)
