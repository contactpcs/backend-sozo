"""Structured logging configuration."""
import json
import logging
import logging.config
import sys
from typing import Any

from .config import get_settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure application logging."""
    settings = get_settings()
    
    # Determine formatter
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add console handler
    root_logger.addHandler(console_handler)
    
    # Suppress verbose third-party loggers
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get logger instance with context support."""
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {})


def log_with_context(
    logger: logging.LoggerAdapter,
    level: str,
    message: str,
    user_id: str = None,
    request_id: str = None,
    **kwargs: Any
) -> None:
    """Log message with contextual information."""
    extra = {}
    if user_id:
        extra["user_id"] = user_id
    if request_id:
        extra["request_id"] = request_id
    
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=extra, **kwargs)
