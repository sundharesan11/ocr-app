"""Vision-based extraction with position detection for text overlay.

Uses Mistral Vision (pixtral-12b) to extract field values and their
positions from document images for text overlay on regular PDFs.
"""

import base64
import json
from dataclasses import dataclass
import io

from mistralai import Mistral
from PIL import Image

from src.config import get_settings
from src.llm.prompts import POSITION_EXTRACTION_SYSTEM_PROMPT, get_position_extraction_prompt
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FieldWithPosition:
    """Extracted field with position information."""

    name: str
    value: str | None
    x_percent: float  # 0-100
    y_percent: float  # 0-100
    width_percent: float  # 0-100
    height_percent: float  # 0-100
    confidence: float = 0.9
    page: int = 0


@dataclass
class PositionExtractionResult:
    """Result from position-aware extraction."""

    fields: list[FieldWithPosition]
    page_dimensions: list[dict]  # [{width, height, page}, ...]


class VisionPositionExtractor:
    """Extract field values and positions from document images using Mistral Vision.

    This uses Mistral's pixtral-12b vision model to analyze form images and return
    both the extracted values AND their positions for text overlay.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the vision extractor.

        Args:
            api_key: Mistral API key. If None, reads from environment.
        """
        settings = get_settings()
        self._api_key = api_key or settings.mistral_api_key
        if not self._api_key:
            raise ValueError("Mistral API key is required for vision extraction")

        self._client = Mistral(api_key=self._api_key)
        self._model = "pixtral-12b-2409"
        logger.info("Initialized Mistral vision position extractor")

    async def extract_with_positions(
        self,
        images: list[bytes],
    ) -> PositionExtractionResult:
        """Extract fields with positions from document images.

        Args:
            images: List of image bytes (one per page)

        Returns:
            PositionExtractionResult with fields and their positions
        """
        if not images:
            return PositionExtractionResult(fields=[], page_dimensions=[])

        all_fields: list[FieldWithPosition] = []
        page_dimensions: list[dict] = []

        for page_idx, image_bytes in enumerate(images):
            logger.debug(f"Extracting positions from page {page_idx + 1}")

            # Get image dimensions
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            page_dimensions.append({"page": page_idx, "width": width, "height": height})

            # Create prompt
            prompt = get_position_extraction_prompt(width, height)

            # Detect image type for MIME
            img_format = img.format or "PNG"
            mime_type = f"image/{img_format.lower()}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"

            # Create base64 data URL
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_url = f"data:{mime_type};base64,{image_b64}"

            try:
                # Call Mistral Vision
                response = await self._client.chat.complete_async(
                    model=self._model,
                    messages=[
                        {
                            "role": "system",
                            "content": POSITION_EXTRACTION_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": image_url},
                                {"type": "text", "text": prompt},
                            ],
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=8192,
                )

                # Parse response
                response_text = response.choices[0].message.content if response.choices else "{}"
                response_text = self._clean_json(response_text or "{}")

                data = json.loads(response_text)
                fields_data = data.get("fields", [])

                for field in fields_data:
                    pos = field.get("position", {})
                    all_fields.append(
                        FieldWithPosition(
                            name=field.get("name", "unknown"),
                            value=field.get("value"),
                            x_percent=pos.get("x", 0),
                            y_percent=pos.get("y", 0),
                            width_percent=pos.get("width", 20),
                            height_percent=pos.get("height", 3),
                            confidence=field.get("confidence", 0.8),
                            page=page_idx,
                        )
                    )

            except Exception as e:
                logger.error(f"Failed to extract positions from page {page_idx}: {e}")

        logger.info(f"Extracted {len(all_fields)} fields with positions")
        return PositionExtractionResult(fields=all_fields, page_dimensions=page_dimensions)

    def _clean_json(self, text: str) -> str:
        """Clean JSON response of markdown formatting."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()


def convert_positions_to_points(
    fields: list[FieldWithPosition],
    page_dimensions: list[dict],
) -> list[dict]:
    """Convert percentage positions to PDF points.

    PDF uses points (1 point = 1/72 inch).
    Standard US Letter is 612 x 792 points.

    Args:
        fields: Fields with percentage positions
        page_dimensions: Page dimensions in pixels

    Returns:
        List of field position dicts with x, y in points
    """
    result = []

    for field in fields:
        if field.value is None:
            continue

        # Convert percentage to points (assuming standard letter size output)
        pdf_width = 612  # Standard letter width in points
        pdf_height = 792  # Standard letter height in points

        x_points = (field.x_percent / 100) * pdf_width
        y_points = (field.y_percent / 100) * pdf_height
        width_points = (field.width_percent / 100) * pdf_width
        height_points = (field.height_percent / 100) * pdf_height

        result.append(
            {
                "name": field.name,
                "value": field.value,
                "x": x_points,
                "y": y_points,
                "width": width_points,
                "height": height_points,
                "page": field.page,
                "font_size": 10,
            }
        )

    return result
