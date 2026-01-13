"""PHI-safe logging utilities.

This module provides logging utilities that automatically redact
Protected Health Information (PHI) to ensure HIPAA compliance.
"""

import logging
import re
import sys
from typing import Any

from src.config import get_settings

# Patterns that may contain PHI - these will be redacted
PHI_PATTERNS = [
    # SSN
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]"),
    # Phone numbers
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED-PHONE]"),
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED-EMAIL]"),
    # Dates of birth (various formats)
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "[REDACTED-DATE]"),
    # Medical record numbers (common patterns)
    (r"\bMRN[:\s]*\d+\b", "[REDACTED-MRN]"),
    # Names after common prefixes (basic pattern)
    (r"\b(patient|name)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "[REDACTED-NAME]"),
]


class PHISafeFormatter(logging.Formatter):
    """Formatter that redacts PHI from log messages."""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        redact_phi: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.redact_phi = redact_phi
        self._compiled_patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in PHI_PATTERNS]

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, redacting PHI if enabled."""
        message = super().format(record)

        if self.redact_phi:
            message = self._redact(message)

        return message

    def _redact(self, text: str) -> str:
        """Redact PHI patterns from text."""
        for pattern, replacement in self._compiled_patterns:
            text = pattern.sub(replacement, text)
        return text


class PHISafeLogger:
    """Logger wrapper that ensures PHI is never logged.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request", request_id="abc123")
        logger.error("Failed to process", error=str(e))

    PHI Safety:
        - Never log raw OCR text or extracted data
        - Never log file contents
        - Use request_id for tracing instead of PHI
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._setup_handler()

    def _setup_handler(self) -> None:
        """Set up the log handler with PHI-safe formatting."""
        if not self._logger.handlers:
            settings = get_settings()

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(settings.log_level)

            # Use JSON-like format for production, readable format for dev
            if settings.is_production:
                fmt = '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
            else:
                fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

            handler.setFormatter(PHISafeFormatter(fmt, redact_phi=True))
            self._logger.addHandler(handler)
            self._logger.setLevel(settings.log_level)

    def _format_kwargs(self, kwargs: dict[str, Any]) -> str:
        """Format keyword arguments for logging."""
        if not kwargs:
            return ""
        return " | " + " ".join(f"{k}={v}" for k, v in kwargs.items())

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(f"{message}{self._format_kwargs(kwargs)}")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(f"{message}{self._format_kwargs(kwargs)}")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(f"{message}{self._format_kwargs(kwargs)}")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(f"{message}{self._format_kwargs(kwargs)}")

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._logger.critical(f"{message}{self._format_kwargs(kwargs)}")

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(f"{message}{self._format_kwargs(kwargs)}")


def get_logger(name: str) -> PHISafeLogger:
    """Get a PHI-safe logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        PHISafeLogger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing document", request_id="abc123", page_count=5)
    """
    return PHISafeLogger(name)


# Pre-configured logger for quick imports
logger = get_logger("medical_ocr")
