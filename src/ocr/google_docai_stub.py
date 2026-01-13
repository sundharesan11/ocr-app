"""Google Document AI placeholder implementation.

This is a stub implementation that provides the interface for future
HIPAA-compliant Google Document AI integration.

When implementing:
1. Set up Google Cloud project with Document AI enabled
2. Create a processor for form parsing
3. Sign BAA with Google Cloud for HIPAA compliance
4. Update this implementation with actual API calls
"""

from src.ocr.base import BaseOCR, OCRError, OCRResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GoogleDocAIPlaceholder(BaseOCR):
    """Placeholder OCR implementation for Google Document AI.

    This stub provides the interface for future implementation of
    Google Document AI, which offers HIPAA-compliant document processing.

    To implement:
        1. Enable Document AI API in Google Cloud Console
        2. Create a form parser processor
        3. Sign Business Associate Agreement (BAA) with Google
        4. Replace this stub with actual implementation

    Reference:
        https://cloud.google.com/document-ai/docs

    HIPAA Notes:
        - Google Document AI can be HIPAA-compliant with BAA
        - Ensure US-region-only processing
        - Use VPC Service Controls for additional security
    """

    def __init__(
        self,
        project_id: str | None = None,
        location: str = "us",
        processor_id: str | None = None,
    ):
        """Initialize Google Document AI client.

        Args:
            project_id: Google Cloud project ID
            location: Processor location (should be 'us' for HIPAA)
            processor_id: Document AI processor ID
        """
        self._project_id = project_id
        self._location = location
        self._processor_id = processor_id
        logger.warning(
            "Google Document AI is a placeholder - not implemented",
            project_id=project_id,
            location=location,
        )

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "google_docai"

    async def extract_text(self, images: list[bytes]) -> OCRResult:
        """Extract text from images using Google Document AI.

        This is a placeholder that raises NotImplementedError.

        Args:
            images: List of image bytes

        Returns:
            OCRResult (not actually returned - raises instead)

        Raises:
            NotImplementedError: Always, as this is a placeholder
        """
        raise NotImplementedError(
            "Google Document AI is not yet implemented. "
            "To implement:\n"
            "1. Enable Document AI API in Google Cloud Console\n"
            "2. Create a form parser processor\n"
            "3. Sign BAA with Google Cloud for HIPAA compliance\n"
            "4. Implement the actual API calls in this class\n\n"
            "For now, please use 'mistral' or 'gemini' as the OCR provider."
        )


# Future implementation example (commented out):
"""
from google.cloud import documentai_v1 as documentai

class GoogleDocAI(BaseOCR):
    def __init__(self, project_id: str, location: str, processor_id: str):
        self._client = documentai.DocumentProcessorServiceClient()
        self._processor_name = (
            f"projects/{project_id}/locations/{location}/processors/{processor_id}"
        )

    async def extract_text(self, images: list[bytes]) -> OCRResult:
        pages_text = []
        for image_bytes in images:
            request = documentai.ProcessRequest(
                name=self._processor_name,
                raw_document=documentai.RawDocument(
                    content=image_bytes,
                    mime_type="application/pdf",  # or detect
                ),
            )
            result = self._client.process_document(request=request)
            pages_text.append(result.document.text)

        return OCRResult(
            text="\\n".join(pages_text),
            pages=pages_text,
            confidence=0.9,  # Document AI provides actual confidence
        )
"""
