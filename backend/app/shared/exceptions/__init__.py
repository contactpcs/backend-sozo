"""Base exception classes for the application."""
from typing import Any, Optional


class SozoException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SozoException):
    """Validation error - 400."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AuthenticationError(SozoException):
    """Authentication error - 401."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(SozoException):
    """Authorization error - 403."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


class NotFoundError(SozoException):
    """Resource not found - 404."""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404
        )


class ConflictError(SozoException):
    """Resource conflict - 409."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class IntegrityError(SozoException):
    """Data integrity violation."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="INTEGRITY_ERROR",
            status_code=400,
            details=details
        )


class InvalidStateTransition(SozoException):
    """Invalid workflow state transition."""
    
    def __init__(
        self,
        current_state: str,
        requested_state: str,
        allowed_transitions: list[str] = None
    ):
        message = f"Cannot transition from {current_state} to {requested_state}"
        details = {}
        if allowed_transitions:
            details["allowed_transitions"] = allowed_transitions
        
        super().__init__(
            message=message,
            error_code="INVALID_STATE_TRANSITION",
            status_code=400,
            details=details
        )


class DomainError(SozoException):
    """Domain logic error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="DOMAIN_ERROR",
            status_code=400,
            details=details
        )


class ExternalServiceError(SozoException):
    """External service integration error."""
    
    def __init__(self, service: str, message: str, details: Optional[dict] = None):
        full_message = f"Error from {service}: {message}"
        super().__init__(
            message=full_message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details=details
        )
