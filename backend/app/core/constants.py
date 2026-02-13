"""Application constants and enumerations."""
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    CLINICIAN = "clinician"
    NURSE = "nurse"
    PATIENT = "patient"
    CENTER_MANAGER = "center_manager"


class AssessmentStatus(str, Enum):
    """Assessment workflow states."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class EligibilityDecision(str, Enum):
    """Eligibility determination outcomes."""
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    CONDITIONAL = "conditional"
    PENDING_REVIEW = "pending_review"


class WorkflowState(str, Enum):
    """Workflow state machine states."""
    INTAKE = "intake"
    ASSESSMENT = "assessment"
    SCORING = "scoring"
    ROUTING = "routing"
    ASSIGNMENT = "assignment"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AuditAction(str, Enum):
    """Audit log action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    TRANSITION = "transition"
    CALCULATE = "calculate"
    ASSIGN = "assign"
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"


class DocumentType(str, Enum):
    """Document classification."""
    INTAKE_FORM = "intake_form"
    QUESTIONNAIRE = "questionnaire"
    ASSESSMENT = "assessment"
    PRS_REPORT = "prs_report"
    ELIGIBILITY_DECISION = "eligibility_decision"
    CLINICAL_NOTE = "clinical_note"
    SUPPORTING_DOCUMENT = "supporting_document"


# PRS Scoring Constants
PRS_MIN_SCORE = 0
PRS_MAX_SCORE = 100

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Token expiration (seconds)
ACCESS_TOKEN_EXPIRE_SECONDS = 3600
REFRESH_TOKEN_EXPIRE_SECONDS = 86400 * 7

# Request size limits
MAX_UPLOAD_SIZE_MB = 10
MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024
