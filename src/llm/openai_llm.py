"""OpenAI LLM implementation for structured text parsing."""

import json

from openai import AsyncOpenAI

from src.config import get_settings
from src.llm.base import BaseLLM, LLMError, ParseResult
from src.llm.prompts import EXTRACTION_SYSTEM_PROMPT, get_extraction_prompt
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAILLM(BaseLLM):
    """LLM implementation using OpenAI GPT-4 for structured parsing.

    Reference:
        https://platform.openai.com/docs/guides/text-generation

    PHI Safety:
        - Does not log parsed data
        - API calls use HTTPS
        - No local caching of results
    """

    def __init__(self, api_key: str | None = None):
        """Initialize OpenAI LLM client.

        Args:
            api_key: OpenAI API key. If None, reads from environment.
        """
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        if not self._api_key:
            raise ValueError("OpenAI API key is required")

        self._client = AsyncOpenAI(api_key=self._api_key)
        self._model = "gpt-4o"
        logger.info("Initialized OpenAI LLM client")

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai"

    async def parse_to_json(
        self,
        ocr_text: str,
        field_hints: list[str] | None = None,
    ) -> ParseResult:
        """Parse OCR text into structured JSON using OpenAI GPT-4.

        Args:
            ocr_text: Raw text from OCR extraction
            field_hints: Optional list of expected field names

        Returns:
            ParseResult with structured data and confidences

        Raises:
            LLMError: If parsing fails
        """
        if not ocr_text or not ocr_text.strip():
            raise LLMError("Empty OCR text provided", self.provider_name)

        logger.info("Starting LLM parsing", text_length=len(ocr_text))

        try:
            # Generate extraction prompt
            prompt = get_extraction_prompt(ocr_text, field_hints)

            # Call OpenAI with JSON mode
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for accuracy
                max_tokens=8192,
            )

            # Parse JSON response
            response_text = response.choices[0].message.content
            if not response_text:
                raise LLMError("Empty response from OpenAI", self.provider_name)

            try:
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise LLMError(f"Invalid JSON response: {e}", self.provider_name)

            # Extract field confidences if present
            raw_confidences = parsed_data.pop("_field_confidences", {})
            field_confidences = self._normalize_confidences(raw_confidences)

            # Calculate overall confidence
            if field_confidences:
                overall_confidence = sum(field_confidences.values()) / len(field_confidences)
            else:
                # Estimate confidence based on data quality
                overall_confidence = self._estimate_confidence(parsed_data)

            logger.info(
                "LLM parsing complete",
                field_count=len(parsed_data),
                confidence=f"{overall_confidence:.2f}",
            )

            return ParseResult(
                data=parsed_data,
                field_confidences=field_confidences,
                overall_confidence=overall_confidence,
                metadata={
                    "model": self._model,
                    "provider": self.provider_name,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": (
                            response.usage.completion_tokens if response.usage else 0
                        ),
                    },
                },
            )

        except LLMError:
            raise
        except Exception as e:
            logger.error("LLM parsing failed", error=str(e))
            raise LLMError(f"Failed to parse text: {e}", self.provider_name) from e

    def _normalize_confidences(self, raw_confidences: dict) -> dict[str, float]:
        """Normalize confidence values to ensure they are floats.

        The LLM may return nested dicts or non-numeric values.
        This method flattens and normalizes them.

        Args:
            raw_confidences: Raw confidence dict from LLM

        Returns:
            Flat dict with float confidence values only
        """
        normalized = {}
        for key, value in raw_confidences.items():
            if isinstance(value, (int, float)):
                # Clamp to valid range
                normalized[key] = max(0.0, min(1.0, float(value)))
            elif isinstance(value, dict):
                # If nested, try to extract a 'confidence' or 'score' key
                if "confidence" in value and isinstance(value["confidence"], (int, float)):
                    normalized[key] = max(0.0, min(1.0, float(value["confidence"])))
                elif "score" in value and isinstance(value["score"], (int, float)):
                    normalized[key] = max(0.0, min(1.0, float(value["score"])))
                # Otherwise skip this field
            # Skip non-numeric, non-dict values
        return normalized

    def _estimate_confidence(self, data: dict) -> float:
        """Estimate confidence when not provided by model.

        Args:
            data: Parsed data dictionary

        Returns:
            Estimated confidence between 0.0 and 1.0
        """
        if not data:
            return 0.2

        # Count non-null values
        non_null_count = sum(1 for v in data.values() if v is not None)
        total_count = len(data)

        if total_count == 0:
            return 0.3

        # Base confidence on data completeness
        completeness = non_null_count / total_count
        return min(0.5 + (completeness * 0.4), 0.95)
