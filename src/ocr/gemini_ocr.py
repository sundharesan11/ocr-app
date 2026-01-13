"""Gemini Vision API OCR implementation."""

import base64

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from src.config import get_settings
from src.ocr.base import BaseOCR, OCRError, OCRResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GeminiOCR(BaseOCR):
    """OCR implementation using Gemini Vision API.

    This is the secondary OCR provider, used when Mistral is not selected.

    Reference:
        https://ai.google.dev/gemini-api/docs/image-understanding

    PHI Safety:
        - Does not log extracted text
        - API calls use HTTPS
        - No local caching of results
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Gemini OCR client.

        Args:
            api_key: Gemini API key. If None, reads from environment.
        """
        settings = get_settings()
        self._api_key = api_key or settings.gemini_api_key
        if not self._api_key:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Initialized Gemini OCR client")

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "gemini"

    async def extract_text(self, images: list[bytes]) -> OCRResult:
        """Extract text from images using Gemini Vision.

        Args:
            images: List of image bytes

        Returns:
            OCRResult with extracted text and confidence

        Raises:
            OCRError: If extraction fails
        """
        if not images:
            raise OCRError("No images provided", self.provider_name)

        logger.info("Starting OCR extraction", page_count=len(images))

        try:
            pages_text: list[str] = []
            page_confidences: list[float] = []

            for idx, image_bytes in enumerate(images):
                logger.debug(f"Processing page {idx + 1}/{len(images)}")

                # Detect image type
                mime_type = self._detect_mime_type(image_bytes)

                # Create image part for Gemini
                image_part = {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                }

                # Call Gemini Vision
                response = await self._model.generate_content_async(
                    [
                        image_part,
                        (
                            "Extract all text from this document image. "
                            "Include all handwritten and printed text. "
                            "Preserve the document structure and formatting as much as possible. "
                            "Return only the extracted text, no additional commentary or explanation."
                        ),
                    ],
                    generation_config=GenerationConfig(
                        temperature=0.1,  # Low temperature for accuracy
                        max_output_tokens=8192,
                    ),
                )

                # Extract text from response
                page_text = response.text if response.text else ""
                pages_text.append(page_text)

                # Estimate confidence based on response
                confidence = self._estimate_confidence(page_text, response)
                page_confidences.append(confidence)

            # Combine all pages
            combined_text = "\n\n--- Page Break ---\n\n".join(pages_text)
            overall_confidence = (
                sum(page_confidences) / len(page_confidences) if page_confidences else 0.0
            )

            logger.info(
                "OCR extraction complete",
                page_count=len(images),
                confidence=f"{overall_confidence:.2f}",
            )

            return OCRResult(
                text=combined_text,
                pages=pages_text,
                confidence=overall_confidence,
                page_confidences=page_confidences,
                metadata={"model": "gemini-2.0-flash", "provider": self.provider_name},
            )

        except Exception as e:
            logger.error("OCR extraction failed", error=str(e))
            raise OCRError(f"Failed to extract text: {e}", self.provider_name) from e

    def _detect_mime_type(self, image_bytes: bytes) -> str:
        """Detect MIME type from magic bytes.

        Args:
            image_bytes: Image file bytes

        Returns:
            MIME type string
        """
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if image_bytes[:2] == b"\xff\xd8":
            return "image/jpeg"
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        if image_bytes[4:12] == b"ftypheic" or image_bytes[4:12] == b"ftypmif1":
            return "image/heic"
        # Default to jpeg
        return "image/jpeg"

    def _estimate_confidence(self, text: str, response) -> float:
        """Estimate confidence score based on response quality.

        Args:
            text: Extracted text
            response: Raw API response

        Returns:
            Estimated confidence between 0.0 and 1.0
        """
        if not text or len(text.strip()) < 10:
            return 0.2

        # Base confidence for Gemini
        confidence = 0.75

        # Boost for reasonable text length
        if len(text) > 100:
            confidence += 0.1

        # Boost for structured content
        if any(marker in text.lower() for marker in ["name:", "date:", "address:", "phone:"]):
            confidence += 0.1

        # Check for safety ratings - lower confidence if content was filtered
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "safety_ratings"):
                # If any safety rating blocked content, reduce confidence
                for rating in candidate.safety_ratings:
                    if hasattr(rating, "blocked") and rating.blocked:
                        confidence -= 0.2
                        break

        return min(max(confidence, 0.0), 0.95)
