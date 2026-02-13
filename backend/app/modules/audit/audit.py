"""Audit logging module."""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging


logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Audit action types."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"
    TRANSITION = "TRANSITION"
    CALCULATE = "CALCULATE"
    ASSIGN = "ASSIGN"
    APPROVE = "APPROVE"


@dataclass
class AuditLog:
    """Audit log entry."""
    
    actor_id: str  # User performing action
    action: str  # AuditAction
    entity_type: str  # e.g., "Patient", "Assessment"
    entity_id: str
    changes: Optional[Dict[str, Any]] = None  # What changed
    metadata: Optional[Dict[str, Any]] = None  # Extra context
    timestamp: datetime = None  # Set automatically
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AuditService:
    """
    Centralized audit logging service.
    
    Records all state changes and important actions for compliance.
    """
    
    def __init__(self):
        """Initialize audit service."""
        self.adapter = None  # Can be injected for persistence
    
    async def log_action(
        self,
        actor_id: str,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        changes: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            actor_id: User ID performing the action
            action: Type of action (from AuditAction enum)
            entity_type: Type of entity being acted upon
            entity_id: ID of the entity
            changes: Dictionary of what changed (before/after)
            metadata: Additional context
        
        Returns:
            Created AuditLog
        """
        audit_log = AuditLog(
            actor_id=actor_id,
            action=action.value if isinstance(action, AuditAction) else action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            metadata=metadata
        )
        
        # Log to structured logging
        logger.info(
            f"Audit: {action.value} {entity_type} {entity_id}",
            extra={
                "audit": audit_log.to_dict()
            }
        )
        
        # Persist to database/audit store if adapter available
        if self.adapter:
            await self.adapter.store(audit_log)
        
        return audit_log
    
    async def log_state_transition(
        self,
        actor_id: str,
        entity_type: str,
        entity_id: str,
        from_state: str,
        to_state: str,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log workflow state transition."""
        changes = {
            "from": from_state,
            "to": to_state
        }
        
        return await self.log_action(
            actor_id=actor_id,
            action=AuditAction.TRANSITION,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            metadata=metadata
        )
    
    async def log_calculation(
        self,
        actor_id: str,
        calculation_type: str,
        entity_id: str,
        result: Any,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log calculation/scoring event."""
        meta = metadata or {}
        meta["calculation_type"] = calculation_type
        meta["result"] = result
        
        return await self.log_action(
            actor_id=actor_id,
            action=AuditAction.CALCULATE,
            entity_type="Scoring",
            entity_id=entity_id,
            metadata=meta
        )
    
    async def log_assignment(
        self,
        actor_id: str,
        patient_id: str,
        assigned_to: str,
        assignment_type: str,  # "center", "clinician", etc.
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """Log assignment action."""
        meta = metadata or {}
        meta["assigned_to"] = assigned_to
        meta["assignment_type"] = assignment_type
        
        changes = {
            "assigned_to": assigned_to
        }
        
        return await self.log_action(
            actor_id=actor_id,
            action=AuditAction.ASSIGN,
            entity_type="Patient",
            entity_id=patient_id,
            changes=changes,
            metadata=meta
        )


# Global audit service instance
audit_service = AuditService()
