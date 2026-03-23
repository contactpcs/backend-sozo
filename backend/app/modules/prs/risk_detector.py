"""
PRS Risk Detector — evaluates score data and creates risk alert records.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any


SEVERITY_ORDER = {"critical": 0, "high": 1, "moderate": 2, "low": 3}


def evaluate_risk_alerts(
    score_data: dict,
    patient_id: str,
    session_id: str,
    scale_response_id: str,
    assigned_clinician_id: str | None = None,
) -> list[dict]:
    """
    Convert raw risk flags from scale_engine into structured alert records
    ready for database insertion.
    """
    flags = score_data.get("risk_flags", [])
    alerts = []

    for flag in flags:
        alerts.append({
            "session_id": session_id,
            "scale_response_id": scale_response_id,
            "patient_id": patient_id,
            "assigned_clinician_id": assigned_clinician_id,
            "alert_type": flag.get("alert_type", "risk_flag"),
            "severity": flag.get("severity", "moderate"),
            "message": flag.get("message", ""),
            "source_scale_id": flag.get("scale_id"),
            "source_question_index": flag.get("source_question_index"),
            "source_value": flag.get("source_value"),
            "status": "active",
        })

    return sorted(alerts, key=lambda a: SEVERITY_ORDER.get(a["severity"], 99))


def get_overall_severity(
    scale_responses: list[dict],
) -> str:
    """
    Determine the worst severity across all completed scales in a session.
    Returns: 'minimal' | 'mild' | 'moderate' | 'severe' | 'critical'
    """
    severity_rank = {
        "minimal": 0, "normal": 0,
        "mild": 1,
        "moderate": 2,
        "moderately-severe": 3,
        "severe": 4,
        "extremely-severe": 5,
        "critical": 6,
    }
    worst = 0
    for resp in scale_responses:
        level = (resp.get("severity_level") or "").lower()
        rank = severity_rank.get(level, 0)
        if rank > worst:
            worst = rank

    reverse_map = {v: k for k, v in severity_rank.items()}
    return reverse_map.get(worst, "minimal")
