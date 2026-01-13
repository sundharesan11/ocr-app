"""Mistral Document AI OCR implementation."""

import base64
from typing import Any

from mistralai import Mistral

from src.config import get_settings
from src.ocr.base import BaseOCR, OCRError, OCRResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MistralOCR(BaseOCR):
    """OCR implementation using Mistral Document AI Basic OCR API.

    This is the primary OCR provider for the pipeline.

    Reference:
        https://docs.mistral.ai/capabilities/document_ai/basic_ocr

    PHI Safety:
        - Does not log extracted text
        - API calls use HTTPS
        - No local caching of results
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Mistral OCR client.

        Args:
            api_key: Mistral API key. If None, reads from environment.
        """
        settings = get_settings()
        self._api_key = api_key or settings.mistral_api_key
        if not self._api_key:
            raise ValueError("Mistral API key is required")
        self._client = Mistral(api_key=self._api_key)
        logger.info("Initialized Mistral OCR client")

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mistral"

    async def extract_text(self, images: list[bytes]) -> OCRResult:
        """Extract text from images using Mistral Document AI.

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
            import asyncio

            # Process pages sequentially with timeout for reliability
            pages_text: list[str] = []
            page_confidences: list[float] = []

            for idx, image_bytes in enumerate(images):
                logger.info(f"Processing page {idx + 1}/{len(images)}")

                try:
                    # Add 60-second timeout per page
                    result = await asyncio.wait_for(
                        self._process_single_page(idx, image_bytes), timeout=60.0
                    )
                    text, confidence = result
                    pages_text.append(text)
                    page_confidences.append(confidence)
                    logger.info(f"Page {idx + 1} complete")

                except asyncio.TimeoutError:
                    logger.warning(f"Page {idx + 1} timed out after 60s")
                    pages_text.append(f"[Page {idx + 1} timed out]")
                    page_confidences.append(0.1)

                except Exception as e:
                    logger.warning(f"Page {idx + 1} failed: {e}")
                    pages_text.append(f"[Page {idx + 1} extraction failed]")
                    page_confidences.append(0.2)

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
                metadata={"model": "pixtral-12b-2409", "provider": self.provider_name},
            )

        except Exception as e:
            logger.error("OCR extraction failed", error=str(e))
            raise OCRError(f"Failed to extract text: {e}", self.provider_name) from e

    async def _process_single_page(self, idx: int, image_bytes: bytes) -> tuple[str, float]:
        """Process a single page for OCR.

        Args:
            idx: Page index
            image_bytes: Image bytes

        Returns:
            Tuple of (extracted_text, confidence)
        """
        logger.debug(f"Processing page {idx + 1}")

        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Determine image type from bytes
        image_type = self._detect_image_type(image_bytes)

        # Call Mistral Document AI with vision model
        response = await self._client.chat.complete_async(
            model="pixtral-12b-2409",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:image/{image_type};base64,{image_b64}",
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this document image. "
                                "Include all handwritten and printed text. "
                                "Preserve the document structure and formatting. "
                                "Return only the extracted text, no commentary."
                            ),
                        },
                    ],
                }
            ],
        )

        # Extract text from response
        page_text = response.choices[0].message.content if response.choices else ""

        # Estimate confidence
        confidence = self._estimate_confidence(page_text, response)

        logger.debug(f"Page {idx + 1} complete")
        return page_text, confidence

    def _detect_image_type(self, image_bytes: bytes) -> str:
        """Detect image type from magic bytes.

        Args:
            image_bytes: Image file bytes

        Returns:
            Image MIME type suffix (jpeg, png, etc.)
        """
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if image_bytes[:2] == b"\xff\xd8":
            return "jpeg"
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "webp"
        # Default to jpeg for unknown
        return "jpeg"

    def _estimate_confidence(self, text: str, response: Any) -> float:
        """Estimate confidence score based on response quality.

        Mistral doesn't provide confidence scores, so we estimate based on:
        - Text length (very short suggests low quality scan)
        - Presence of common document markers
        - Response structure

        Args:
            text: Extracted text
            response: Raw API response

        Returns:
            Estimated confidence between 0.0 and 1.0
        """
        if not text or len(text.strip()) < 10:
            return 0.2

        # Base confidence
        confidence = 0.7

        # Boost for reasonable text length
        if len(text) > 100:
            confidence += 0.1

        # Boost for structured content (likely successful extraction)
        if any(marker in text.lower() for marker in ["name:", "date:", "address:", "phone:"]):
            confidence += 0.1

        # Cap at 0.95 (we can never be 100% certain without ground truth)
        return min(confidence, 0.95)
