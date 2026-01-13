"""API request and response models."""

import base64
from typing import Any

from pydantic import BaseModel, Field

from src.config import LLMProvider, OCRProvider


class ProcessRequestParams(BaseModel):
    """Query parameters for process request.

    These are separate from the file upload and can be passed as form fields.
    """

    ocr_provider: OCRProvider = Field(
        default=OCRProvider.MISTRAL,
        description="OCR provider to use for text extraction",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.GEMINI,
        description="LLM provider to use for parsing OCR text",
    )
    field_hints: list[str] | None = Field(
        default=None,
        description="Optional list of expected field names to guide extraction",
    )


class FieldConfidence(BaseModel):
    """Confidence information for a single field."""

    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)


class ProcessResponse(BaseModel):
    """Response from document processing.

    Contains extracted data, confidence scores, and optionally the filled PDF.
    """

    # Extracted data
    extracted_data: dict[str, Any] = Field(
        description="Structured data extracted from the document"
    )

    # Filled PDF (base64 encoded)
    filled_pdf_base64: str | None = Field(
        default=None,
        description="Filled PDF as base64-encoded string (if input was PDF)",
    )

    # Confidence scores
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence score (weighted average of OCR and LLM)",
    )
    ocr_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="OCR text extraction confidence",
    )
    llm_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM parsing confidence",
    )
    field_confidences: dict[str, float] = Field(
        default_factory=dict,
        description="Per-field confidence scores",
    )

    # Processing info
    processing_time_ms: int = Field(description="Total processing time in milliseconds")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metadata",
    )

    @classmethod
    def from_process_result(cls, result) -> "ProcessResponse":
        """Create response from ProcessResult.

        Args:
            result: ProcessResult from pipeline

        Returns:
            ProcessResponse instance
        """
        filled_pdf_b64 = None
        if result.filled_pdf:
            filled_pdf_b64 = base64.b64encode(result.filled_pdf).decode("utf-8")

        return cls(
            extracted_data=result.extracted_data,
            filled_pdf_base64=filled_pdf_b64,
            confidence_score=result.overall_confidence,
            ocr_confidence=result.ocr_confidence,
            llm_confidence=result.llm_confidence,
            field_confidences=result.field_confidences,
            processing_time_ms=result.processing_time_ms,
            metadata=result.metadata,
        )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str | None = None
    stage: str | None = None
