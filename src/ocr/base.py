"""Base OCR interface - Abstract class for all OCR providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRResult:
    """Result from OCR processing.

    Attributes:
        text: Extracted text from all pages combined
        pages: List of extracted text per page
        confidence: Overall confidence score (0.0 to 1.0)
        page_confidences: Confidence score per page
        metadata: Additional provider-specific metadata
        raw_response: Raw response from the OCR provider (for debugging)
    """

    text: str
    pages: list[str] = field(default_factory=list)
    confidence: float = 0.0
    page_confidences: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_response: Any = None

    def __post_init__(self) -> None:
        """Validate the result."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class BaseOCR(ABC):
    """Abstract base class for OCR providers.

    All OCR implementations must inherit from this class and implement
    the extract_text method.

    Example:
        class MyOCR(BaseOCR):
            async def extract_text(self, images: list[bytes]) -> OCRResult:
                # Implementation here
                pass

    PHI Safety:
        - Implementations should NOT log extracted text
        - Use request IDs for tracing
        - Avoid storing images or text to disk
    """

    @abstractmethod
    async def extract_text(self, images: list[bytes]) -> OCRResult:
        """Extract text from images.

        Args:
            images: List of image bytes (one per page/image)
                   Supported formats: JPEG, PNG, HEIC, PDF pages as images

        Returns:
            OCRResult containing extracted text and confidence scores

        Raises:
            OCRError: If text extraction fails
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the OCR provider."""
        pass


class OCRError(Exception):
    """Exception raised when OCR processing fails."""

    def __init__(self, message: str, provider: str, details: dict[str, Any] | None = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")
