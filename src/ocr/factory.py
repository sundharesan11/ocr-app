"""Factory for creating OCR provider instances."""

from src.config import OCRProvider, get_settings
from src.ocr.base import BaseOCR
from src.ocr.gemini_ocr import GeminiOCR
from src.ocr.google_docai_stub import GoogleDocAIPlaceholder
from src.ocr.mistral_ocr import MistralOCR


def create_ocr_provider(provider: OCRProvider | str) -> BaseOCR:
    """Create an OCR provider instance based on the provider type.

    Args:
        provider: OCR provider type (enum or string)

    Returns:
        Configured OCR provider instance

    Raises:
        ValueError: If provider type is unknown or not configured

    Example:
        ocr = create_ocr_provider(OCRProvider.MISTRAL)
        result = await ocr.extract_text([image_bytes])
    """
    settings = get_settings()

    # Convert string to enum if needed
    if isinstance(provider, str):
        provider = OCRProvider(provider.lower())

    # Validate the provider has required configuration
    settings.validate_ocr_provider(provider)

    if provider == OCRProvider.MISTRAL:
        return MistralOCR(api_key=settings.mistral_api_key)
    elif provider == OCRProvider.GEMINI:
        return GeminiOCR(api_key=settings.gemini_api_key)
    elif provider == OCRProvider.GOOGLE_DOCAI:
        return GoogleDocAIPlaceholder(
            project_id=settings.google_docai_project_id,
            location=settings.google_docai_location,
            processor_id=settings.google_docai_processor_id,
        )
    else:
        raise ValueError(f"Unknown OCR provider: {provider}")
