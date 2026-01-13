"""OCR package - Abstract base and provider implementations."""

from src.ocr.base import BaseOCR, OCRResult
from src.ocr.factory import create_ocr_provider
from src.ocr.gemini_ocr import GeminiOCR
from src.ocr.google_docai_stub import GoogleDocAIPlaceholder
from src.ocr.mistral_ocr import MistralOCR

__all__ = [
    "BaseOCR",
    "OCRResult",
    "MistralOCR",
    "GeminiOCR",
    "GoogleDocAIPlaceholder",
    "create_ocr_provider",
]
