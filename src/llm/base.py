"""Base LLM interface - Abstract class for all LLM parsing providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseResult:
    """Result from LLM parsing.

    Attributes:
        data: Extracted structured data as dictionary
        field_confidences: Confidence score per field (0.0 to 1.0)
        overall_confidence: Overall parsing confidence
        raw_response: Raw response from the LLM provider
        metadata: Additional provider-specific metadata
    """

    data: dict[str, Any]
    field_confidences: dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    raw_response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_low_confidence_fields(self, threshold: float = 0.7) -> list[str]:
        """Get fields with confidence below threshold.

        Args:
            threshold: Confidence threshold (default 0.7)

        Returns:
            List of field names with low confidence
        """
        return [
            field_name
            for field_name, confidence in self.field_confidences.items()
            if confidence < threshold
        ]


class BaseLLM(ABC):
    """Abstract base class for LLM parsing providers.

    All LLM implementations must inherit from this class and implement
    the parse_to_json method.

    Example:
        class MyLLM(BaseLLM):
            async def parse_to_json(self, ocr_text: str, field_hints: list[str] | None) -> ParseResult:
                # Implementation here
                pass

    PHI Safety:
        - Implementations should NOT log parsed data
        - Use request IDs for tracing
        - Avoid storing extracted data to disk
    """

    @abstractmethod
    async def parse_to_json(
        self,
        ocr_text: str,
        field_hints: list[str] | None = None,
    ) -> ParseResult:
        """Parse OCR text into structured JSON.

        Args:
            ocr_text: Raw text from OCR extraction
            field_hints: Optional list of expected field names to guide extraction

        Returns:
            ParseResult containing structured data and confidence scores

        Raises:
            LLMError: If parsing fails
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the LLM provider."""
        pass


class LLMError(Exception):
    """Exception raised when LLM parsing fails."""

    def __init__(self, message: str, provider: str, details: dict[str, Any] | None = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")
